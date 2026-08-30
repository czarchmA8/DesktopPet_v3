import logging
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from datetime import datetime
import multiprocessing
import atexit

import config

_log_queue: "multiprocessing.Queue" = multiprocessing.Queue()
_listener = None

class ColorFormatter(logging.Formatter):
    """Formatter with ANSI colors for console"""

    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[92m',  # Light Green
        'WARNING': '\033[93m',  # Light Yellow
        'ERROR': '\033[91m',  # Light Red
        'CRITICAL': '\033[41m\033[97m',  # Red bg + White text
    }
    RESET = '\033[0m'

    def format(self, record):
        levelname = record.levelname
        orig_levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{f'[{levelname}]':10s}{self.RESET}"
        result = super().format(record)
        record.levelname = orig_levelname

        return result

class PlainFormatter(logging.Formatter):
    """Formatter without ANSI colors"""

    def format(self, record):
        # Zwykły format bez kolorów
        return super().format(record)

def _clean_old_logs(logs_folder: Path, prefiks: str, logger, max_old_logs: int = 3) -> None:
    """Deletes old log files, keeping only a specified number of the most recent ones"""
    if not logs_folder.exists():
        return

    # Znajdź wszystkie pliki logów z danym prefiksem
    log_files = sorted(
        logs_folder.glob(f"{prefiks}_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True  # Najnowsze pierwsze
    )

    # Usuń pliki starsze niż top N
    for file_to_delete in log_files[max_old_logs:]:
        try:
            file_to_delete.unlink()
            logger.debug(f"Old log file deleted: \"{file_to_delete.name}\"")
        except Exception as e:
            logger.warning(f"Failed to delete \"{file_to_delete.name}\": {e}")

def stop():
    """Closes the listener and flushes the remaining logs from the queue."""
    global _listener
    if _listener is not None:
        _listener.stop()
        _listener = None

def init(file_name: str="main", debug=False, max_old_logs: int=3) -> None:
    global _listener
    if _listener is not None:
        return

    logs_folder = config.APP_DIR / "logs"
    logs_folder.mkdir(exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = logs_folder / f"{file_name}_{now}.log"

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(ColorFormatter(fmt="%(levelname)s [%(name)s]: %(message)s"))

    file_handler = logging.FileHandler(file_path, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        PlainFormatter(
            fmt="[%(asctime)s]-[%(levelname)s]-(%(filename)s:%(lineno)d) -> %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    _listener = QueueListener(_log_queue, console_handler, file_handler, respect_handler_level=True)
    _listener.start()
    atexit.register(stop)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(QueueHandler(_log_queue))

    sys_logger = get_logger("logger_setup")
    sys_logger.info("[✅] Started central logging system")
    _clean_old_logs(logs_folder, file_name, sys_logger, max_old_logs)

def get_queue() -> "multiprocessing.Queue":
    """Returns the shared multiprocessing queue used for logging."""
    return _log_queue

def init_child(log_queue: "multiprocessing.Queue") -> None:
    """Attaches a QueueHandler to the root logger in a child process."""
    global _log_queue
    _log_queue = log_queue

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(QueueHandler(_log_queue))

def get_logger(logger_name: str | None) -> logging.Logger:
    """Returns a logger for the given name."""
    return logging.getLogger(logger_name if logger_name else __name__)
