# Step 3: Deploy the MCP Server

3.1 Determine whether the optimal deployment plan includes starting and verifying the MCP server. If it does, avoid starting the MCP server in Step 3; instead, start and verify the MCP server in Step 5.
3.2 Follow the optimal deployment plan to perform the deployment. If the deployment is successful, proceed to Step 4; if it fails, terminate the task and strictly output “❌ @@Task Failed@@”.

# Step 4: Add Configuration

4.1 Use the `add_config` tool to add the MCP server’s configuration information to the configuration file. Then proceed to Step 5.

# Instructions

- Name the server `{id}_{owner}_{name}`.
- When executing any commands, use absolute paths and avoid relative paths.
- The standard structure for MCP server configuration is as follows:

```json
"{id1}_{owner1}_{name1}": {
    "type": "stdio",
    "command": "npx" | "uv" | "fastmcp" | "...",
    "args": ["arg1", "arg2", "..."],
    "env": {
        "ENV_VAR1": "value1",
        "ENV_VAR2": "value2"
    },
    "cwd": "/your/path"
},
"{id2}_{owner2}_{name2}": {
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
"{id3}_{owner3}_{name3}": {
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
```

* If `type` is `stdio`, there is no need to provide `url` or `headers`.
* If `type` is `sse` or `streamable_http`, `url` must be provided. If the MCP server is also deployed locally, you must additionally provide `command`, `args`, `env`, and `cwd` to run the MCP server on the local machine. Furthermore, the port specified in `args` must match the port used in the `url`.
* If it’s not a local project, you must set the `cwd` to `{WORKSPACE}/mcp_server/` by default.