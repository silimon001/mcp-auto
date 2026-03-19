# Best practices for Git

* Please use `mkdir -p {WORKSPACE}/mcp_server` in combination with `git clone`.

```bash
$ mkdir -p {WORKSPACE}/mcp_server && git clone xxx
```

* When using `git clone`, you must clone via the SSH protocol, in the format `git clone git@github.com:user/repo.git {WORKSPACE}/mcp_server/{id}_{owner}_{name}`; avoid using the HTTPS protocol.
* Pull the repository into the `{WORKSPACE}/mcp_server/` directory.
* Carefully verify that the repository path is correct to prevent cloning the wrong repository or placing the code in the wrong directory.