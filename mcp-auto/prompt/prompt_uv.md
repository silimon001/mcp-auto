# uv Best Practices

## What is uv?

uv is an extremely fast Python package and project manager.

**Task Requirement**: For any Python project, deployment must be performed using uv.

---

## uv Usage Guide

### Running Scripts

Use `uv run <scripts>.py` instead of `python <script>.py`.

* Script without dependencies

```example.py
print("Hello world")
```

```bash
$ uv run example.py
Hello world
```

* Passing arguments to a script

```example.py
import sys

print(" ".join(sys.argv[1:]))
```

```bash
$ uv run example.py test
test

$ uv run example.py hello world!
hello world!
```

* Script with dependencies

```example.py
import time
from rich.progress import track

for i in track(range(20), description="For example:"):
    time.sleep(0.05)
```

Use `--with` to install dependencies and `--python` to specify the Python version.

```bash
$ uv run --with rich --python 3.12 example.py
For example: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
```

### Running Tools

* `uvx` is used to run command-line tools; when used, the tool is installed into a temporary isolated environment.

```bash
$ uvx --python 3.10 ruff
```

**Note**: When you run `uvx <package>`, a server starts and waits for communication, blocking the process. Therefore, during **Step 4: Execute the Deployment Plan**, do not use this command to directly start the server, as it will cause the process to remain blocked indefinitely. The correct approach is to place the configuration information directly into the configuration file and then proceed to **Step 6: Verify the Server**.

### Project Management

* The `uv init` command initializes a new project.

```bash
$ mkdir hello-world
$ cd hello-world
$ uv init
```

uv will create the following files:

```bash
├── .gitignore
├── .python-version
├── README.md
├── main.py
└── pyproject.toml
```

The `pyproject.toml` file contains the project's metadata:

```toml
[project]
name = "hello-world"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
dependencies = []
```

The `.python-version` file specifies the Python version to be used for the project.

* Managing dependencies: Use `uv add` and `uv remove` to add or remove dependencies.

```bash
$ # Specify a version constraint
$ uv add 'requests==2.31.0'

$ # Add a git dependency
$ uv add git+https://github.com/psf/requests

$ # Add all dependencies from `requirements.txt`.
$ uv add -r requirements.txt -c constraints.txt

$ uv remove requests
```

* Synchronizing the project environment:

```bash
$ uv sync
```

### pip Interface

* Create a virtual environment (.venv); you can specify the Python version.

```bash
$ uv venv --python 3.xx

$ # Forcefully switch the Python version
$ uv venv --python 3.xx --clear
```

* Manage dependencies:

```bash
$ uv pip install <package>

$ # for example
$ uv pip install flask[dotenv] ruff

$ uv pip install -e .
$ uv pip install -r requirements.txt
$ uv pip install -r pyproject.toml

$ # uninstall
$ uv pip uninstall flash ruff
```

## Environment Setup (Guarantees)

- uv has already been deployed in the user’s development environment, so there is no need to install or verify it again.
- The paths for the uv tools are as follows; please use them directly:

```bash
$ which uv
{HOME}/.local/bin/uv

$ which uvx
{HOME}/.local/bin/uvx
```

* Any uv command should first change to the corresponding project directory before being executed.

```bash
$ cd /path/to/project/dir && uv xxx
```

**Important: Use `uv` to manage your Python environment and dependencies.**
Once you have initialized or are managing your project with `uv`, **do not use the native `python` or `pip` commands**, as they can bypass `uv`’s environment management and lead to execution failures.

Always use the commands provided by `uv`:

- To run a Python script: `uv run <script>.py`
- To install dependencies: `uv pip install <package>`

**Incorrect examples (do not use):**

```bash
$ python main.py # Don't do this.
$ pip install requests
```

**Correct examples:**

```bash
$ uv run main.py
$ uv pip install requests
```

In all command examples, script instructions, and documentation, **you must use the `uv` command set instead of `python` or `pip`.**