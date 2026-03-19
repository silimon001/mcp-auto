from typing import Any, Optional, Dict
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

def get_safe_value(config: dict, key: str):
    tmp_value = config.get(key)
    if isinstance(tmp_value, dict) and tmp_value == {}:
        tmp_value = None
    elif isinstance(tmp_value, str) and tmp_value == '':
        tmp_value = None
    return tmp_value


# Environment variables to inherit by default
DEFAULT_INHERITED_ENV_VARS = (
    [
        "APPDATA",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "PROCESSOR_ARCHITECTURE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "USERNAME",
        "USERPROFILE",
    ]
)

import os
def get_default_environment() -> dict[str, str]:
    """
    Returns a default environment object including only environment variables deemed
    safe to inherit.
    """
    env: dict[str, str] = {}

    for key in DEFAULT_INHERITED_ENV_VARS:
        value = os.environ.get(key)
        if value is None:
            continue  # pragma: no cover

        if value.startswith("()"):  # pragma: no cover
            # Skip functions, which are a security risk
            continue  # pragma: no cover

        env[key] = value

    env['UV_DEFAULT_INDEX'] = 'https://pypi.tuna.tsinghua.edu.cn/simple'

    return env


import subprocess
import socket
import time
from typing import List

def wait_for_port(host: str, port: int, timeout: int = 30, interval: float = 0.5) -> bool:
    """
    等待某个 TCP 端口可连接，最多等待 timeout 秒
    :param host: 主机
    :param port: 端口
    :param timeout: 最大等待时间（秒）
    :param interval: 每次重试间隔（秒）
    :return: True if port is ready, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(interval)
    return False

def start_process(command: str, args: List[str] = None, env: dict = None, cwd: str = None,
                  wait_url: str = None, wait_timeout: int = 30):
    """
    启动一个长期运行的进程（如服务器），等待服务可用后继续执行
    :param command: 可执行文件
    :param args: 参数列表
    :param env: 环境变量字典
    :param cwd: 工作目录
    :param wait_url: 等待服务的 URL，例如 "http://localhost:5173/mcp"
    :param wait_timeout: 最多等待服务启动的秒数
    :return: Popen 对象
    """
    if isinstance(command, tuple):
        command = command[0]

    cmd_list = [command] + (args or [])

    process = subprocess.Popen(
        cmd_list,
        env=({**get_default_environment(), **env} if env is not None else get_default_environment()),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    import fcntl
    def make_non_blocking(file):
        """将文件描述符设置为非阻塞"""
        fd = file.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    # 将 stdout 和 stderr 设置为非阻塞
    make_non_blocking(process.stdout)
    make_non_blocking(process.stderr)

    # 等待服务器端口就绪
    if wait_url:
        from urllib.parse import urlparse
        parsed = urlparse(wait_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (80 if parsed.scheme == "http" else 443)
        print(f"Waiting for server {host}:{port} to be ready...")
        if wait_for_port(host, port, timeout=wait_timeout):
            print("Server is ready!")
        else:
            print("Timeout waiting for server to start")

    # 非阻塞读取缓冲区中已有的 stdout/stderr
    try:
        stdout = process.stdout.read() or ""
    except Exception:
        stdout = ""
    try:
        stderr = process.stderr.read() or ""
    except Exception:
        stderr = ""

    if stdout:
        print("=== STDOUT ===")
        print(stdout, end="")
    if stderr:
        print("=== STDERR ===")
        print(stderr, end="")

    return process



class Client:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools = []
        self.process = None
        self._server_process_started = False  # 标记是否由我们启动了服务器进程

    async def init(self, name: str, config: dict):
        type = config.get("type", "stdio")
        
        if type == "stdio":
            await self.init_stdio(config)
        elif type == "sse":
            await self.init_sse(config)
        elif type == "streamable_http":
            await self.init_streamable_http(config)
        else:
            raise Exception(f"[FAIL] server {name}: Unknown transport type '{type}'")       

    async def init_stdio(self, config: dict):
        server_params = StdioServerParameters(
            command=get_safe_value(config, "command"),
            args=get_safe_value(config, "args"),
            env=get_safe_value(config, "env"),
            cwd=get_safe_value(config, "cwd"))
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        read_stream, write_stream = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        
        await self.session.initialize()
        response = await self.session.list_tools()
        self.tools = response.tools if hasattr(response, 'tools') else []
            
    async def init_sse(self, config: dict):
        url = get_safe_value(config, "url")
        headers = get_safe_value(config, "headers")
        if not url:
            raise ValueError("URL is required for SSE transport")

        if get_safe_value(config, 'command') is not None:
            command = get_safe_value(config, "command"),
            args = get_safe_value(config, "args")
            env = get_safe_value(config, "env")
            cwd = get_safe_value(config, "cwd")
            start_process(command,args,env,cwd,url)


        sse_transport = await self.exit_stack.enter_async_context(sse_client(url=url, headers=headers))
        read_stream, write_stream = sse_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        
        await self.session.initialize()
        response = await self.session.list_tools()
        self.tools = response.tools if hasattr(response, 'tools') else []

    async def init_streamable_http(self, config: dict):
        url = get_safe_value(config, "url")
        if not url:
            raise ValueError("URL is required for SSE transport")

        if get_safe_value(config, 'command') is not None:
            command = get_safe_value(config, "command"),
            args = get_safe_value(config, "args")
            env = get_safe_value(config, "env")
            cwd = get_safe_value(config, "cwd")
            start_process(command,args,env,cwd,url)

        streamablehttp_transport = await self.exit_stack.enter_async_context(streamable_http_client(url=url))
        read_stream, write_stream, _ = streamablehttp_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        
        await self.session.initialize()
        response = await self.session.list_tools()
        self.tools = response.tools if hasattr(response, 'tools') else []
            
    async def cleanup(self):
        """清理所有资源，确保正确释放"""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            print(f"[WARN] Cleanup error: {e}")
        finally:
            self.session = None


