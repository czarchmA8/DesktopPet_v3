# Editor support (autocomplete)

The `ModAPI` object is injected by the application, so editors do not know it. **Stub files** describe it to them.
They are generated from `desktop/mod_api.py`, so the documentation written there (docstrings, types) is what your
editor shows in hover and completion popups. That makes the stubs the practical API reference for mod authors.

| File                             | For    |
|:---------------------------------|--------|
| `tools/output/stubs/mod_api.lua` | Lua    |
| `tools/output/stubs/mod_api.pyi` | Python |

Generate (or regenerate after changing `ModAPI`) with:

```bash
uv run desktop/mod_api.py
```

## Lua

Install the **Lua** extension in your code editor and open the repository folder. The
[`.luarc.json`](../../.luarc.json) in the repository root loads the stubs, selects Lua 5.4 and declares the global
`ModAPI`.

For a mod project outside the repository, copy `mod_api.lua` to a folder in your project and create a `.luarc.json`
pointing to it:

```json
{
    "runtime.version": "Lua 5.4",
    "workspace.library": ["path/to/folder/with/mod_api.lua"],
    "diagnostics.globals": ["ModAPI"]
}
```

## Python

The stub declares `ModAPI` as a global instance. Add this to the top of your `main.py`. The import runs only for
editors and type checkers, never at runtime, where the application injects the real `ModAPI`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mod_api import ModAPI
```

Then let your editor find `mod_api.pyi`:

- **Any other setup**: put `mod_api.pyi` next to your mod or on the search path of your type checker.
- **PyCharm**: right-click `tools/output/stubs` → *Mark Directory as* → *Sources Root*. This setting is stored in `.idea/` and is local to your machine.
