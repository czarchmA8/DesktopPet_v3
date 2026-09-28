import sys
from pathlib import Path
import json

APP_NAME: str = "DesktopPet_v3"
APP_AUTHOR: str = "czarchmA8"
REPO_NAME: str = "DesktopPet_v3"
"""The name of the github repository where this project is located"""
RESOURCE_DIR: Path
"""Path to resources packed inside .exe (read-only e.g. translations/defaults)"""
APP_DIR: Path
"""Path to the directory where the .exe file is located (for saving logs/database/settings where the user has access)"""

if getattr(sys, 'frozen', False):
    RESOURCE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    APP_DIR = Path(sys.executable).parent
else:
    RESOURCE_DIR = Path(__file__).resolve().parent
    APP_DIR = RESOURCE_DIR

_version_data: dict = json.loads((RESOURCE_DIR / "version.json").read_text(encoding="utf-8"))
APP_VERSION: str = _version_data["APP_VERSION"]
"""format: 'x.y.z' or 'x.y.z.dev0', for example: '2.4.3.dev5'"""
APP_VERSION_DATE: str = _version_data["APP_VERSION_DATE"]
"""format: 'yyyy.mm.dd, HH:MM', for example: '2023.05.07, 13:15'"""
