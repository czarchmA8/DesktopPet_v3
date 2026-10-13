from multiprocessing import Process, Pipe, Manager, Queue
import sys
import traceback
import json
import argparse
import time

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtCore import Qt, QUrl
from PySide6.QtCore import QTimer

import app.config as config
from app.settings import load_settings
import app.logger as logger
from app.log_console import LogWindow
from app.ipc import IpcChannel, SharedState
from app.desktop.overlay_manager import run_app as run_app_desktop
from app.dashboard.dashboard import run_app as run_app_dashboard

def except_hook(cls, exception, traceback_obj) -> None:
    """Global exception hook for uncaught exceptions"""
    sys.__excepthook__(cls, exception, traceback_obj)

def safe_run(run_func, process_name: str, conn, shared_data, error_queue, log_queue, *extra) -> None:
    """Safely runs a process function with exception handling"""
    def child_except_hook(cls, exception, traceback_obj):
        error_msg = f"{process_name} PROCESS ERROR:\n{''.join(traceback.format_exception(cls, exception, traceback_obj))}"
        error_queue.put(error_msg)
        # sys.__excepthook__(cls, exception, traceback_obj)
        sys.exit(1)

    sys.excepthook = child_except_hook
    try:
        run_func(conn, shared_data, log_queue, *extra)
    except Exception:
        error_msg = f"{process_name} PROCESS ERROR:\n{traceback.format_exc()}"
        error_queue.put(error_msg)
        # print(error_msg)

def show_error_msg_box(error_msg) -> None:
    """Displays an error message dialog box"""
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

def run_processes(shared_data: SharedState, error_queue, log_queue, app, ctl_dash) -> str | None:
    """Starts the DESKTOP and DASHBOARD processes and monitors them until both terminate. Returns an error message (if any) or None."""
    log = logger.get_logger("main")
    ipc_desktop, ipc_dash = Pipe()

    p1 = Process(target=safe_run, args=(run_app_desktop, "DESKTOP", ipc_desktop, shared_data, error_queue, log_queue), name="DESKTOP")
    p2 = Process(target=safe_run, args=(run_app_dashboard, "DASHBOARD", ipc_dash, shared_data, error_queue, log_queue, ctl_dash), name="DASHBOARD")
    processes = [p1, p2]
    error_msg: str | None = None

    def supervise() -> None:
        nonlocal error_msg

        if not error_queue.empty():
            error_msg = error_queue.get()
            log.critical(f"\n[❌] {error_msg}\n")
            app.exit()
            return
        alive = [p.is_alive() for p in processes]
        if all(alive):
            return
        for p in processes:
            if not p.is_alive() and p.exitcode != 0:
                error_msg = f"{p.name} process exited with error code: {p.exitcode}"
        app.exit()

    timer = QTimer()
    timer.timeout.connect(supervise)
    try:
        for p in processes:
            p.start()
        log.info("[✅] Both processes started")
        timer.start(200)
        app.exec()
    except KeyboardInterrupt:
        log.error("[⚠️] User interruption")
    except Exception:
        log.exception("[❌] Unexpected critical error in main loop")
    finally:
        timer.stop()
        if error_msg is None:
            deadline = time.monotonic() + 3
            for p in processes:
                p.join(timeout=max(0, deadline - time.monotonic()))
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

    return error_msg

def main() -> None:
    """Main entry point of the application"""
    sys.excepthook = except_hook
    error_queue: Queue = Queue()

    settings = load_settings()

    # Handling arguments passed from the command line
    parser = argparse.ArgumentParser(description="DesktopPet_v3")
    parser.add_argument("--debug", "-D", type=int, help="Debug level 0-2", required=False, default=0, choices=[0, 1, 2])
    parser.add_argument("--autostart", action="store_true", help="Indicates the app was launched by autostart", required=False)
    args = parser.parse_args()

    logger.init(
        file_name="main",
        max_old_logs=settings["debug"]["delete_logs_older_than"]
    )
    log = logger.get_logger("main")
    log.debug(f"Args: {args}")
    log.info(f"APP_NAME: \"{config.APP_NAME}\"")
    log.info(F"APP_DIR: \"{config.APP_DIR}\"")
    log.info(f'RESOURCE_DIR: "{config.RESOURCE_DIR}"')
    log.info(f"APP_VERSION: \"{config.APP_VERSION}\"")
    log.info(f"APP_VERSION_DATE: \"{config.APP_VERSION_DATE}\"")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    ctl_main_conn, ctl_dash = Pipe()
    ctl = IpcChannel(ctl_main_conn, "CTL", "DASHBOARD", log)

    error_msg: str | None = None

    with Manager() as manager:
        shared_data = SharedState(manager)
        shared_data.args = args
        shared_data.settings = settings
        shared_data.restarted = False

        log_queue = logger.get_queue()
        
        console = LogWindow(logger.get_gui_queue(), shared_data)
        console.visibility_changed.connect(lambda v: ctl.send(["console_visibility_changed", v]))

        def _handle_ctl_commands() -> None:
            for msg in ctl.receive():
                if msg[0] == "set_console_visibility":
                    console.setVisible(msg[1])
                else:
                    ctl.unknown(msg)

        ctl_timer = QTimer()
        ctl_timer.timeout.connect(_handle_ctl_commands)
        ctl_timer.start(100)

        while True:
            shared_data.active_mods = {}
            shared_data.spawnable_entities = {}
            shared_data.displayed_entities = {}
            shared_data.restart_requested = False
            shared_data.selected_entity_instance_id = None
            shared_data.selected_entity_details = {}

            ctl.send(["console_visibility_changed", console.isVisible()])
            error_msg = run_processes(shared_data, error_queue, log_queue, app, ctl_dash)

            shared_data.pull() # Update changes
            if error_msg is not None or not shared_data.restart_requested:
                break

            shared_data.restarted = True
            log.info("[🔄] Restarting application...")

        if error_msg is not None:
            if shared_data.settings["active_mods"]:
                shared_data.settings["saved_mods_list"]["ERROR"] = shared_data.settings["active_mods"]
                shared_data.settings["active_mods"] = []
                log.info('Saved active mod list to mod list with name "ERROR" in settings.')
            else:
                log.info('Due to the empty list of active mods, saving the list under the name "ERROR" in settings was omitted.')

        console.save_state_to_settings()
        
        try:
            settings_file_path = config.APP_DIR / "settings.json"
            settings_file_path.write_text(json.dumps(shared_data.settings, indent=4, ensure_ascii=False), encoding="utf-8")
            log.info('Saved "settings.json".')
        except Exception as e:
            log.exception(f'Failed to save "settings.json". Error: {e}')
        
        if error_msg is not None:
            show_error_msg_box(error_msg)

        logger.stop()

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
