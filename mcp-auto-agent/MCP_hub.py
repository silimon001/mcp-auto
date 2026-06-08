import asyncio
import json
from openai import AsyncOpenAI
import os
from MCP_Client import Client

from dotenv import load_dotenv

load_dotenv('.mcp-auto_env')

test_flag = True

API_KEY = ''

if test_flag:
    API_KEY = os.getenv("QWEN_TMP_KEY")
else:
    API_KEY = os.getenv("QWEN_MCP_AUTO_KEY")

class MCPHost:

    def __init__(self):
        self.mcp_client = None
        self.messages = []

    async def connect(self, name: str, config: dict):
        self.mcp_client = Client()
        print(config)
        await self.mcp_client.init(name, config)

        print(f"[CONNECTED] {name}")

        print("\nAvailable tools:\n")

        for tool in self.mcp_client.tools:
            print(f"- {tool.name}")

    def build_openai_tools(self):
        tools = []

        for tool in self.mcp_client.tools:

            tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema
                }
            })

        return tools

    async def call_tool(self, tool_name: str, arguments: dict):

        print(f"\n[TOOL CALL] {tool_name}")
        print(arguments)

        result = await self.mcp_client.session.call_tool(
            tool_name,
            arguments
        )

        if hasattr(result, "content"):
            texts = []

            for item in result.content:
                if hasattr(item, "text"):
                    texts.append(item.text)

            return "\n".join(texts)

        return str(result)

    async def chat(self):

        tools = self.build_openai_tools()

        print("\n=== MCP Host Started ===\n")

        while True:
            from openai import OpenAI

            user_input = input("\nYou > ")

            if user_input.strip().lower() in ["exit", "quit"]:
                break

            self.messages.append({
                "role": "user",
                "content": user_input
            })

            while True:

                session = OpenAI(
                    api_key=API_KEY,
                    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                )
                response = session.chat.completions.create(
                    model='qwen3.5-plus',
                    messages=self.messages,
                    tools=tools,
                    stream=False,
                    temperature=0.1, # (0, 2]
                    tool_choice="auto",
                    extra_body={"enable_thinking": True}
                )

                msg = response.choices[0].message

                # tool call
                if msg.tool_calls:

                    self.messages.append(msg)

                    for tool_call in msg.tool_calls:

                        tool_name = tool_call.function.name

                        arguments = json.loads(
                            tool_call.function.arguments
                        )

                        result = await self.call_tool(
                            tool_name,
                            arguments
                        )
                        print("Tool result: ", result)
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })

                    continue

                # final response
                final_text = msg.content

                print(f"\nAssistant > {final_text}")

                self.messages.append({
                    "role": "assistant",
                    "content": final_text
                })

                break

        await self.mcp_client.cleanup()


async def main():

    with open("MCP-Auto-Server/mcp_server_config.json", "r") as f:
        configs = json.load(f)

    configs = configs.get("Servers", {})

    name, config = next(iter(configs.items()))

    host = MCPHost()

    await host.connect(name, config)

    await host.chat()


if __name__ == "__main__":
    asyncio.run(main())