import os
import random
import time
from PySide6 import QtWidgets, QtCore, QtGui
import win32gui, win32con
import math
from dataclasses import dataclass
import logging

from windows_layer import get_immediate_neighbors_above_and_below as get_immediate_neighbors_above_and_below
from windows_layer import is_real_window as is_real_window
from logger_setup import setup_process_logger
from desktop.collisions import XYXY_Rectangle, XYWH_Rectangle, CollisionTypes, CustomHitboxCollisions

logger: logging.Logger = None

class PetWidget(QtWidgets.QWidget):
    '''Main pet character widget with physics and animation'''
    def __init__(self, log_queue, shared_data, world_objects: list):
        super().__init__()
        global logger
        logger = setup_process_logger("pet", log_queue)
        logger.info("Creating the PetWidget...")

        self.shared_data = shared_data
        self.world_objects = world_objects

        # Ustawianie atrybutów okna (tytuł, flagi itp.)
        self.setWindowTitle("Charmander")
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.hwnd_self = int(self.winId())
        logger.info(f"hwnd: {self.hwnd_self} ({win32gui.GetWindowText(self.hwnd_self)})")

        # Ładowanie animacji i hitboxu
        self.animations: dict = {}
        self.hitbox_animations: dict = {}
        for filename in os.listdir("Assets\\animations"):
            if filename.endswith("_hitbox.gif"):
                continue

            self.animations[filename] = QtGui.QMovie(f"Assets\\animations\\{filename}")
            self.animations[filename].setCacheMode(QtGui.QMovie.CacheMode.CacheAll)

            # base_name = os.path.splitext(plik)[0]
            # ext = os.path.splitext(plik)[1]
            # hitbox_file = f"{base_name}_hitbox{ext}"
            hitbox_file = filename

            self.hitbox_animations[filename] = QtGui.QMovie(f"Assets\\animations\\{hitbox_file}")
            self.hitbox_animations[filename].setCacheMode(QtGui.QMovie.CacheMode.CacheAll)

        # Ustawianie wagi zadań
        @dataclass
        class TaskContainer:
            weights: list[int]
            names: list[str]

        self.tasks = [(4, "Walking"), (2, "Standing"), (2, "Sitting"), (0, "Change window"), (1, "Sleeping")]
        weights: list[int] = [weight for weight, _ in self.tasks]
        names: list[str] = [task_name for _, task_name in self.tasks]
        self.tasks: TaskContainer = TaskContainer(weights, names)
        total_task_weight = sum(self.tasks.weights)
        logger.debug(f"Total task weight: {total_task_weight}")
        for weight, task_name in sorted(zip(self.tasks.weights, self.tasks.names)):
            logger.debug(f"{task_name}: {round(weight / total_task_weight * 100, 1)}%")

        self.current_task: str = "Falling"
        self.pet_label = QtWidgets.QLabel(self)
        self.current_animation: str = None
        self.orientation: str = "left"
        self.task_end_time: float = time.perf_counter()
        self.set_animation("left_falling.gif")

        # Stan okien / platformy
        self.on_window_hwnd: int = None
        self.old_on_window_hwnd: int = None
        self.old_window_rect: XYXY_Rectangle = None

        # Pasek zadań: ziemia ma być NAD paskiem zadań
        self.taskbar_y: int = QtWidgets.QApplication.primaryScreen().availableGeometry().bottom()

        # Ruch i fizyka
        self.velocity: list = [400.0, 0.0]
        self.mass = 1.0
        self.gravity = 2500.0
        self.drag_air_k = 0.0015
        self.mu_kinetic: float = 0.9
        self.mu_static: float = 1.5
        self.min_vx_threshold = 1.0
        self.restitution = 0.45

        self.is_dragging: bool = False
        self.real_x, self.real_y = self.x(), self.y()
        self.old_real_x, self.old_real_y = self.real_x, self.real_y
        self.on_ground: bool = False
        self.on_window: bool = False

        # Hitbox stóp (GIF 256x256)
        self.foot_x: int = 96
        self.foot_y: int = 176
        self.foot_width: int = 48

        # Pet współdzielone informacje
        self.shared_data.pet = {
            "hwnd": self.hwnd_self,
            "stats": {
                "fitness": 100,
                "friendship": 100,
                "happiness": 100,
                "comfort": 100,
                "hunger": 100,
                "thirst": 100,
                "energy": 100,
                "cleanliness": 100,
                "warmth": 100,
                "attention": 100,
                "playfulness": 100,
            }
        }

        self.dt = None

        # zmienne tylko do debugowania
        self._debug_expanded_platform_rect = None
        self._debug_pet_foot_rect = None
        self._debug_window_rect = None
        self._debug_platform_vx = None
        self._debug_platform_vy = None

    def tick(self, dt):
        self.dt = dt
        if self.on_window_hwnd is None or not is_real_window(self.on_window_hwnd): # Jeżeli okno nie istnieje
            above_rwindow_hwnd, below_rwindow_hwnd = get_immediate_neighbors_above_and_below(self.hwnd_self, True, [obj.hwnd_self for obj in self.world_objects])
            logger.debug(f"Set \"on_window_hwnd\" to {below_rwindow_hwnd} ({win32gui.GetWindowText(below_rwindow_hwnd)}) due to detection of non-existent window {self.on_window_hwnd}")
            self.on_window_hwnd = below_rwindow_hwnd
        else: # Jeżeli okno istnieje, ale na przykład zmieniło z-index
            above_rwindow_hwnd, below_rwindow_hwnd = get_immediate_neighbors_above_and_below(self.hwnd_self, True, [obj.hwnd_self for obj in self.world_objects] + [self.hwnd_self])
            if below_rwindow_hwnd != self.on_window_hwnd: # Zmień z-index zwierzątka tylko wtedy gdy `self.on_window_hwnd` zmieniło z-index
                above_window_hwnd, below_window_hwnd = get_immediate_neighbors_above_and_below(self.on_window_hwnd, False, [obj.hwnd_self for obj in self.world_objects] + [self.hwnd_self, self.on_window_hwnd])
                win32gui.SetWindowPos(self.hwnd_self, above_window_hwnd, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
                # logger.debug(f"Changed pet z-index")

        # --- Pobieranie pozycji i wymiarów platformy ---
        window_rect: tuple[int, int, int, int] = win32gui.GetWindowRect(self.on_window_hwnd) # (x, y, x2, y2)
        # --- Obliczanie hitboxu platformy ---
        window_rect: XYXY_Rectangle = XYXY_Rectangle(window_rect[0], window_rect[1], window_rect[2], window_rect[1]) # platforma o wysokości 1 pixela (y = y2)
        if self.old_window_rect is None or self.old_on_window_hwnd != self.on_window_hwnd:
            self.old_window_rect = window_rect
        expanded_platform_rect: XYXY_Rectangle = XYXY_Rectangle(
            min(window_rect.x, self.old_window_rect.x),
            min(window_rect.y, self.old_window_rect.y),
            max(window_rect.x2, self.old_window_rect.x2),
            max(window_rect.y2, self.old_window_rect.y2),
        )
        self._debug_expanded_platform_rect = expanded_platform_rect

        # --- Fizyka platformy ---
        platform_dx = window_rect.x - self.old_window_rect.x
        platform_dy = window_rect.y2 - self.old_window_rect.y2
        platform_vx = platform_dx / dt
        platform_vy = platform_dy / dt
        self._debug_window_rect = window_rect
        self._debug_platform_vx = platform_vx
        self._debug_platform_vy =  platform_vy

        # --- Obliczanie fizyki (tarcia i grawitacji) ---
        if self.is_dragging == False:
            self.velocity[1] = self.velocity[1] + self.gravity * dt
            ax_drag = -self.drag_air_k * self.velocity[0] * abs(self.velocity[0]) / self.mass
            ay_drag = -self.drag_air_k * self.velocity[1] * abs(self.velocity[1]) / self.mass
            self.velocity[0] += ax_drag * dt
            if self.on_ground:
                if abs(self.velocity[0]) < self.min_vx_threshold:
                    self.velocity[0] = 0.0
                dv = self.mu_static * self.gravity * dt
                if dv >= abs(self.velocity[0]):
                    self.velocity[0] -= self.velocity[0]
                else:
                    self.velocity[0] -= (dv * (1 if self.velocity[0] > 0 else -1))
            self.velocity[1] += ay_drag * dt

        # System zadań i zachowań
        if self.on_ground or self.on_window:
            # Ustawianie zadania
            if time.perf_counter() - self.task_end_time > 0:
                # Ustawianie zadań priorytetowych
                screen_geo = QtWidgets.QApplication.primaryScreen().virtualGeometry()
                size = self.animations[self.current_animation].frameRect().size()
                if self.real_x < screen_geo.left() - size.width() // 2:
                    self.current_task = "Walking"
                    self.task_end_time = time.perf_counter() + random.randint(5, 10)
                    self.orientation = "right"
                    self.set_animation(f"{self.orientation}_walking.gif")
                elif self.real_x > screen_geo.right() - size.width() // 2:
                    self.current_task = "Walking"
                    self.task_end_time = time.perf_counter() + random.randint(5, 10)
                    self.orientation = "left"
                    self.set_animation(f"{self.orientation}_walking.gif")
                else:
                    # Szansa na zmiane kierunku
                    r = random.randint(0, 100)
                    if r <= 25:
                        self.orientation = "right" if self.orientation == "left" else "left"

                    # Ustawianie zadań nie priorytetowych
                    task = random.choices(self.tasks.names, self.tasks.weights)[0]
                    if task == "Standing":
                        self.current_task = "Standing"
                        self.task_end_time = time.perf_counter() + random.randint(5, 10)
                        self.set_animation(f"{self.orientation}.gif")
                    elif task == "Sleeping":
                        self.current_task = "Sleeping"
                        self.task_end_time = time.perf_counter() + random.randint(60, 120)
                        self.set_animation(f"{self.orientation}_sleeping.gif")
                    elif task == "Sitting":
                        self.current_task = "Sitting"
                        self.task_end_time = time.perf_counter() + random.randint(10, 20)
                        self.set_animation(f"{self.orientation}_sitting.gif")
                    elif task == "Walking":
                        self.current_task = "Walking"
                        self.task_end_time = time.perf_counter() + random.randint(5, 10)
                        self.set_animation(f"{self.orientation}_walking.gif")
                    else:
                        raise Exception("Error: No task was set. This should not happen!")

            # Wykonywanie zadania
            if self.current_task == "Walking":
                if self.orientation == "left":
                    self.real_x -= 50 * dt
                elif self.orientation == "right":
                    self.real_x += 50 * dt
        else:
            self.current_task = "Falling"
            self.task_end_time = time.perf_counter() + 0.1
            self.set_animation(f"{self.orientation}_falling.gif")

        # --- Zapisywanie starej pozycji zwierzątka ---
        self.old_window_rect = window_rect
        self.old_real_x, self.old_real_y = self.real_x, self.real_y
        self.old_on_window_hwnd = self.on_window_hwnd

        # --- Aktualizowanie wyświetlanej pozycji zwierzątka ---
        if self.is_dragging == False:
            self.real_x += self.velocity[0] * dt
            self.real_y += self.velocity[1] * dt

        # self.move(round(self.real_x), round(self.real_y))

        if self.is_dragging == False:
            # --- Obliczanie hitboxu stóp zwierzątka ---
            pet_foot_rect: XYWH_Rectangle = XYWH_Rectangle(
                self.real_x + self.foot_x,
                self.real_y + self.foot_y,
                self.real_x + self.foot_x + self.foot_width,
                self.real_y + self.foot_y
            )
            pet_foot_rect = XYWH_Rectangle(
                int(min(pet_foot_rect.x, pet_foot_rect.x + self.velocity[0] * dt)),
                int(min(pet_foot_rect.y, pet_foot_rect.y - self.velocity[1] * dt)),
                math.ceil(max(pet_foot_rect.width, pet_foot_rect.width + self.velocity[0] * dt)),
                math.ceil(max(pet_foot_rect.height, pet_foot_rect.height + self.velocity[1] * dt))
            )
            self._debug_pet_foot_rect = pet_foot_rect

            if CustomHitboxCollisions.check_rect_hitbox_collision(pet_foot_rect, expanded_platform_rect):
                if self.velocity[1] - platform_vy > 0:
                    self.velocity[1] = -(self.velocity[1] - platform_vy) * self.restitution
                    self.real_y = window_rect.y2 - self.foot_y
                    # self.move(round(self.real_x), round(self.real_y))
                if platform_vy < 0.0:
                    self.velocity[1] = platform_vy

                v_rel = self.velocity[0] - platform_vx
                max_dv_friction = self.mu_kinetic * self.gravity * dt
                impulse_gain = 0.25
                max_dv_impulse = abs(platform_vx) * impulse_gain
                max_dv = max(max_dv_friction, max_dv_impulse)
                static_threshold = self.mu_static * self.gravity * dt
                if abs(v_rel) <= static_threshold:
                    self.velocity[0] = platform_vx
                else:
                    dv = math.copysign(min(abs(v_rel), max_dv), v_rel)
                    new_v_rel = v_rel - dv
                    self.velocity[0] = platform_vx + new_v_rel

                self.on_window = True
            else:
                self.on_window = False

            # --- Fizyka ziemi ---
            if self.real_y >= self.taskbar_y - self.foot_y:
                self.real_y = self.taskbar_y - self.foot_y
                if self.velocity[1] > 0:
                    self.velocity[1] = -self.velocity[1] * self.restitution
                # self.move(round(self.real_x), round(self.real_y))
                self.on_ground = True
            else:
                self.on_ground = False
        else:
            self.on_window = False
            self.on_ground = False

        self.move(round(self.real_x), round(self.real_y))

    def compute_launch_velocity(self, target_x: int, target_y: int) -> tuple[float, float]:
        '''Calculates velocity needed to reach target position'''
        start_x, start_y = self.real_x, self.real_y

        # Przesunięcie do celu
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy)

        T = max(0.5, min(dist / 700.0, 2.5))

        g = self.gravity
        vx = dx / T
        vy = (dy - 0.5 * g * T ** 2) / T

        dt_sim = 0.016

        for _ in range(12):
            sim_x, sim_y = start_x, start_y
            sim_vx, sim_vy = vx, vy
            t = 0.0

            while t < T:
                sim_vy += g * dt_sim

                ax_drag = -self.drag_air_k * sim_vx * abs(sim_vx) / self.mass
                ay_drag = -self.drag_air_k * sim_vy * abs(sim_vy) / self.mass

                sim_vx += ax_drag * dt_sim
                sim_vy += ay_drag * dt_sim

                sim_x += sim_vx * dt_sim
                sim_y += sim_vy * dt_sim

                t += dt_sim

            error_x = target_x - sim_x
            error_y = target_y - sim_y

            if abs(error_x) < 2 and abs(error_y) < 2:
                break

            vx += (error_x / T) * 1.1
            vy += (error_y / T) * 1.1

        return (vx, vy)

    def keyPressEvent(self, event): # Tymczasowa funkcja do debugowania i testowania
        '''Temporary function for debugging and testing'''
        if event.key() == QtCore.Qt.Key.Key_Space:
            self.real_x, self.real_y = 800 , 200
            self.velocity: list = [400.0, -800.0]
        elif event.key() == QtCore.Qt.Key.Key_1:
            self.velocity = list(self.compute_launch_velocity(0, self.taskbar_y))
        elif event.key() == QtCore.Qt.Key.Key_Up:
            self.on_window_hwnd = get_immediate_neighbors_above_and_below(self.shared_data.pet["hwnd"], True, [obj.hwnd_self for obj in self.world_objects])[0]
            logger.debug(f"Set \"on_window_hwnd\" to {self.on_window_hwnd} ({win32gui.GetWindowText(self.on_window_hwnd)})")
        elif event.key() == QtCore.Qt.Key.Key_Down:
            self.on_window_hwnd = get_immediate_neighbors_above_and_below(self.shared_data.pet["hwnd"], True, [obj.hwnd_self for obj in self.world_objects] + [self.on_window_hwnd])[1]
            logger.debug(f"Set \"on_window_hwnd\" to {self.on_window_hwnd} ({win32gui.GetWindowText(self.on_window_hwnd)})")
        else:
            super().keyPressEvent(event)

    def set_animation(self, animation):
        '''Sets and starts a new animation'''
        if animation != self.current_animation:
            # Zatrzymanie poprzednich animacji
            if self.current_animation:
                self.animations[self.current_animation].stop()
                self.hitbox_animations[self.current_animation].stop()

            #Ustawienie i start nowej animacji
            self.pet_label.setMovie(self.animations[animation])
            self.animations[animation].start()
            # Ustawienie i start nowej maski hitboxa
            self.hitbox_animations[animation].start()
            self.hitbox_animations[animation].jumpToFrame(0)

            self.pet_label.resize(self.animations[animation].frameRect().size())
            self.resize(self.animations[animation].frameRect().size())
            self.current_animation = animation

    def mousePressEvent(self, event):
        self.is_dragging = True
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self.velocity = [0, 0]

    def mouseMoveEvent(self, event):
        pos = event.globalPosition().toPoint() - self._drag_pos
        self.real_x, self.real_y = pos.x(), pos.y()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.velocity = [
            (self.real_x - self.old_real_x) / self.dt,
            (self.real_y - self.old_real_y) / self.dt
        ]
