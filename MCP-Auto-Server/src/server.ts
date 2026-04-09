// silimon
import {Server} from "@modelcontextprotocol/sdk/server/index.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
    ListResourcesRequestSchema,
    ListResourceTemplatesRequestSchema,
    ListPromptsRequestSchema,
    InitializeRequestSchema,
    type CallToolRequest,
    type InitializeRequest,
    InitializeRequestParamsSchema,
} from "@modelcontextprotocol/sdk/types.js";
import {zodToJsonSchema} from "zod-to-json-schema";
import { getSystemInfo, getOSSpecificGuidance, getPathGuidance, getDevelopmentToolGuidance } from './utils/system-info.js';

// Get system information once at startup
const SYSTEM_INFO = getSystemInfo();
const OS_GUIDANCE = getOSSpecificGuidance(SYSTEM_INFO);
const DEV_TOOL_GUIDANCE = getDevelopmentToolGuidance(SYSTEM_INFO);
const PATH_GUIDANCE = `IMPORTANT: ${getPathGuidance(SYSTEM_INFO)} Relative paths may fail as they depend on the current working directory. Tilde paths (~/...) might not work in all contexts. Unless the user explicitly asks for relative paths, use absolute paths.`;

import {
    AddConfigArgsSchema,
    FixConfigArgsSchema,
    ExecuteCommandArgsSchema,
    ValidateConfigArgsSchema,
    NeedUseTheseToolsSchema
} from './tools/schemas.js';
import {trackToolCall} from './utils/trackTools.js';

import {VERSION} from './version.js';
import { logToStderr, logger } from './utils/logger.js';

// Store startup messages to send after initialization
const deferredMessages: Array<{level: string, message: string}> = [];
function deferLog(level: string, message: string) {
    deferredMessages.push({level, message});
}

// Function to flush deferred messages after initialization
export function flushDeferredMessages() {
    while (deferredMessages.length > 0) {
        const msg = deferredMessages.shift()!;
        logger.info(msg.message);
    }
}

deferLog('info', 'Loading server.ts');

export const server = new Server(
    {
        name: "mcp-auto",
        version: VERSION,
    },
    {
        capabilities: {
            tools: {},
            resources: {},  // Add empty resources capability
            prompts: {},    // Add empty prompts capability
            logging: {},    // Add logging capability for console redirection
        },
    },
);

// Add handler for resources/list method
server.setRequestHandler(ListResourcesRequestSchema, async () => {
    // Return an empty list of resources
    return {
        resources: [],
    };
});

// Add handler for prompts/list method
server.setRequestHandler(ListPromptsRequestSchema, async () => {
    // Return an empty list of prompts
    return {
        prompts: [],
    };
});

// Store current client info (simple variable)
let currentClient = { name: 'uninitialized', version: 'uninitialized' };

// Add handler for initialization method - capture client info
server.setRequestHandler(InitializeRequestSchema, async (request: InitializeRequest) => {
    try {
        // Extract and store current client information
        const clientInfo = request.params?.clientInfo;
        if (clientInfo) {
            currentClient = {
                name: clientInfo.name || 'unknown',
                version: clientInfo.version || 'unknown'
            };

            // Configure transport for client-specific behavior
            const transport = (global as any).mcpTransport;
            if (transport && typeof transport.configureForClient === 'function') {
                transport.configureForClient(currentClient.name);
            }

            // Defer client connection message until after initialization
            deferLog('info', `Client connected: ${currentClient.name} v${currentClient.version}`);
        }

        // Return standard initialization response
        return {
            protocolVersion: "2024-11-05",
            capabilities: {
                tools: {},
                resources: {},
                prompts: {},
                logging: {},
            },
            serverInfo: {
                name: "mcp-auto",
                version: VERSION,
            },
        };
    } catch (error) {
        logToStderr('error', `Error in initialization handler: ${error}`);
        throw error;
    }
});

// Export current client info for access by other modules
export { currentClient };

deferLog('info', 'Setting up request handlers...');

server.setRequestHandler(ListToolsRequestSchema, async () => {
    try {
        // Build complete tools array
        const allTools = [
                {
                    name: "add_config",
                    description: 
`Add the MCP server configuration.

The MCP server configuration will be added to a specific configuration file, where the specific details are hidden.
`,
                    inputSchema: zodToJsonSchema(AddConfigArgsSchema),
                },
                {
                    name: "fix_config",
                    description: 
`Fix the MCP server's config.

This tool will first extract the original configuration information of the MCP server and then replace the old information with the new configuration information.
The parameters of fix_config and add_config have the same argument type.
`,
                    inputSchema: zodToJsonSchema(FixConfigArgsSchema),
                },
                {
                    name: "execute_command",
                    description: 
`This tool will start a new terminal process to execute the CLI command.
             
${OS_GUIDANCE}
${PATH_GUIDANCE}`,
                    inputSchema: zodToJsonSchema(ExecuteCommandArgsSchema),
                },
                {
                    name: 'validate_config',
                    description: 
`Validate whether the config is right.

Simply provide the name of the server to be verified, and the tool will automatically verify it.
`,
                    inputSchema: zodToJsonSchema(ValidateConfigArgsSchema),
                },
                {
                    name: 'need_use_these_tools',
                    description: 
`Tell the user which tools you will use.

Please select from the following tools:
- uv
- node
- git
- None

For all python items, please choose uv to manage them.
For all local-installation items, please choose git to pull them.
For all Node.js items, please choose node to manage them.
For remote deployment, please choose None.
`,
                    inputSchema: zodToJsonSchema(NeedUseTheseToolsSchema),
                }
            ];

        return {
            tools: allTools,
        };
    } catch (error) {
        logToStderr('error', `Error in list_tools request handler: ${error}`);
        throw error;
    }
});

import * as handlers from './handlers/index.js';
import {ServerResult} from './types.js';
import { describe } from "node:test";

server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest): Promise<ServerResult> => {
    const {name, arguments: args} = request.params;
    const startTime = Date.now();

    try {
        // Track tool call
        trackToolCall(name, args);

        // Using a more structured approach with dedicated handlers
        let result: ServerResult;

        switch (name) {
            case "add_config":
                result = await handlers.handleAddConfig(args);
                break;
            
            case "fix_config":
                result = await handlers.handleFixConfig(args);
                break;
            
            case "execute_command":
                result = await handlers.handleExecuteCommand(args);
                break;
            
            case "validate_config":
                result = await handlers.handleValidateConfig(args);
                break;

            case "need_use_these_tools":
                result = await handlers.handleNeedTools(args);
                break;

            default:
                result = {
                    content: [{type: "text", text: `Error: Unknown tool: ${name}`}],
                    isError: true,
                };
        }

        // Add tool call to history (exclude only get_recent_tool_calls to prevent recursion)
        const duration = Date.now() - startTime;

        // Track success or failure based on result
        if (result.isError) {
            console.log(`[FEEDBACK DEBUG] Tool ${name} failed, not checking feedback`);
        } else {
            console.log(`[FEEDBACK DEBUG] Tool ${name} succeeded, checking feedback...`);
        }
        return result;
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);

        return {
            content: [{type: "text", text: `Error: ${errorMessage}`}],
            isError: true,
        };
    }
});

// Add no-op handlers so Visual Studio initialization succeeds
server.setRequestHandler(ListResourceTemplatesRequestSchema, async () => ({ resourceTemplates: [] }));