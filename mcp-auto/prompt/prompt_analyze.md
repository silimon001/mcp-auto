# Step 1: List Deployment Options

1.1 If deployment options are provided only via external links, the README document is considered to lack a concrete, actionable deployment plan.
1.2 If the README document does not provide any concrete, actionable deployment option, no further reasoning, assumptions, or inferences should be made. Immediately terminate the task and strictly output “❌ @@Task Failed@@”.
1.3 List all deployment options provided in the README document, then proceed to Step 2.

# Step 2: Select the Optimal Deployment Option

2.1 Among all available options, identify and select the optimal deployment method. Inform the user of the category to which this optimal option belongs.
2.2 Using the tool `need_use_these_tools`, accurately specify which development environments you will be using.

# Notes

* How to categorize deployment options:
  * Server communication methods: `stdio`, `sse`, `streamable_http`
  * Server deployment location: local deployment, remote deployment
  * Whether manual installation is required: installation-based deployment (e.g., `node`, `uv`) vs. install-free deployment (e.g., `uvx`, `npx`)

* Criteria for evaluating the optimal option:
  * The `stdio` communication method is preferred over other methods.
  * Install-free deployment is preferred over installation-based deployment.
  * Avoid deployment options related to `Smithery`.
  * Avoid deployment options related to `docker`.

* The user’s available development environments include:
  * Python (managed with uv)
  * Node.js
  * Git