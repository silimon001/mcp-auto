# Node.js Best Practices

* During deployment, do not use global installation commands such as `npm install -g <package>`. Instead, create a separate virtual development environment within the corresponding project directory and perform all installations inside that environment.

- When using `npx`, always include the `-y` flag, for example, `npx -y inspector`.

**Important Notes**: Running `npx -y <package>` will directly start the server and keep it waiting for connections, thereby blocking the process. Therefore, in Step 4, avoid using this command to start the server directly, as it will cause the process to remain blocked. The correct approach is to proceed directly to Step 5, configure it in the configuration file, and then execute Step 6 to start the server and verify its operation.