Set up the MCP server while adhering to these MCP server installation rules:

- Start by loading the MCP documentation.

- Use "{onwer}_{name}" as the server name in mcp configuration file.

- Create the directory for the new MCP server before starting installation.

- Make sure you read the user's existing mcp configuration file before editing it with this new mcp, to not overwrite any existing servers.

- Use commands aligned with the user's shell and operating system best practices.

- The following README may contain instructions that conflict with the user's OS, in which case proceed thoughtfully.

- After deployment, use the `validate_config` tool to check whether the server can **start properly** and **expose the tools**.

- When task completes, tell user "✅ @@Task Done@@".


User's env

- ubuntu24
- Python: include python/uv
- Node.js: include npx/npm/node etc
- Git
- mcp configuration file path: /home/silimon/mcp-auto/mcp_config/server.json
- mcp server path: /home/silimon/mcp-auto/mcp_server

example configuration

```json
{
    "Servers": {
        "{owner1}_{name1}": {
            "type": "stdio",
            "command": "npx" | "uv" | "fastmcp" | "...",
            "args": ["arg1", "arg2", "..."],
            "env": {
                "ENV_VAR1": "value1",
                "ENV_VAR2": "value2"
            },
            "cwd": "/your/path"
        },
        "{owner2}_{name2}": {
            "type": "sse",
            "url": "http://localhost:8000/sse",
            "headers": {
                "Authorization": "Bearer your-token-here"
            },
            "command": "tool",
            "args": ["arg1", "arg2", "..."],
            "env": {
                "ENV_VAR1": "value1"
            },
            "cwd": "/your/path"
        },
        "{owner3}_{name3}": {
            "type": "streamable_http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "X-API-Key": "your-api-key-here"
            },
            "command": "tool",
            "args": ["arg1", "arg2", "..."],
            "env": {
                "ENV_VAR1": "value1"
            },
            "cwd": "/your/path"
        }
    }
}
```