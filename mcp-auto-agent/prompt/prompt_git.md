# Git Best Practices

* To reduce the number of dialogue rounds, please combine these two commands. For example:

```bash
$ mkdir -p {WORKSPACE}/mcp_server && git clone git@github.com:{owner}/{name}.git {WORKSPACE}/mcp_server/{id_owner_name}
```

Simultaneously create folders and pull the repository.

* When using `git clone`, you must use the SSH protocol, in the format `git clone git@github.com:user/repo.git {WORKSPACE}/mcp_server/{id}_{owner}_{name}`; avoid using the HTTPS protocol.
* Please carefully verify that the repository path is correct to prevent cloning the wrong repository or placing the code in the wrong directory.