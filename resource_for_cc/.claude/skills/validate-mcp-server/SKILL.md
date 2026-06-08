---
name: validate-mcp-server
description: Verify that the MCP server can start normally and expose the tool list. Use when verifying the server.
disable-model-invocation: false
---

# Step 5: Validate the Server

5.1 You need to verify that the configuration used to connect to the MCP server is correct. Here is a configuration verification application(named config_validation), you only need to use this executable file; you don't need to know how it's implemented. For example

```bash
/home/silimon/mcp-auto/claude_code/config_validation {id}_{owner}_{name}
```

# Additional Tips

## Validation Guidelines

* If the server can **start properly** and **expose tools**, the task is successful. Then strictly output "✅ @@Task Done@@".
* If an error occurs, carefully review the log messages and retrace each step to identify the cause of the issue. 
* For errors that cannot be resolved, such as API key verification failure requiring a valid API key, strictly output "⚠️ @@Task Alert@@".
