import * as grpc from '@grpc/grpc-js'
import * as protoLoader from '@grpc/proto-loader'
import path from 'path'
import { existsSync, readFileSync } from 'fs'
import { randomUUID } from 'crypto'
import { QueryEngine } from '../QueryEngine.js'
import { getTools } from '../tools.js'
import { getDefaultAppState } from '../state/AppStateStore.js'
import { AppState } from '../state/AppState.js'
import {
  FileStateCache,
  READ_FILE_STATE_CACHE_SIZE,
} from '../utils/fileStateCache.js'
import { reconnectMcpServerImpl } from '../services/mcp/client.js'
import type { MCPServerConnection } from '../services/mcp/types.js'

const PROTO_PATH = path.resolve(
  import.meta.dirname,
  '../proto/openclaude.proto',
)

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
})

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition) as any
const openclaudeProto = protoDescriptor.openclaude.v1

const MAX_SESSIONS = 1000

// ─────────────────────────────────────────────────────────────────────
// Rhodawk-vendor extensions
// ─────────────────────────────────────────────────────────────────────
const AUTO_APPROVE = process.env.OPENCLAUDE_AUTO_APPROVE === '1'
const MCP_RUNTIME_CONFIG =
  process.env.MCP_RUNTIME_CONFIG || '/tmp/mcp_runtime.json'

type McpRuntimeServerConfig = {
  command: string
  args?: string[]
  env?: Record<string, string>
  description?: string
}

let _mcpCache: {
  mtimeMs: number
  clients: MCPServerConnection[]
} | null = null

async function loadRuntimeMcpClients(): Promise<MCPServerConnection[]> {
  try {
    if (!existsSync(MCP_RUNTIME_CONFIG)) {
      return []
    }
    const stat = (await import('fs/promises')).then(m =>
      m.stat(MCP_RUNTIME_CONFIG),
    )
    const { mtimeMs } = await stat
    if (_mcpCache && _mcpCache.mtimeMs === mtimeMs) {
      return _mcpCache.clients
    }
    const raw = readFileSync(MCP_RUNTIME_CONFIG, 'utf8')
    const parsed = JSON.parse(raw) as {
      mcpServers?: Record<string, McpRuntimeServerConfig>
    }
    const servers = parsed.mcpServers || {}
    const out: MCPServerConnection[] = []
    for (const [name, cfg] of Object.entries(servers)) {
      try {
        const result = await reconnectMcpServerImpl(name, {
          type: 'stdio',
          command: cfg.command,
          args: cfg.args || [],
          env: cfg.env || {},
          scope: 'project',
        } as any)
        if (result?.client) {
          out.push(result.client)
        }
      } catch (err) {
        console.warn(
          `[rhodawk] MCP server ${name} failed to connect: ${(err as Error).message}`,
        )
      }
    }
    _mcpCache = { mtimeMs, clients: out }
    console.log(
      `[rhodawk] Loaded ${out.length}/${Object.keys(servers).length} MCP servers from ${MCP_RUNTIME_CONFIG}`,
    )
    return out
  } catch (err) {
    console.warn(
      `[rhodawk] Failed to load MCP runtime config (${MCP_RUNTIME_CONFIG}): ${(err as Error).message}`,
    )
    return []
  }
}

export class GrpcServer {
  private server: grpc.Server
  private sessions: Map<string, any[]> = new Map()

  constructor() {
    this.server = new grpc.Server()
    this.server.addService(openclaudeProto.AgentService.service, {
      Chat: this.handleChat.bind(this),
    })
  }

  start(port: number = 50051, host: string = '0.0.0.0') {
    this.server.bindAsync(
      `${host}:${port}`,
      grpc.ServerCredentials.createInsecure(),
      (error, boundPort) => {
        if (error) {
          console.error('[rhodawk] Failed to start gRPC server:', error)
          return
        }
        console.log(`[rhodawk] gRPC daemon ready at ${host}:${boundPort}`)
      },
    )
  }

