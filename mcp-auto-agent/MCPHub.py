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
from exp_setting import dataset_name, framework_name, model_name

load_dotenv('.mcp-auto_env')

os.makedirs(f"{os.getcwd()}/mcp_server", exist_ok=True)

# ==================== 配置类 ====================
class Config:
    """集中管理应用配置"""
    def __init__(self, pos: int, count: int, model_name:str, enable_logging: bool = False):
        self.pos = pos
        self.count = count
        self.enable_logging = enable_logging
        self.auto_deploy = False
        self.max_chat_loop = 0

        # LLM 配置
        self.model: str = None
        self.base_url: str = None
        self.headers: Optional[Dict] = None
        self.api_key: str = None
        self.is_streaming: bool = False
        self.enable_thinking: bool = False

        # 路径配置
        self.cwd = os.getcwd()
        self.prompt_dir = Path(self.cwd) / "mcp-auto-agent" / "prompt"
        self.log_dir = Path(self.cwd) / "log_file" / dataset_name / framework_name / model_name
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
        
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = self.config.log_dir / f"{self.config.pos}_{self.config.pos+self.config.count}_{timestamp}.log"

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
            client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            response = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=tools,
                stream=self.config.is_streaming,
                temperature=0.1, # [0, 2)
                tool_choice="auto",
                extra_body={"enable_thinking": self.config.enable_thinking}
            )
            usage = response.usage.to_dict()
            choices = response.choices[0].message.to_dict()
        elif self.config.base_url == "https://api.deepseek.com":
            client = OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.deepseek.com")

            enable = 'disabled'
            if self.config.enable_thinking:
                enable = 'enabled'

            response = client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                stream=False,
                temperature=0.1,
                tools=tools,
                reasoning_effort="high",
                extra_body={"thinking": {"type": enable}}
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
        self.tools: List[str] = []

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
            self.tools.append(tool_msg)

    def add_system_message(self, content: str):
        self.messages.append({"role": "system", "content": content})

    def add_query(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]})

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
            except Exception as e:
                pass
        return combined


# 高风险模式，可根据实际需求扩展
FORBIDDEN_PATTERNS = [
    r'\bsudo\b',               # 提权
    r'\bmkfs\.',               # 格式化
]

