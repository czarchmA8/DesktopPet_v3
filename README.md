<div align="center">

# DesktopPet_v3

![Python](https://img.shields.io/badge/python-3.13-3776ab?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows%2011-0078d4)
[![GitHub release](https://img.shields.io/github/v/release/czarchmA8/DesktopPet_v3)](https://github.com/czarchmA8/DesktopPet_v3/releases)
![status](https://img.shields.io/badge/status-in%20development-yellow)
[![LICENSE](https://img.shields.io/github/license/czarchmA8/DesktopPet_v3)](./LICENSE.txt)

[Download](#download) · [Modding](#modding) · [Documentation](docs/README.md) · [Report a bug](https://github.com/czarchmA8/DesktopPet_v3/issues)

<img width="100%" alt="DesktopPet_v3 banner" src="https://github.com/user-attachments/assets/2b336819-59cc-42f9-924e-b669a19ffa67" />

</div>

## About

DesktopPet_v3 is a Python application that draws animated characters and objects directly on your desktop. Everything is
drawn on transparent overlay layers placed at the right spot of the Windows z-order, and the behavior of every entity is
defined by mods written in Python or Lua.

> [!WARNING]
> Development is still in progress. Bugs may occur and the mod API may still change.

## 📸 Preview

<div align="center">
  <img width="800" height="450" alt="2026-06-22 18-40-51" src="https://github.com/user-attachments/assets/74f2b2ec-055e-4af8-a9c6-826a366df9b3" />
  <img width="854" height="480" alt="2026-07-21 13-10-42" src="https://github.com/user-attachments/assets/4c0af889-84c4-46f5-ad65-d47d22764a54" />
  <video src="https://github.com/user-attachments/assets/6198545f-e84f-4092-84f9-3ae283c6f808" width="1220" controls></video>
</div>

## Key Features

- Animated GIF-based character with multiple states (walking, sitting, sleeping, falling)
- Physics-driven movement — gravity, collisions, inertia
- Mouse interactions — catch, drag, throw
- Follows the active window around the desktop
- Windows are treated as platforms for the pet and world objects to stand on
- Dynamic window layering — the pet decides on its own when to bring itself to the front, not strictly tied to the currently active window
- Interactive objects (balls, food) with collisions between pet and objects, and object-to-object
- Stats system — happiness, health, hunger, sleepiness, shifting with interaction
- Control panel for hotkeys, sound volume, FPS, debug level, and multi-language translations
- Objects Editor — create and edit object hitboxes and physics properties from the control panel
- Multi-process logging — colored console output, file logs, automatic cleanup
- Debug mode with hitbox/collision overlay and live state panel
- Mod system with Lua (sandboxed) and Python scripting.
- Update checker with in-app notification dialog

---

## Download

> [!NOTE]
> Works only on Windows (for now). Mac and Linux may come later!

**Requirements:** Python 3.13 and Windows 11.

### Run from source

1. **Clone the repository**
   ```bash
   git clone https://github.com/czarchmA8/DesktopPet_v3.git
   cd DesktopPet_v3
   ```
   No Git? [Download ZIP](https://github.com/czarchmA8/DesktopPet_v3/archive/refs/heads/master.zip) and extract it
   instead.

2. **Install `uv`** (if you don't have it yet)
   ```bash
   winget install --id=astral-sh.uv -e
   ```

3. **Install dependencies**
   ```bash
   uv sync --group dev
   ```

4. **Compile translations**
    ```bash
    uv run tools/update_languages.py
    ```

5. **Run application**
    ```bash
    uv run main.py
    ```

### Launch Options with Arguments

The application supports the following command-line parameters:

| Argument      | Short | Description                                                            | Default |
|---------------|-------|------------------------------------------------------------------------|---------|
| `--debug`     | `-D`  | Debug level 0-2 (0 = disabled)                                         | `0`     |
| `--autostart` |       | Flag used internally by the autostart entry, you don't need to pass it | off     |

```bash
uv run main.py --debug 2
```

### Creating an .exe file (Windows)

If you want to create an executable .exe file, you can use the included build script:

```bash
uv run tools/create_exe.py
```

---

## ⚙️ Configuration

All application settings are located in the `settings.json` file, with only some configurable through the control panel.
It is recommended to change settings via the control panel to avoid errors. Some settings must be changed through the
control panel to work correctly (e.g., `autostart`).

---

## Modding

Mods add new entities and behavior to the application. They are written in Lua or Python and live in the `Mods/` folder.

> [!WARNING]
> Lua mods run in a restricted sandbox, but **Python mods are not sandboxed**: they run inside the application process
> with full access to your system. Install mods only from sources you trust.
> Details: [Mod security](docs/modding/security.md).

- **Create a mod**: [Getting started](docs/modding/getting-started.md), with a complete example.
- **API reference**: [concepts and what ModAPI exposes](docs/modding/api-reference.md). Exact signatures live as docstrings in [`desktop/mod_api.py`](desktop/mod_api.py) and show up in your editor via [autocomplete](docs/modding/editor-support.md).

## Troubleshooting

- **Logs** are written to the `logs/` folder.
- **A mod does not show up**. The reason should be written in the log (e.g. `Error loading mod "id": ...`).
- **Reset settings**: close the application and delete `settings.json`, it is recreated from `settings.default.json`.
- **Something else?** [Open an issue](https://github.com/czarchmA8/DesktopPet_v3/issues) and attach the latest log file.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md). The rest of the documentation is in [docs/](docs/README.md).

## License

This project is independently developed by czarchmA8. License details can be found in the [LICENSE.txt](LICENSE.txt) file.

Built with PySide6, lupa, Box2D, pywin32, PyInstaller. The full dependency list is in [`pyproject.toml`](pyproject.toml).

---

Thank you for visiting! If you like this project, consider giving it a star ⭐ — it helps others find it and is much appreciated!
