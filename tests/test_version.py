import pytest
from datetime import datetime
import re

from config import APP_VERSION, APP_VERSION_DATE

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:\.dev\d+)?$")
DATE_FORMAT = "%Y.%m.%d, %H:%M"

def is_valid_version(version: str) -> bool:
    """Checks if a string matches the pattern 'X.Y.Z' or 'X.Y.Z.devN'."""
    return bool(VERSION_PATTERN.match(version))

def is_valid_date(date_str: str) -> bool:
    """Checks if the string is a valid date in the format 'yyyy.mm.dd, HH:MM'."""
    try:
        return datetime.strptime(date_str, DATE_FORMAT).strftime(DATE_FORMAT) == date_str
    except ValueError:
        return False

@pytest.mark.parametrize(
    "version_str, expected",
    [
        (APP_VERSION, True),
        ("1.2.3", True),
        ("0.0.1", True),
        ("10.20.30", True),
        ("1.2.3.dev0", True),
        ("1.2.3.dev4", True),
        ("1.2", False),
        ("1.2.3.4", False),
        ("1.2.3-dev4", False),
        ("1.2.3.dev", False),
        ("v1.2.3", False),
    ],
)
def test_version_format(version_str: str, expected: bool) -> None:
    assert is_valid_version(version_str) is expected, f"Failed for version: '{version_str}'"

@pytest.mark.parametrize(
    "date_str, expected",
    [
        (APP_VERSION_DATE, True),
        ("2026.08.27, 10:48", True),
        ("2024.01.01, 00:00", True),
        ("2026.8.27, 10:48", False),
        ("2026-08-27, 10:48", False),
        ("2026.08.27 10:48", False),
        ("2026.08.27, 24:00", False),
        ("2026.02.30, 10:48", False),
    ],
)
def test_version_date_format(date_str: str, expected: bool) -> None:
    assert is_valid_date(date_str) is expected, f"Failed for date: '{date_str}'"
