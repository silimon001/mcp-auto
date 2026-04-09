# uv Best Practices

## What is uv?

uv is an extremely fast Python package and project manager.

## Mandatory Requirements (Must Follow)

* For any Python project, deployment using `uv` is mandatory.
* You must create a separate virtual development environment for each MCP server project using the commands `uv venv` or `uv sync`.
* You must use `uv` to manage Python environments and dependencies. The commands `python` or `pip` are prohibited because they bypass the separate virtual development environment and disrupt the user's local development environment.
* Replace the Python and pip commands in the deployment tutorial with the following:
  - Running Python scripts: Use `uv run <script>.py`, do not use `python <script>.py`
  - Installing dependencies: `uv pip install <package>`, do not use `pip install <package>`

---

## uv Usage Guide

### Running Tools

* `uvx` is used to run command-line tools. When used, the tool is installed into a temporary, isolated environment.

```bash
$ uvx --python 3.10 ruff
```

**Note**: When you execute `uvx <package>`, it starts a server and waits for communication, blocking the process. Therefore, during **Step 4: Execute the Deployment Plan**, do not use this command to directly start the server, as it will cause the process to remain blocked indefinitely. Instead, configure the settings in the configuration file and then proceed to **Step 6: Verify the Server**.

## Two Methods for Setting Up a uv Project

For any project, follow the steps carefully and manage the project using uv.

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

- uv has already been deployed to the user’s development environment; simply use it directly.

```bash
$ which uv
{HOME}/.local/bin/uv

$ which uvx
{HOME}/.local/bin/uvx
```

* Always navigate to the project directory before running any uv commands.

```bash
$ cd /path/to/project/dir && uv xxx
```