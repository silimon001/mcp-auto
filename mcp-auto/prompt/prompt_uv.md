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

* The interface varies significantly between different versions of the mcp package, which can easily lead to interface incompatibility issues when using uvx. If you encounter this problem, please use the smallest available version as the dependency. You can use this command(curl -s https://pypi.org/pypi/<package>/json | jq '.info') to get package dependency information.

```bash
$ uvx --with mcp[cli]==x.x.x <mcp server> # Version x.x.x is the minimum available version.
```

**Note**: Executing the `uvx <package>` command will start the server and wait for communication, causing the process to block. This does not necessarily mean the server failed to start. Do not use this method to verify whether the server can start, because even if the server starts normally, it will time out while waiting for input.

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