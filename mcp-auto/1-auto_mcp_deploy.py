import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
import os
import json
import re
import time
from glob import glob
from dotenv import load_dotenv
from openai import OpenAI
import requests
import logging
from pathlib import Path

from MCP_Client import Client
from mcp import Tool

import simplify
from dataset_setting import dataset_name

load_dotenv('.mcp-auto_env')

os.makedirs(f"{os.getcwd()}/mcp_server", exist_ok=True)

# ==================== 配置类 ====================
class Config:
    """集中管理应用配置"""
    def __init__(self, pos: int, count: int, enable_logging: bool = False):
        self.pos = pos
        self.count = count
        self.enable_logging = enable_logging
        self.auto_deploy = False
        self.max_chat_loop = 20

        # LLM 配置
        self.model: str = None
        self.base_url: str = None
        self.headers: Optional[Dict] = None
        self.api_key: str = None
        self.is_streaming: bool = False
        self.enable_thinking: bool = False

        # 路径配置
        self.cwd = os.getcwd()
        self.prompt_dir = Path(self.cwd) / "mcp-auto" / "prompt"
        self.log_dir = Path(self.cwd) / "log_file"
        self.data_dir = Path(self.cwd) / "data"

    def set_llm(self, model: str, base_url: str, headers: Optional[Dict] = None,
                api_key: str = None, is_streaming: bool = False, enable_thinking: bool = False):
        self.model = model
        self.base_url = base_url
        self.headers = headers
        self.api_key = api_key
        self.is_streaming = is_streaming
        self.enable_thinking = enable_thinking


