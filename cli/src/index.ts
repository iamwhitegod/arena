#!/usr/bin/env node

import { Command, Option } from 'commander';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { processCommand } from './commands/process.js';
import { initCommand } from './commands/init.js';
import { setupCommand } from './commands/setup.js';
import { analyzeCommand } from './commands/analyze.js';
import { transcribeCommand } from './commands/transcribe.js';
import { generateCommand } from './commands/generate.js';
import { configCommand } from './commands/config.js';
import { extractAudioCommand } from './commands/extract-audio.js';
import { formatCommand } from './commands/format.js';
import { detectScenesCommand } from './commands/detect-scenes.js';
import { diagnoseCommand } from './commands/diagnose.js';
import { unsupportedNodeVersionMessage } from './core/node-version.js';
import { SUPPORTED_PROVIDERS } from './core/providers.js';

const nodeVersionError = unsupportedNodeVersionMessage();
if (nodeVersionError) {
  console.error(nodeVersionError);
  process.exit(1);
}

// Get package.json version (ES module compatible)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageJson = JSON.parse(readFileSync(join(__dirname, '../package.json'), 'utf-8'));

const program = new Command();

const providerOption = (flags: string, description: string) =>
  new Option(flags, description).choices([...SUPPORTED_PROVIDERS]);
const modelOption = (flags: string, description: string) => new Option(flags, description);
const transcriptionModelOption = (flags: string, description: string) =>
  new Option(flags, description);

program
  .name('arena')
  .description('AI-powered video clip generation tool for the terminal')
  .version(packageJson.version);

// Init command - Setup wizard
program.command('init').description('Interactive setup wizard for Arena').action(initCommand);

// Setup command - Create and verify Arena's managed runtime
program
  .command('setup')
  .description('Install or repair Arena processing dependencies')
  .option('--check', 'check installation health without changing anything')
  .option('--force', 'rebuild the Arena-managed Python runtime')
  .option('--local', 'include hash-locked llama.cpp and faster-whisper runtimes')
  .addOption(
    new Option('--model-pack <pack>', 'install a verified local model pack').choices([
      'lite',
      'default',
      'pro',
    ])
  )
  .option('-y, --yes', 'approve supported system dependency installation')
  .action(setupCommand);

// Process command - All-in-one processing
program
  .command('process')
  .description('Process a video and generate clips automatically')
  .argument('<video>', 'path to video/audio file or URL')
  .option('-o, --output <dir>', 'output directory', 'output')
  .option('-n, --num-clips <number>', 'target number of clips to generate', '8')
  .option('--min <seconds>', 'minimum clip duration', '30')
  .option('--max <seconds>', 'maximum clip duration', '90')
  .addOption(modelOption('--editorial-model <model>', 'backward-compatible alias for --chat-model'))
  .option('--export-layers', 'export intermediate layer results for debugging')
  .option('--fast', 'fast mode - stream copy (10x faster)')
  .option('--no-cache', 'force re-transcription, ignore cached transcript')
  .option('--padding <seconds>', 'seconds of padding before/after clips', '0.1')
  .option('--scene-detection', 'enable scene detection for better clip boundaries')
  .option(
    '-p, --platform <platform>',
    'auto-format for platform (tiktok, instagram-reels, youtube-shorts, youtube, instagram-feed, twitter, linkedin)'
  )
  .option(
    '--crop <strategy>',
    'crop strategy for platform formatting: center, smart, top, bottom',
    'center'
  )
  .option(
    '--pad <strategy>',
    'pad strategy for platform formatting: blur, black, white, color',
    'blur'
  )
  .option('--pad-color <color>', 'padding color (hex) for platform formatting', '#000000')
  .option(
    '--cookies-from-browser <browser>',
    'use browser cookies for URL downloads (chrome, firefox, safari, brave, edge)'
  )
  .option('--captions', 'burn subtitle captions into clips')
  .option('--caption-font-size <size>', 'caption font size')
  .option('--caption-color <color>', 'caption text color: white, yellow, red, black')
  .option('--caption-position <position>', 'caption position: bottom, top, middle')
  .addOption(providerOption('--provider <provider>', 'provider shorthand for all capabilities'))
  .addOption(providerOption('--chat-provider <provider>', 'chat inference provider'))
  .addOption(modelOption('--chat-model <model>', 'chat inference model'))
  .addOption(providerOption('--overview-chat-provider <provider>', 'overview chat provider'))
  .addOption(modelOption('--overview-chat-model <model>', 'overview chat model'))
  .addOption(providerOption('--embedding-provider <provider>', 'embedding provider'))
  .addOption(modelOption('--embedding-model <model>', 'embedding model'))
  .addOption(providerOption('--transcription-provider <provider>', 'transcription provider'))
  .addOption(transcriptionModelOption('--transcription-model <model>', 'transcription model'))
  .option('--debug', 'show debug information')
  .action(processCommand);

