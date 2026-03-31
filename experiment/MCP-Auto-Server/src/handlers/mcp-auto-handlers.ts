import {
    AddConfig,
    FixConfig,
    ExecuteCommand,
    ValidateConfig,
    NeedTools
} from '../tools/mcp-auto-tool.js';

import {ServerResult} from '../types.js';

import {
    AddConfigArgsSchema,
    FixConfigArgsSchema,
    ExecuteCommandArgsSchema,
    ValidateConfigArgsSchema,
    NeedUseTheseToolsSchema
} from '../tools/schemas.js';

export async function handleAddConfig(args: unknown): Promise<ServerResult> {
    const parsed = AddConfigArgsSchema.parse(args);

    return await AddConfig(parsed.name, parsed.type, parsed.url, parsed.headers, parsed.command, parsed.args, parsed.env, parsed.cwd);
}

export async function handleFixConfig(args: unknown): Promise<ServerResult> {
    const parsed = FixConfigArgsSchema.parse(args);
    
    return await FixConfig(parsed.name, parsed.type, parsed.url, parsed.headers, parsed.command, parsed.args, parsed.env, parsed.cwd);
}

export async function handleExecuteCommand(args: unknown): Promise<ServerResult> {
    const parsed = ExecuteCommandArgsSchema.parse(args);

    return ExecuteCommand(parsed);
}

export async function handleValidateConfig(args: unknown): Promise<ServerResult> {
    const parsed = ValidateConfigArgsSchema.parse(args);

    return ValidateConfig(parsed.name, parsed.timeout_ms);
}

export async function handleNeedTools(args: unknown) {
    const parsed = NeedUseTheseToolsSchema.parse(args);
    
    return NeedTools(parsed.names)
}