# Getting started with mods

A mod is a folder with a script (Lua or Python) that registers **entities**. An entity is something drawn on the
desktop, such as a pet, a ball or a decoration. Entities are spawned from the control panel, and every spawned copy
is an independent **instance**.

## 1. Folder layout

Each mod is a subfolder of `Mods/`. The folder name is the mod ID.

```text
Mods/
└── my-mod/
    ├── about.json     # required
    ├── preview.png    # optional
    └── main.lua       # or main.py (required)
```

| File                   | Description                                                                                                  |
|------------------------|--------------------------------------------------------------------------------------------------------------|
| `about.json`           | Mod metadata. Without it the mod is skipped.                                                                 |
| `preview.png`          | Preview shown in the control panel. Any image format supported by Qt works, the base name must be `preview`. |
| `main.lua` / `main.py` | The entry point script. If both exist, `main.py` is used.                                                    |

Other files (images, ...) can live in the mod folder and can be loaded with paths relative to it, e.g. `"images/ball.png"`.

## 2. `about.json`

```json
{
    "name": "My mod",
    "author": "Your name",
    "version": "1.0.0",
    "description": "What the mod does.",
    "dependencies": {}
}
```

All fields are optional (`name` defaults to the mod ID, `author` to `unknown`, `version` to `0.0.0`). `dependencies`
is stored with the mod metadata but is not enforced by the loader.

## 3. How a script runs

1. When the application starts, the script of every **enabled** mod is executed once, from top to bottom.
2. In its top-level code the script calls `ModAPI.register_entity(...)`.
3. Optionally the script defines a global function `tick(hitbox_overlay)`.
4. When the user spawns an entity, its `create_func(instance_id)` is called and returns the callbacks of that instance.

The `ModAPI` object is available in the script without importing anything. Lua and Python use the same API. In Python
`ModAPI` is a global too, see [Editor support](editor-support.md) for autocomplete.

What each of these calls actually does, what `create_func` must return, and everything else `ModAPI` exposes (drawing,
windows, mouse, logging, ...) is described in the [API reference](api-reference.md) — see that page for the concepts,
not repeated here.

## 4. Install and enable

1. Copy the mod folder into `Mods/`
2. Enable the mod in the control panel.
3. Restart the application. Mods are loaded on startup.
4. Spawn the entity from the control panel.

## 5. Debugging

- `print(...)` and `ModAPI.Logger` write to the application log (`logs/`).
- If the script fails while loading, the mod is not started and `Error in mod code "<id>": ...` is logged.
- Errors raised inside `tick` or a callback are **not** caught by the loader, and they interrupt the current frame.

## 6. Complete example

A single-file Lua mod that registers one entity bouncing around the screen, similar to the classic DVD logo. It shows
a typical `create_func`/`tick_func` pair, reading window info, and drawing with a `hit_id` so the entity can be
selected. Python mods use the exact same `ModAPI` calls, just with Python syntax, so a separate Python example is not
needed here — see the [API reference](api-reference.md) for what each call does.

`Mods/bouncing-entity/main.lua`:

```lua
print(string.format('Running a lua script from a mod "%s"', ModAPI.Mod.id))
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

Copy this next to a `preview.png` and an `about.json` (see [step 2](#2-aboutjson)), then follow
[Install and enable](#4-install-and-enable).

## Next steps

- [ModAPI reference](api-reference.md): concepts, entity lifecycle and what `ModAPI` exposes
- [Editor support](editor-support.md): autocomplete and type checking
- [Mod security](security.md)