// Transcribe command - Transcription only
program
  .command('transcribe')
  .description('Transcribe video or audio (supports URLs)')
  .argument('<video>', 'path to video/audio file or URL')
  .option('-o, --output <file>', 'output transcript file path')
  .option('--no-cache', 'force re-transcription, ignore cached transcript')
  .option(
    '--cookies-from-browser <browser>',
    'use browser cookies for URL downloads (chrome, firefox, safari, brave, edge)'
  )
  .addOption(providerOption('--provider <provider>', 'transcription provider shorthand'))
  .addOption(providerOption('--transcription-provider <provider>', 'transcription provider'))
  .addOption(transcriptionModelOption('--transcription-model <model>', 'transcription model'))
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
  .addOption(modelOption('--editorial-model <model>', 'backward-compatible alias for --chat-model'))
  .option('--transcript <file>', 'use existing transcript file')
  .option('--scene-detection', 'enable scene detection for better clip boundaries')
  .addOption(providerOption('--provider <provider>', 'provider shorthand for all capabilities'))
  .addOption(providerOption('--chat-provider <provider>', 'chat inference provider'))
  .addOption(modelOption('--chat-model <model>', 'chat inference model'))
  .addOption(providerOption('--overview-chat-provider <provider>', 'overview chat provider'))
  .addOption(modelOption('--overview-chat-model <model>', 'overview chat model'))
  .addOption(providerOption('--embedding-provider <provider>', 'embedding provider'))
  .addOption(modelOption('--embedding-model <model>', 'embedding model'))
  .addOption(providerOption('--transcription-provider <provider>', 'transcription provider'))
  .addOption(transcriptionModelOption('--transcription-model <model>', 'transcription model'))
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
  .description('Extract audio from video or URL')
  .argument('<video>', 'path to video file or URL')
  .option('-o, --output <file>', 'output audio file path')
  .option('--format <format>', 'audio format: mp3, wav, aac, flac', 'mp3')
  .option('--bitrate <rate>', 'audio bitrate (e.g., "192k")')
  .option('--sample-rate <rate>', 'sample rate in Hz (e.g., "44100")')
  .option('--mono', 'convert to mono')
  .option(
    '--cookies-from-browser <browser>',
    'use browser cookies for URL downloads (chrome, firefox, safari, brave, edge)'
  )
  .option('--debug', 'show debug information')
  .action(extractAudioCommand);

// Config command - Configuration management
program
  .command('config [action] [key] [value]')
  .description('Manage Arena configuration (view, set, get, reset)')
  .action(configCommand);

// Format command - Platform formatting
program
  .command('format')
  .description('Format clips for specific social media platforms')
  .argument('<input>', 'path to video file or directory of clips')
  .requiredOption(
    '-p, --platform <platform>',
    'target platform (tiktok, instagram-reels, youtube-shorts, youtube, instagram-feed, twitter, linkedin)'
  )
  .option('-o, --output <dir>', 'output directory for formatted clips')
  .option('--crop <strategy>', 'crop strategy: center, smart, top, bottom', 'center')
  .option('--pad <strategy>', 'pad strategy: blur, black, white, color', 'blur')
  .option('--pad-color <color>', 'padding color (hex), e.g., #000000', '#000000')
  .option('--no-quality', 'disable high quality encoding (faster, smaller files)')
  .option('--captions <srt>', 'path to SRT subtitle file to burn into clips')
  .option('--caption-font-size <size>', 'caption font size')
  .option('--caption-color <color>', 'caption text color: white, yellow, red, black')
  .option('--caption-position <position>', 'caption position: bottom, top, middle')
  .action(formatCommand);

// Detect-scenes command - Scene detection
program
  .command('detect-scenes')
  .description('Detect scene changes in video for better clip boundaries')
  .argument('<video>', 'path to video file')
  .option('-o, --output <file>', 'output scenes JSON file path')
  .option('--threshold <value>', 'scene detection threshold (0.0-1.0, default: 0.4)')
  .option('--min-duration <seconds>', 'minimum scene duration in seconds (default: 2.0)')
  .option('--report', 'generate detailed scene report')
  .option('--debug', 'show debug information')
  .action(detectScenesCommand);

// Diagnose command - System diagnostics
program
  .command('diagnose')
  .description('Run system diagnostics and troubleshooting checks')
  .action(diagnoseCommand);

program.parse();