def is_command_safe(command: str) -> bool:
    """检查命令是否包含禁止模式"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, command):
            return False
    # 还可以限制命令长度、检查命令是否存在等
    return True

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
        self.conv_manager.add_query(query)

        while True:
            if self.llm_client.communicate_count > self.config.max_chat_loop:
                break

            # 阶段控制：第一次通信前插入分析 prompt 并设置工具
            if self.llm_client.communicate_count == 0:
                analyze_prompt = self.prompt_manager.load_prompts(['analyze'])
                self.conv_manager.add_user_message(analyze_prompt)

            # 调用 LLM
            all_response = self.llm_client.communicate(self.conv_manager.messages, self.conv_manager.tools)
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
                    raw_args = tool_call['function']['arguments']
                    try:
                        tool_args = json.loads(raw_args)
                    except json.JSONDecodeError as e:
                        self.logger.log(
                            f"[Invalid Tool Args Raw]\n{raw_args}", is_error=True)
                        call_tool_result = (f"Tool arguments are not valid JSON: {e}")

                        self.conv_manager.add_tool_result(tool_call['id'], call_tool_result)
                        continue

                    server_name = "MCP-Auto"   # 固定服务器名（可根据实际情况调整）
                    self.logger.log(f"[Call Tool] Server: {server_name}, Tool: {tool_name}, Args: {tool_args}")

                    # 1. 参数校验 / 修正
                    checked_args, can_proceed = await self.tool_calling_hook(server_name, tool_name, tool_args)

                    if not can_proceed:
                        # 校验失败，将错误消息作为工具调用结果返回给模型
                        call_tool_result = checked_args
                        self.logger.log('\n' + call_tool_result + '\n' + '-'*52 + '\n')
                        self.conv_manager.add_tool_result(tool_call['id'], call_tool_result)
                        continue

                    # 2. 用户确认（非 auto 时）
                    if not self.config.auto_deploy:
                        if input("(Y/N): ").strip().lower() != 'y':
                            call_tool_result = "Users refuse to use this tool; please reflect on this and choose the right tool."
                            self.logger.log('\n' + call_tool_result + '\n' + '-'*52 + '\n')
                            self.conv_manager.add_tool_result(tool_call['id'], call_tool_result)
                            continue

                    # 3. 实际工具调用
                    call_tool_result = await self.mcp_manager.call_tool(server_name, tool_name, checked_args)

                    # 4. 结果简化（后处理）
                    call_tool_result = await self.tool_result_hook(tool_name, call_tool_result)

                    # 5. 将最终结果加入对话历史
                    self.conv_manager.add_tool_result(tool_call['id'], call_tool_result)
                    self.logger.log('\n' + call_tool_result + '\n' + '-'*52 + '\n')

                    # 6. 动态 prompt 路由（根据工具名插入阶段提示词）
                    await self.prompt_router_trigger(tool_name, call_tool_result)

            else:
                # 检查任务完成标志
                if content and any(marker in content for marker in ["@@Task Done@@", "@@Task Failed@@", "@@Task Alert@@"]):
                    break
                # 继续对话
                self.conv_manager.add_user_message("come on!")

    async def tool_calling_hook(self, server_name: str, tool_name: str, tool_args: dict) -> tuple:

        if tool_name == 'execute_command':
            command = tool_args.get('command', '')
            timeout_ms = tool_args.get('timeout_ms')

            if not command.strip():
                return "Command is empty.", False

            if timeout_ms is None:
                return "Missing required parameter: timeout_ms", False

            try:
                timeout_ms = int(timeout_ms)
                if timeout_ms <= 0:
                    return "Invalid timeout_ms: must be greater than 0", False
            except (TypeError, ValueError):
                return "Invalid timeout_ms: must be a number", False

            if not is_command_safe(command):
                error_msg = (
                    f"Command rejected due to security policy: {command[:100]}..."
                    if len(command) > 100 else f"Command rejected: {command}"
                )
                self.logger.log(
                    f"[Security] Blocked command: {command}",
                    is_error=True
                )
                return error_msg, False

        if tool_name == 'need_use_these_tools':
            tools = tool_args.get('tools', [])
            if not self._is_valid_tools_combination(tools):
                error_msg = (
                    'tools must be one of: ["git","uv"], ["git","node"], '
                    '["node"], ["uv"], ["none"], ["git","uv","node"] '
                    '(order does not matter)'
                )
                return error_msg, False

        return tool_args, True

    async def tool_result_hook(self, tool_name: str, call_tool_result: str) -> str:
        """接入 simplify 做简化（或其它结果后处理）"""
        if tool_name == 'execute_command':
            return simplify.simplify_log(call_tool_result)
        return call_tool_result

    async def prompt_router_trigger(self, tool_name: str, call_tool_result: str) -> None:
        """根据被调用的工具动态添加提示词，切换阶段"""
        if tool_name == 'need_use_these_tools':
            deploy_prompt = self.prompt_manager.load_prompts(['deploy'])
            self.conv_manager.add_user_message(deploy_prompt)

            tools_prompt = self.prompt_manager.load_prompts(json.loads(call_tool_result))
            self.conv_manager.add_user_message(tools_prompt)

        elif tool_name == 'add_config':
            validate_prompt = self.prompt_manager.load_prompts(['validate'])
            self.conv_manager.add_user_message(validate_prompt)

    @staticmethod
    def _is_valid_tools_combination(tools: list) -> bool:
        """校验 tools 列表是否符合允许的组合"""
        if not isinstance(tools, list):
            return False
        length = len(tools)
        if length == 1:
            return tools[0] in {'node', 'uv', 'none'}
        if length == 2:
            tool_set = set(tools)
            return 'git' in tool_set and ('uv' in tool_set or 'node' in tool_set) and len(tool_set) == 2
        if length == 3:
            return set(tools) == {'git', 'uv', 'node'}
        return False

# ==================== 工具函数 ====================
def add_extra_info(dataset_name: str, repo_id: str) -> str:
    final_text = ''
    repo_info_path = Path.cwd() / "data" / "dataset" / dataset_name / "repo_info.json"
    if repo_info_path.exists():
        with open(repo_info_path, 'r', encoding='utf-8') as f: repo_infos = json.load(f)
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

    API_KEY = os.getenv("DEEPSEEK_KEY")

    pos = 18
    count = 40

    # 初始化配置
    config = Config(pos, count, model_name, enable_logging=True)

    config.set_llm(
        model=model_name,
        base_url='https://api.deepseek.com',  # https://api.deepseek.com https://dashscope.aliyuncs.com/compatible-mode/v1
        api_key=API_KEY,
        is_streaming=False,
        enable_thinking=True
    )

    config.auto_deploy = True
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

    logger.log(f"Based on {model_name}.")

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