  private handleChat(call: grpc.ServerDuplexStream<any, any>) {
    let engine: QueryEngine | null = null
    let appState: AppState = getDefaultAppState()
    const fileCache: FileStateCache = new FileStateCache(
      READ_FILE_STATE_CACHE_SIZE,
      25 * 1024 * 1024,
    )
    const pendingRequests = new Map<string, (reply: string) => void>()
    let previousMessages: any[] = []
    let sessionId = ''
    let interrupted = false

    call.on('data', async clientMessage => {
      try {
        if (clientMessage.request) {
          if (engine) {
            call.write({
              error: {
                message: 'A request is already in progress on this stream',
                code: 'ALREADY_EXISTS',
              },
            })
            return
          }
          interrupted = false
          const req = clientMessage.request
          sessionId = req.session_id || ''
          previousMessages = []

          if (sessionId && this.sessions.has(sessionId)) {
            previousMessages = [...this.sessions.get(sessionId)!]
          }

          // Hot-load MCP servers from /tmp/mcp_runtime.json
          const mcpClients = await loadRuntimeMcpClients()

          const toolNameById = new Map<string, string>()

          engine = new QueryEngine({
            cwd: req.working_directory || process.cwd(),
            tools: getTools(appState.toolPermissionContext),
            commands: [],
            mcpClients,
            agents: [],
            ...(previousMessages.length > 0
              ? { initialMessages: previousMessages }
              : {}),
            includePartialMessages: true,
            canUseTool: async (tool, input, context, assistantMsg, toolUseID) => {
              if (toolUseID) {
                toolNameById.set(toolUseID, tool.name)
              }
              call.write({
                tool_start: {
                  tool_name: tool.name,
                  arguments_json: JSON.stringify(input),
                  tool_use_id: toolUseID,
                },
              })

              if (AUTO_APPROVE) {
                return { behavior: 'allow' }
              }

              const promptId = randomUUID()
              call.write({
                action_required: {
                  prompt_id: promptId,
                  question: `Approve ${tool.name}?`,
                  type: 'CONFIRM_COMMAND',
                },
              })
              return new Promise(resolve => {
                pendingRequests.set(promptId, reply => {
                  if (
                    reply.toLowerCase() === 'yes' ||
                    reply.toLowerCase() === 'y'
                  ) {
                    resolve({ behavior: 'allow' })
                  } else {
                    resolve({ behavior: 'deny', reason: 'User denied via gRPC' })
                  }
                })
              })
            },
            getAppState: () => appState,
            setAppState: updater => {
              appState = updater(appState)
            },
            readFileCache: fileCache,
            userSpecifiedModel: req.model,
            fallbackModel: req.model,
          })

          let fullText = ''
          let promptTokens = 0
          let completionTokens = 0

          const generator = engine.submitMessage(req.message)

          for await (const msg of generator) {
            if (msg.type === 'stream_event') {
              if (
                msg.event.type === 'content_block_delta' &&
                msg.event.delta.type === 'text_delta'
              ) {
                call.write({
                  text_chunk: { text: msg.event.delta.text },
                })
                fullText += msg.event.delta.text
              }
            } else if (msg.type === 'user') {
              const content = msg.message.content
              if (Array.isArray(content)) {
                for (const block of content) {
                  if (block.type === 'tool_result') {
                    let outputStr = ''
                    if (typeof block.content === 'string') {
                      outputStr = block.content
                    } else if (Array.isArray(block.content)) {
                      outputStr = block.content
                        .map(c => (c.type === 'text' ? c.text : ''))
                        .join('\n')
                    }
                    call.write({
                      tool_result: {
                        tool_name:
                          toolNameById.get(block.tool_use_id) ?? block.tool_use_id,
                        tool_use_id: block.tool_use_id,
                        output: outputStr,
                        is_error: block.is_error || false,
                      },
                    })
                  }
                }
              }
            } else if (msg.type === 'result') {
              if (msg.subtype === 'success') {
                if (msg.result) {
                  fullText = msg.result
                }
                promptTokens = msg.usage?.input_tokens ?? 0
                completionTokens = msg.usage?.output_tokens ?? 0
              }
            }
          }

          if (!interrupted) {
            previousMessages = [...engine.getMessages()]
            if (sessionId) {
              if (
                !this.sessions.has(sessionId) &&
                this.sessions.size >= MAX_SESSIONS
              ) {
                this.sessions.delete(this.sessions.keys().next().value)
              }
              this.sessions.set(sessionId, previousMessages)
            }
            call.write({
              done: {
                full_text: fullText,
                prompt_tokens: promptTokens,
                completion_tokens: completionTokens,
              },
            })
          }
          engine = null
        } else if (clientMessage.input) {
          const promptId = clientMessage.input.prompt_id
          const reply = clientMessage.input.reply
          if (pendingRequests.has(promptId)) {
            pendingRequests.get(promptId)!(reply)
            pendingRequests.delete(promptId)
          }
        } else if (clientMessage.cancel) {
          interrupted = true
          if (engine) {
            engine.interrupt()
          }
          call.end()
        }
      } catch (err: any) {
        console.error('[rhodawk] Error processing stream:', err)
        call.write({
          error: {
            message: err.message || 'Internal server error',
            code: 'INTERNAL',
          },
        })
        call.end()
      }
    })

    call.on('end', () => {
      interrupted = true
      for (const resolve of pendingRequests.values()) {
        resolve('no')
      }
      if (engine) {
        engine.interrupt()
      }
      engine = null
      pendingRequests.clear()
    })
  }
}
