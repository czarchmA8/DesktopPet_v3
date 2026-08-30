from multiprocessing import Process, Pipe, Manager, Queue
import sys
import traceback
import json
import argparse
import shutil

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import Qt, QUrl

import config
import logger
from desktop.entities_manager import run_app as run_app_desktop
from dashboard.dashboard import run_app as run_app_dashboard

def except_hook(cls, exception, traceback_obj) -> None:
    """Global exception hook for uncaught exceptions"""
    sys.__excepthook__(cls, exception, traceback_obj)

def safe_run(run_func, process_name: str, conn, shared_data, error_queue, log_queue) -> None:
    """Safely runs a process function with exception handling"""
    def child_except_hook(cls, exception, traceback_obj):
        error_msg = f"{process_name} PROCESS ERROR:\n{''.join(traceback.format_exception(cls, exception, traceback_obj))}"
        error_queue.put(error_msg)
        # sys.__excepthook__(cls, exception, traceback_obj)
        sys.exit(1)

    sys.excepthook = child_except_hook
    try:
        run_func(conn, shared_data, log_queue)
    except Exception:
        error_msg = f"{process_name} PROCESS ERROR:\n{traceback.format_exc()}"
        error_queue.put(error_msg)
        # print(error_msg)

def show_error_msg_box(error_msg) -> None:
    """Displays an error message dialog box"""
    QApplication(sys.argv)

    msg_box = QMessageBox()
    msg_box.setWindowTitle(f"{config.APP_NAME} - Critical Error")
    msg_box.setWindowIcon(QIcon(str(config.RESOURCE_DIR / "icon.ico")))
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setText("An error occurred in the child process!")
    msg_box.setInformativeText("To view the full error log, click 'Show Details...' below.")
    msg_box.setDetailedText(error_msg)

    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    open_folder_btn = msg_box.addButton("Open crash log folder", QMessageBox.ButtonRole.ActionRole)

    msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    msg_box.show()
    msg_box.setWindowFlags(msg_box.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
    msg_box.show()

    msg_box.raise_()
    msg_box.activateWindow()

    msg_box.exec()

    if msg_box.clickedButton() == open_folder_btn:
        log_dir = str(config.APP_DIR / "logs")
        QDesktopServices.openUrl(QUrl.fromLocalFile(log_dir))

def deep_fill_defaults(settings: dict, default_settings: dict) -> dict:
    for key, value in default_settings.items():
        if key not in settings:
            settings[key] = value
        elif isinstance(settings[key], dict) and isinstance(value, dict):
            deep_fill_defaults(settings[key], value)
    return settings

def load_settings() -> dict:
    settings_file = config.APP_DIR / "settings.json"
    default_settings_file = config.RESOURCE_DIR / "settings.default.json"
    if settings_file.exists():
        with open(default_settings_file, "r", encoding="utf-8") as f:
            default_settings = json.load(f)

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        return deep_fill_defaults(settings, default_settings)
    else:
        shutil.copy(default_settings_file, settings_file)
        print("🔄 Created a local \"settings.json\" file from the defaults.")

        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)

        return settings

def main() -> None:
    """Main entry point of the application"""
    sys.excepthook = except_hook
    # Połączenie pomiędzy procesami
    conn1, conn2 = Pipe()
    error_queue: Queue = Queue()

    settings = load_settings()

    # Obsługa argumentów przekazywanych z linii komend
    parser = argparse.ArgumentParser(description="DesktopPet_v3")
    parser.add_argument("--debug", "-D", type=int, help="Debug level 0-2", required=False, default=0, choices=[0, 1, 2])
    args = parser.parse_args()

    logger.init(file_name="main", debug=False if args.debug == 0 else True, max_old_logs=settings["debug"]["delete_logs_older_than"])
    log = logger.get_logger("main")

    error_msg = None

    with Manager() as manager:
        shared_data = manager.Namespace()
        shared_data.args = args
        shared_data.settings = settings
        shared_data.mods = {}
        shared_data.entities = {}

        log_queue = logger.get_queue()
        p1 = Process(target=safe_run, args=(run_app_desktop, "PET", conn1, shared_data, error_queue, log_queue), name="PET")
        p2 = Process(target=safe_run, args=(run_app_dashboard, "DASHBOARD", conn2, shared_data, error_queue, log_queue), name="DASHBOARD")
        processes = [p1, p2]

        try:
            p1.start()
            p2.start()
            log.info("[✅] Both processes started")

            # Monitoruj procesy i błędy
            while True:
                # Sprawdź czy jest błąd w queue
                if not error_queue.empty():
                    error_msg = error_queue.get()
                    log.critical(f"\n[❌] {error_msg}\n")
                    log.critical("[⚠️] Error caught, closing application...")
                    break

                p1_alive = p1.is_alive()
                p2_alive = p2.is_alive()
                # Jeśli jeden proces się zakończył, drugi powinien się też zamknąć
                if not p1_alive and p2_alive:
                    log.info(f"[⚠️] DESKTOP process ended (exit code: {p1.exitcode}), closing DASHBOARD...")
                    if p1.exitcode != 0:
                        error_msg = f"DESKTOP process exited with error code: {p1.exitcode}"
                    break
                if not p2_alive and p1_alive:
                    log.info(f"[⚠️] DASHBOARD process ended (exit code: {p2.exitcode}), closing DESKTOP...")
                    if p2.exitcode != 0:
                        error_msg = f"DASHBOARD process exited with error code: {p2.exitcode}"
                    break

                # Jeśli oba się skończyły normalnie
                if not p1_alive and not p2_alive:
                    log.info("[✅] Both processes ended normally")
                    break

                # Czekaj krótko przed następnym sprawdzeniem
                p1.join(timeout=0.1)
                p2.join(timeout=0.1)

        except KeyboardInterrupt:
            log.error("[⚠️] User interruption")
        except Exception:
            log.exception("[❌] Unexpected critical error in main loop")
        finally:
            for p in processes:
                if p.is_alive():
                    log.warning(f"[⚠️] Terminating process {p.name}...")
                    p.terminate()
                    p.join(timeout=2)
                    if p.is_alive():
                        log.error(f"[⚠️]️ Force killing process {p.name}")
                        p.kill()
                    p.join()
            log.info("[✅] All processes closed")

            if error_msg is not None:
                show_error_msg_box(error_msg)

            logger.stop()

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
