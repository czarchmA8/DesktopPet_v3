# Contributing

🎉 Thanks for taking the time to contribute! 🎉

When contributing, you are expected to follow our Code of Conduct.

Here are some of the ways in which you can contribute:

## Discussions

If you want to ask a question to understand a concept, or need help with the project, please check the Discussions. If you don't find a thread that fits your needs, feel free to create a new one.

## Issues

If you found unexpected behavior, please browse our existing issues. If no issues fit your case, create a new one.

If you would like to suggest a new feature, create a new issue. This helps have meaningful conversations about design, feasibility, and general expectations of how a feature would work. If you plan to work on this yourself, we ask you to state this as well, so that you receive the guidance you need.

## Pull requests

Code contributions are greatly appreciated. Here is the general workflow you should follow:

1. **State in the associated issue your desire to work on it**

   If there is no issue for the work you would like to do, please open one. This helps reduce duplicated efforts and give contributors the help and guidance they might need.

2. **Write some code!**

   If this is your first contribution, you will need to fork and clone the repository using git. If you need help with the code you are working on, don't hesitate to ask questions in the associated issue. We will be happy to help you.

3. **Open the pull request**
   - **General code guidelines**

     - When possible, please document relevant pieces of code following [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/). For more information on how to write docstrings, check the [Python documentation](https://docs.python.org/3/tutorial/controlflow.html#documentation-strings).
     - Comment your code. It will be useful for your reviewer and future contributors.

   - **Pull request titles**

     - Pull request titles look like this: `type: description`

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

     - **Description**

       A summary of what your pull request achieves and a rough list of changes.

     - **Related Issues**
     
       Link to the issue(s) this PR closes or relates to. For example: Closes #123

     - **Breaking Changes**

       Optional, if there are any breaking changes document them, including how to migrate older code.

     - **Notes & open questions**

       Notes, open questions and remarks about your changes.

     - **Checklist**

       - **Self review**: We ask you to thoroughly review your changes until you are happy with them. This helps speed up the review process.
       - **Add documentation**: If your change requires documentation updates, make sure they are properly added.
       - **Breaking Changes**: All breaking changes need to be documented.


4. **Review process**

    - Mark your pull request as ready for review.
    - If a team member in particular is guiding you, feel free to directly tag them in your pull request to get a review. Otherwise, wait for someone to pick it up.
    - Attend to constructive criticism and make changes when necessary.

5. **My code is ready to be merged!**

    Congratulations on becoming an official contributor!

## Python Naming Conventions

Please follow [PEP 8](https://pep8.org/) naming conventions for all Python code:

### Variables and Functions
- Use `lowercase_with_underscores` (snake_case) for variable and function names
- Example: `my_variable`, `calculate_total()`, `is_valid()`

### Classes
- Use `CapWords` (PascalCase) for class names
- Example: `MyClass`, `UserManager`, `DataProcessor`

### Constants
- Use `UPPERCASE_WITH_UNDERSCORES` for constants
- Example: `MAX_RETRIES`, `DEFAULT_TIMEOUT`, `API_KEY`

### Private Members
- Prefix private variables and functions with a single underscore
- Example: `_private_var`, `_internal_method()`

### General Guidelines
- Avoid single-letter variable names except for loop counters or mathematical expressions
- Use descriptive names that clearly indicate the purpose
- Avoid abbreviations unless they are widely understood
- Maximum line length: 79 characters (PEP 8 recommendation)
