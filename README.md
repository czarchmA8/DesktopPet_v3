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
  <img width="854" height="480" alt="2026-07-21 13-10-42" src="https://github.com/user-attachments/assets/4c0af889-84c4-46f5-ad65-d47d22764a54" />
  <video src="https://github.com/user-attachments/assets/6198545f-e84f-4092-84f9-3ae283c6f808" width="1220" controls></video>
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
- Mod system with Lua scripting support — user-created mods loaded from the `Mods/` folder
- Update checker with in-app notification dialog

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
   No Git? [Download ZIP](https://github.com/czarchmA8/DesktopPet_v3/archive/refs/heads/master.zip) and extract it instead.

2. **Install `uv`** (if you don't have it yet)
   ```bash
   winget install --id=astral-sh.uv -e
   ```

3. **Install dependencies**
   ```bash
   uv sync --group dev
   ```

## ▶️ Running the Application

### Generating compiled `.qm` translation files from `.ts` files
```bash
uv run tools/update_languages.py
```

### Normal Launch

```bash
uv run main.py
```

### Launch Options with Arguments

The application supports the following command-line parameters:

| Argument      | Short | Type         | Description                                 | Default |
|---------------|-------|--------------|---------------------------------------------|---------|
| `--debug`     | `-D`  | `int`        | Debug level (0-2)                           | `0`     |
| `--autostart` |       | `store_true` | Indicates the app was launched by autostart | `False` |

```bash
uv run main.py --debug 0
```

### Creating an .exe file (Windows, optional)
If you want to create an executable .exe file, you can use the included build script:
```bash
uv run tools/create_exe.py
```

---

## ⚙️ Configuration

All application settings are located in the `settings.json` file, with only some configurable through the control panel. It is recommended to change settings via the control panel to avoid errors. Some settings must be changed through the control panel to work correctly (e.g., `autostart`).

---

## Modding

Mods extend the application with custom entities and behavior through a sandboxed `ModAPI`, exposed to a Lua runtime (Python-based mods are planned but not yet supported).

### Mods structure

Each mod is a subfolder inside `Mods/` — the folder name is used as the mod's ID — and contains:

| File          | Description                                                               |
|:--------------|:--------------------------------------------------------------------------|
| `about.json`  | Mod metadata: `name`, `author`, `version`, `description`, `dependencies`. |
| `preview.png` | Preview image shown in the control panel.                                 |
| `main.lua`    | The mod's entry point script.                                             |

A mod script can define one optional global function `tick()` called every frame, and register spawnable entities via `ModAPI.register_entity(...)`. `ModAPI` also provides drawing (`draw_rect`, `draw_line`, `draw_text`, `draw_image`), mouse input (`ModAPI.Mouse`), logging (`ModAPI.Logger`), and window watching for z-order updates.

### First mod

A mod that registers a spawnable entity — an image bouncing around the screen like a DVD logo:

```lua
-- Get the handle of the active window to render over it
window_hwnd = ModAPI.get_foreground_window_hwnd()
ModAPI.Logger.debug("Window title: " .. ModAPI.get_window_title(window_hwnd))

-- Creates a single entity instance
function create_entity(instance_id)
    local x, y = 0, 0
    local add_to_x, add_to_y = 1, 1
    local visible = true

    local screen_width = 1920
    local screen_height = 1080
    local image_width = 300
    local image_height = 150

    -- Return entity callbacks used by the main application
    return {
        -- Action callbacks
        delete_func = nil,
        show_func = function() visible = true end,
        hide_func = function() visible = false end,
        teleport_func = function() x, y = 0, 0 end,
        -- Return detailed entity info displayed in the control panel
        get_info_func = function() return {
            visible = visible,
            pos = string.format("%s, %s", x, y),
        } end,
        tick_func = function(hitbox_overlay)
            -- Bounce logic for screen edges
            x = x + add_to_x
            if x >= screen_width - image_width or x <= 0 then add_to_x = -add_to_x end
            y = y + add_to_y
            if y >= screen_height - image_height or y <= 0 then add_to_y = -add_to_y end

            if visible then
                ModAPI.draw_image(window_hwnd, x, y, "preview.png", image_width, image_height, nil, instance_id)
            end

            -- Draw border if hitbox debug overlay is enabled
            if hitbox_overlay then
                ModAPI.draw_rect(window_hwnd, x, y, image_width, image_height, { 255, 0, 0 }, false)
            end
        end,
    }
end

-- Register entity to make it available in the control panel
ModAPI.register_entity("first-entity", "First entity", "preview.png", "Bounces off the screen edges", create_entity)
```

`register_entity` makes the entity spawnable from the control panel; each spawned instance gets its own `instance_id` and the set of callback functions returned above. Detailed `ModAPI` reference and a full modding guide are planned as separate documentation.

---

## 🎯 Architecture and Performance

### Multi-Process Architecture

The application runs on two independent processes:

- **DESKTOP Process** — pet engine, mods, physics, animations, window layer (z-order) management
- **DASHBOARD Process** — control interface, settings handling

Communication between processes occurs via a structured JSON protocol sent through `multiprocessing.Pipe`.

### Project Structure

#### Main structure of the application:

| File                               | Description                                                                                                                                                                             |
|:-----------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`main.py`**                      | **Starting point.** Launches `dashboard.py` and `desktop/app.py` as separate processes.                                                                                                 |
| **`config.py`**                    | **Configuration.** Stores and initializes variables for the application.                                                                                                                |
| **`logger.py`**                    | **Log management.** Handles message logging, file saving, and automatic cleanup of old log files.                                                                                       |
| **`shared_state.py`**              | **Interprocess communication.** Stores a local copy of data and updates it when reading its value and calling the `pull()` function                                                     |
| **`utils_debug.py`**               | **Debugging utilities.** Debug info window, hitbox rendering, and general helper functions.                                                                                             |
| **`windows_z_order/neighbors.py`** | **Window layering (Z-order).** Retrieves windows directly above and below a specified window handle (`hwnd`).                                                                           |
| **`windows_z_order/watcher.py`**   | **Window layering (Z-order).** Listens to window events and then updates the z-order list that can be used                                                                              |
| **`dashboard/dashboard.py`**       | **Control Panel & GUI.** Central hub for application control, displaying settings, mods, list of entities, and entities creation via interactive buttons, including a system tray icon. |
| **`dashboard/objects_editor.py`**  | **Objects Editor.** A GUI tool for automatically generating object shapes, and manually editing hitbox vertices and physics properties.                                                 |
| **`dashboard/translator.py`**      | **Translation System.** Manages dynamic, on-the-fly language switching within the application using registration callbacks.                                                             |
| **`dashboard/ui/`**                | **Generated UI layout.** Qt Designer-generated main window layout files.                                                                                                                |
| **`dashboard/widgets/`**           | **Custom widgets.** Reusable UI components used across the dashboard (dialogs, list rows, custom controls, etc.).                                                                       |
| **`desktop/overlay_manager.py`**   | **Desktop manager.** Launches and manages overlay windows on which mods can draw.                                                                                                       |
| **`desktop/mods_manager.py`**      | **Mods manager.** Loads, manages and runs mods.                                                                                                                                         |
| **`desktop/mod_api.py`**           | **Mod API.** Functions and classes shared with mods.                                                                                                                                    |
| **`desktop/input_events.py`**      | **Input events & data types.** Defines input structures, enums, and dataclasses (mouse states, clicks, scroll) used by overlay and mod API.                                             |
| **`desktop/app.py`**               | **(Not used)** Legacy pet and world objects manager implementation — replaced by `overlay_manager.py`.                                                                                  |
| **`desktop/pet.py`**               | **(Not used, pending update)** Legacy virtual pet implementation — to be reworked for the mod system.                                                                                   |
| **`desktop/world_objects.py`**     | **(Not used, pending update)** Legacy interactive world objects — to be reworked for the mod system.                                                                                    |
| **`desktop/physics_utils.py`**     | **Physics utilities.** Helper module providing custom collision detection, data structures for shapes, Box2D unit conversions, and geometry simplification utilities.                   |
| **`pyproject.toml`**               | **Project configuration.** Declares dependencies, dependency groups, and project metadata for `uv`.                                                                                     |
| **`uv.lock`**                      | **Dependency lockfile.** Pins exact resolved versions of all dependencies (including transitive ones) for reproducible installs. Auto-generated — do not edit manually.                 |
| **`settings.default.json`**        | **Default configuration.** Contains the baseline application settings used to initialize or restore settings.json                                                                       |
| **`version.json`**                 | **Version.** Stores information about the version and its date.                                                                                                                         |

| Directory           | Description                                                                                                                |
|:--------------------|:---------------------------------------------------------------------------------------------------------------------------|
| **`logs/`**         | Stores application log files.                                                                                              |
| **`Assets/`**       | Contains all project assets, including sounds, animations, and object images.                                              |
| **`translations/`** | Contains Compiled Qt translation files (.qm) and translation source files (.ts) used for application internationalization. |
| *`Mods/`*           | Stores all user mods                                                                                                       |

#### Additional files and folders:

| File / Directory                  | Description                                                                                                                                               |
|:----------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`.github/`**                    | **GitHub configuration.** Contains issue templates, the pull request template, and CI workflows.                                                          |
| **`tests/`**                      | **Tests.** Contains the automated tests suite                                                                                                             |
| **`tools/`**                      | **Helper scripts.** Contains scripts useful only for the developer                                                                                        |
| **`tools/create_exe.py`**         | **Executable builder.** Packages the application into a standalone `.exe` using PyInstaller.                                                              |
| **`tools/run_tests.py`**          | **Test runner.** Runs the full code-quality pipeline: Ruff linting, MyPy type checking, dependency verification via `pipreqs`, and the pytest test suite. |
| **`tools/update_languages.py`**   | **Translation updater.** Automates the Qt translation workflow — regenerates `.ts` files from the source code and compiles them into `.qm` files.         |
| **`tools/generate_lua_stubs.py`** | **Lua definitions updater.** Generates a `mod_api.lua` file used to add autocomplete and better code formatting in mod scripts.                           |
| **`.luarc.json`**                 | **Lua configuration.** Definitions and settings for the Lua language server, utilized for mod development.                                                |

---

Thank you for visiting! If you like this project, consider giving it a star ⭐ — it helps others find it and is much appreciated!

---

## 📄 License

This project is independently developed by czarchmA8. License details can be found in the LICENSE file.
