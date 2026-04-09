import asyncio
from datetime import datetime
from typing import Optional, Dict
import os
import json
import re
import time
from glob import glob
from dotenv import load_dotenv
from openai import OpenAI
import requests
import logging

from MCP_Client import Client
from mcp import Tool

import simplify
from dataset_setting import dataset_name

load_dotenv('.mcp-auto_env')

os.makedirs(f"{os.getcwd()}/mcp_server", exist_ok=True)

class MCPHub:
    def __init__(self, pos, count, enable_logging: bool = False):
        self.clients: Dict[str, Client] = {}

        # context
        self.all_tools_messages = []
        self.selected_tool_message = []
        self.messages = []

        self.communicate_count = 0
        self.enable_logging = enable_logging

        # LLM
        self.base_url = None
        self.headers = None
        self.model = None
        self.api_key = None

        self.is_streaming = False
        self.enable_thinking = False

        # automation
        self.auto_deploy = False

        if enable_logging:
            # ---------------- 初始化日志 ---------------- #
            os.makedirs(f"{os.getcwd()}/log_file", exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_filename = f"{os.getcwd()}/log_file/AMSD_{dataset_name}_{pos}_{pos+count}_{timestamp}.log"
            print(log_filename)
            logging.basicConfig(
                filename=log_filename,
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                filemode='w',
                force=True
            )
            logging.info("mcp-auto is running!")

    async def shutdown(self):
            for name, client in self.clients.items():
                try:
                    if self.enable_logging:
                        self.log(f"Shutting down client-server connect: {name}")
                    await client.cleanup()
                except Exception as e:
                    print(f"Error shutting down client-server connect {name}: {e}")

    def log(self, content, is_error = False):
        print(content)
        if self.enable_logging:
            if is_error:
                logging.error(content)
            else:
                logging.info(content)

    def select_model(self, model, base_url, headers = None, api_key = None, is_streaming = False, enable_thinking = False):
        self.model = model
        self.base_url = base_url
        self.headers = headers
        self.api_key = api_key

        self.is_streaming = is_streaming
        self.enable_thinking = enable_thinking

    async def connect_servers(self, configs: dict):
        servers = configs.get("Servers", {})
        for name, config in servers.items():
            client = Client()
            try:
                await client.init(name, config)
            except Exception as e:
                self.log(str(e), is_error=True)
                return
            self.clients[name] = client
            for tool in client.tools:
                self.fill_tools_message(tool)
            self.log(f"Client {name} initialized with tools: {[tool.name for tool in client.tools]}")

    def fill_tools_message(self, tool: Tool):
        tool_message = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": tool.inputSchema.get('type', 'object'),
                    "properties": tool.inputSchema.get('properties', {}),
                    "required": tool.inputSchema.get('required', [])
                }
            }
        }
        self.all_tools_messages.append(tool_message)

    def communicate(self) -> dict:
        response = None
        if self.base_url == 'https://dashscope.aliyuncs.com/compatible-mode/v1':
            session = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            response = session.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.selected_tool_message,
                stream=self.is_streaming,
                temperature=0.1, # [0,2)
                tool_choice="auto",
                extra_body={"enable_thinking": self.enable_thinking}
            )
            usage = response.usage.to_dict()
            choices = response.choices[0].message.to_dict()

        self.communicate_count += 1
        self.log(f"--- Communicate Count: {self.communicate_count} ---")
    
        return {
            'usage': usage,
            'response': self.delete_reasoning(choices)
        }

    def delete_reasoning(self, msg: dict) -> dict:
        """remove reasoning content"""
        if 'reasoning_content' in msg:
            msg = {k: v for k, v in msg.items() if k != 'reasoning_content'}
        return msg

    async def call_tool(self, server_name, tool_name, tool_args):
        result = await self.clients[server_name].session.call_tool(tool_name, tool_args)
        response = result.content[0].text
        if tool_name == 'execute_command':
            response = self.simplify_context(response, tool_args)

        return response

    async def chat_loop(self, prompt, query, id, readme_path, max_chat_loop):
        self.communicate_count = 0
        self.log(f'dealing with {id} {readme_path} ...')
        self.log(f'\n=========\n{query}\n==========\n')
        try:
            self.messages = []
            self.messages.append({"role": "system", "content": prompt})
            self.messages.append({"role": "user", "content": query})
            while True:
                if self.communicate_count == 0:
                    analyze_prompt = self.dynamic_prompt(['analyze',])
                    self.messages.append({"role": "system", "content": analyze_prompt})
                    self.selected_tool_message = self.dynamic_tool(['need_use_these_tools'])
                elif self.communicate_count >= max_chat_loop:
                    break
                
                all_response = self.communicate()
                usage = all_response['usage']
                self.log('Token Usage: ' + json.dumps(usage, ensure_ascii=False))
                response = all_response['response']
                self.messages.append(response)
                content = self.messages[-1].get('content')
                self.log('Response: ' + content)

                if response.get('tool_calls') is not None:
                    for tool_call in response.get('tool_calls'):
                        server_name = "MCP-Auto"
                        tool_name = tool_call.get('function').get('name')
                        tool_args = json.loads(tool_call.get('function').get('arguments'))
                        self.log(f"[Call Tool] Server: {server_name}, Tool: {tool_name}, Args: {tool_args}")                    

                        if self.auto_deploy:
                            call_tool_result = await self.call_tool(server_name, tool_name, tool_args)
                        else:
                            if input("(Y/N): ").strip().lower() == 'y':
                                call_tool_result = await self.call_tool(server_name, tool_name, tool_args)
                            else:
                                call_tool_result = "Users refuse to use this tool; please reflect on this and choose the right tool."
                    
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get('id'),
                            "content": call_tool_result
                        })
                        self.log('\n' + call_tool_result + '\n----------------------------------------------------\n')

                        if tool_name == 'need_use_these_tools':
                            # message = self.messages.pop(2) # delete analyze_prompt
                            # message = message.get('content', '')
                            # self.log("Delete analyze_prompt. First line: " + message.split('\n')[0])

                            self.selected_tool_message = self.dynamic_tool(['add_config', 'execute_command'])
                            deploy_prompt = self.dynamic_prompt(['deploy'])
                            self.messages.append({"role": "system", "content": deploy_prompt})

                            tools_prompt = self.dynamic_prompt(json.loads(call_tool_result))
                            self.messages.append({"role": "system", "content": tools_prompt})

                        elif tool_name == 'add_config':
                            # message = self.messages.pop(4) # delete deploy_prompt
                            # message = message.get('content', '')
                            # self.log("Delete deploy_prompt. First line: " + message.split('\n')[0])

                            self.selected_tool_message = self.dynamic_tool(['validate_config'])
                            validate_prompt = self.dynamic_prompt(['validate'])
                            self.messages.append({"role": "system", "content": validate_prompt})

                        elif tool_name == 'validate_config':
                            self.selected_tool_message = self.dynamic_tool(['fix_config', 'execute_command', 'validate_config'])
                        
                else:
                    if content.find("✅ @@Task Done@@") != -1 or content.find("❌ @@Task Failed@@") != -1 or content.find("⚠️ @@Task Alert@@") != -1:
                        break
                    # query = input("user's input:")
                    query = 'come on!'
                    self.messages.append({"role": "user", "content": query})
        except Exception as e:
            self.log(f"Error: {str(e)}", is_error = True)        

    def dynamic_prompt(self, names: list[str]):
        prompt = ''
        for name in names:
            try:
                with open(f"mcp-auto/prompt/prompt_{name}.md", "r", encoding="utf-8") as f:
                    prompt += f.read()
                self.log(f"add the prompt of {name}")
                if name == 'git' or name == 'deploy':
                    from pathlib import Path

                    def git_fix_prompt(template: str) -> str:
                        workspace = Path.cwd()
                        return template.replace("{WORKSPACE}", str(workspace))
                    prompt = git_fix_prompt(prompt)

                elif name == 'uv':
                    from pathlib import Path

                    def uv_fix_prompt(template: str) -> str:
                        home_dir = Path.home()
                        return template.replace("{HOME}", str(home_dir))
                    prompt = uv_fix_prompt(prompt)

            except Exception as e:
                pass
        return prompt

    def dynamic_tool(self, names: list[str]):
        selected_tool_message = []
        for tool_message in self.all_tools_messages:
            if tool_message.get('function').get('name') in names:
                selected_tool_message.append(tool_message)
                self.log(f"add the tool message of {tool_message.get('function').get('name')}")
        return selected_tool_message

    def simplify_context(self, text: str, tool_args) -> str:
        text = simplify.simplify_log(text)
        return text

