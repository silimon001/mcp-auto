# Step 4: Deploy the MCP Server

4.1 Determine whether the optimal deployment plan includes the process of starting and verifying the MCP server. If it does, avoid starting the MCP server in Step 4; instead, start and verify the MCP server in Step 6.

4.2 Follow the optimal deployment plan to perform the deployment operation. If the deployment succeeds, proceed to Step 5; if the deployment fails, terminate the task and strictly output “❌ @@Task Failed@@”.

# Step 5: Add Configuration

5.1 Use the `add_config` tool to add the configuration information for the MCP server to the configuration file. Then proceed to Step 6.

# Notes

- Name the server `{id}_{owner}_{name}`.
- When executing any commands, use absolute paths and avoid using relative paths.
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

* If `type` is `stdio`, then `url` and `headers` do not need to be provided.
* If `type` is `sse` or `streamable_http`, then `url` must be provided. If the MCP server is also deployed locally, then `command`, `args`, `env`, and `cwd` are additionally required to run the MCP server locally. In addition, `args` must specify the same port as `url`.