export const SUPPORTED_PROVIDERS = ['openai', 'local', 'ollama'] as const;
export const DEFAULT_PROVIDER_MODELS = {
  openai: {
    chat: 'gpt-4o',
    embedding: 'text-embedding-3-small',
    transcription: 'whisper-1',
  },
  local: {
    chat: 'qwen3.5-4b-q4_k_m',
    embedding: 'nomic-embed-text-v1.5-q4_k_m',
    transcription: 'faster-whisper-small',
  },
  ollama: {
    chat: 'llama3.2',
    embedding: 'nomic-embed-text',
  },
} as const;
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

export interface RequiredProviderBinding {
  capability: ProviderCapability;
  provider: ProviderName;
  model?: string;
  modelExplicit?: boolean;
}

export function isValidModelIdentifier(value: string): boolean {
  if (!value || value.length > 256) return false;
  return !Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127;
  });
}

const PROVIDER_CAPABILITIES: Record<ProviderName, ReadonlySet<ProviderCapability>> = {
  openai: new Set(['chat', 'overviewChat', 'embedding', 'transcription']),
  local: new Set(['chat', 'overviewChat', 'embedding', 'transcription']),
  ollama: new Set(['chat', 'overviewChat', 'embedding']),
};

export function providerSupportsCapability(
  provider: ProviderName,
  capability: ProviderCapability
): boolean {
  return PROVIDER_CAPABILITIES[provider]?.has(capability) ?? false;
}

function defaultModel(provider: ProviderName, capability: ProviderCapability): string | undefined {
  const modelCapability = capability === 'overviewChat' ? 'chat' : capability;
  const defaults = DEFAULT_PROVIDER_MODELS[provider] as Partial<Record<string, string>> | undefined;
  if (!defaults) return undefined;
  return defaults[modelCapability];
}

export function requiredProviderBindings(
  selectors: ProviderSelectors,
  capabilities: ProviderCapability[]
): RequiredProviderBinding[] {
  const fallback = selectors.provider || 'openai';
  const chatProvider = selectors.chatProvider || fallback;
  const overviewProvider = selectors.overviewChatProvider || chatProvider;
  const mapping: Record<ProviderCapability, RequiredProviderBinding> = {
    chat: {
      capability: 'chat',
      provider: chatProvider,
      model: selectors.chatModel || defaultModel(chatProvider, 'chat'),
      ...(selectors.chatModel ? { modelExplicit: true } : {}),
    },
    overviewChat: {
      capability: 'overviewChat',
      provider: overviewProvider,
      model:
        selectors.overviewChatModel ||
        (overviewProvider === chatProvider ? selectors.chatModel : undefined) ||
        defaultModel(overviewProvider, 'overviewChat'),
      ...(selectors.overviewChatModel || (overviewProvider === chatProvider && selectors.chatModel)
        ? { modelExplicit: true }
        : {}),
    },
    embedding: {
      capability: 'embedding',
      provider: selectors.embeddingProvider || fallback,
      model:
        selectors.embeddingModel ||
        defaultModel(selectors.embeddingProvider || fallback, 'embedding'),
      ...(selectors.embeddingModel ? { modelExplicit: true } : {}),
    },
    transcription: {
      capability: 'transcription',
      provider: selectors.transcriptionProvider || fallback,
      model:
        selectors.transcriptionModel ||
        defaultModel(selectors.transcriptionProvider || fallback, 'transcription'),
      ...(selectors.transcriptionModel ? { modelExplicit: true } : {}),
    },
  };
  return capabilities.map((capability) => mapping[capability]);
}

export function requiredProviders(
  selectors: ProviderSelectors,
  capabilities: ProviderCapability[]
): string[] {
  return [
    ...new Set(
      requiredProviderBindings(selectors, capabilities).map((binding) => binding.provider)
    ),
  ];
}
