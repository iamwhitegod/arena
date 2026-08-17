export const SUPPORTED_PROVIDERS = ['openai', 'local', 'ollama'] as const;
export const TRANSCRIPTION_MODELS = [
  'whisper-1',
  'base',
  'faster-whisper-base',
  'faster-whisper-small',
  'faster-whisper-medium',
] as const;

export type ProviderName = (typeof SUPPORTED_PROVIDERS)[number];
export type TranscriptionModelName = (typeof TRANSCRIPTION_MODELS)[number];

export interface ProviderSelectors {
  provider?: ProviderName;
  chatProvider?: ProviderName;
  chatModel?: string;
  overviewChatProvider?: ProviderName;
  overviewChatModel?: string;
  embeddingProvider?: ProviderName;
  embeddingModel?: string;
  transcriptionProvider?: ProviderName;
  transcriptionModel?: string;
}

export interface StoredProviderSelectors {
  provider?: ProviderName;
  chat_provider?: ProviderName;
  chat_model?: string;
  overview_chat_provider?: ProviderName;
  overview_chat_model?: string;
  embedding_provider?: ProviderName;
  embedding_model?: string;
  transcription_provider?: ProviderName;
  transcription_model?: string;
}

/**
 * Merge command-line selectors with stored configuration without carrying a
 * model identifier across provider boundaries. A command-level --provider
 * overrides stored per-capability providers; explicit per-capability command
 * options still have the highest precedence.
 */
export function resolveProviderSelectors(
  command: ProviderSelectors,
  stored: StoredProviderSelectors
): ProviderSelectors {
  const storedGlobal = stored.provider || 'openai';
  const provider = command.provider || storedGlobal;
  const commandOverridesStoredProviders = command.provider !== undefined;

  const storedChatProvider = stored.chat_provider || storedGlobal;
  const chatProvider =
    command.chatProvider || (commandOverridesStoredProviders ? undefined : stored.chat_provider);
  const effectiveChatProvider = chatProvider || provider;
  const chatModel =
    command.chatModel ||
    (effectiveChatProvider === storedChatProvider ? stored.chat_model : undefined);

  const storedOverviewProvider = stored.overview_chat_provider || storedChatProvider;
  const overviewChatProvider =
    command.overviewChatProvider ||
    (commandOverridesStoredProviders ? undefined : stored.overview_chat_provider);
  const effectiveOverviewProvider = overviewChatProvider || effectiveChatProvider;
  const overviewChatModel =
    command.overviewChatModel ||
    (effectiveOverviewProvider === storedOverviewProvider ? stored.overview_chat_model : undefined);

  const storedEmbeddingProvider = stored.embedding_provider || storedGlobal;
  const embeddingProvider =
    command.embeddingProvider ||
    (commandOverridesStoredProviders ? undefined : stored.embedding_provider);
  const effectiveEmbeddingProvider = embeddingProvider || provider;
  const embeddingModel =
    command.embeddingModel ||
    (effectiveEmbeddingProvider === storedEmbeddingProvider ? stored.embedding_model : undefined);

  const storedTranscriptionProvider = stored.transcription_provider || storedGlobal;
  const transcriptionProvider =
    command.transcriptionProvider ||
    (commandOverridesStoredProviders ? undefined : stored.transcription_provider);
  const effectiveTranscriptionProvider = transcriptionProvider || provider;
  const transcriptionModel =
    command.transcriptionModel ||
    (effectiveTranscriptionProvider === storedTranscriptionProvider
      ? stored.transcription_model
      : undefined);

  return {
    provider,
    chatProvider,
    chatModel,
    overviewChatProvider,
    overviewChatModel,
    embeddingProvider,
    embeddingModel,
    transcriptionProvider,
    transcriptionModel,
  };
}

export type ProviderCapability = 'chat' | 'overviewChat' | 'embedding' | 'transcription';

export function requiredProviders(
  selectors: ProviderSelectors,
  capabilities: ProviderCapability[]
): string[] {
  const fallback = selectors.provider || 'openai';
  const chat = selectors.chatProvider || fallback;
  const mapping: Record<ProviderCapability, ProviderName> = {
    chat,
    overviewChat: selectors.overviewChatProvider || chat,
    embedding: selectors.embeddingProvider || fallback,
    transcription: selectors.transcriptionProvider || fallback,
  };
  return [...new Set(capabilities.map((capability) => mapping[capability]))];
}
