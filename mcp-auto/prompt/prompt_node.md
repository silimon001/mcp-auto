# Best Practices for Node.js

* During task execution, global installations are prohibited, such as `npm install -g <package>`.

- Install tools as project dependencies using `npm install <package>`.
- When using `npx`, you must include the `-y` flag, for example, `npx -y inspector`.



**Important Notes**: Running `npx -y <package>` will directly start the server and keep it waiting for connections, thereby blocking the process. Therefore, in Step 4, avoid using this command to launch the server directly, as it will cause the process to remain blocked. The correct approach is to proceed directly to Step 5, configure the settings in the configuration file, and then execute Step 6 to start the server and perform verification.