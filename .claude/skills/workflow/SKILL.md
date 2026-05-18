---
name: workflow
description: xxx
---

# Step 1: List Deployment Options

1.1 Analyze whether the MCP server described in this README can be deployed on a Linux platform. Some MCP servers can only be deployed on specific platforms, such as Windows or macOS. For such servers, immediately declare the task failed and strictly output "❌ @@Task Failed@@".

1.2 Extract all deployment options provided in the README document and categorize them according to the "Deployment Option Classification Standards".

1.3 If the README document does not provide any concrete, feasible deployment options, design a local deployment plan yourself based on the standard MCP server deployment process. The standard local deployment process typically includes pulling the repository, installing dependencies, building the project, and adding configurations.

# Step 2: Select the Optimal Deployment Option

2.1 Based on the "Criteria for Determining the Optimal Deployment Option", select what you consider to be the best deployment option to proceed with. And then proceed to Step 3.

# Additional Tips

## Deployment Option Classification Standards

* **Free-installation deployment:** Deploy using free-installation methods such as `npx` or `uvx`, which require no additional setup steps. This deployment method uses the local ("STDIO") transport protocol.
* **Local deployment:** Need to use the `git` tool to clone the source code to your local machine and then perform the corresponding deployment operations. The transport protocol for this deployment method can be local ("STDIO") or remote ("SSE ", "Streamable-HTTP") protocols.
* **Remote deployment:** The MCP server has been deployed on a cloud server by the developers. Users only need to write configurations and communicate with the cloud MCP server through remote transport protocols such as SSE or Streamable-HTTP.

**Notes**

* The README document may offer multiple deployment options. Ensure that you extract each one without duplication or omission.
* Some deployment options are related to Smithery; these projects are marked with `[PROHIBITED]`.
* Some deployment options are related to Docker; these projects are marked with `[PROHIBITED]`.

---

## Criteria for Determining the Optimal Deployment Option

* Free-installation deployment has the highest priority.
* Remote deployment has the second-highest priority.
* Local deployment has the third-highest priority.

**Notes**

* Deployment options marked `[PROHIBITED]` must not be used.

---

### Development Environments Available on the User’s Machine

* Linux (Ubuntu)
* Python: The user does not have Python installed. Please use uv to replace Python.
* Node.js：node、npm、npx、yarn、pnpm
* Git

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

# Step 5: Validate the Server

5.1 You need to verify that the configuration used to connect to the MCP server is correct. Here is a configuration verification application(named config_validation), and you only need to provide the name of the MCP server to perform a connection test. For example

```bash
/home/silimon/MCP-Auto/claude_code/config_validation id_onwer_name
```

# Additional Tips

## Validation Guidelines

* If the server can **start properly** and **expose tools**, the task is successful. Then strictly output "✅ @@Task Done@@".
* If an error occurs, carefully review the log messages and retrace each step to identify the cause of the issue. 
* For errors that cannot be resolved, such as API key verification failure requiring a valid API key, strictly output "⚠️ @@Task Alert@@".