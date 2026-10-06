# Mod security

A mod is code that runs on your computer. This page describes what it can and cannot do.

## Lua mods

Lua mods run in a restricted environment:

- The Lua functions that give access to files, the operating system, other code and the interpreter itself are removed
  (`os`, `io`, `file`, `dofile`, `loadfile`, `debug`, `require`, `package`, `load`, `python`).
- Python objects exposed to Lua, such as `ModAPI`, hide every attribute starting with `_`.
- Images can only be read from the mod's own folder.

This is not a hard security boundary. There are no CPU or memory limits: a mod that runs an infinite loop freezes the
application, because mods run inside the frame loop of the desktop process.

## Python mods

**Python mods are not sandboxed.** They run inside the application process with the same rights as the application:
they can read and write your files, access the network, start programs and reach the internals of the application
(the `_` prefix of private members is only a convention in Python). Treat a Python mod like any program you install.

## What every mod can do through `ModAPI`

This applies to Lua and Python mods alike. A mod can:

- **See your windows.** It learns the titles, positions, sizes, state (minimized, maximized, fullscreen, focused) and
  stacking order of all windows, including those of other programs. Titles often reveal what you are working on.
- **Follow your mouse.** It knows where the cursor is at any moment and receives mouse button and scroll events.
- **Draw anywhere on the desktop**, over any window, including content that imitates other programs.
- **Manage entities.** It can spawn entities, see which entity is selected in the control panel and
  remove any entity.

## Trusting a mod

When you enable a mod, the control panel warns you and asks for confirmation. You can choose not to be asked again for
that mod, and later revoke or grant trust from the mod's menu. Trust only means "do not ask"; it checks nothing.

## Recommendations

**For users**

- Install mods only from sources you trust and read `main.lua` / `main.py` before enabling them.
- Prefer Lua mods from unknown authors.

**For mod authors**

- Do not obfuscate your code, so that users can review it.
- Use Lua unless you need Python.

To report a vulnerability in the application itself, see the [security policy](../../SECURITY.md).
