Set up the MCP server while adhering to these MCP server installation rules:

* Complete the task based on the information provided in the README document of the MCP server.
* Use `{id}_{owner}_{name}` as the server name in `{WORKSPACE}/mcp_server_config/config.json`.
* Before you begin the installation, please create a new MCP server directory under the `{WORKSPACE}/mcp_server/` directory.
* Make sure you read the user's existing config.json file before editing it with this new mcp, to not overwrite any existing servers.
* The configuration includes the following fields: `type`, `url`, `headers`, `command`, `args`, `env`, and `cwd`.
* Use commands aligned with the user's shell and operating system best practices.
* Use an executable file (named config_validation; do not attempt to read it as a file) to validate the new configuration added to config.json. For example

```bash
{WORKSPACE}/claude_code/config_validation {id}_{owner}_{name}
```

* When the verification program indicates a successful connection and exposes the tool list, the task is successful, and then strictly output "✅ @@Task Done@@".

# Development Environments Available on the User’s Machine

* Python: The user does not have Python installed. Please use uv to replace Python.
* uv path: /home/silimon/.local/bin/uv
* Node.js：node、npm、npx、yarn、pnpm