# ==================== 日志管理器 ====================
class Logger:
    """封装日志记录功能"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._setup()

    def _setup(self):
        if not self.config.enable_logging:
            return
        self.config.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = self.config.log_dir / f"EXP_{dataset_name}_{self.config.pos}_{self.config.pos+self.config.count}_{timestamp}.log"
        print(f"Logging to: {log_filename}")
        logging.basicConfig(
            filename=str(log_filename),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='w',
            force=True
        )

    def log(self, content: str, is_error: bool = False):
        print(content)
        if self.config.enable_logging:
            if is_error:
                logging.error(content)
            else:
                logging.info(content)


# ==================== MCP 客户端管理器 ====================
class MCPClientManager:
    """管理多个 MCP 客户端连接与工具调用"""
    def __init__(self, logger: Logger):
        self.clients: Dict[str, Client] = {}
        self.logger = logger
        self.all_tools: List[Tool] = []

    async def connect_servers(self, configs: dict):
        servers = configs.get("Servers", {})
        for name, server_config in servers.items():
            client = Client()
            try:
                await client.init(name, server_config)
            except Exception as e:
                self.logger.log(str(e), is_error=True)
                return
            self.clients[name] = client
            self.all_tools.extend(client.tools)
            self.logger.log(f"Client {name} initialized with tools: {[tool.name for tool in client.tools]}")

    async def call_tool(self, server_name: str, tool_name: str, tool_args: dict) -> str:
        result = await self.clients[server_name].session.call_tool(tool_name, tool_args)
        response = result.content[0].text
        if tool_name == 'execute_command':
            response = simplify.simplify_log(response)
        return response

    async def shutdown(self):
        for name, client in self.clients.items():
            try:
                self.logger.log(f"Shutting down client-server connect: {name}")
                await client.cleanup()
            except Exception as e:
                print(f"Error shutting down client-server connect {name}: {e}")


# ==================== LLM 客户端 ====================
class LLMClient:
    """封装与 LLM 的通信"""
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.communicate_count = 0

    @staticmethod
    def _delete_reasoning(msg: dict) -> dict:
        """移除 reasoning_content 字段"""
        if 'reasoning_content' in msg:
            return {k: v for k, v in msg.items() if k != 'reasoning_content'}
        return msg

    def communicate(self, messages: List[dict], tools: List[dict]) -> dict:
        """发送请求并返回解析后的响应和用量"""
        response = None
        if self.config.base_url == 'https://dashscope.aliyuncs.com/compatible-mode/v1':
            session = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            response = session.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=tools,
                stream=self.config.is_streaming,
                temperature=0.1, # (0, 2]
                tool_choice="auto",
                extra_body={"enable_thinking": self.config.enable_thinking}
            )
            usage = response.usage.to_dict()
            choices = response.choices[0].message.to_dict()
        else:
            # 预留其他 API 适配位置
            raise NotImplementedError("Unsupported base_url")

        self.communicate_count += 1
        self.logger.log(f"--- Communicate Count: {self.communicate_count} ---")
        return {
            'usage': usage,
            'response': self._delete_reasoning(choices)
        }


# ==================== 对话管理器 ====================
class ConversationManager:
    """管理消息列表、工具消息筛选"""
    def __init__(self):
        self.messages: List[dict] = []
        self.all_tool_messages: List[dict] = []          # 所有可用工具（OpenAI格式）
        self.active_tool_names: List[str] = []           # 当前可用的工具名列表

    def register_tools(self, tools: List[Tool]):
        """将 MCP Tool 转换为 OpenAI function 格式并存储"""
        for tool in tools:
            tool_msg = {
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
            self.all_tool_messages.append(tool_msg)

    def set_active_tools(self, names: List[str]):
        """设置当前阶段可用的工具"""
        self.active_tool_names = names

    def get_active_tool_messages(self) -> List[dict]:
        """返回当前激活的工具消息列表"""
        return [t for t in self.all_tool_messages if t['function']['name'] in self.active_tool_names]

    def add_system_message(self, content: str):
        self.messages.append({"role": "system", "content": content})

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, message: dict):
        self.messages.append(message)

    def add_tool_result(self, tool_call_id: str, content: str):
        self.messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": content})


# ==================== Prompt 与工具动态管理器 ====================
class PromptManager:
    """负责从文件加载动态 prompt，并根据工具名返回对应的 prompt 内容"""
    def __init__(self, config: Config):
        self.config = config

    def load_prompts(self, names: List[str]) -> str:
        """加载多个 prompt 文件内容并拼接"""
        combined = ""
        for name in names:
            prompt_path = self.config.prompt_dir / f"prompt_{name}.md"
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if name == 'git' or name == 'deploy':
                    content = content.replace("{WORKSPACE}", str(self.config.cwd))
                elif name == 'uv':
                    content = content.replace("{HOME}", str(Path.home()))
                combined += content
            except Exception:
                pass
        return combined

    def get_tool_names_for_phase(self, phase: str) -> List[str]:
        """根据阶段返回应激活的工具名称列表"""
        phase_tool_map = {
            'analyze': ['need_use_these_tools'],
            'deploy': ['add_config', 'execute_command'],
            'validate': ['validate_config'],
            'fix': ['fix_config', 'execute_command', 'validate_config'],
        }
        return phase_tool_map.get(phase, [])


# ==================== 执行循环（状态机） ====================
class ExecutionLoop:
    """处理单个 README 的完整对话流程"""
    def __init__(self, config: Config, logger: Logger, mcp_manager: MCPClientManager,
                 llm_client: LLMClient, conv_manager: ConversationManager, prompt_manager: PromptManager):
        self.config = config
        self.logger = logger
        self.mcp_manager = mcp_manager
        self.llm_client = llm_client
        self.conv_manager = conv_manager
        self.prompt_manager = prompt_manager

    async def run(self, prompt: str, query: str, readme_id: str, readme_path: str):
        """执行主对话循环"""
        self.llm_client.communicate_count = 0
        self.logger.log(f'Dealing with {readme_id} {readme_path} ...')
        self.logger.log(f'\n=========\n{query}\n==========\n')

        # 初始化消息
        self.conv_manager.messages = []
        self.conv_manager.add_system_message(prompt)
        self.conv_manager.add_user_message(query)

        while True:
            if self.llm_client.communicate_count >= self.config.max_chat_loop:
                break

            # 阶段控制：第一次通信前插入分析 prompt 并设置工具
            if self.llm_client.communicate_count == 0:
                analyze_prompt = self.prompt_manager.load_prompts(['analyze'])
                self.conv_manager.add_system_message(analyze_prompt)
                self.conv_manager.set_active_tools(self.prompt_manager.get_tool_names_for_phase('analyze'))

            # 调用 LLM
            tools = self.conv_manager.get_active_tool_messages()
            all_response = self.llm_client.communicate(self.conv_manager.messages, tools)
            usage = all_response['usage']
            self.logger.log('Token Usage: ' + json.dumps(usage, ensure_ascii=False))

            response = all_response['response']
            self.conv_manager.add_assistant_message(response)
            content = response.get('content', '')
            self.logger.log('Response: ' + (content if content else '[tool_calls]'))

            # 处理工具调用
            if response.get('tool_calls') is not None:
                for tool_call in response['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args = json.loads(tool_call['function']['arguments'])
                    server_name = "MCP-Auto"   # 固定服务器名（可根据实际情况调整）
                    self.logger.log(f"[Call Tool] Server: {server_name}, Tool: {tool_name}, Args: {tool_args}")

                    # 自动化/用户确认逻辑
                    tool_validation = False
                    call_tool_result, tool_validation = await self._execute_tool_with_policy(
                        server_name, tool_name, tool_args, auto=self.config.auto_deploy)

                    self.conv_manager.add_tool_result(tool_call['id'], call_tool_result)
                    self.logger.log('\n' + call_tool_result + '\n' + '-'*52 + '\n')

                    # 根据工具调用结果进行阶段切换
                    if tool_validation:
                        await self._handle_phase_transition(tool_name, tool_args, call_tool_result)

            else:
                # 检查任务完成标志
                if content and any(marker in content for marker in ["✅ @@Task Done@@", "❌ @@Task Failed@@", "⚠️ @@Task Alert@@"]):
                    break
                # 继续对话
                self.conv_manager.add_user_message("come on!")

    async def _execute_tool_with_policy(self, server_name: str, tool_name: str, tool_args: dict, auto: bool):
        """根据自动化策略执行工具调用"""
        command = tool_args.get('command', '')
        if 'python' in command and 'uv' not in command:
            return "Don't use python, use uv instead.", False
        if 'pip' in command and 'uv' not in command:
            return "Don't use pip, use uv pip instead.", False

        if auto:
            result = await self.mcp_manager.call_tool(server_name, tool_name, tool_args)
            return result, True
        else:
            if input("(Y/N): ").strip().lower() == 'y':
                result = await self.mcp_manager.call_tool(server_name, tool_name, tool_args)
                return result, True
            else:
                return "Users refuse to use this tool; please reflect on this and choose the right tool.", False

    async def _handle_phase_transition(self, tool_name: str, tool_args: dict, call_tool_result: str):
        """根据调用的工具名称切换阶段、插入系统 prompt 和工具集"""
        if tool_name == 'need_use_these_tools':
            # 进入部署阶段
            self.conv_manager.set_active_tools(self.prompt_manager.get_tool_names_for_phase('deploy'))
            deploy_prompt = self.prompt_manager.load_prompts(['deploy'])
            self.conv_manager.add_system_message(deploy_prompt)
            # 动态插入工具说明（原 call_tool_result 内容）
            tools_prompt = self.prompt_manager.load_prompts(json.loads(call_tool_result))
            self.conv_manager.add_system_message(tools_prompt)

        elif tool_name == 'add_config':
            self.conv_manager.set_active_tools(self.prompt_manager.get_tool_names_for_phase('validate'))
            validate_prompt = self.prompt_manager.load_prompts(['validate'])
            self.conv_manager.add_system_message(validate_prompt)

        elif tool_name == 'validate_config':
            self.conv_manager.set_active_tools(self.prompt_manager.get_tool_names_for_phase('fix'))
            # 可以插入额外的用户提示（被注释掉的部分）


# ==================== 工具函数 ====================
def add_extra_info(dataset_name: str, repo_id: str) -> str:
    """从数据集读取仓库额外信息"""
    final_text = ''
    repo_info_path = Path.cwd() / "data" / "dataset" / dataset_name / "repo_info.json"
    if repo_info_path.exists():
        with open(repo_info_path, 'r', encoding='utf-8') as f:
            repo_infos = json.load(f)
        for repo_info in repo_infos:
            if repo_info.get('id') == int(repo_id):
                info = {k: repo_info.get(k) for k in ["id", "description", "language", "size", "topic", "html_url"]}
                info['owner'] = repo_info.get('full_name').split('/')[0]
                info['name'] = repo_info.get('full_name').split('/')[1]
                final_text += f'\n=== REPO INFO START ===\n{info}\n=== REPO INFO END ===\n'
                break
    return final_text


# ==================== 主函数 ====================
async def main():
    pos = 0
    count = 20

    # 初始化配置
    config = Config(pos, count, enable_logging=True)
    config.set_llm(
        model='qwen3-coder-plus',
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        api_key=os.getenv('QWEN_API_KEY'),
        is_streaming=False,
        enable_thinking=True
    )
    config.auto_deploy = False
    config.max_chat_loop = 20

    # 初始化各组件
    logger = Logger(config)
    mcp_manager = MCPClientManager(logger)
    llm_client = LLMClient(config, logger)
    conv_manager = ConversationManager()
    prompt_manager = PromptManager(config)

    # 连接 MCP 服务器
    config_path = Path.cwd() / "MCP-Auto-Server" / "mcp_server_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        server_configs = json.load(f)
    await mcp_manager.connect_servers(server_configs)
    conv_manager.register_tools(mcp_manager.all_tools)

    # 读取初始 prompt
    init_prompt_path = config.prompt_dir / "prompt_init.md"
    with open(init_prompt_path, "r", encoding="utf-8") as f:
        init_prompt = f.read()

    # 获取待处理的 README 文件列表
    readme_dir = Path.cwd() / "data" / "dataset" / dataset_name / "sampled_validated_readme"
    readme_files = sorted(glob(str(readme_dir / "*.md")), key=os.path.getsize)

    # 创建执行循环实例
    loop = ExecutionLoop(config, logger, mcp_manager, llm_client, conv_manager, prompt_manager)

    for readme_path in readme_files[pos:pos+count]:
        readme_path = Path(readme_path)
        filename_parts = readme_path.stem.split('_')
        repo_id = filename_parts[0]
        repo_name = '_'.join(filename_parts[1:]).replace('_README', '')

        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        extra_info = add_extra_info(dataset_name, repo_id)
        query = f'''=== README.md START ===\n{readme_content}\n=== README.md END ===\n{extra_info}'''
        await loop.run(init_prompt, query, repo_id, str(readme_path))

    await mcp_manager.shutdown()


if __name__ == '__main__':
    asyncio.run(main())