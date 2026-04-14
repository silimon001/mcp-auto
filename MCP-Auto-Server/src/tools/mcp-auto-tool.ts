import { ServerResult } from '../types.js';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import fs from "fs/promises";
import path from 'node:path';
import { terminalManager } from '../terminal-manager.js';
import { commandManager } from '../command-manager.js';
import { ExecuteCommandArgsSchema } from './schemas.js';
import { analyzeProcessState, formatProcessStateMessage } from '../utils/process-detection.js';
import * as os from 'os';
import { configManager } from '../config-manager.js';
import { killProcess } from './process.js';
import { readProcessOutput } from './improved-process-tools.js';
import { parseDateDef } from 'zod-to-json-schema';
import { tmpdir } from 'node:os';
import { time } from 'node:console';

const CONFIG_FILE_NAME = "config.json";

async function getOrCreateConfig(configDir: string): Promise<any> {
  const configPath = path.join(configDir, CONFIG_FILE_NAME);
  
  if (existsSync(configPath)) {
    const data = await fs.readFile(configPath, "utf-8").then(d => d.trim());
    if (data === "") {
      return { Servers: {} };
    }
    return JSON.parse(data);
  } else {
    return { Servers: {} };
  }
}

export async function AddConfig(
  name: string,
  type: string,
  url: string,
  headers: Record<string, string>,
  command: string,
  args: Array<string>,
  env: Record<string, string>,
  cwd: string
): Promise<ServerResult> {
  try {
    const configDir = global.configDir;
    
    if (!existsSync(configDir)) {
      await fs.mkdir(configDir, { recursive: true });
    }

    const configs = await getOrCreateConfig(configDir);
    if (!configs.Servers) {
      configs.Servers = {};
    }

    // 检查配置是否已存在，禁止覆盖
    if (configs.Servers.hasOwnProperty(name)) {
      return {
        content: [
          {
            type: "text",
            text: `Config with name "${name}" already exists. Overwriting is not allowed.`
          }
        ],
        isError: true
      };
    }

    // 添加新配置
    configs.Servers[name] = {
      type,
      url,
      headers,
      command,
      args,
      env,
      cwd
    };

    const configPath = path.join(configDir, CONFIG_FILE_NAME);
    await fs.writeFile(configPath, JSON.stringify(configs, null, 2), "utf-8");

    return {
      content: [
        {
          type: "text",
          text: `Successfully added ${name} config.`
        }
      ]
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Failed to add ${name} config!\nError: ${error}`
        }
      ],
      isError: true
    };
  }
}

export async function UpdateAndValidateConfig(
  name: string,
  type: string,
  url: string,
  headers: Record<string, string>,
  command: string,
  args: Array<string>,
  env: Record<string, string>,
  cwd: string,
  timeout_ms: number
): Promise<ServerResult> {
  const configDir = global.configDir;

  // --- 第一部分：修改配置，捕获并返回明确错误 ---
  try {
    if (!existsSync(configDir)) {
      await fs.mkdir(configDir, { recursive: true });
    }

    // 读取现有配置
    const configs = await getOrCreateConfig(configDir);
    if (!configs.Servers || !configs.Servers[name]) {
      return {
        content: [{ type: "text", text: `Config '${name}' does not exist.` }],
        isError: true
      };
    }

    // 更新配置内容
    configs.Servers[name] = {
      type,
      url,
      headers,
      command,
      args,
      env,
      cwd
    };

    // 写入配置文件
    const configPath = path.join(configDir, CONFIG_FILE_NAME);
    await fs.writeFile(configPath, JSON.stringify(configs, null, 2), "utf-8");

  } catch (error) {
    return {
      content: [{ type: "text", text: `Failed to update config '${name}': ${error}` }],
      isError: true
    };
  }

  // --- 第二部分：验证配置，捕获并返回明确错误 ---
  try {
    const python = global.pythonPath;
    const workdir = global.cwd;
    const configPath = path.join(configDir, CONFIG_FILE_NAME);
    const validationCmd = `${python} ${workdir}/dist/config_validation.py ${configPath} ${name}`;

    // 执行验证命令（假设 ExecuteCommand 已定义）
    return await ExecuteCommand({ command: validationCmd, timeout_ms });

  } catch (error) {
    return {
      content: [{ type: "text", text: `Config updated, but validation failed: ${error}` }],
      isError: true
    };
  }
}


export async function ExecuteCommand(args: unknown): Promise<ServerResult> {
  const parsed = ExecuteCommandArgsSchema.safeParse(args);
  if (!parsed.success) {
    return {
      content: [{ type: "text", text: `Error: Invalid arguments for execute_command: ${parsed.error}` }],
      isError: true,
    };
  }

  const isAllowed = await commandManager.validateCommand(parsed.data.command);
  if (!isAllowed) {
    return {
      content: [{ type: "text", text: `Error: Command not allowed: ${parsed.data.command}` }],
      isError: true,
    };
  }

  let shellUsed: string | undefined = parsed.data.shell;

  if (!shellUsed) {
    const config = await configManager.getConfig();
    if (config.defaultShell) {
      shellUsed = config.defaultShell;
    } else {
      const isWindows = os.platform() === 'win32';
      if (isWindows && process.env.COMSPEC) {
        shellUsed = process.env.COMSPEC;
      } else if (!isWindows && process.env.SHELL) {
        shellUsed = process.env.SHELL;
      } else {
        shellUsed = isWindows ? 'cmd.exe' : '/bin/sh';
      }
    }
  }

  const result = await terminalManager.executeCommand(
    parsed.data.command,
    parsed.data.timeout_ms,
    shellUsed,
    false
  );

  if (result.pid === -1) {
    return {
      content: [{ type: "text", text: result.output }],
      isError: true,
    };
  }

  killProcess(result.pid)
  let output = terminalManager.getNewOutput(result.pid);

  if (output !== null && !output.includes("Process completed with exit code")) {
      output += `\nOperation timed out. The process has been forcibly terminated. Please try a different command or increase the timeout period and retry.\nRuntime: ${Math.round(parsed.data.timeout_ms / 1000)} s`
  }

  return {
    content: [{
      type: "text",
      text: `Process started with PID ${result.pid} (shell: ${shellUsed})\nInitial output:\n${output}`
    }],
  };
}

export async function ValidateConfig(name: string, timeout_ms: number): Promise<ServerResult> {
  const configDir = global.configDir;

  // 读取现有配置
  const configs = await getOrCreateConfig(configDir);
  if (!configs.Servers || !configs.Servers[name]) {
    return {
      content: [{ type: "text", text: `Config '${name}' does not exist.` }],
      isError: true
    };
  }

  const configPath = path.join(configDir, CONFIG_FILE_NAME);

  const python = global.pythonPath;
  const workdir = global.cwd;
  const command = `${python} ${workdir}/dist/config_validation.py ${configPath} ${name}`;

  return ExecuteCommand({ command, timeout_ms });
}

export async function NeedTools(names: Array<string>) {
  return {
    content: [{
      type: "text",
      text: JSON.stringify(names)
    }]
  };
}