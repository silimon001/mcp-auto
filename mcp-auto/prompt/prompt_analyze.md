# Step 1: List Deployment Options

1.1 Analyze whether the MCP server described in this README can be deployed on a Linux platform. Some MCP servers can only be deployed on specific platforms, such as Windows or macOS. For such servers, immediately declare the task failed and strictly output “❌ @@Task Failed@@”.

1.2 Extract all deployment options provided in the README document and categorize them according to the “Deployment Option Classification Standards.”

1.3 If the README document does not provide any concrete, feasible deployment options, design a local deployment plan yourself based on the standard MCP server deployment process.

# Step 2: Select the Optimal Deployment Option

2.1 Based on the “Criteria for Determining the Optimal Deployment Option,” select what you consider to be the best deployment option to proceed with.

2.2 Use the tool `need_use_these_tools` to accurately inform the user which development environments you will be using.

# Additional Tips

## Deployment Option Classification Standards

* **No-Installation Deployment:** Deploy using no-installation methods such as `npx` or `uvx`, which require no additional setup steps.
* **Local Deployment:** Requires using the `git` tool to clone the source code locally, followed by executing the appropriate deployment commands.
* **Remote deployment:** Remote refers to communication using remote protocols such as SSE or StreamableHTTP, without requiring the user to deploy an MCP server locally; all that is needed is the URL of the remote server.
* **Locally Installed but Deployed via Remote Protocol:** The MCP server communicates using remote protocols like SSE or StreamableHTTP, yet still requires cloning the source code locally with `git` before performing deployment operations.

**Notes**

* The README document may offer multiple deployment options. Ensure that you extract each one without duplication or omission.
* Some deployment options are related to Smithery; these projects are marked with `[PROHIBITED]`.
* Some deployment options are related to Docker; these projects are marked with `[PROHIBITED]`.
* Carefully distinguish between local deployment and locally installed deployments that use remote communication protocols.

---

## Criteria for Determining the Optimal Deployment Option

* No-installation deployment has the highest priority.
* Remote deployment has the second-highest priority.
* Local deployment has the third-highest priority.
* Locally installed deployments using remote protocols have the lowest priority.

**Notes**

* Deployment options marked `[PROHIBITED]` must not be used.

---

### Development Environments Available on the User’s Machine

* Linux (Ubuntu)

* Python (managed with uv)
* Node.js：node、npm、npx、yarn、pnpm
* Git