# Task

Connect to an MCP server according to the Readme document.

# Notes

* If you need to install the MCP server locally, please install it to `{WORKSPACE}/mcp_server/` and name it `{id}_{owner}_{name}`. And create an independent virtual environment for the MCP server.
* Write the configuration used to connect to the MCP server into `{WORKSPACE}/mcp_server_config/config.json`. 
* You need to verify that the configuration used to connect to the MCP server is correct. The user provides an executable file , and you only need to provide the name of the MCP server to perform a connection test. For example

```bash
{WORKSPACE}/claude_code/config_validation id_onwer_name
```

* If you can successfully connect to the MCP server and obtain the list of tools it provides, the task is successful, then strictly output "✅ @@Task Done@@".
* If any errors occur, please try to fix it.
* If you encounter problems with API-Key or other key verification methods, immediately end the task and strictly output "⚠️ @@Task Alert@@".

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