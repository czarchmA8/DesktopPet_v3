# Contributing

🎉 Thanks for taking the time to contribute! 🎉

When contributing, you are expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

Here are some of the ways in which you can contribute:

## Discussions

If you want to ask a question to understand a concept, or need help with the project, please check the Discussions. If
you don't find a thread that fits your needs, feel free to create a new one.

## Issues

If you found unexpected behavior, please browse our existing issues. If no issues fit your case, create a new one.

If you would like to suggest a new feature, create a new issue. This helps have meaningful conversations about design,
feasibility, and general expectations of how a feature would work. If you plan to work on this yourself, we ask you to
state this as well, so that you receive the guidance you need.

Security problems should not be reported in public issues, see the [security policy](SECURITY.md).

## Development setup

Set the project up as described in [Run from source](README.md#run-from-source). The design of the application is
described in the
[architecture](docs/architecture.md).

## Quality checks

Before opening a pull request run the same quality pipeline that CI runs:

```bash
uv run tools/run_tests.py
```

## Pull requests

Code contributions are greatly appreciated. Here is the general workflow you should follow:

1. **State in the associated issue your desire to work on it**

   If there is no issue for the work you would like to do, please open one. This helps reduce duplicated efforts and
   give contributors the help and guidance they might need.

2. **Write some code!**

   If this is your first contribution, you will need to fork and clone the repository using git. If you need help with
   the code you are working on, don't hesitate to ask questions in the associated issue. We will be happy to help you.

   Comment your code. It will be useful for your reviewer and future contributors.
   Follow [General code guidelines](#code-style)

3. **Check your changes**

   Run [`uv run tools/run_tests.py`](#quality-checks) and make sure it passes.

4. **Open the pull request**
    - **Pull request titles**

      Pull request titles look like this: `type: description`

      |   **type** | **When to use**                                                                              |
      |-----------:|----------------------------------------------------------------------------------------------|
      |     `feat` | A new feature                                                                                |
      |     `test` | Changes that exclusively affect tests, either by adding new ones or correcting existing ones |
      |      `fix` | A bug fix                                                                                    |
      |     `docs` | Documentation only changes                                                                   |
      | `refactor` | A code change that neither fixes a bug nor adds a feature                                    |
      |     `perf` | A code change that improves performance                                                      |
      |     `deps` | Dependency only updates                                                                      |
      |    `chore` | Changes to the build process or auxiliary tools and libraries                                |

      **`description`** is a short sentence that summarizes your changes.

      If there is a breaking change please use a `!` in the commit message to denote this, eg. `feat!: break the API`.

    - **Pull request descriptions**

      Once you open a pull request, you will be prompted to follow a template with three simple parts:

        - **Description** - A summary of what your pull request achieves and a rough list of changes.
        - **Related Issues** - Link to the issue (s) this PR closes or relates to. For example: Closes #123
        - **Changelog Context** - Added / Changed / Fixed entries, if relevant.
        - **Breaking Changes** - Optional, if there are any breaking changes document them, including how to migrate older code.
        - **Notes & open questions** - Notes, open questions and remarks about your changes.
        - **Checklist** - self-review, tested locally, documentation updated, breaking changes documented, ready for critical review.

5. **Review process**

    - Mark your pull request as ready for review.
    - If a team member in particular is guiding you, feel free to directly tag them in your pull request to get a
      review. Otherwise, wait for someone to pick it up.
    - Attend to constructive criticism and make changes when necessary.

6. **My code is ready to be merged!**

   Congratulations on becoming an official contributor!

## Code style

- **Docstrings**: when possible, document relevant pieces of code
  following [PEP 257](https://peps.python.org/pep-0257/).
- **Comments**: comment your code. It will be useful for your reviewer and future contributors.
- **Naming** follows [PEP 8](https://pep8.org/):

| What                          | Style                        | Example                          |
|-------------------------------|------------------------------|----------------------------------|
| Variables, functions, modules | `lowercase_with_underscores` | `mods_manager`, `spawn_entity()` |
| Classes                       | `CapWords`                   | `ModsManager`, `OverlayManager`  |
| Constants                     | `UPPERCASE_WITH_UNDERSCORES` | `MODS_DIR`                       |
| Private members               | leading underscore           | `_run_python_mod()`              |

- Avoid single-letter variable names except for loop counters or mathematical expressions
- Use descriptive names that clearly indicate the purpose
- Avoid abbreviations unless they are widely understood
- Line length: there is no enforced limit, but keep lines readable.
