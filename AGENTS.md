# Repository Guidelines

## Project Structure and Module Organization

```
ammo/
    __init__.py      # Package initialization
    lib.py           # Utility functions
    component.py     # Core mod component definitions
    ui.py            # Terminal user interface
    bin/             # Executable scripts
    controller/      # Controllers:
                      - download.py    # Archive extraction/management.
                      - mod.py         # Generic game mod management.
                      - bethesda.py    # Bethesda game mod / plugin management.
                      - fomod.py       # FOMOD configuration dialogs.
                      - game.py        # Game selection. Mod controller selection and initialization.
                      - tool.py        # External tools management
                      - bool_prompt.py # Boolean prompt dialogs
test/
    conftest.py      # Pytest fixtures and test setup
    mod/             # Tests for generic games.
    bethesda/        # Tests for Bethesda games.
```

## Build, Test, and Development Commands

- **pre-commit**: `pre-commit install` - Install pre-commit hooks which handle
  linting and formatting.
- **Create .venv**: `python3 -m venv .venv` - Create an environment to install
  dependencies into.
- **Activate .venv**: `. .venv/bin/activate` - Use the .venv.
- **Install dependencies**: `pip3 install -r requirements.txt` - Install
  dependencies. Make sure the .venv is active first.
- **Install ammo**: `pip3 install . --force-reinstall` - Install ammo from the
  local codebase. Make sure the .venv is active first. Install ammo before
  running tests.
- **Lint**: `ruff check --fix` — Fixes linter issues automatically
- **Format**: `ruff format` — Formats code to ruff standards
- **Test**: `pytest --cov=.` — Runs tests with coverage reporting. Make sure the
  .venv is active first and that ammo and its dependencies are installed into
  the .venv.

## Coding Style and Naming Conventions

- **Indentation**: 4 spaces
- **Imports**: Group standard library, then third-party, then local
- **Type Hints**: Use `py.typed` compatible hints; prefer `Optional[T]` over
  `T | None` for readability
- **Functions**: `snake_case` for functions, `CamelCase` for classes.
- **Constants**: UPPERCASE with underscores.
- **File Naming**: Use snake_case for modules (e.g., `bethesda.py`).
- **Abstractions**:
    - Balance having high code locality without exceeding human limits of
      working memory.
    - Only reduce repetition when the consequential abstraction is also
      conceptually useful for understanding the code, and reduction of the
      repetition doesn't cause undue harm to code locality. Repetition within
      and of itself is not inherently evil.
    - Don't write abstractions for familiar interfaces unless the conceptual
      scope of the abstraction is both useful and exceeds the scope of those
      familiar interfaces.
    - Don't write abstractions before you are ready to capitalize on the utility
      the abstraction provides.
- **Commit Scope**:
    - Each commit should be contained to one conceptual change. E.g., if you
      have to say "and" in your commit title or "Also" in your commit body, your
      commit is doing too many things and you need to break it up into multiple
      patches.
    - Each commit must provide value independently of any other commit.

## Testing Guidelines

- **Framework**: pytest
- **Coverage**: Enabled by default with `--cov=.` flag
- **Naming**: Test files use `{feature}_controller.py` or `test_{topic}.py`
  pattern
- **Fixtures**: Use `@pytest.fixture` for setup; `autouse=True` for global
  fixtures
- **Mocks**: Use `unittest.mock.patch` for external dependencies
- **Run**: `pytest test/bethesda/` for game-specific tests

## Commit and Pull Request Guidelines

### Commit Messages

- Keep message lines (including titles) under 72 characters.
- Title: Summarize the change. E.g., "Ignore case of ignored files"
- The message body must contain:
    - Context: What will a reviewer need to know to understand the problem,
      behavior, code, or the reason for the change? E.g., "We have a few files
      we avoid using to detect collisions and we don't install them into the
      game directory.".
    - Why: Describe why this change needs to happen. This might be a clearly
      stated problem description. Assume the reader hasn't read the GitHub
      issue, if one exists. E.g., "Previously, the comparison to these files was
      case-sensitive, so files that didn't match the declared casing were
      unintentionally being installed into the game directory."
    - How: Describe what happened to the code. E.g.,
      "Lowercase the files and list items before comparing them to each other."
    - Value: What is the behavior after the change? E.g.,
      "This helps prevent anything getting past the filter, like readMe.txt from
      the mod Reduced NPC Headtracking."

### Pull Requests

- Include `#96` style issue references if there is a relevant issue in GitHub.
- Ensure tests pass before merging.
- Ensure pre-commit checks pass.
- If the PR contains multiple commits, include important commit messages from
  the commits within the merge or squash (exclude stuff like formatting or
  fixing issues that only existed due to other commits in the PR).

## Architecture Overview

- Ammo uses the Model/View/Controller pattern.
- Models are the dataclasses defined in ammo/components.py.
- View is ammo/ui.py which consumes controllers, and defines the interface that
  controllers must expose via an abstract base class. It parses controller
  methods and generates commands that map to those methods. It also generates a
  help menu from parsed methods. It casts user args into the types expected by
  controller methods. It validates argument count against controller methods. It
  operates via a read/execute/clear/print loop. It prints the `.__str__()`
  method of the controller, so each controller can produce a relevant interface.
- Controllers under ammo/controllers/ track the state of models and mutate
  models; or they expose prompts. They handle extracting downloads, installing
  and configuring mods or fomods, searching for installed games, spinning up
  nested ui(controller) instances, etc.
- Tools are stored in ~/.local/share/ammo/<game>/tools/ by default.
- Mods are stored in ~/.local/share/ammo/<game>/mods/ by default.
- Mods are installed into a game directory by creating symlinks in the game
  directory that link back to the mod files under
  ~/.local/share/ammo/<game>/mods/.
- Conflict resolution is handled via the ModController.stage method.
- This program is for case-sensitive filesystems but the games we're managing
  are for case-insensitive filesystems. Ammo must accommodate this.
- There are two ways to reconcile differences between a game in storage and the
  in-memory state of ammo: `refresh`, which makes the in-memory state of ammo
  match the state of the game in storage; and `commit`, which makes the game in
  storage match the in-memory state of ammo.
- Commands which diverge the in-memory state and the stored game state to
  diverge are tracked via ModController.changes or BethesdaController.changes,
  depending on the game.
- Some commands are only safe to execute when states are reconciled, either
  because they require a reconciled state before they execute to behave
  accurately, or because they must reconcile to accurately represent the state
  of the stored game to the user. These are decorated with `@requires_sync`.
