/**
 * Config command - Manage Arena configuration
 * View, set, get, and reset configuration values
 */

import chalk from 'chalk';
import inquirer from 'inquirer';
import { ConfigManager, isSensitiveConfigKey } from '../core/config.js';
import {
  isValidModelIdentifier,
  providerSupportsCapability,
  SUPPORTED_PROVIDERS,
  type ProviderName,
} from '../core/providers.js';
import { commandHeader } from '../ui/output.js';

type ConfigAction = 'view' | 'set' | 'get' | 'reset';

export async function configCommand(action?: string, key?: string, value?: string): Promise<void> {
  const configManager = new ConfigManager();

  // Determine action
  const resolvedAction: ConfigAction = (action as ConfigAction) || 'view';

  try {
    switch (resolvedAction) {
      case 'view':
        await viewConfig(configManager);
        break;

      case 'set':
        if (!key) {
          console.error(chalk.red('\n✗ Usage: arena config set <key> [value]\n'));
          process.exit(1);
          return;
        }
        await setConfig(configManager, key, value);
        break;

      case 'get':
        if (!key) {
          console.error(chalk.red('\n✗ Usage: arena config get <key>\n'));
          process.exit(1);
          return;
        }
        await getConfig(configManager, key);
        break;

      case 'reset':
        await resetConfig(configManager);
        break;

      default:
        console.error(chalk.red(`\n✗ Unknown action: ${action}\n`));
        console.log(chalk.white('  Valid actions: view, set, get, reset\n'));
        process.exit(1);
        return;
    }
  } catch (error) {
    console.error(chalk.red('\n✗ Config operation failed\n'));
    console.error(chalk.white(`  ${error instanceof Error ? error.message : String(error)}\n`));
    process.exit(1);
  }
}

/**
 * View current configuration
 */
async function viewConfig(configManager: ConfigManager): Promise<void> {
  const config = await configManager.getGlobalConfig();

  if (!config || Object.keys(config).length === 0) {
    console.log(chalk.yellow('\n⚠️  No configuration found\n'));
    console.log(chalk.gray('  Run: ') + chalk.cyan('arena init') + chalk.gray(' to create one\n'));
    return;
  }

  commandHeader('Arena configuration', [['File', '~/.arena/config.json']]);

  // Format and display config
  const configEntries = Object.entries(config);
  const maxKeyLength = Math.max(...configEntries.map(([k]) => k.length));

  configEntries.forEach(([key, val]) => {
    const paddedKey = key.padEnd(maxKeyLength);
    const displayValue = formatConfigValue(val, key);
    console.log(`  ${chalk.white(paddedKey)} = ${displayValue}`);
  });

  if (await configManager.hasStoredOpenAIApiKey()) {
    console.log(
      `  ${chalk.white('openai_api_key'.padEnd(maxKeyLength))} = ${chalk.gray('[stored securely]')}`
    );
  }

  console.log();
}

/**
 * Set a configuration value
 */
async function setConfig(configManager: ConfigManager, key: string, value?: string): Promise<void> {
  if (isSensitiveConfigKey(key)) {
    if (key.toLowerCase().replaceAll('-', '_') !== 'openai_api_key') {
      throw new Error(`Unsupported credential key "${key}".`);
    }
    if (value !== undefined) {
      throw new Error(
        'Refusing an API key passed as a command-line argument because it may remain in shell history. Run: arena config set openai_api_key'
      );
    }

    const { apiKey } = await inquirer.prompt<{ apiKey: string }>([
      {
        type: 'password',
        name: 'apiKey',
        message: 'OpenAI API key:',
        mask: '*',
        validate: validateOpenAIApiKey,
      },
    ]);
    await configManager.setOpenAIApiKey(apiKey);
    console.log(chalk.green(`\n✓ Stored ${chalk.white(key)} with owner-only permissions\n`));
    return;
  }

  if (value === undefined) {
    throw new Error(`A value is required for non-sensitive key "${key}".`);
  }

  const providerKeys = new Set([
    'provider',
    'chat_provider',
    'overview_chat_provider',
    'embedding_provider',
    'transcription_provider',
  ]);
  if (providerKeys.has(key)) {
    if (!SUPPORTED_PROVIDERS.includes(value as (typeof SUPPORTED_PROVIDERS)[number])) {
      throw new Error(
        `Unsupported provider "${value}". Choose: ${SUPPORTED_PROVIDERS.join(', ')}.`
      );
    }
    if (
      key === 'transcription_provider' &&
      !providerSupportsCapability(value as ProviderName, 'transcription')
    ) {
      throw new Error(
        `Provider "${value}" does not support transcription. Choose local or openai.`
      );
    }
  }

  if (key.endsWith('_model') && !isValidModelIdentifier(value)) {
    throw new Error('Model identifiers must be bounded text without control characters.');
  }

  // Parse value (handle booleans, numbers, strings)
  const parsedValue = parseConfigValue(value);
  await configManager.updateGlobalConfig({ [key]: parsedValue });

  console.log(
    chalk.green(`\n✓ Set ${chalk.white(key)} = ${formatConfigValue(parsedValue, key)}\n`)
  );
}

