#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { processCommand } from './commands/process.js';
import { initCommand } from './commands/init.js';
import { analyzeCommand } from './commands/analyze.js';
import { transcribeCommand } from './commands/transcribe.js';
import { generateCommand } from './commands/generate.js';
import { configCommand } from './commands/config.js';
import { extractAudioCommand } from './commands/extract-audio.js';

const program = new Command();

program
  .name('arena')
  .description('AI-powered video editing tool for the terminal')
  .version('0.1.0');

// Init command - Setup wizard
program
  .command('init')
  .description('Interactive setup wizard for Arena')
  .action(initCommand);

// Process command - All-in-one processing
program
  .command('process')
  .description('Process a video and generate clips automatically')
  .argument('<video>', 'path to video file')
  .option('-o, --output <dir>', 'output directory', 'output')
  .option('-n, --num-clips <number>', 'target number of clips to generate', '5')
  .option('--min <seconds>', 'minimum clip duration', '30')
  .option('--max <seconds>', 'maximum clip duration', '90')
  .option('--use-4layer', 'use 4-layer editorial system (higher quality)')
  .option('--editorial-model <model>', 'model for Layers 1-2: gpt-4o or gpt-4o-mini', 'gpt-4o')
  .option('--export-layers', 'export intermediate layer results for debugging')
  .option('--fast', 'fast mode - stream copy (10x faster)')
  .option('--no-cache', 'force re-transcription, ignore cached transcript')
  .option('--padding <seconds>', 'seconds of padding before/after clips', '0.5')
  .option('--debug', 'show debug information')
  .action(processCommand);

// Transcribe command - Transcription only
program
  .command('transcribe')
  .description('Transcribe video audio only')
  .argument('<video>', 'path to video file')
  .option('-o, --output <file>', 'output transcript file path')
  .option('--no-cache', 'force re-transcription, ignore cached transcript')
  .option('--debug', 'show debug information')
  .action(transcribeCommand);

// Analyze command - Analysis without generating clips
program
  .command('analyze')
  .description('Analyze video without generating clips')
  .argument('<video>', 'path to video file')
  .option('-o, --output <file>', 'output analysis file path')
  .option('-n, --num-clips <number>', 'target number of clips to analyze')
  .option('--min <seconds>', 'minimum clip duration')
  .option('--max <seconds>', 'maximum clip duration')
  .option('--use-4layer', 'use 4-layer editorial system (higher quality)')
  .option('--editorial-model <model>', 'model for Layers 1-2: gpt-4o or gpt-4o-mini', 'gpt-4o')
  .option('--transcript <file>', 'use existing transcript file')
  .option('--debug', 'show debug information')
  .action(analyzeCommand);

// Generate command - Generate clips from existing analysis
program
  .command('generate')
  .description('Generate clips from existing analysis')
  .argument('<video>', 'path to video file')
  .argument('<analysis>', 'path to analysis JSON file')
  .option('-o, --output <dir>', 'output directory for clips')
  .option('-n, --num-clips <number>', 'number of clips to generate')
  .option('--select <indices>', 'comma-separated clip indices to generate (e.g., "1,3,5")')
  .option('--fast', 'fast mode - stream copy (10x faster)')
  .option('--padding <seconds>', 'seconds of padding before/after clips')
  .option('--debug', 'show debug information')
  .action(generateCommand);

// Extract-audio command - Extract audio from video
program
  .command('extract-audio')
  .description('Extract audio from video')
  .argument('<video>', 'path to video file')
  .option('-o, --output <file>', 'output audio file path')
  .option('--format <format>', 'audio format: mp3, wav, aac, flac', 'mp3')
  .option('--bitrate <rate>', 'audio bitrate (e.g., "192k")')
  .option('--sample-rate <rate>', 'sample rate in Hz (e.g., "44100")')
  .option('--mono', 'convert to mono')
  .option('--debug', 'show debug information')
  .action(extractAudioCommand);

// Config command - Configuration management
program
  .command('config [action] [key] [value]')
  .description('Manage Arena configuration (view, set, get, reset)')
  .action(configCommand);

program.parse();
