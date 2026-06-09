---
name: analyze-readme
description: Analyze an MCP server README to extract all available deployment methods (including free-install, local, and remote options), classify them, and determine the optimal deployment strategy. Use this when the task involves understanding, comparing, or selecting deployment approaches from documentation or setup guides.
disable-model-invocation: false
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