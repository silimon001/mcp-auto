# Step 6: Verify the Server

6.1 Use the `validate_config` tool to check whether the server can **start properly** and **expose the relevant APIs**.

* If the server passes validation and a list of specific tools is retrieved, strictly output “✅ @@Task Done@@”.
* If validation fails due to missing sensitive information such as **API keys, tokens, or URLs**, this is not considered a fixable issue. In this case, strictly output “⚠️ @@Task Alert@@”, terminate the task, and prompt the user to manually configure these sensitive settings.

6.2 If validation fails because of an error during the deployment process, resolve the issue, restart the server, and perform another validation.

6.3 If the server fails validation three times and cannot be repaired, strictly output “❌ @@Task Failed@@”.