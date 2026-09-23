# Security policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Use [GitHub private vulnerability reporting](https://github.com/czarchmA8/DesktopPet_v3/security/advisories/new) and include:

- what is affected and how to reproduce the problem,
- the impact you expect,
- the version of the application and your Windows version.

You can expect an acknowledgement, and a fix or an explanation, as soon as the maintainer is able to look into it.

## Scope

- **In scope**: a way for a Lua mod to escape its sandbox (read files, run programs, access Python internals) or otherwise
  go beyond what `ModAPI` allows, and vulnerabilities in the application itself.
- **Not a vulnerability by itself**: harmful behavior of a *Python* mod, because Python mods are not sandboxed by design. See [Mod security](docs/modding/security.md).
