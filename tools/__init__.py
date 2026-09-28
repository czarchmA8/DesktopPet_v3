from pathlib import Path

PROJECT_DIR: Path = Path(__file__).resolve().parent.parent
"""Repository root during development. Not available/useful as a runtime concept in a packaged application."""
