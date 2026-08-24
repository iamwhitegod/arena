import http from 'node:http';
import { PreflightError } from '../errors/index.js';
import { isValidModelIdentifier } from './providers.js';

const OLLAMA_HOST = '127.0.0.1';
const OLLAMA_PORT = 11434;
const OLLAMA_TAGS_PATH = '/api/tags';
const OLLAMA_PREFLIGHT_TIMEOUT_MS = 3_000;
const MAX_TAGS_RESPONSE_BYTES = 1024 * 1024;

type TagsLoader = () => Promise<unknown>;

function fetchOllamaTags(): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let settled = false;
    let wallClockTimer: NodeJS.Timeout | undefined;
    const settle = (action: () => void) => {
      if (settled) return;
      settled = true;
      if (wallClockTimer) clearTimeout(wallClockTimer);
      action();
    };
    const request = http.request(
      {
        hostname: OLLAMA_HOST,
        port: OLLAMA_PORT,
        path: OLLAMA_TAGS_PATH,
        method: 'GET',
        headers: { Accept: 'application/json' },
      },
      (response) => {
        if (response.statusCode !== 200) {
          response.resume();
          settle(() =>
            reject(
              new PreflightError(
                'OLLAMA_UNAVAILABLE',
                `Ollama readiness check returned HTTP ${response.statusCode || 'unknown'}`,
                'Restart Ollama, then try again'
              )
            )
          );
          return;
        }

        const declaredLength = Number(response.headers['content-length']);
        if (Number.isFinite(declaredLength) && declaredLength > MAX_TAGS_RESPONSE_BYTES) {
          response.resume();
          request.destroy();
          settle(() =>
            reject(
              new PreflightError(
                'OLLAMA_INVALID_RESPONSE',
                'Ollama returned an oversized readiness response',
                'Restart or update Ollama, then try again'
              )
            )
          );
          return;
        }

        const chunks: Buffer[] = [];
        let totalBytes = 0;
        response.on('data', (chunk: Buffer) => {
          totalBytes += chunk.length;
          if (totalBytes > MAX_TAGS_RESPONSE_BYTES) {
            request.destroy();
            settle(() =>
              reject(
                new PreflightError(
                  'OLLAMA_INVALID_RESPONSE',
                  'Ollama returned an oversized readiness response',
                  'Restart or update Ollama, then try again'
                )
              )
            );
            return;
          }
          chunks.push(chunk);
        });
        response.on('end', () => {
          try {
            settle(() => resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))));
          } catch {
            settle(() =>
              reject(
                new PreflightError(
                  'OLLAMA_INVALID_RESPONSE',
                  'Ollama returned an invalid readiness response',
                  'Restart or update Ollama, then try again'
                )
              )
            );
          }
        });
        response.on('error', () => {
          settle(() =>
            reject(
              new PreflightError(
                'OLLAMA_UNAVAILABLE',
                'Ollama closed the readiness response unexpectedly',
                'Restart Ollama, then try again'
              )
            )
          );
        });
      }
    );

    wallClockTimer = setTimeout(() => {
      request.destroy();
      settle(() =>
        reject(
          new PreflightError(
            'OLLAMA_UNAVAILABLE',
            'Ollama did not respond within 3 seconds',
            'Make sure Ollama is running, then try again'
          )
        )
      );
    }, OLLAMA_PREFLIGHT_TIMEOUT_MS);

    request.setTimeout(OLLAMA_PREFLIGHT_TIMEOUT_MS, () => {
      request.destroy();
      settle(() =>
        reject(
          new PreflightError(
            'OLLAMA_UNAVAILABLE',
            'Ollama did not respond within 3 seconds',
            'Make sure Ollama is running, then try again'
          )
        )
      );
    });
    request.on('error', () => {
      settle(() =>
        reject(
          new PreflightError(
            'OLLAMA_NOT_RUNNING',
            'Arena could not connect to Ollama at http://127.0.0.1:11434',
            'Install and start Ollama, then run: ollama serve'
          )
        )
      );
    });
    request.end();
  });
}

function installedModelNames(payload: unknown): Set<string> {
  if (
    !payload ||
    typeof payload !== 'object' ||
    !Array.isArray((payload as { models?: unknown }).models)
  ) {
    throw new PreflightError(
      'OLLAMA_INVALID_RESPONSE',
      'Ollama returned an invalid model list',
      'Restart or update Ollama, then try again'
    );
  }

  const names = new Set<string>();
  for (const item of (payload as { models: unknown[] }).models.slice(0, 10_000)) {
    if (!item || typeof item !== 'object') continue;
    const candidate = item as { name?: unknown; model?: unknown };
    for (const value of [candidate.name, candidate.model]) {
      if (typeof value === 'string' && isValidModelIdentifier(value)) {
        names.add(value);
      }
    }
  }
  return names;
}

function hasModel(installed: Set<string>, requested: string): boolean {
  if (installed.has(requested)) return true;
  return !requested.includes(':') && installed.has(`${requested}:latest`);
}

export async function validateOllamaReadiness(
  requiredModels: readonly string[],
  loadTags: TagsLoader = fetchOllamaTags
): Promise<void> {
  const models = [...new Set(requiredModels)];
  for (const model of models) {
    if (!isValidModelIdentifier(model)) {
      throw new PreflightError(
        'INVALID_MODEL',
        'An Ollama model identifier is invalid',
        'Use a non-empty model name without control characters'
      );
    }
  }

  const installed = installedModelNames(await loadTags());
  const missing = models.filter((model) => !hasModel(installed, model));
  if (missing.length > 0) {
    throw new PreflightError(
      'OLLAMA_MODEL_MISSING',
      `Required Ollama ${missing.length === 1 ? 'model is' : 'models are'} not installed: ${missing.join(', ')}`,
      missing.map((model) => `ollama pull ${model}`).join('\n    ')
    );
  }
}
