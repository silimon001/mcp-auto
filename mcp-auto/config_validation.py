import anyio
import asyncio
import os
import json
from dotenv import load_dotenv

from MCP_Client import Client

load_dotenv()

async def test_server(name, config: dict):
    client = Client()
    try:
        await client.init(name, config)
        tools_str = ", ".join(t.name for t in client.tools)
        print(f"\n[OK] server {name} is OK, tools: {tools_str}\n", flush=True)
    except asyncio.CancelledError:
        print(f"[WARN] server {name} init cancelled")
    except Exception as e:
        print(str(e))
    finally:
        await client.cleanup()


async def main(path: str, name: str):
    config_path = os.path.join(path)
    with open(config_path, "r", encoding="utf-8") as f:
        configs = json.load(f)

    servers = configs.get("Servers", {})
        
    if servers.get(name, None) is not None:
        await test_server(name, servers[name])
    else:
        print(f"server {name} is not exists.")

if __name__ == "__main__":

    # import sys
    # if len(sys.argv) != 3:
    #     print("用法: python script.py  <config_filename> <server_name>")
    #     sys.exit(1)

    config_path = 'mcp_server_config/1.json'
    name = "1054419133_sveltejs_mcp"

    anyio.run(lambda: main(config_path, name))
