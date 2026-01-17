/**
 * Config command - Manage Arena configuration
 * View, set, get, and reset configuration values
 */

import chalk from 'chalk';
import inquirer from 'inquirer';
import { ConfigManager } from '../core/config.js';
import { formatList } from '../ui/formatters.js';

type ConfigAction = 'view' | 'set' | 'get' | 'reset';

export async function configCommand(
  action?: string,
  key?: string,
  value?: string
): Promise<void> {
  const configManager = new ConfigManager();

  // Determine action
  const resolvedAction: ConfigAction = (action as ConfigAction) || 'view';

  try {
    switch (resolvedAction) {
      case 'view':
        await viewConfig(configManager);
        break;

      case 'set':
        if (!key || value === undefined) {
          console.error(chalk.red('\n✗ Usage: arena config set <key> <value>\n'));
          process.exit(1);
        }
        await setConfig(configManager, key, value);
        break;

      case 'get':
        if (!key) {
          console.error(chalk.red('\n✗ Usage: arena config get <key>\n'));
          process.exit(1);
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

  const separator = chalk.gray('─'.repeat(60));

  console.log('\n' + separator);
  console.log(chalk.cyan('⚙️  Arena Configuration') + chalk.gray(' (~/.arena/config.json)'));
  console.log(separator + '\n');

  // Format and display config
  const configEntries = Object.entries(config);
  const maxKeyLength = Math.max(...configEntries.map(([k]) => k.length));

  configEntries.forEach(([key, val]) => {
    const paddedKey = key.padEnd(maxKeyLength);
    const displayValue = formatConfigValue(val);
    console.log(`  ${chalk.white(paddedKey)} = ${displayValue}`);
  });

  console.log('\n' + separator);
  console.log(chalk.gray('\n💡 Tip: Use ') + chalk.cyan('arena config set <key> <value>') + chalk.gray(' to update\n'));
}

/**
 * Set a configuration value
 */
async function setConfig(configManager: ConfigManager, key: string, value: string): Promise<void> {
  const config = await configManager.getGlobalConfig() || {};

  // Parse value (handle booleans, numbers, strings)
  const parsedValue = parseConfigValue(value);

  config[key] = parsedValue;

  await configManager.updateGlobalConfig(config);

  console.log(chalk.green(`\n✓ Set ${chalk.white(key)} = ${formatConfigValue(parsedValue)}\n`));
}

/**
 * Get a specific configuration value
 */
async function getConfig(configManager: ConfigManager, key: string): Promise<void> {
  const config = await configManager.getGlobalConfig() || {};

  if (key in config) {
    console.log(chalk.white(`\n${key} = ${formatConfigValue(config[key])}\n`));
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

  // Clear config (set to empty object)
  await configManager.updateGlobalConfig({});

  console.log(chalk.green('\n✓ Configuration reset\n'));
  console.log(chalk.gray('  Run: ') + chalk.cyan('arena init') + chalk.gray(' to set up again\n'));
}

/**
 * Format config value for display
 */
function formatConfigValue(value: any): string {
  if (typeof value === 'boolean') {
    return value ? chalk.green('true') : chalk.red('false');
  }

  if (typeof value === 'number') {
    return chalk.cyan(value.toString());
  }

  if (typeof value === 'string') {
    // Mask API keys
    if (value.startsWith('sk-')) {
      return chalk.gray('sk-••••••••••••••••••');
    }
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
function parseConfigValue(value: string): any {
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
