# Mod security

A mod is code that runs on your computer. This page describes what it can and cannot do.

## Lua mods

Lua mods run in a restricted environment:

- The globals `os`, `io`, `file`, `dofile`, `loadfile`, `debug`, `require`, `package`, `load` and `python` are removed.
- Python objects exposed to Lua (such as `ModAPI`) hide every attribute starting with `_`.
- `draw_image` can only read files inside the mod's own folder.

This is not a hard security boundary. There are no CPU or memory limits: a mod that runs an infinite loop freezes the
application, because mods run inside the frame loop of the desktop process.

## Python mods

**Python mods are not sandboxed.** They run inside the application process with the same rights as the application:
they can read and write your files, access the network, start programs and reach the internals of the application
(the `_` prefix of private members is only a convention in Python). Treat a Python mod like any program you install.

## What `ModAPI` exposes to every mod

Every enabled mod, Lua or Python, can read:

- The title, position and z-order neighbors of your windows (`get_window_title`, `get_window_rect`, ...).
- The cursor position (`ModAPI.Mouse.get_pos`) and clicks on shapes drawn by the mod.

## Recommendations

**For users**

- Install mods only from sources you trust and read `main.lua` / `main.py` before enabling them.
- Prefer Lua mods from unknown authors.

**For mod authors**

- Do not obfuscate your code, so that users can review it.
- Use Lua unless you need Python.

To report a vulnerability in the application itself, see the [security policy](../../SECURITY.md).
