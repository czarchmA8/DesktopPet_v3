![language](https://img.shields.io/badge/language-python-239120)
![platform](https://img.shields.io/badge/platform-windows%2011-0078d4)
[![GitHub release](https://img.shields.io/github/v/release/czarchmA8/DesktopPet_v3)](#)
![status](https://img.shields.io/badge/status-in%20development-yellow)
[![LICENSE](https://img.shields.io/github/license/czarchmA8/DesktopPet_v3)](./LICENSE.txt)

<img width="1280" height="640" alt="social-preview" src="https://github.com/user-attachments/assets/2b336819-59cc-42f9-924e-b669a19ffa67" />

## 📄 About the Project

**DesktopPet_v3** is a Python application that allows users to have an intelligent, physically simulated virtual pet on their desktop. The pet autonomously moves around the screen, interacts with system windows, responds to user actions, and maintains its own statistics system.

> [!Caution]
> development is still in progress, bugs may occur

---

## 📸 Preview
<div align="center">
  <img width="800" height="450" alt="2026-06-22 18-40-51" src="https://github.com/user-attachments/assets/74f2b2ec-055e-4af8-a9c6-826a366df9b3" />
  <img width="854" height="480" alt="2026-07-06 18-17-17" src="https://github.com/user-attachments/assets/b9bd72f3-cf8e-4ad1-b0be-20b061a16aea" />
</div>

## ✨ Key Features

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

---

## 🚀 Installation

> [!NOTE]
> Works only on Windows (for now). Mac and Linux may come later!

**Requirements:** Python 3.13 and Windows 11.

1. **Clone the repository**
   ```bash
   git clone https://github.com/czarchmA8/DesktopPet_v3.git
   cd DesktopPet_v3
   ```

2. **Create a virtual environment (optional, but recommended)**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install required libraries**
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Running the Application

### Normal Launch

```bash
python main.py
```

### Launch Options with Arguments

The application supports the following command-line parameters:

| Argument  | Short | Type  | Description              | Default |
|-----------|-------|-------|--------------------------|---------|
| `--debug` | `-D`  | `int` | Debug level (0-2)        | `0`     |

```bash
python main.py --debug 0
```

### Creating an .exe file (Windows, optional)
If you want to create an executable .exe file, you can use the following command:
```bash
pyinstaller main.py --onedir --windowed --icon=icon.ico --name=DesktopPet_v3
```

---

## ⚙️ Configuration

All application settings are located in the `settings.json` file, with only some configurable through the control panel. It is recommended to change settings via the control panel to avoid errors. Some settings must be changed through the control panel to work correctly (e.g., `autostart`).

---

## 🎯 Architecture and Performance

### Multi-Process Architecture

The application runs on two independent processes:

- **PET Process** — pet engine, physics, animations, window layer (z-order) management
- **DASHBOARD Process** — control interface, settings handling

Communication between processes occurs via a structured JSON protocol sent through `multiprocessing.Pipe`.

### Project Structure

#### Main structure of the application:

| File                              | Description                                                                                                                                                               |
|:----------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`main.py`**                     | **Starting point.** Launches `dashboard.py` and `desktop/app.py` as separate processes.                                                                                   |
| **`logger_setup.py`**             | **Log management.** Handles message logging, file saving, and automatic cleanup of old log files.                                                                         |
| **`utils_debug.py`**              | **Debugging utilities.** Debug info window, hitbox rendering, and general helper functions.                                                                               |
| **`windows_layer.py`**            | **Window layering (Z-order).** Retrieves windows directly above and below a specified window handle (`hwnd`).                                                             |
| **`dashboard/dashboard.py`**      | **Control Panel & GUI.** Central hub for application control, displaying statistics, settings, and object creation via interactive buttons, including a system tray icon. |
| **`dashboard/objects_editor.py`** | **Objects Editor.** A GUI tool for automatically generating object shapes, and manually editing hitbox vertices and physics properties.                                   |
| **`dashboard/translator.py`**     | **Translation System.** Manages dynamic, on-the-fly language switching within the application using registration callbacks.                                               |
| **`desktop/app.py`**              | **Desktop manager.** Launches and manages the pet and world objects.                                                                                                      |
| **`desktop/pet.py`**              | **Pet.** The virtual pet itself.                                                                                                                                          |
| **`desktop/world_objects.py`**    | **World Objects.** Manages interactive, physical objects within the pet's environment.                                                                                    |
| **`desktop/physics_utils.py`**    | **Physics utilities.** Helper module providing custom collision detection, data structures for shapes, Box2D unit conversions, and geometry simplification utilities.     |
| **`requirements.txt`**            | **Dependencies list.** Contains external Python packages required by the project.                                                                                         |
| **`settings.default.json`**       | **Default configuration.** Contains the baseline application settings used to initialize or restore settings.json                                                         |

| Directory           | Description                                                                             |
|:--------------------|:----------------------------------------------------------------------------------------|
| **`logs/`**         | Stores application log files.                                                           |
| **`Assets/`**       | Contains all project assets, including sounds, animations, and object images.           |
| **`translations/`** | Contains Compiled Qt translation files (.qm) used for application internationalization. |

#### Additional files and folders:

| File / Directory                | Description                                                                                                                                               |
|:--------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`requirements_dev.txt`**      | **Dependencies list.** Contains external Python packages required by additional scripts.                                                                  |
| **`tools/`**                    | **Helper scripts.** Contains scripts useful only for the developer                                                                                        |
| **`tools/run_tests.py`**        | **Test runner.** Runs the full code-quality pipeline: Ruff linting, MyPy type checking, dependency verification via `pipreqs`, and the pytest test suite. |
| **`tools/update_languages.py`** | **Translation updater.** Automates the Qt translation workflow — regenerates `.ts` files from the source code and compiles them into `.qm` files.         |
| **`.github/`**                  | **GitHub configuration.** Contains issue templates, the pull request template, and CI workflows.                                                          |
| **`tests/`**                    | **Tests.** Contains the automated tests suite                                                                                                             |

### Performance Optimizations

- **BeginDeferWindowPos / EndDeferWindowPos** — batching z-order updates for all objects
- **Cached Z-Order Neighbors** — optimized `get_immediate_neighbors_above_and_below()` function for benchmarking

---

Thank you for visiting! If you like this project, consider giving it a star ⭐ — it helps others find it and is much appreciated!

---

## 📄 License

This project is independently developed by czarchmA8. License details can be found in the LICENSE file.
