import asyncio
from typing import Optional, Dict
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import requests
import logging
import sys

from MCP_Client import Client

load_dotenv()

class Colors:
    OK = "\033[92m"      # 绿色
    WARN = "\033[93m"    # 黄色
    ERR = "\033[91m"     # 红色
    RESET = "\033[0m"

class MCPHub:
    def __init__(self, enable_logging: bool = False):
        self.clients: Dict[str, Client] = {}

        self.tools_messages = []
        self.messages = []

        self.base_url = None
        self.headers = None
        self.model = None
        self.api_key = None

        self.is_streaming = False
        self.enable_thinking = False

        self.log_queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(1)  # 限制最多并发 1 个初始化

        self.enable_logging = enable_logging

        if enable_logging:
            # ---------------- 初始化日志 ---------------- #
            logging.basicConfig(
                filename=f"data/log/MCP_HUB.log",
                level=logging.INFO,  # 默认日志级别
                format='%(asctime)s - %(levelname)s - %(message)s',
                filemode='a'
            )
            logging.info("MCP_HUB is running")

    def clear_context(self):
        self.messages = self.messages[0]

    def select_model(self, model, base_url, prompt = 'You are a helpful assistant.', headers = None, api_key = None, is_streaming = False, enable_thinking = False):
        self.model = model
        self.base_url = base_url
        self.messages.append({'role': 'system', 'content': prompt})
        self.headers = headers
        self.api_key = api_key
        self.is_streaming = is_streaming
        self.enable_thinking = enable_thinking

    async def call_tool(self, server_name, tool_name, tool_args):
        result = await self.clients[server_name].session.call_tool(tool_name, tool_args)
        response = result.content[0].text
        # import time
        # time.sleep(10)
        return response

    async def log(self, msg: str, level="INFO"):
        """统一异步日志函数"""
        if level == "OK":
            msg = f"{Colors.OK}{msg}{Colors.RESET}"
        elif level == "WARN":
            msg = f"{Colors.WARN}{msg}{Colors.RESET}"
        elif level == "ERROR":
            msg = f"{Colors.ERR}{msg}{Colors.RESET}"
        await self.log_queue.put(msg)

    async def logger_task(self):
        """单独日志输出协程"""
        while True:
            msg = await self.log_queue.get()
            print(msg)
            sys.stdout.flush()
            self.log_queue.task_done()

    async def connect_servers(self, configs):
        """并行连接所有 MCP servers"""
        asyncio.create_task(self.logger_task())  # 启动日志任务

        servers = configs.get("Servers", {})
        print(f"Found {len(servers)} servers in configuration.")
        tasks = []
        for name, config in servers.items():
            task = asyncio.create_task(self._limited_add_client(name, config))
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.log_queue.join()  # 等待日志全部输出完毕
        await self.log(f"MCP Host Started!", level="OK")

    async def _limited_add_client(self, name, config, timeout=10):
            """每个服务器的初始化（带限流+超时）"""
            async with self.semaphore:  # 并发限制
                try:
                    await self.log(f"[INIT] Starting {name}...")
                    # 带超时执行初始化
                    await asyncio.wait_for(self.add_client(name, config), timeout=timeout)
                    await self.log(f"[OK] {name} initialized successfully.", level="OK")

                except asyncio.TimeoutError:
                    await self.log(f"[TIMEOUT] {name} initialization exceeded {timeout}s, cancelled.", level="WARN")

                except asyncio.CancelledError:
                    await self.log(f"[CANCELLED] {name} initialization cancelled.", level="WARN")

                except Exception as e:
                    await self.log(f"[ERROR] {name} initialization failed: {e}", level="ERROR")

    async def _safe_add_client(self, name, config):
        """带错误保护的 add_client 包装"""
        try:
            await self.log(f"[INIT] Starting {name}...")
            await self.add_client(name, config)
            await self.log(f"[OK] {name} initialized successfully.", level="OK")
        except asyncio.CancelledError:
            await self.log(f"[CANCELLED] {name} initialization cancelled.", level="WARN")
        except Exception as e:
            await self.log(f"[ERROR] {name} initialization failed: {e}", level="ERROR")

    async def add_client(self, name: str, config: dict):
        """原始客户端添加逻辑"""
        client = Client()
        client.transport = config.get('type')
        try:
            await client.init(
                command=config.get('command'),
                args=config.get('args', []),
                envs=config.get('env'),
            )
            if not client.session:
                await self.log(f"[SKIP] Client {name} failed to initialize, continuing...", level="WARN")
                return
            self.clients[name] = client
            for tool in client.tools:
                await self.fill_tools_message(name, tool)
            await self.log(f"Client {name} initialized with tools: {[tool.name for tool in client.tools]}", level="OK")
        except asyncio.CancelledError:
            await self.log(f"[CANCELLED] Client {name} init cancelled.", level="WARN")
            raise
        except Exception as e:
            await self.log(f"[ERROR] Unexpected failure initializing {name}: {e}", level="ERROR")
            raise

    async def fill_tools_message(self, name: str, tool):
        self.tools_messages.append({
            "type": "function",
            "function": {
                "name": f"{name}-{tool.name}",
                # "name": f"{tool.name}",
                "description": tool.description or '',
                "parameters": {
                    "type": tool.inputSchema.get('type', ''),
                    "properties": tool.inputSchema.get('properties', {}),
                    "required": tool.inputSchema.get('required', [])
                },
            }
        })

    def delete_reasoning(self, msg: dict) -> dict:
        """移除模型中的推理字段"""
        if 'reasoning_content' in msg:
            msg = {k: v for k, v in msg.items() if k != 'reasoning_content'}
        return msg

    def communicate(self) -> dict:
        response = {}
        if self.base_url == 'https://api.siliconflow.cn/v1/chat/completions':
            payload = {
                "model": self.model,
                "messages": self.messages,
                "stream": self.is_streaming,
                "max_tokens": 512,
                "temperature": 0,
                "tools": self.tools_messages,
                }
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            print(response.json())
            response = response.json().get('choices')[0].get('message')
        elif self.base_url == 'https://api.siliconflow.cn/v1/messages':
            print("暂不支持该接口")
            pass
        elif self.base_url == 'https://api.deepseek.com':
            session = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            response = session.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools_messages,
                stream=self.is_streaming,
                temperature=0,
                tool_choice="auto",
            ).choices[0].message.to_dict()
        elif self.base_url == 'https://dashscope.aliyuncs.com/compatible-mode/v1':
            session = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            response = session.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools_messages,
                stream=self.is_streaming,
                temperature=0,
                tool_choice="auto",
                extra_body={"enable_thinking": self.enable_thinking}
            ).choices[0].message.to_dict()

        return self.delete_reasoning(response)

    def logging(self, content, is_error = False):
        print(content)
        if self.enable_logging:
            if is_error:
                logging.error(content)
            else:
                logging.info(content)
    
    async def chat_loop(self):
        self.logging("\nMCP Host Started!\nType your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                self.logging(f"User Query: {query}")
                if query.lower() == 'quit':
                    self.logging("it's over!")
                    break
                await self.process_query(query)
            except Exception as e:
                self.logging(f"Error: {str(e)}", is_error = True)

    async def process_query(self, query: str) -> str:
        self.messages.append({"role": "user", "content": query})
        if self.is_streaming:
            return await self.streamable_chat()
        else:
            return await self.direct_chat()

    async def direct_chat(self):
        response = self.communicate()
        self.messages.append(response)

        while response.get('tool_calls'):
            self.logging(' Response : ' + response.get('content'))
            for tool_call in response.get('tool_calls'):
                server_name = tool_call.get('function').get('name').split('-')[0]
                tool_name = tool_call.get('function').get('name').replace(f"{server_name}-", "")
                tool_args = eval(tool_call.get('function').get('arguments'))
                self.logging(f"[准备调用工具] Server: {server_name}, Tool: {tool_name}, Args: {tool_args}")

                if input("是否继续调用？(y/n): ").strip().lower() == 'y':
                    call_tool_result = await self.call_tool(server_name, tool_name, tool_args)
                else:
                    call_tool_result = "用户选择不调用该工具。"
              
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get('id'),
                    "content": "调用结果：\n" + call_tool_result
                })
                self.logging('调用结果: \n' + call_tool_result + '\n----------------------------------------------------\n')

            response = self.communicate()
            self.messages.append(response)
        else:
            self.logging(' Response : ' + response.get('content'))

    async def streamable_chat():
        pass

    async def cleanup(self):
        for name, client in self.clients.items():
            try:
                if client.session:
                    await client.close()
                else:
                    print(f"[SKIP] Cleanup: {name} had no active session.")
            except Exception as e:
                print(f"[WARN] Cleanup failed for {name}: {e}")


async def main():
    hub = MCPHub(enable_logging=True)


    config_path = os.path.join(os.getcwd(), "server_benchmark/mcp_server_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        configs = json.load(f)

    headers = {
        "Authorization": f"Bearer {os.getenv('siliconflow_api_key')}",
        "Content-Type": "application/json"
    }

    model = 'qwen3-coder-plus'  # Qwen/Qwen3-235B-A22B-Instruct-2507 deepseek-reasoner qwen3-coder-plus
    base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'  # https://api.siliconflow.cn/v1/chat/completions https://api.deepseek.com https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key = os.getenv('QWEN_API_KEY')  # siliconflow_api_key DEEPSEEK_API_KEY QWEN_API_KEY

    try:
        hub.select_model(model=model,
                         base_url=base_url,
                         headers=headers,
                         api_key=api_key,
                         is_streaming=False,
                         enable_thinking=False
                         )
        await hub.connect_servers(configs)
        await hub.chat_loop()
    finally:
        await hub.cleanup()

if __name__ == '__main__':
    asyncio.run(main())