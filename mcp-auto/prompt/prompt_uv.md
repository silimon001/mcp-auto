# uv Best Practices

## What is uv?

uv is an extremely fast Python package and project manager.

**Task Requirement**: For any Python project, deployment must be performed using uv.

---

## uv Usage Guide

### Running Tools

* `uvx` is used to run command-line tools; when used, the tool is installed into a temporary isolated environment.

```bash
$ uvx --python 3.10 ruff
```

**Note**: When you execute `uvx <package>`, a server will start and wait for communication, blocking the process. Therefore, during **Step 4: Execute the Deployment Plan**, do not use this command to directly start the server, as it will cause the process to remain blocked indefinitely. The correct approach is to place the configuration information in the configuration file and then proceed to **Step 6: Verify the Server**.

## Two Methods for Setting Up a uv Project

```bash
$ uv init # Initialize the project
$ uv add <package> # Add a dependency package
$ uv sync # Create a virtual environment and install dependencies
```

Alternatively:

```bash
$ uv init # Initialize the project
$ uv venv # Create a virtual environment
$ uv pip install <package> # Install dependencies in the virtual environment
```

## Environment Setup (Guarantees)

- uv has already been deployed in the user’s development environment, so there is no need to reinstall or verify it again.
- The paths for the uv tools are as follows; please use them directly:

```bash
$ which uv
{HOME}/.local/bin/uv

$ which uvx
{HOME}/.local/bin/uvx
```

* Before executing any uv command, first navigate to the corresponding project directory:

 ```bash 
$ cd /path/to/project/dir && uv xxx
 ```

## Notes

* You must create a separate virtual environment for each project using `uv venv` or `uv sync`.
* **Important: Use `uv` to manage your Python environment and dependencies.** Once you have initialized or are managing a project with `uv`, **do not use native `python` or `pip` commands**, as these commands may bypass uv’s environment management and lead to execution failures.
* Always use the commands provided by uv:

  - To run a Python script: `uv run <script>.py`

  - To install dependencies: `uv pip install <package>`

**Incorrect Examples (Prohibited):**

```bash
$ python main.py
$ pip install requests
```

**Correct Examples:**

```bash
uv run main.py
uv pip install requests
```

In all command examples, script explanations, and documentation, **you must use the `uv` command system instead of `python` or `pip`.**