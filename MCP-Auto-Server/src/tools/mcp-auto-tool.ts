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

async function getConfigFile(configDir: string, name: string): Promise<{ fileName: string; configs: any }> {
  if (name in global.configIndex) {
    let file: string = global.configIndex[name];
    let configs = JSON.parse(readFileSync(path.join(configDir, file), "utf-8").trim());
    return { fileName: file, configs };
  }

  const files = (await fs.readdir(configDir))
    .filter(f => f.endsWith(".json"))
    .sort((a, b) => {
      const numA = parseInt(a.match(/\d+/)?.[0] || "0", 10);
      const numB = parseInt(b.match(/\d+/)?.[0] || "0", 10);
      return numA - numB;
    });

  if (files.length === 0) return { fileName: "1.json", configs: { Servers: {} } };

  let lastFile: string = files[files.length - 1];
  const filePath = path.join(configDir, lastFile);
  let configs: any = { Servers: {} };

  let data = readFileSync(filePath, "utf-8").trim();

  if (data === "") {} else {
    configs = JSON.parse(data);
  }
  
  if (Object.keys(configs.Servers || {}).length >= 10) {
    const index = parseInt(lastFile.match(/\d+/)?.[0] || "0", 10) + 1;
    lastFile = `${index}.json`;
    configs = { Servers: {} };
  }

  return { fileName: lastFile, configs };
}

export async function AddConfig(name: string, type: string, url: string, headers: Record<string, string>, command: string, args: Array<String>, env: Record<string, string>, cwd: string): Promise<ServerResult> {
  try{
    if (!global.configIndex || typeof global.configIndex !== "object") {
      global.configIndex = {};
    }

    configDir = global.configDir;
    if (!existsSync(configDir)) {
      await fs.mkdir(configDir, { recursive: true });
    }

    let { fileName: lastFile, configs } = await getConfigFile(configDir, name);
    if (!configs.Servers) configs.Servers = {};

    // 添加新的 server 配置
    configs.Servers[name] = {
      type,
      url,
      headers,
      command,
      args,
      env,
      cwd
    };

    // 写入文件
    writeFileSync(path.join(configDir, lastFile), JSON.stringify(configs, null, 2));

    // 更新索引
    global.configIndex[name] = lastFile;

    return {
      content: [
        {
          type: 'text',
          text: `Successfully added ${name} config.`
        }
      ]
    };
  } catch(error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to add ${name} config!\nError: ${error}`
        }
      ],
      isError: true,
    };
  }
  
}

export async function FixConfig(name: string, type: string, url: string, headers: Record<string, string>, command: string, args: Array<String>, env: Record<string, string>, cwd: string): Promise<ServerResult> {
  // 先找到配置文件
  const configfile = global.configIndex[name];
  if (!configfile) {
    return {
      content: [
        {
          type: 'text',
          text: `${name}'s config does not exist.`
        }
      ],
      isError: true,
    };
  }

  const filePath = path.join(global.configDir, configfile);

  // 读取文件
  let fileData: any;
  try {
    const data = readFileSync(filePath, 'utf-8');
    fileData = JSON.parse(data);
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to read config file: ${configfile}.\nError: ${error}`
        }
      ],
      isError: true,
    };
  }

  // 检查 Servers 是否存在
  if (!fileData.Servers || !fileData.Servers[name]) {
    return {
      content: [
        {
          type: 'text',
          text: `The server named ${name} not found.`
        }
      ],
      isError: true,
    };
  }

  // 修改配置
  fileData.Servers[name] = {
    type,
    url,
    headers,
    command,
    args,
    env,
    cwd
  };

  // 写回文件
  try {
    writeFileSync(filePath, JSON.stringify(fileData, null, 2));
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Failed to update config.\nError: ${error}`
        }
      ]
    };
  }

  return {
    content: [
      {
        type: 'text',
        text: `Successfully updated the ${name} config.`
      }
    ]
  };
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
      output += `\nOperation timed out. The process has been forcibly terminated. Please try a different command or increase the timeout period and retry.\nRuntime: ${Math.round(parsed.data.timeout_ms / 1000)} s"`
  }

  return {
    content: [{
      type: "text",
      text: `Process started with PID ${result.pid} (shell: ${shellUsed})\nInitial output:\n${output}`
    }],
  };
}

export async function ValidateConfig(name: string, timeout_ms: number): Promise<ServerResult> {

  const configfile = global.configIndex[name];
  if (!configfile) {
    return {
      content: [
        {
          type: 'text',
          text: `${name}'s config does not exist.`
        }
      ],
      isError: true,
    };
  }

  const filePath = path.join(global.configDir, configfile);

  let python = global.pythonPath;
  let workdir = global.cwd;
  let command = `${python} ${workdir}/dist/config_validation.py ${filePath} ${name}`;

  return ExecuteCommand({command, timeout_ms});
}

export async function NeedTools(names: Array<string>) {
  return {
    content: [{
      type: "text",
      text: JSON.stringify(names)
    }]
  };
}