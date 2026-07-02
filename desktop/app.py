import sys
import time
from PySide6 import QtWidgets, QtCore, QtGui
import logging
import os
import win32gui, win32con

import utils_debug
from logger_setup import setup_process_logger
from desktop.pet import PetWidget
from desktop.world_objects import WorldObjectsManager, WorldObject

logger: logging.Logger = None

class DesktopApp(QtWidgets.QApplication):
    '''Główny menedżer pętli odświeżania i okien na pulpicie'''
    def __init__(self, conn, shared_data, log_queue):
        super().__init__(sys.argv)

        self.conn = conn
        self.shared_data = shared_data
        self.log_queue = log_queue

        self.world_objects_manager = WorldObjectsManager(self.log_queue)
        self.pet = PetWidget(self.log_queue, shared_data, self.world_objects_manager.world_objects)
        self.pet.show()

        # Debugowanie
        self.process_timer = utils_debug.NamedStopwatch(update_rate_sec=1)
        self.debug_window = utils_debug.DebugWindow()
        self.hitbox_overlay = utils_debug.HitboxOverlay()
        self.debug_window.hide()
        self.hitbox_overlay.hide()
        self.update_debug_visibility()
        if self.shared_data.args.debug >= 2:
            self.debug_window.show()
            self.hitbox_overlay.show()

        # Timer / dt
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.timeout.connect(self.tick)
        self.refresh_timer.start(1000 // self.shared_data.settings["FPS"])
        self._last_tick_time = time.perf_counter()
        self.dt: float = 0.0

    def tick(self):
        self.process_timer.start("tick")
        # --- Obliczenie Delta Time ---
        now = time.perf_counter()
        self.dt = now - self._last_tick_time
        self._last_tick_time = now

        self.process_timer.start("pet tick")
        self.pet.tick(self.dt)
        self.process_timer.stop("pet tick")

        self.process_timer.start("check IPC")
        self._handle_ipc_commands()
        self.process_timer.stop("check IPC")

        self.process_timer.start("objects tick")
        self.world_objects_manager.tick(self.dt, self.pet.hwnd_self)
        self.process_timer.stop("objects tick")

        self.process_timer.start("debug tick")
        self.process_timer.start("show hitboxes")
        # --- Rysowanie hitboxów do debugowania ---
        if self.hitbox_overlay.isVisible():
            rect_objects: list = list({(obj.debug_expanded_platform_rect.as_tuple, (100, 255, 0, 180)) for obj in self.world_objects_manager.world_objects})
            polygons_objects: list[tuple[list[tuple[float | int, float | int]], tuple[int, int, int]]] = []
            for obj in self.world_objects_manager.world_objects:
                local_vertices: list[tuple[float | int, float | int]] = []
                for vertex in obj.shape.get_vertices():
                    world_pos = obj.body.local_to_world(vertex)
                    local_vertices.append((float(world_pos.x), float(world_pos.y)))
                polygons_objects.append((local_vertices, (255, 200, 200)))
            if self.hitbox_overlay is not None:
                self.hitbox_overlay.update_hitboxes(
                    [
                        (self.pet._debug_pet_foot_rect.as_tuple, (0, 255, 0, 180) if self.pet.on_window else (255, 0, 0, 180)),
                        (self.pet._debug_expanded_platform_rect.as_tuple, (0, 255, 0, 180) if self.pet.on_window else (255, 0, 0, 180))
                    ] + rect_objects,
                    [
                        # (self.animacje_hitbox[self.obecna_animacja].currentImage(), int(self.real_x), int(self.real_y))
                    ],
                    polygons_objects
                )
        self.process_timer.stop("show hitboxes")

        # --- Aktualizacja panelu debugowego ---
        self.process_timer.start("update debug window")
        self.process_timer.add_time("real fps", self.dt)
        if self.debug_window is not None and self.debug_window.isVisible():
            c = utils_debug.Color
            stringifyColors = c.StringifyColors()
            c_name = c(200, 200, 200)
            c_int = c(0, 200, 0)
            self.debug_window.update_debug(
                f'''{c_name}on_window_hwnd: {stringifyColors.stringify(self.pet.on_window_hwnd)}{c_name} ({win32gui.GetWindowText(self.pet.on_window_hwnd)})
{c_name}real_x: {stringifyColors.stringify(round(self.pet.real_x, 1))}
{c_name}real_y: {stringifyColors.stringify(round(self.pet.real_y, 1))}
{c_name}velocity_x: {stringifyColors.stringify(round(self.pet.velocity[0] * self.dt, 1))}
{c_name}velocity_y: {stringifyColors.stringify(round(self.pet.velocity[1] * self.dt, 1))}
{c_name}on_ground: {stringifyColors.stringify(self.pet.on_ground)}
{c_name}on_window: {stringifyColors.stringify(self.pet.on_window)}
{c_name}pet_foot_rect: {stringifyColors.stringify(self.pet._debug_pet_foot_rect)}
{c_name}platform_rect: {stringifyColors.stringify(self.pet._debug_window_rect)}
{c_name}expanded_platform_rect: {stringifyColors.stringify(self.pet._debug_expanded_platform_rect)}
{c_name}platform_expand: {stringifyColors.stringify((self.pet._debug_expanded_platform_rect.x2 - self.pet._debug_window_rect.x2, self.pet._debug_expanded_platform_rect.y2 - self.pet._debug_window_rect.y2))}
{c_name}platform_velocity_x: {stringifyColors.stringify(round(self.pet._debug_platform_vx))}
{c_name}platform_velocity_y": {stringifyColors.stringify(round(self.pet._debug_platform_vy))}
{"".join([f"{c_name}{name}: {c_int}{utils_debug.format_number(self.process_timer.get_avg_fps(name), f"{c(0, 150, 0)}'{c_int}")} {c(200, 255, 200)}FPS\n" for name in self.process_timer.get_timers()])}'''
            )
        self.process_timer.stop("update debug window")
        self.process_timer.stop("debug tick")

        self.process_timer.stop("tick")

    def update_debug_visibility(self):
        '''Updates visibility of debug overlays'''
        if self.shared_data.settings["debug"]["active"] and self.shared_data.settings["debug"]["hitbox_overlay"]: self.hitbox_overlay.show()
        else: self.hitbox_overlay.hide()
        if self.shared_data.settings["debug"]["active"] and self.shared_data.settings["debug"]["debug_window"]: self.debug_window.show()
        else: self.debug_window.hide()

    def _send_ipc_command(self, msg):
        '''Sends message to other processes'''
        if msg:
            logger.info(f"Sent IPC: {msg}")
            self.conn.send(msg)

    def _handle_ipc_commands(self):
        '''Checks messages from other processes'''
        if self.conn.poll():
            msg = self.conn.recv()
            logger.info(f"[Pet] Received IPC: {msg}")
            if msg[0] == "spawn_object":
                img_path = os.path.join("Assets", "Objects", msg[1])
                if not os.path.exists(img_path):
                    logger.error("[Obj] File not found:", img_path)

                x, y = win32gui.GetCursorPos()
                obj = WorldObject(self.shared_data, self.world_objects_manager.world_objects, self.world_objects_manager.space, img_path, x, y)
                self.world_objects_manager.world_objects.append(obj)
                obj.show()
            elif msg[0] == "clear_all_objects":
                for obj in list(self.world_objects_manager.world_objects):
                    self.world_objects_manager.space.remove(obj.platform_body, obj.platform_shape)
                    self.world_objects_manager.space.remove(obj.body, obj.shape)
                    obj.deleteLater()
                    obj.close()
                self.world_objects_manager.world_objects.clear()
            elif msg[0] == "toggle_debug":
                self.update_debug_visibility()
            elif msg[0] == "show_pet":
                self.pet.show()
            elif msg[0] == "hide_pet":
                self.pet.hide()
            elif msg[0] == "teleport_pet":
                size = self.pet.animations[self.pet.current_animation].frameRect().size()
                pos = QtGui.QCursor.pos()
                self.pet.velocity = [0, 0]
                self.pet.real_x, self.pet.real_y = pos.x() - size.width() // 2, pos.y() - size.height() // 2
                self.pet.is_dragging = False
            else:
                logger.error(f"Unknown command: {msg}")

def run_app(conn, shared_data, log_queue):
    global logger
    logger = setup_process_logger("desktop", log_queue)
    logger.info("Starting the DESKTOP process...")

    app = DesktopApp(conn, shared_data, log_queue)
    sys.exit(app.exec())
