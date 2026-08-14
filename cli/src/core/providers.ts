export const SUPPORTED_PROVIDERS = ['openai'] as const;
export const CHAT_MODELS = ['gpt-4o', 'gpt-4o-mini'] as const;
export const EMBEDDING_MODELS = ['text-embedding-3-small', 'text-embedding-3-large'] as const;
export const TRANSCRIPTION_MODELS = ['whisper-1'] as const;

export type ProviderName = (typeof SUPPORTED_PROVIDERS)[number];
export type ChatModelName = (typeof CHAT_MODELS)[number];
export type EmbeddingModelName = (typeof EMBEDDING_MODELS)[number];
export type TranscriptionModelName = (typeof TRANSCRIPTION_MODELS)[number];

export interface ProviderSelectors {
  provider?: ProviderName;
  chatProvider?: ProviderName;
  chatModel?: ChatModelName;
  overviewChatProvider?: ProviderName;
  overviewChatModel?: ChatModelName;
  embeddingProvider?: ProviderName;
  embeddingModel?: EmbeddingModelName;
  transcriptionProvider?: ProviderName;
  transcriptionModel?: TranscriptionModelName;
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
