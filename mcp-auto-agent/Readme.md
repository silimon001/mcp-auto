## 总览说明

**client_hub.py**: 一个集成MCP客户端
其中：

**MCPHUB类**用于管理所有Client-Server链接，和模型上下文

MCPHUB初始化参数说明
- prompt: 提示词
- streaming: bool类型，是否使用流式输出
- auto_run: 是否执行"根据readme文件，自动化安装和配置流程"

**Client类**持有一个一对一Client-Server链接

**Host**使用的是deepseek-chat（目前）

目前**已知的问题**：当配置写错，Client与Server的链接初始化存在问题时，此处没有正确的异常处理；同时MCPHUB的cleanup函数执行也不正确

**prompt.txt/prompt_zh.txt**: 都是提示词

**mcp_server_config.json**: 给Host提供MCP能力的配置文件，目前只使用了@wonderwhy-er/desktop-commander这个MCP服务器，用以提供文件操作和命令执行功能

**mini_client.py**: 具有最低限度client能力的一个client，主要用于简单测试，目前仍在建设中