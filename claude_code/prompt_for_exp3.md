# Task

Connect to an MCP server according to the Readme document. Complete the task in an efficient manner.

# Notes

* If you need to install the MCP server locally, please install it to `{WORKSPACE}/mcp_server/` and name it `{id}_{owner}_{name}`. And create an independent virtual environment for the MCP server.
* Use the `add_config` tool to add the MCP server’s configuration information to the configuration file.
* Use the `validate_config` tool to check whether the server can **start properly** and **expose tools**.

* If you can successfully connect to the MCP server and obtain the list of tools it provides, the task is successful, then strictly output "✅ @@Task Done@@".
* If any errors occur, please try to fix it.

# MCP server configuration example

```json
"{id}_{owner}_{name}": {
    "type": "stdio" | "sse" | "streamable_http",
    "url": "http://localhost:8000/mcp" | "http://localhost:8080/sse",
    "headers": {
    	"X-API-Key": "your-api-key-here"
    },
    "command": "uv" | "node" | "npx" | "other tools",
    "args": ["arg1", "arg2", "..."],
    "env": {
        "ENV_VAR1": "value1",
        "ENV_VAR2": "value2"
    },
    "cwd": "{WORKSPACE}/mcp_server/{id}_{owner}_{name}"
}
```

# Development Environments Available on the User’s Machine

* Linux (Ubuntu)
* Python: The user does not have Python installed. Please use uv to replace Python.
* uv path: /home/silimon/.local/bin/uv
* Node.js：node、npm、npx、yarn、pnpm