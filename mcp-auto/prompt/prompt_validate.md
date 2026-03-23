# Step 5: Verify the Server

5.1 Use the `validate_config` tool to check whether the server can **start properly** and **expose the relevant APIs**.

* If the server passes validation and a list of specific APIs is retrieved, strictly output “✅ @@Task Done@@”;
* If the server fails validation due to missing sensitive information such as **API keys, tokens, or URLs**, this is not considered a fixable issue. In this case, strictly output “⚠️ @@Task Alert@@”, end the task, and prompt the user to manually configure these sensitive settings.

5.2 If the server fails validation because of an error during deployment, fix the issue, restart the server, and perform the validation again.
5.3 If the server fails validation three times and cannot be repaired, strictly output “❌ @@Task Failed@@”.