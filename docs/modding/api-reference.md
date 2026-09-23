# ModAPI reference

`ModAPI` is a global object available in every mod script (Lua and Python). This page explains the concepts behind it
and what each group of functions is for. It does not repeat parameter lists or types — those live as docstrings in
[`desktop/mod_api.py`](../../desktop/mod_api.py) and are what generates the [editor autocomplete](editor-support.md)
and the `mod_api.pyi` / `mod_api.lua` stubs, so they stay in one place instead of being duplicated here.

## Concepts

**Windows and layers.** Drawing functions take a window handle `hwnd`. The application creates a transparent layer
for that window and places it directly above it in the z-order (below the windows that are above it). A layer exists
only while something is drawn on it in the current frame. Get handles with the [window functions](#windows).

**Coordinates.** Drawing coordinates are in pixels in the coordinate space of the overlay, which covers the whole
virtual desktop (all monitors). The origin is the top-left corner of the virtual desktop.

**Draw order.** Commands are painted in call order, so what you draw later is on top.

**Immediate mode.** `ModAPI.draw_*` calls only apply to the current frame; the application clears all drawing
commands before each frame. To keep something on screen, draw it again every frame — normally from `tick_func` (see
[Entity lifecycle](#entity-lifecycle)).

**Hit testing.** Passing a `hit_id` to a drawing function makes the shape *clickable*. Use the `instance_id` of your
entity as `hit_id`. Clicking then selects the entity in the control panel, and the [Mouse](#mouse) functions can tell
whether that shape was pressed. Where shapes overlap, the one drawn last wins. Pixels with alpha `<= 10` are not hit.

## Entity lifecycle

### `register_entity(...)`

Makes an entity available in the control panel.

| Parameter      | Description                                                                          |
|----------------|--------------------------------------------------------------------------------------|
| `entity_id`    | ID unique within the mod.                                                            |
| `name`         | Display name.                                                                        |
| `preview_path` | Preview image relative to the mod folder, or `nil`.                                  |
| `description`  | Description, or `nil` (defaults to "No description available.").                     |
| `create_func`  | `create_func(instance_id)` called for every spawned instance. Returns the callbacks. |

### Callbacks returned by `create_func`

`create_func(instance_id)` returns a table (Lua) or dict (Python) of callbacks for that instance. All callbacks are
optional — a missing one simply does nothing, and the table/dict itself may be empty, but it must be returned.

| Callback                      | When it is called                                                                             |
|-------------------------------|-----------------------------------------------------------------------------------------------|
| `tick_func(hitbox_overlay)`   | Called in every frame (see [Immediate mode](#concepts)).                                      |
| `show_func()` / `hide_func()` | The user shows or hides the entity from the control panel.                                    |
| `teleport_func()`             | The user uses "teleport" in the control panel.                                                |
| `get_info_func()`             | Every frame while the entity is selected. Returns a table/dict shown as its details.          |
| `delete_func()`               | The instance is removed (from the control panel or with [`kill_entity`](#removing-entities)). |

`hitbox_overlay` is `true` when debug mode and the hitbox overlay are enabled. Use it to draw hitbox outlines.

### `tick(hitbox_overlay)`

A global function of the script, called every frame independently of any instance. Use it for mod-wide logic that
does not belong to a specific entity.

## Windows

Functions to look up window handles and information about them: the current foreground window, a window's title and
rectangle, and its neighbors in the z-order. Mods use these mainly to get the `hwnd` that drawing functions need (see
[Windows and layers](#concepts)). Exact signatures: `get_foreground_window_hwnd`, `get_window_title`,
`get_window_rect`, `get_window_above`, `get_window_below`, `get_real_window_above`, `get_real_window_below` in the
[stubs](editor-support.md).

## Drawing

Functions to draw shapes, text and images onto a window's layer: rectangles, lines, text and images loaded from the
mod's own folder. Governed by the concepts above — coordinates, draw order, immediate mode and hit testing. Exact
signatures: `draw_rect`, `draw_line`, `draw_text`, `draw_image` in the [stubs](editor-support.md).

## Mouse

`ModAPI.Mouse` reports the cursor position and, per `hit_id`, whether a shape drawn with that `hit_id` was clicked,
pressed, held or released this frame. Exact signatures: `Mouse.get_pos`, `Mouse.get_scroll`,
`Mouse.is_entity_clicked`, `Mouse.is_entity_pressed`, `Mouse.is_entity_holding`, `Mouse.is_entity_released` and
related scroll functions in the [stubs](editor-support.md).

## Logger

`ModAPI.Logger` writes to the application log (`logs/`) under the mod's own name, at `debug`, `info`, `warning`,
`error` or `critical` level. See [Debugging](getting-started.md#5-debugging).

## Focus

Functions to check whether an instance is currently selected in the control panel, and whether a window is the
active one: `is_entity_focused`, `is_window_focused`, `is_focused` in the [stubs](editor-support.md).

## Removing entities

`kill_entity(instance_id)` removes an instance, the same as the user removing it from the control panel — this also
triggers its `delete_func`.