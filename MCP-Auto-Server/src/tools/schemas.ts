import { z } from "zod";
import { string } from "zod/v4";

// Config tools schemas
export const GetConfigArgsSchema = z.object({});

export const SetConfigValueArgsSchema = z.object({
  key: z.string(),
  value: z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.array(z.string()),
    z.null(),
  ]),
});

// Empty schemas
export const ListProcessesArgsSchema = z.object({});

// Terminal tools schemas
export const StartProcessArgsSchema = z.object({
  command: z.string(),
  timeout_ms: z.number(),
  shell: z.string().optional(),
  verbose_timing: z.boolean().optional(),
});

export const ReadProcessOutputArgsSchema = z.object({
  pid: z.number(),
  timeout_ms: z.number().optional(),
  verbose_timing: z.boolean().optional(),
});

export const ForceTerminateArgsSchema = z.object({
  pid: z.number(),
});

export const ListSessionsArgsSchema = z.object({});

export const KillProcessArgsSchema = z.object({
  pid: z.number(),
});

// Filesystem tools schemas
export const ReadFileArgsSchema = z.object({
  path: z.string(),
  isUrl: z.boolean().optional().default(false),
  offset: z.number().optional().default(0),
  length: z.number().optional().default(1000),
});

export const ReadMultipleFilesArgsSchema = z.object({
  paths: z.array(z.string()),
});

export const WriteFileArgsSchema = z.object({
  path: z.string(),
  content: z.string(),
  mode: z.enum(['rewrite', 'append']).default('rewrite'),
});

export const ListDirectoryArgsSchema = z.object({
  path: z.string(),
  depth: z.number().optional().default(2),
});

// Edit tools schema
export const EditBlockArgsSchema = z.object({
  file_path: z.string(),
  old_string: z.string(),
  new_string: z.string(),
  expected_replacements: z.number().optional().default(1),
});

// Send input to process schema
export const InteractWithProcessArgsSchema = z.object({
  pid: z.number(),
  input: z.string(),
  timeout_ms: z.number().optional(),
  wait_for_prompt: z.boolean().optional(),
  verbose_timing: z.boolean().optional(),
});


// Add config schema
export const AddConfigArgsSchema = z.object({
  name: z.string(),
  type: z.enum(["stdio", "sse", "streamable_http"]),
  url: z.string().optional().default(''),
  headers: z.record(z.string(), z.string()).optional().default({}),
  command: z.string().optional().default(''),
  args: z.array(z.string()).optional().default([]),
  env: z.record(z.string(), z.string()).optional().default({}),
  cwd: z.string(),
});

// Update and validate config schema
export const UpdateAndValidateConfigArgsSchema = z.object({
  name: z.string(),
  type: z.enum(["stdio", "sse", "streamable_http"]),
  url: z.string().optional().default(''),
  headers: z.record(z.string(), z.string()).optional().default({}),
  command: z.string().optional().default(''),
  args: z.array(z.string()).optional().default([]),
  env: z.record(z.string(), z.string()).optional().default({}),
  cwd: z.string(),
  timeout_ms: z.number().optional().default(60000)
});

// Execute command schema
export const ExecuteCommandArgsSchema = z.object({
  command: z.string(),
  timeout_ms: z.number().optional().default(30000),
  shell: z.string().optional()
});

// Validate config schema
export const ValidateConfigArgsSchema = z.object({
  name: z.string(),
  timeout_ms: z.number().optional().default(60000)
});

export const NeedUseTheseToolsSchema = z.object({
  tools: z.array(z.enum(['git', 'uv', 'node', 'none'])).refine(
    (arr) => {
      // 长度为1：只允许 ['node'], ['uv'], ['none']
      if (arr.length === 1) {
        return ['node', 'uv', 'none'].includes(arr[0]);
      }
      // 长度为2：允许 {'git', 'uv'} 或 {'git', 'node'}（顺序不限）
      if (arr.length === 2) {
        const set = new Set(arr);
        return set.has('git') && (set.has('uv') || set.has('node')) && set.size === 2;
      }
      if (arr.length === 3) {
        const set = new Set(arr);
        return set.has('git') && (set.has('uv') && set.has('node')) && set.size === 3;
      }
      // 其他长度均不允许
      return false;
    },
    {
      message:
        'tools must be one of: ["git","uv"], ["git","node"], ["node"], ["uv"], ["none"], ["git","uv","node"] (order does not matter)',
    }
  ),
});