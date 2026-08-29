import sys
from pathlib import Path

APP_VERSION: str = "0.0.0.dev0"
APP_VERSION_DATE: str = "2026.08.27, 12:00"
APP_NAME: str = "DesktopPet_v3"
APP_AUTHOR: str = "czarchmA8"
REPO_NAME: str = "DesktopPet_v3"

if getattr(sys, 'frozen', False):
    # Path to resources packed inside .exe (read-only e.g. translations/defaults)
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    # Path to the directory where the .exe file is located (for saving logs/database/settings where the user has access)
    APP_DIR = Path(sys.executable).parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    APP_DIR = RESOURCE_DIR
