# Step 5: Validate the Server

5.1 Use the `validate_config` tool to check whether the server can **start properly** and **expose the corresponding tools**. During validation, strictly follow the requirements of the "Validation Guidelines".

# Additional Tips

## Validation Guidelines

* If the server starts correctly and retrieves a valid list of tools, the task is successful. Output exactly: "✅ @@Task Done@@".
* If an error occurs, carefully review the log messages and retrace each step to identify the cause of the issue. Once resolved, use the `validate_config` tool again to perform the validation.
* For unrecoverable errors, such as API key verification failure requiring a valid API key, output exactly: "❌ @@Task Failed@@".