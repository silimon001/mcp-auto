# Step 3: Deploy the MCP Server

3.1 Follow the optimal deployment plan to perform the deployment. During the deployment process, strictly adhere to the requirements outlined in the "Deployment Guidelines."

3.2 If the deployment is successful, proceed to Step 4; if it fails, terminate the task and output exactly "❌ @@Task Failed@@".

# Step 4: Add Configuration

4.1 Use the `add_config` tool to add the MCP server’s configuration information to the configuration file. The configuration must strictly comply with the "Configuration Information Guidelines". Then proceed to step 5.

# Additional Tips

## Deployment Guidelines

- Distinguish between the deployment operation and the server startup operation. Do not start the server during deployment—only execute deployment-related commands. Starting the server often causes it to remain in a waiting state for input, thereby blocking the process.

- If you encounter timeout issues during deployment, the cause may be a slow internet connection. Try increasing the timeout period and retrying. For example, when installing dependencies times out, consider extending the timeout to 5–10 minutes.
- Name the server `{id}_{owner}_{name}`.
- Regardless of the deployment method used, create a dedicated project folder for this MCP server at the path `{WORKSPACE}/mcp_server/{id}_{owner}_{name}`, and set this folder as the "cwd."
- When executing any command, use absolute paths instead of relative paths.
- For servers that need to be deployed locally, be sure to set up a separate virtual development environment for this MCP server to ensure that it does not contaminate the user’s development environment.

## Configuration Information Guidelines

- The standard structure for MCP server configurations is as follows:

```json
"{id1}_{owner1}_{name1}": {
    "type": "stdio",
    "command": "npx" | "uv" | "fastmcp" | "...",
    "args": ["arg1", "arg2", "..."],
    "env": {
        "ENV_VAR1": "value1",
        "ENV_VAR2": "value2"
    },
    "cwd": "{WORKSPACE}/mcp_server/{id1}_{owner1}_{name1}"
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
    "cwd": "{WORKSPACE}/mcp_server/{id2}_{owner2}_{name2}"
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
    "cwd": "{WORKSPACE}/mcp_server/{id3}_{owner3}_{name3}"
}
```

* The `type` can be one of three options: `stdio`, `sse`, or `streamable_http`.
* If a remote deployment method is used, the `url` must be provided.
* The `url` must include the host, port, and endpoint.
* If local installation is combined with a remote transmission protocol for deployment, in addition to the `url`, you must also provide `command`, `args`, `env`, and `cwd` to run the MCP server locally.
* The `cwd` must be set to `{WORKSPACE}/mcp_server/{id}_{owner}_{name}`.

