# Git Best Practices

* If the `{WORKSPACE}/mcp_server` directory already exists, you can directly clone the project into `{WORKSPACE}/mcp_server/{id_owner_name}`.

```bash
$ git clone git@github.com:{owner}/{name}.git {WORKSPACE}/mcp_server/{id_owner_name}
```

* When using `git clone`, you must use the SSH protocol, in the format `git clone git@github.com:user/repo.git {WORKSPACE}/mcp_server/{id}_{owner}_{name}`; avoid using the HTTPS protocol.
* Please carefully verify that the repository path is correct to prevent cloning the wrong repository or placing the code in the wrong directory.