/**
 * Get a specific configuration value
 */
async function getConfig(configManager: ConfigManager, key: string): Promise<void> {
  if (isSensitiveConfigKey(key)) {
    const configured =
      key.toLowerCase().replaceAll('-', '_') === 'openai_api_key' &&
      (await configManager.hasStoredOpenAIApiKey());
    console.log(
      configured
        ? chalk.white(`\n${key} = ${chalk.gray('[stored securely]')}\n`)
        : chalk.yellow(`\n⚠️  Credential "${key}" is not configured\n`)
    );
    return;
  }

  const config = (await configManager.getGlobalConfig()) || {};

  if (key in config) {
    console.log(chalk.white(`\n${key} = ${formatConfigValue(config[key], key)}\n`));
  } else {
    console.log(chalk.yellow(`\n⚠️  Key "${key}" not found in configuration\n`));
  }
}

/**
 * Reset configuration to defaults
 */
async function resetConfig(configManager: ConfigManager): Promise<void> {
  const { confirm } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'confirm',
      message: 'Are you sure you want to reset configuration?',
      default: false,
    },
  ]);

  if (!confirm) {
    console.log(chalk.yellow('\n✗ Reset cancelled\n'));
    return;
  }

  await configManager.resetGlobalConfig(true);

  console.log(chalk.green('\n✓ Configuration and stored credentials reset\n'));
  console.log(chalk.gray('  Run: ') + chalk.cyan('arena init') + chalk.gray(' to set up again\n'));
}

/**
 * Format config value for display
 */
function formatConfigValue(value: unknown, key?: string): string {
  if (key && isSensitiveConfigKey(key)) {
    return chalk.gray('[redacted]');
  }

  if (typeof value === 'boolean') {
    return value ? chalk.green('true') : chalk.red('false');
  }

  if (typeof value === 'number') {
    return chalk.cyan(value.toString());
  }

  if (typeof value === 'string') {
    return chalk.yellow(`"${value}"`);
  }

  if (Array.isArray(value)) {
    return chalk.magenta(`[${value.join(', ')}]`);
  }

  if (typeof value === 'object' && value !== null) {
    return chalk.magenta(JSON.stringify(value));
  }

  return chalk.gray(String(value));
}

/**
 * Parse config value from string
 */
function parseConfigValue(value: string): unknown {
  // Boolean
  if (value === 'true') return true;
  if (value === 'false') return false;

  // Number
  const num = parseFloat(value);
  if (!isNaN(num) && value === num.toString()) {
    return num;
  }

  // Array (JSON array)
  if (value.startsWith('[') && value.endsWith(']')) {
    try {
      return JSON.parse(value);
    } catch {
      // Not valid JSON, treat as string
    }
  }

  // Object (JSON object)
  if (value.startsWith('{') && value.endsWith('}')) {
    try {
      return JSON.parse(value);
    } catch {
      // Not valid JSON, treat as string
    }
  }

  // String (default)
  return value;
}

function validateOpenAIApiKey(input: string): true | string {
  if (!input) {
    return 'API key is required';
  }
  if (!input.startsWith('sk-')) {
    return 'API key should start with "sk-"';
  }
  if (input.length < 40) {
    return 'API key appears to be incomplete';
  }
  return true;
}
