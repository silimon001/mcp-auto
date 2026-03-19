# Step 1: Analyze the Project

1.1 Based on the information in the README document, determine whether this project is an MCP server project.

1.2 If it is an MCP server project, proceed to Step 2; if it is not an MCP server project, determine whether the project can be deployed as an MCP server.

1.3 If it cannot be deployed as an MCP server, terminate the task and strictly output “❌ @@Task Failed@@”.

# Step 2: List Deployment Options

2.1 If deployment options are provided only via external links, consider that the README document does not offer any concrete, feasible deployment methods.

2.2 If the README document provides no specific, viable deployment options whatsoever, do not make any inferences, assumptions, or associations. Instead, immediately terminate the task and strictly output “❌ @@Task Failed@@”.

2.3 List all deployment options provided in the README document, then proceed to Step 3.

# Step 3: Select the Optimal Deployment Option

3.1 Among all available options, identify and select the optimal deployment method. Inform the user of the category of the chosen deployment option.

3.2 Using the tool `need_use_these_tools`, accurately specify which development environments you will be using.

# Notes

* How to classify deployment options:
  * Server communication methods: `stdio`, `sse`, `streamable_http`
  * Server deployment location: local deployment, remote deployment
  * Whether manual installation is required: installation-based deployment (e.g., `node`, `uv`) vs. install-free deployment (e.g., `uvx`, `npx`)

* Criteria for evaluating the optimal solution:
  * The `stdio` communication method is preferred over other methods.
  * Install-free deployment is preferred over installation-based deployment.
  * Avoid deployment methods related to `Smithery`.
  * Avoid deployment methods related to `docker`.

* The user’s available development environments include:

  * Python (managed with uv)
  * Node.js
  * Git