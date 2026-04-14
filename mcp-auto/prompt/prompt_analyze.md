# Step 1: List Deployment Options

1.1 Analyze whether the MCP server described in this README can be deployed on a Linux platform. Some MCP servers can only be deployed on specific platforms, such as Windows or macOS. For such servers, immediately declare the task failed and strictly output "❌ @@Task Failed@@".

1.2 Extract all deployment options provided in the README document and categorize them according to the "Deployment Option Classification Standards".

1.3 If the README document does not provide any concrete, feasible deployment options, design a local deployment plan yourself based on the standard MCP server deployment process. The standard local deployment process typically includes pulling the repository, installing dependencies, building the project, and adding configurations.

# Step 2: Select the Optimal Deployment Option

2.1 Based on the "Criteria for Determining the Optimal Deployment Option", select what you consider to be the best deployment option to proceed with.

2.2 Use the tool `need_use_these_tools` to accurately inform the user which development environments you will be using. Then proceed to step 3.

# Additional Tips

## Deployment Option Classification Standards

* **Free-installation deployment:** Deploy using free-installation methods such as `npx` or `uvx`, which require no additional setup steps.
* **Local deployment:** Need to use the `git` tool to clone the source code to your local machine and then perform the corresponding deployment operations.
* **Remote deployment:** The MCP server has been deployed on a cloud server by the developers. Users only need to write configurations and communicate with the cloud MCP server through remote transport protocols such as SSE or Streamable-HTTP.
* **Locally installed but transport via remote protocol deployment:** These types of MCP servers require users to deploy the MCP server locally, but instead of communicating via stdio, they communicate via remote transport protocols such as SSE or Streamable-HTTP.

**Notes**

* The README document may offer multiple deployment options. Ensure that you extract each one without duplication or omission.
* Some deployment options are related to Smithery; these projects are marked with `[PROHIBITED]`.
* Some deployment options are related to Docker; these projects are marked with `[PROHIBITED]`.

---

## Criteria for Determining the Optimal Deployment Option

* Free-installation deployment has the highest priority.
* Remote deployment has the second-highest priority.
* Local deployment has the third-highest priority.
* Locally installed but transport via remote protocol deployment has the lowest priority.

**Notes**

* Deployment options marked `[PROHIBITED]` must not be used.

---

### Development Environments Available on the User’s Machine

* Linux (Ubuntu)

* Python (managed with uv)
* Node.js：node、npm、npx、yarn、pnpm
* Git