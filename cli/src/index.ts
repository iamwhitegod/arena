#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { processCommand } from './commands/process.js';

const program = new Command();

program
  .name('arena')
  .description('AI-powered video editing tool for the terminal')
  .version('0.1.0');

program
  .command('process')
  .description('Process a video and generate clips automatically')
  .argument('<video>', 'path to video file')
  .option('-o, --output <dir>', 'output directory', '.arena/output')
  .option('-c, --clips <number>', 'target number of clips to generate', '10')
  .option('--min-duration <seconds>', 'minimum clip duration', '30')
  .option('--max-duration <seconds>', 'maximum clip duration', '90')
  .action(processCommand);

program
  .command('analyze')
  .description('Analyze video without generating clips')
  .argument('<video>', 'path to video file')
  .action((video: string) => {
    console.log(chalk.yellow('analyze command coming soon...'));
    console.log(`Analyzing: ${video}`);
  });

program
  .command('review')
  .description('Review and select clips from analysis')
  .action(() => {
    console.log(chalk.yellow('review command coming soon...'));
  });

program
  .command('generate')
  .description('Generate clips from selection')
  .action(() => {
    console.log(chalk.yellow('generate command coming soon...'));
  });

program
  .command('config')
  .description('Configure Arena settings')
  .action(() => {
    console.log(chalk.yellow('config command coming soon...'));
  });

program.parse();
