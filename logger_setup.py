import logging
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from datetime import datetime

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

def setup_main_listener(file_name: str, queue, debug=False, max_old_logs: int=3) -> QueueListener:
    '''Sets up the main logging listener with queue support'''
    logs_folder = Path("logs")
    if not logs_folder.exists():
        logs_folder.mkdir()

    # Tworzenie nazwy pliku z datą i czasem
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename_with_datetime = f"{file_name}_{now}.log"
    file_path = logs_folder / filename_with_datetime

    # Handler konsoli (z kolorami)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

    console_formatter = ColorFormatter(fmt="%(levelname)s [%(name)s]: %(message)s")
    console_handler.setFormatter(console_formatter)

    # Handler pliku (bez kolorów)
    file_handler = logging.FileHandler(
        file_path,
        mode="w",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    file_formatter = PlainFormatter(
        fmt="[%(asctime)s]-[%(levelname)s]-(%(filename)s:%(lineno)d) -> %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    listener = QueueListener(queue, console_handler, file_handler, respect_handler_level=True)

    # Czyszczenie starych plików logów
    logger = setup_process_logger("logger_setup", queue)
    logger.info("[✅] Started central logging system")
    _clean_old_logs(logs_folder, file_name, logger, max_old_logs)

    return listener

def setup_process_logger(logger_name: str, queue) -> logging.Logger:
    '''Configures a process-specific logger with queue handler'''
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    queue_handler = QueueHandler(queue)
    logger.addHandler(queue_handler)

    return logger
