import anyio
import asyncio
import os
import json
from dotenv import load_dotenv

from MCP_Client import Client

async def test_server(name, config: dict):
    client = Client()
    try:
        await client.init(name, config)
        tools_str = ", ".join(t.name for t in client.tools)
        if tools_str == '':
            print(f"\n[Warning] The server {name} started successfully, but no tools were found.", flush=True)
        else:
            print(f"\n[OK] The server {name} started successfully, tools: {tools_str}\n", flush=True)
    except asyncio.CancelledError:
        print(f"[WARN] The server {name} init cancelled")
    except Exception as e:
        print(str(e))
    finally:
        await client.cleanup()


def normalize_key(key: str) -> str:
    return (
        key.lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )


def looks_like_server_config(obj: dict) -> bool:
    """
    判断是否像单个 MCP server 配置
    """
    return any(
        key in obj
        for key in ("command", "url", "transport")
    )


async def main(path: str, name: str):
    config_path = os.path.join(path)

    with open(config_path, "r", encoding="utf-8") as f:
        configs = json.load(f)

    if not isinstance(configs, dict):
        print("Invalid config format.")
        return

    normalized = {
        normalize_key(k): v
        for k, v in configs.items()
    }

    # 1. 标准格式
    servers = (
        normalized.get("servers")
        or normalized.get("mcpservers")
    )

    # 2. fallback:
    #    整个文件本身就是 server map
    if servers is None:
        if all(
            isinstance(v, dict)
            for v in configs.values()
        ):
            servers = configs

    # 3. fallback:
    #    整个文件本身是单个 server config
    if servers is None and looks_like_server_config(configs):
        servers = {
            name: configs
        }

    if not isinstance(servers, dict):
        print("No server configuration found.")
        return

    if name in servers:
        await test_server(name, servers[name])
    else:
        print(f"The server {name} does not exist.")


if __name__ == "__main__":

    import sys
    if len(sys.argv) != 3:
        print("Usage: python script.py  <config_filename> <server_name>")
        sys.exit(1)

    config_path = str(sys.argv[1])
    name = str(sys.argv[2])

    anyio.run(lambda: main(config_path, name))
