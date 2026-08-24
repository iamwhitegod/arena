import { spawn } from 'node:child_process';
import path from 'node:path';
import { PreflightError } from '../errors/index.js';
import { getPythonPath } from '../utils/deps.js';
import { getArenaHome } from './runtime.js';
import type { RequiredProviderBinding } from './providers.js';

const LOCAL_READINESS_TIMEOUT_MS = 120_000;
const MAX_LOCAL_PROBE_OUTPUT_BYTES = 64 * 1024;
const LOCAL_ENV_ALLOWLIST = [
  'APPDATA',
  'COMSPEC',
  'HOME',
  'LANG',
  'LC_ALL',
  'LC_CTYPE',
  'LOCALAPPDATA',
  'PATH',
  'PATHEXT',
  'SYSTEMROOT',
  'TEMP',
  'TMP',
  'TMPDIR',
  'USERPROFILE',
  'WINDIR',
  'XDG_CACHE_HOME',
  'XDG_CONFIG_HOME',
] as const;

const LOCAL_PROBE = String.raw`
import json
import sys

bindings = json.loads(sys.argv[1])
capabilities = {binding["capability"] for binding in bindings}
if capabilities & {"chat", "overviewChat", "embedding"}:
    import llama_cpp
if "transcription" in capabilities:
    import ctranslate2
    import faster_whisper

from arena.models.locator import ModelLocator
locator = ModelLocator()
for binding in bindings:
    capability = binding["capability"]
    selected = binding.get("model") if binding.get("modelExplicit") else "auto"
    if capability in {"chat", "overviewChat"}:
        locator.resolve_gguf(selected, capability="chat")
    elif capability == "embedding":
        locator.resolve_gguf(selected, capability="embedding")
    elif capability == "transcription":
        locator.resolve_speech_model(selected)
print("arena-local-ready")
`.trim();

export type LocalReadinessProbe = (bindings: readonly RequiredProviderBinding[]) => Promise<void>;

function localProbeEnvironment(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {
    ARENA_MODEL_ROOT: path.join(getArenaHome(), 'models'),
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
  };
  for (const key of LOCAL_ENV_ALLOWLIST) {
    if (process.env[key] !== undefined) env[key] = process.env[key];
  }
  return env;
}

async function runLocalProbe(bindings: readonly RequiredProviderBinding[]): Promise<void> {
  const python = await getPythonPath();
  const payload = JSON.stringify(bindings);

  return new Promise((resolve, reject) => {
    const child = spawn(python, ['-c', LOCAL_PROBE, payload], {
      env: localProbeEnvironment(),
      stdio: ['ignore', 'pipe', 'ignore'],
      windowsHide: true,
      shell: false,
    });
    let settled = false;
    let stdout = '';
    let outputBytes = 0;
    let timer: NodeJS.Timeout | undefined;
    const settle = (action: () => void) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      action();
    };
    timer = setTimeout(() => {
      child.kill();
      settle(() => reject(new Error('local readiness probe timed out')));
    }, LOCAL_READINESS_TIMEOUT_MS);

    child.stdout.on('data', (chunk: Buffer) => {
      outputBytes += chunk.length;
      if (outputBytes > MAX_LOCAL_PROBE_OUTPUT_BYTES) {
        child.kill();
        settle(() => reject(new Error('local readiness probe output exceeded limit')));
        return;
      }
      stdout += chunk.toString();
    });
    child.on('error', (error) => {
      settle(() => reject(error));
    });
    child.on('close', (code) => {
      if (code === 0 && stdout.includes('arena-local-ready')) settle(resolve);
      else settle(() => reject(new Error(`local readiness probe exited with ${code}`)));
    });
  });
}

export async function validateLocalReadiness(
  bindings: readonly RequiredProviderBinding[],
  probe: LocalReadinessProbe = runLocalProbe
): Promise<void> {
  const localBindings = bindings.filter((binding) => binding.provider === 'local');
  if (localBindings.length === 0) return;

  try {
    await probe(localBindings);
  } catch {
    throw new PreflightError(
      'LOCAL_NOT_READY',
      'Local inference runtime or verified models are not ready',
      'Run: arena setup --local --model-pack lite'
    );
  }
}
