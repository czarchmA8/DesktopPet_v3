![language](https://img.shields.io/badge/language-python-239120)
![platform](https://img.shields.io/badge/platform-windows%2011-0078d4)
![status](https://img.shields.io/badge/status-in%20development-yellow)
[![GitHub release](https://img.shields.io/github/v/release/czarchmA8/DesktopPet_v3)](#)

# 🐉 DesktopPet_v3

An advanced, interactive virtual desktop pet featuring physics simulation, control panel, and sophisticated Windows window layering.

---

## 📄 About the Project

**DesktopPet_v3** is a Python application that allows users to have an intelligent, physically simulated virtual pet on their desktop. The pet autonomously moves around the screen, interacts with system windows, responds to user actions, and maintains its own statistics system.

---

## 📸 Screenshots
<div align="center">
  <img width="800" height="450" alt="2026-06-22 18-40-51" src="https://github.com/user-attachments/assets/74f2b2ec-055e-4af8-a9c6-826a366df9b3" />
  <img width="854" height="480" alt="2026-07-06 18-17-17" src="https://github.com/user-attachments/assets/b9bd72f3-cf8e-4ad1-b0be-20b061a16aea" />
</div>

## ✨ Key Features

- 🐉 **Intelligent Pet**
  - Autonomous behavior system with multiple animation states (walking, sitting, sleeping, falling)
  - Advanced physics system — gravity, collisions, movement inertia
  - Responsiveness to mouse actions — catching, dragging, and throwing
  - Smooth GIF-based animations with fluid refresh rates

- 🎮 **Interactive Objects**
  - Dynamic objects placed on the desktop (balls, food, items)
  - Collision physics between pet and objects, and between objects
  - Window edge handling and platforming on system windows

- 📊 **Statistics and Mood System**
  - Pet statistics variables: happiness, health, hunger, sleepiness
  - Dynamic mood changes based on user interactions
  - Tracking time spent with the pet

- 🎛️ **Control Panel**
  - Dedicated interface for application configuration
  - Hotkey support — assign keyboard shortcuts to actions
  - Pet sound volume control
  - FPS adjustment and debug level settings

- 📝 **Logging System**
  - Centralized logging with multi-process support
  - Colored console output + file logging
  - Automatic old log cleanup

- 🖥️ **Debug Mode**
  - Hitbox overlay with collision visualization and pet masks
  - Debug panel with real-time application state information
  - Animation paths and FPS statistics

---

## 🚀 Installation

**Requirements:** Requires Python 3.13 and Windows 11.

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

- **PET Process** — pet engine, physics, animations, Windows window layer management
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

## 📄 License

This project is independently developed by czarchmA8. License details can be found in the LICENSE file.
