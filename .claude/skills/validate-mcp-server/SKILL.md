---
name: validate-mcp-server
description: Verify that the MCP server can start normally and expose the tool list. Use when verifying the server.
disable-model-invocation: true
---

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