def add_extra_info(dataset_name = None, id = None):
        final_text = ''
        if dataset_name:
            with open(f"data/dataset/{dataset_name}/repo_info.json", 'r', encoding='utf-8') as f:
                repo_infos = json.load(f)
            for repo_info in repo_infos:
                if repo_info.get('id') == int(id):
                    info = {k: repo_info.get(k) for k in ["id", "description", "language", "size", "topic", "html_url"]}
                    info['owner'] = repo_info.get('full_name').split('/')[0]
                    info['name'] = repo_info.get('full_name').split('/')[1]
                    final_text += f'\n=== REPO INFO START ===\n{info}\n=== REPO INFO END ===\n'
                    break

        return final_text

async def main():
    pos = 0
    count = 20

    hub = MCPHub(pos, count, enable_logging=True)

    headers = None
    model = 'qwen3-coder-plus'  # deepseek-reasoner qwen3-coder-plus qwen3-coder-flash
    base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'  # https://api.deepseek.com https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key = os.getenv('QWEN_API_KEY')  # siliconflow_api_key DEEPSEEK_API_KEY QWEN_API_KEY
    hub.select_model(model, base_url, headers, api_key, is_streaming=False, enable_thinking=True)

    config_path = os.path.join(os.getcwd(), "MCP-Auto-Server/mcp_server_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        configs = json.load(f)
    await hub.connect_servers(configs)

    readme_repos = sorted(
        glob(os.path.join(f"data/dataset/{dataset_name}/sampled_validated_readme", "*.md")),
        key=os.path.getsize,
        # reverse=True
    )
    hub.auto_deploy = True
    max_chat_loop = 20

    print(readme_repos)

    with open("mcp-auto/prompt/prompt_init.md", "r", encoding="utf-8") as f:
        init_prompt = f.read()

    for readme_path in readme_repos[pos:pos+count]:
        id = readme_path.split('/')[-1].split('_')[0]
        name = readme_path.split('/')[-1].replace(id+'_', '').replace('_README.md', '')

        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        prompt = init_prompt
        
        extra_info = add_extra_info(dataset_name, id)

        query = f'''=== README.md START ===\n{readme_content}\n=== README.md END ===\n{extra_info}'''
        await hub.chat_loop(prompt, query, id, readme_path, max_chat_loop)

    await hub.shutdown()


if __name__ == '__main__':
    asyncio.run(main())