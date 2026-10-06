# ModAPI reference

`ModAPI` is a global object available in every mod script (Lua and Python). This page explains the **concepts** behind
it and the **entity lifecycle**. It does not list functions, parameters or return values: those are the docstrings in
[`app/desktop/mod_api.py`](../../app/desktop/mod_api.py), which your editor shows through the
[generated stubs](editor-support.md). Everything about one specific function (what it returns, when it raises, the
callbacks `create_func` returns) is written there.

## Overview

`ModAPI` is split into groups, called as e.g. `ModAPI.Overlay.draw_rect(...)`:

| Group            | What it is for                                                                      |
|------------------|-------------------------------------------------------------------------------------|
| `ModAPI.Mod`     | Metadata of the running mod, read from its `about.json`.                            |
| `ModAPI.Entity`  | Registering, spawning and removing entities, selection, input on a specific entity. |
| `ModAPI.Overlay` | Windows, screens and drawing.                                                       |
| `ModAPI.Mouse`   | Cursor position, button state and scroll.                                           |
| `ModAPI.Logger`  | Writing to the application log.                                                     |

## Concepts

**Windows and layers.** Drawing functions take a window handle `hwnd`. The application creates a transparent layer
for that window and places it directly above it in the z-order (below the windows that are above it). A layer exists
only while something is drawn on it in the current frame. Handles come from the window functions of `ModAPI.Overlay`.
A window can be closed at any time, so a mod that keeps an `hwnd` between frames should check that it still exists.

**Coordinates.** Drawing coordinates are whole pixels in the coordinate space of the overlay, which covers the whole
virtual desktop (all monitors). The point (0, 0) is the top left corner of the main screen, and monitors to the left or
above it have negative coordinates. Window rectangles and the cursor position use the same coordinates.

**Immediate mode and draw order.** Drawing calls only apply to the current frame; the application clears all drawing
commands before each frame. To keep something on screen, draw it again every frame, normally from `tick_func`.
Commands are painted in call order, so what is drawn later is on top.

**Frame time.** `tick` and `tick_func` receive `dt`, the time since the previous frame in seconds. Multiply speeds by
`dt` so that movement does not depend on the FPS set in the control panel.

**Hit testing.** Passing a `hit_id` to a drawing function makes the shape *clickable*. Use the `instance_id` of your
entity as `hit_id`: clicking the shape then selects the entity in the control panel, and the input functions of
`ModAPI.Entity` tell whether that shape was pressed, held, released or scrolled over.

- Shapes are tested from the last drawn to the first and the first one hit wins. Shapes without a `hit_id` never
  block the ones below them.
- Filled rectangles and lines are hit within their area, unless their color has alpha `<= 10`. Outlined rectangles are
  hit only on the outline. Images are hit on pixels with alpha `> 10`. Text cannot be clicked.

**Mouse input.** A button is `pressed` for the first frame after it went down, `holding` for the following frames and
`released` for one frame after it went up. A held button keeps the `hit_id` of the shape it was pressed on, even if the
cursor leaves it, so dragging works. Very short clicks can be missed at a low FPS.

**Errors.** Invalid input (an image that cannot be loaded, a path leaving the mod folder) raises an error, see
[Debugging](getting-started.md#5-debugging) for what happens then.

## Entity lifecycle

An entity is registered once with `Entity.register`. Every time the user spawns it, `create_func(instance_id)` is called and returns the callbacks of that instance: `tick_func`, `show_func`, `hide_func`, `teleport_func`, `get_info_func` and `delete_func`. When each of them is called and with what arguments is described in the docstring of `Entity.register`.

A script can also define a global function `tick(dt, hitbox_overlay)`, with the same arguments as `tick_func`. It is called every frame, independently of any instance and before their `tick_func`. Use it for logic that belongs to the whole mod.
