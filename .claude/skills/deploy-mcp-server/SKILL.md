---
name: deploy-mcp-server
description: Deploy the MCP server and add configuration information to the configuration file. Use when deploying the MCP server.
disable-model-invocation: true
---

# Step 3: Deploy the MCP Server

3.1 Follow the optimal deployment option to perform the deployment. During the deployment process, strictly adhere to the requirements outlined in the "Deployment Guidelines".

3.2 If the deployment is successful, proceed to Step 4; if it fails, terminate the task and strictly output "❌ @@Task Failed@@".

# Step 4: Add Configuration

4.1 Write the configuration used to connect to the MCP server into `/home/silimon/MCP-Auto/mcp_server_config/config.json`. The configuration must strictly comply with the "Configuration Information Guidelines". And then proceed to Step 5.

# Additional Tips

## Deployment Guidelines

* Distinguish between the deployment operation and the server startup operation. Do not start the server during deployment—only execute deployment-related commands. Starting the server often causes it to remain in a waiting state for input, thereby blocking the process.
- Name the server `{id}_{owner}_{name}`.
- Regardless of the deployment method used, create a dedicated project folder for this MCP server at the path `/home/silimon/MCP-Auto/mcp_server/{id}_{owner}_{name}`, and set this folder as the "cwd".
- When executing any command, use absolute paths instead of relative paths.
- For servers that need to be deployed locally, be sure to set up a separate virtual development environment for this MCP server to ensure that it does not contaminate the user’s development environment.

## Configuration Information Guidelines

- The standard structure for MCP server configurations is as follows:

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
    "cwd": "/home/silimon/MCP-Auto/mcp_server/{id}_{owner}_{name}"
}
```

* The `type` can be one of three options: `stdio`, `sse`, or `streamable_http`.
* For MCP servers using the remote deployment, the `url` must be provided.
* For MCP servers using the locally installed but transport via remote protocol deployment, the `url` must be provided, along with configurations such as `command` and `args`.
* The `url` must include the host, port, and endpoint.
* The `cwd` must be set to `/home/silimon/MCP-Auto/mcp_server/{id}_{owner}_{name}`.