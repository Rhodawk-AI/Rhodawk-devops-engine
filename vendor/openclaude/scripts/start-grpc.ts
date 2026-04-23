/**
 * Rhodawk-vendored entrypoint for the OpenClaude headless gRPC daemon.
 *
 * Differences from upstream:
 *   - Honors OPENCLAUDE_AUTO_APPROVE=1 — short-circuits permission prompts
 *     so Rhodawk's orchestrator never has to answer ActionRequired events.
 *   - Hot-loads MCP servers from MCP_RUNTIME_CONFIG (default
 *     /tmp/mcp_runtime.json) on every chat session, so the daemon
 *     immediately picks up the per-audit MCP suite that app.py writes.
 *   - Logs the resolved provider (OPENAI_BASE_URL / OPENAI_MODEL) so
 *     log scraping can correlate which daemon answered which call.
 */

import { GrpcServer } from '../src/grpc/server.ts'
import { init } from '../src/entrypoints/init.ts'

Object.assign(globalThis, {
  MACRO: {
    VERSION: '0.6.0-rhodawk',
    DISPLAY_VERSION: '0.6.0-rhodawk',
    PACKAGE_URL: '@gitlawb/openclaude',
  },
})

async function main() {
  console.log('[rhodawk] Starting OpenClaude gRPC daemon…')
  await init()

  const { enableConfigs } = await import('../src/utils/config.js')
  enableConfigs()
  const { applySafeConfigEnvironmentVariables } = await import(
    '../src/utils/managedEnv.js'
  )
  applySafeConfigEnvironmentVariables()

  const { hydrateGeminiAccessTokenFromSecureStorage } = await import(
    '../src/utils/geminiCredentials.js'
  )
  hydrateGeminiAccessTokenFromSecureStorage()
  const { hydrateGithubModelsTokenFromSecureStorage } = await import(
    '../src/utils/githubModelsCredentials.js'
  )
  hydrateGithubModelsTokenFromSecureStorage()

  const { buildStartupEnvFromProfile, applyProfileEnvToProcessEnv } =
    await import('../src/utils/providerProfile.js')
  const { getProviderValidationError, validateProviderEnvOrExit } = await import(
    '../src/utils/providerValidation.js'
  )
  const startupEnv = await buildStartupEnvFromProfile({
    processEnv: process.env,
  })
  if (startupEnv !== process.env) {
    const startupProfileError = await getProviderValidationError(startupEnv)
    if (!startupProfileError) {
      applyProfileEnvToProcessEnv(process.env, startupEnv)
    } else {
      console.warn(
        `[rhodawk] Ignoring saved provider profile: ${startupProfileError}`,
      )
    }
  }
  await validateProviderEnvOrExit()

  const port = process.env.GRPC_PORT
    ? parseInt(process.env.GRPC_PORT, 10)
    : 50051
  const host = process.env.GRPC_HOST || '0.0.0.0'

  console.log(
    `[rhodawk] Provider resolved → base=${process.env.OPENAI_BASE_URL || '(default)'} ` +
      `model=${process.env.OPENAI_MODEL || '(default)'} ` +
      `auto_approve=${process.env.OPENCLAUDE_AUTO_APPROVE || '0'}`,
  )

  const server = new GrpcServer()
  server.start(port, host)
}

main().catch(err => {
  console.error('[rhodawk] Fatal error starting gRPC server:', err)
  process.exit(1)
})
