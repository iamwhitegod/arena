/**
 * Interactive setup wizard for Arena CLI
 * Helps users configure Arena for their workflow
 */

import chalk from 'chalk';
import inquirer from 'inquirer';
import { ConfigManager } from '../core/config.js';

interface InitAnswers {
  workflow: 'content-creator' | 'podcast' | 'course' | 'custom';
  clipDuration: 'short' | 'medium' | 'long';
  quality: 'balanced' | 'high' | 'cost-optimized';
  apiKey?: string;
}

export async function initCommand(): Promise<void> {
  console.log(chalk.cyan('\n✨ Welcome to Arena!\n'));
  console.log(chalk.white("Let's set up your video clip generation workspace.\n"));

  // Check if config already exists
  const configManager = new ConfigManager();
  const existingConfig = await configManager.getGlobalConfig();

  if (existingConfig && Object.keys(existingConfig).length > 0) {
    const { overwrite } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'overwrite',
        message: 'Configuration already exists. Overwrite?',
        default: false,
      },
    ]);

    if (!overwrite) {
      console.log(chalk.yellow('\n✓ Keeping existing configuration\n'));
      return;
    }
  }

  // Interactive prompts
  const answers = await inquirer.prompt<InitAnswers>([
    {
      type: 'list',
      name: 'workflow',
      message: 'Select your workflow:',
      choices: [
        {
          name: 'Content Creator (social media clips)',
          value: 'content-creator',
        },
        {
          name: 'Podcast Editor (long-form → highlights)',
          value: 'podcast',
        },
        {
          name: 'Course Creator (educational snippets)',
          value: 'course',
        },
        {
          name: 'Custom (configure manually)',
          value: 'custom',
        },
      ],
      default: 'content-creator',
    },
    {
      type: 'list',
      name: 'clipDuration',
      message: 'Default clip duration:',
      choices: [
        {
          name: 'Short (15-30s) - TikTok, Instagram Reels',
          value: 'short',
        },
        {
          name: 'Medium (30-60s) - YouTube Shorts',
          value: 'medium',
        },
        {
          name: 'Long (60-120s) - Full segments',
          value: 'long',
        },
      ],
      default: 'medium',
    },
    {
      type: 'list',
      name: 'quality',
      message: 'Quality vs Cost preference:',
      choices: [
        {
          name: 'Balanced (gpt-4o-mini, ~$0.20/video)',
          value: 'balanced',
        },
        {
          name: 'High Quality (gpt-4o, ~$0.50/video)',
          value: 'high',
        },
      ],
      default: 'balanced',
    },
  ]);

  // Check for API key
  const hasApiKey = !!process.env.OPENAI_API_KEY;
  if (!hasApiKey) {
    console.log(chalk.yellow('\n⚠️  OpenAI API key not found in environment\n'));

    const { provideApiKey } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'provideApiKey',
        message: 'Would you like to set your OpenAI API key now?',
        default: true,
      },
    ]);

    if (provideApiKey) {
      const { apiKey } = await inquirer.prompt([
        {
          type: 'password',
          name: 'apiKey',
          message: 'OpenAI API Key (starts with sk-):',
          mask: '*',
          validate: (input: string) => {
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
          },
        },
      ]);

      answers.apiKey = apiKey;
    }
  }

  // Build configuration
  const config = buildConfiguration(answers);

  // Save non-sensitive configuration separately from credentials.
  await configManager.updateGlobalConfig(config);
  if (answers.apiKey) {
    await configManager.setOpenAIApiKey(answers.apiKey);
  }

  // Display success
  console.log(chalk.green('\n✓ Created ~/.arena/config.json'));
  if (answers.apiKey) {
    console.log(chalk.green('✓ Stored API key with owner-only permissions'));
  }
  console.log(chalk.green('✓ Workspace ready!\n'));

  // Show next steps
  displayNextSteps(answers, hasApiKey || !!answers.apiKey);
}

interface ConfigurationObject {
  [key: string]: unknown;
  workflow: string;
  minDuration?: number;
  maxDuration?: number;
  editorialModel?: string;
  numClips?: number;
  padding?: number;
}

/**
 * Build configuration object from answers
 */
function buildConfiguration(answers: InitAnswers): ConfigurationObject {
  const config: ConfigurationObject = {
    workflow: answers.workflow,
  };

  // Clip duration settings
  const durationSettings = {
    short: { min: 15, max: 30 },
    medium: { min: 30, max: 60 },
    long: { min: 60, max: 120 },
  };

  config.minDuration = durationSettings[answers.clipDuration].min;
  config.maxDuration = durationSettings[answers.clipDuration].max;

  // Quality settings (4-layer editorial is always on)
  if (answers.quality === 'balanced') {
    config.editorialModel = 'gpt-4o-mini';
  } else if (answers.quality === 'high') {
    config.editorialModel = 'gpt-4o';
  }

  // Workflow-specific defaults
  if (answers.workflow === 'content-creator') {
    config.numClips = 5;
    config.padding = 0.5;
  } else if (answers.workflow === 'podcast') {
    config.numClips = 10;
    config.padding = 1.0;
  } else if (answers.workflow === 'course') {
    config.numClips = 3;
    config.padding = 0.5;
  }

  return config;
}

/**
 * Display next steps based on configuration
 */
function displayNextSteps(answers: InitAnswers, hasApiKey: boolean): void {
  console.log(chalk.cyan('💡 Try it now:\n'));

  if (!hasApiKey) {
    console.log(chalk.yellow('  First, set your API key:'));
    console.log(chalk.white('    export OPENAI_API_KEY="sk-..."\n'));
  }

  console.log(chalk.white('  Process a video:'));
  console.log(chalk.cyan('    arena process video.mp4\n'));

  console.log(chalk.gray('  Or customize:'));
  console.log(chalk.cyan('    arena process video.mp4 -n 3 --min 20 --max 45\n'));

  if (answers.quality !== 'high') {
    console.log(chalk.gray('  Try premium model:'));
    console.log(chalk.cyan('    arena process video.mp4 --editorial-model gpt-4o\n'));
  }
}
