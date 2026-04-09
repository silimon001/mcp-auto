# Step 1: List Deployment Options

1.1 Analyze whether the MCP server described in this README can be deployed on a Linux platform. Some MCP servers can only be deployed on specific platforms, such as Windows or macOS. For such servers, immediately declare the task failed and strictly output "❌ @@Task Failed@@".

1.2 Extract all deployment options provided in the README document and categorize them according to the "Deployment Option Classification Standards."

1.3 If the README document does not provide any concrete, feasible deployment options, design a local deployment plan yourself based on the standard MCP server deployment process.

# Step 2: Select the Optimal Deployment Option

2.1 Based on the "Criteria for Determining the Optimal Deployment Option," select what you consider to be the best deployment option to proceed with.

2.2 Use the tool `need_use_these_tools` to accurately inform the user which development environments you will be using.

# Additional Tips

## Deployment Option Classification Standards

* **No-Installation Deployment:** Deploy using no-installation methods such as `npx` or `uvx`, which require no additional setup steps.
* **Local Deployment:** Requires using the `git` tool to clone the source code locally, followed by executing the appropriate deployment commands.
* **Remote Deployment:** Similar to no-installation deployment, it requires no manual setup; however, it necessitates a corresponding URL and necessary configuration.
* **Locally Installed but Deployed via Remote Protocol:** The MCP server communicates using remote protocols like SSE or StreamableHTTP, yet still requires cloning the source code locally with `git` before performing deployment operations.

**Notes**

* The README document may offer multiple deployment options. Ensure that you extract each one without duplication or omission.
* Carefully distinguish between local deployment and locally installed deployments that use remote communication protocols.

---

## Criteria for Determining the Optimal Deployment Option

* No-installation deployment has the highest priority.
* Remote deployment has the second-highest priority.
* Local deployment has the third-highest priority.
* Locally installed deployments using remote protocols have the lowest priority.

**Notes**

* Avoid using deployment methods related to `Smithery`.
* Avoid using deployment methods related to `docker`.

---

### Development Environments Available on the User’s Machine

* Linux (Ubuntu)

* Python (managed with uv)
* Node.js：node、npm、npx、yarn、pnpm
* Git