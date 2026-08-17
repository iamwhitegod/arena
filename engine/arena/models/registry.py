"""Immutable metadata for Arena-supported local model packs.

Every network-installable artifact is pinned to a repository revision and an
expected SHA-256 digest. Adding or changing a model is a security-sensitive
release operation: review the source, license, format, digest, and size bound.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping, Optional


ModelCapability = Literal["chat", "embedding", "speech"]
ModelFormat = Literal["gguf", "ctranslate2"]


@dataclass(frozen=True)
class ModelArtifact:
    filename: str
    url: str
    sha256: str
    max_bytes: int
    expected_bytes: Optional[int] = None


@dataclass(frozen=True)
class ModelSpec:
    identifier: str
    capability: ModelCapability
    format: ModelFormat
    install_name: str
    source: str
    revision: str
    license: str
    artifacts: tuple[ModelArtifact, ...]
    upstream: str = ""
    quantization: Optional[str] = None


@dataclass(frozen=True)
class ModelPack:
    name: str
    chat: str
    embedding: str
    speech: str
    description: str
    minimum_memory_gib: int
    recommended_memory_gib: int
    context_size: int


QWEN_CHAT_LITE = ModelSpec(
    identifier="qwen3.5-2b-q4_k_m",
    capability="chat",
    format="gguf",
    install_name="qwen3.5-2b-q4_k_m.gguf",
    source="bartowski/Qwen_Qwen3.5-2B-GGUF",
    revision="7d26695454df6de5fbcce2e58681e62dae06ce43",
    license="apache-2.0",
    upstream="Qwen/Qwen3.5-2B",
    quantization="Q4_K_M",
    artifacts=(
        ModelArtifact(
            filename="Qwen_Qwen3.5-2B-Q4_K_M.gguf",
            url=(
                "https://huggingface.co/bartowski/Qwen_Qwen3.5-2B-GGUF/resolve/"
                "7d26695454df6de5fbcce2e58681e62dae06ce43/"
                "Qwen_Qwen3.5-2B-Q4_K_M.gguf"
            ),
            sha256="57a1085840f497d764a7fc5d346922dbde961efb54cc792ea81d694fd846a1d8",
            max_bytes=2 * 1024 * 1024 * 1024,
            expected_bytes=1396198496,
        ),
    ),
)

QWEN_CHAT = ModelSpec(
    identifier="qwen3.5-4b-q4_k_m",
    capability="chat",
    format="gguf",
    install_name="qwen3.5-4b-q4_k_m.gguf",
    source="bartowski/Qwen_Qwen3.5-4B-GGUF",
    revision="ed51ebba9cedcf99c821e11aec379ea67455a97c",
    license="apache-2.0",
    upstream="Qwen/Qwen3.5-4B",
    quantization="Q4_K_M",
    artifacts=(
        ModelArtifact(
            filename="Qwen_Qwen3.5-4B-Q4_K_M.gguf",
            url=(
                "https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/"
                "ed51ebba9cedcf99c821e11aec379ea67455a97c/"
                "Qwen_Qwen3.5-4B-Q4_K_M.gguf"
            ),
            sha256="2c08bf55fdde0b2e4bd52fa7dc6d49150e83eac997910cf014b7221c172a4b20",
            max_bytes=4 * 1024 * 1024 * 1024,
            expected_bytes=2856936480,
        ),
    ),
)

QWEN_CHAT_PRO = ModelSpec(
    identifier="qwen3.5-9b-q4_k_m",
    capability="chat",
    format="gguf",
    install_name="qwen3.5-9b-q4_k_m.gguf",
    source="bartowski/Qwen_Qwen3.5-9B-GGUF",
    revision="182be2fd6c7bc44887d88a91cb03ff009cc9f549",
    license="apache-2.0",
    upstream="Qwen/Qwen3.5-9B",
    quantization="Q4_K_M",
    artifacts=(
        ModelArtifact(
            filename="Qwen_Qwen3.5-9B-Q4_K_M.gguf",
            url=(
                "https://huggingface.co/bartowski/Qwen_Qwen3.5-9B-GGUF/resolve/"
                "182be2fd6c7bc44887d88a91cb03ff009cc9f549/"
                "Qwen_Qwen3.5-9B-Q4_K_M.gguf"
            ),
            sha256="d784ce9eda1a5a7b51e8f705a9e6310844bf4f173654d115823c775fdea56d43",
            max_bytes=7 * 1024 * 1024 * 1024,
            expected_bytes=6169341984,
        ),
    ),
)

NOMIC_EMBEDDING = ModelSpec(
    identifier="nomic-embed-text-v1.5-q4_k_m",
    capability="embedding",
    format="gguf",
    install_name="nomic-embed-text-v1.5-q4_k_m.gguf",
    source="nomic-ai/nomic-embed-text-v1.5-GGUF",
    revision="f750a25aba2d24830d874eb4e1af468f37248a37",
    license="apache-2.0",
    upstream="nomic-ai/nomic-embed-text-v1.5",
    quantization="Q4_K_M",
    artifacts=(
        ModelArtifact(
            filename="nomic-embed-text-v1.5.Q4_K_M.gguf",
            url=(
                "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/"
                "f750a25aba2d24830d874eb4e1af468f37248a37/"
                "nomic-embed-text-v1.5.Q4_K_M.gguf"
            ),
            sha256="d4e388894e09cf3816e8b0896d81d265b55e7a9fff9ab03fe8bf4ef5e11295ac",
            max_bytes=128 * 1024 * 1024,
            expected_bytes=84106624,
        ),
    ),
)

FASTER_WHISPER_BASE = ModelSpec(
    identifier="faster-whisper-base",
    capability="speech",
    format="ctranslate2",
    install_name="faster-whisper-base",
    source="Systran/faster-whisper-base",
    revision="a80717a3a48b1b28aa687bca146cb7301feae1b1",
    license="mit",
    upstream="openai/whisper-base",
    quantization=None,
    artifacts=(
        ModelArtifact(
            filename="config.json",
            url=(
                "https://huggingface.co/Systran/faster-whisper-base/resolve/"
                "a80717a3a48b1b28aa687bca146cb7301feae1b1/config.json"
            ),
            sha256="56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a",
            max_bytes=16 * 1024,
            expected_bytes=2309,
        ),
        ModelArtifact(
            filename="model.bin",
            url=(
                "https://huggingface.co/Systran/faster-whisper-base/resolve/"
                "a80717a3a48b1b28aa687bca146cb7301feae1b1/model.bin"
            ),
            sha256="d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9",
            max_bytes=160 * 1024 * 1024,
            expected_bytes=145217532,
        ),
        ModelArtifact(
            filename="tokenizer.json",
            url=(
                "https://huggingface.co/Systran/faster-whisper-base/resolve/"
                "a80717a3a48b1b28aa687bca146cb7301feae1b1/tokenizer.json"
            ),
            sha256="fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
            max_bytes=4 * 1024 * 1024,
            expected_bytes=2203239,
        ),
        ModelArtifact(
            filename="vocabulary.txt",
            url=(
                "https://huggingface.co/Systran/faster-whisper-base/resolve/"
                "a80717a3a48b1b28aa687bca146cb7301feae1b1/vocabulary.txt"
            ),
            sha256="34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
            max_bytes=1024 * 1024,
            expected_bytes=459861,
        ),
    ),
)

FASTER_WHISPER_SMALL = ModelSpec(
    identifier="faster-whisper-small",
    capability="speech",
    format="ctranslate2",
    install_name="faster-whisper-small",
    source="Systran/faster-whisper-small",
    revision="536b0662742c02347bc0e980a01041f333bce120",
    license="mit",
    upstream="openai/whisper-small",
    quantization=None,
    artifacts=(
        ModelArtifact(
            filename="config.json",
            url=(
                "https://huggingface.co/Systran/faster-whisper-small/resolve/"
                "536b0662742c02347bc0e980a01041f333bce120/config.json"
            ),
            sha256="9c75e5dbd260ef1b55d0059433682a49c95d274b4b25ea1daefecc6744005956",
            max_bytes=16 * 1024,
            expected_bytes=2370,
        ),
        ModelArtifact(
            filename="model.bin",
            url=(
                "https://huggingface.co/Systran/faster-whisper-small/resolve/"
                "536b0662742c02347bc0e980a01041f333bce120/model.bin"
            ),
            sha256="3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
            max_bytes=512 * 1024 * 1024,
            expected_bytes=483546902,
        ),
        ModelArtifact(
            filename="tokenizer.json",
            url=(
                "https://huggingface.co/Systran/faster-whisper-small/resolve/"
                "536b0662742c02347bc0e980a01041f333bce120/tokenizer.json"
            ),
            sha256="fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
            max_bytes=4 * 1024 * 1024,
            expected_bytes=2203239,
        ),
        ModelArtifact(
            filename="vocabulary.txt",
            url=(
                "https://huggingface.co/Systran/faster-whisper-small/resolve/"
                "536b0662742c02347bc0e980a01041f333bce120/vocabulary.txt"
            ),
            sha256="34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
            max_bytes=1024 * 1024,
            expected_bytes=459861,
        ),
    ),
)

FASTER_WHISPER_MEDIUM = ModelSpec(
    identifier="faster-whisper-medium",
    capability="speech",
    format="ctranslate2",
    install_name="faster-whisper-medium",
    source="Systran/faster-whisper-medium",
    revision="08e178d48790749d25932bbc082711ddcfdfbc4f",
    license="mit",
    upstream="openai/whisper-medium",
    quantization=None,
    artifacts=(
        ModelArtifact(
            filename="config.json",
            url=(
                "https://huggingface.co/Systran/faster-whisper-medium/resolve/"
                "08e178d48790749d25932bbc082711ddcfdfbc4f/config.json"
            ),
            sha256="c4cad52b091e2d7c120a47e605981a260a0cfa34c8cf64f6d5a16a588d1de3a1",
            max_bytes=16 * 1024,
            expected_bytes=2257,
        ),
        ModelArtifact(
            filename="model.bin",
            url=(
                "https://huggingface.co/Systran/faster-whisper-medium/resolve/"
                "08e178d48790749d25932bbc082711ddcfdfbc4f/model.bin"
            ),
            sha256="9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae",
            max_bytes=2 * 1024 * 1024 * 1024,
            expected_bytes=1527906378,
        ),
        ModelArtifact(
            filename="tokenizer.json",
            url=(
                "https://huggingface.co/Systran/faster-whisper-medium/resolve/"
                "08e178d48790749d25932bbc082711ddcfdfbc4f/tokenizer.json"
            ),
            sha256="fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
            max_bytes=4 * 1024 * 1024,
            expected_bytes=2203239,
        ),
        ModelArtifact(
            filename="vocabulary.txt",
            url=(
                "https://huggingface.co/Systran/faster-whisper-medium/resolve/"
                "08e178d48790749d25932bbc082711ddcfdfbc4f/vocabulary.txt"
            ),
            sha256="34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
            max_bytes=1024 * 1024,
            expected_bytes=459861,
        ),
    ),
)


MODEL_SPECS: Mapping[str, ModelSpec] = MappingProxyType({
    spec.identifier: spec
    for spec in (
        QWEN_CHAT_LITE,
        QWEN_CHAT,
        QWEN_CHAT_PRO,
        NOMIC_EMBEDDING,
        FASTER_WHISPER_BASE,
        FASTER_WHISPER_SMALL,
        FASTER_WHISPER_MEDIUM,
    )
})

MODEL_PACKS: Mapping[str, ModelPack] = MappingProxyType({
    "lite": ModelPack(
        name="lite",
        chat=QWEN_CHAT_LITE.identifier,
        embedding=NOMIC_EMBEDDING.identifier,
        speech=FASTER_WHISPER_BASE.identifier,
        description="Verified compact local pack for CPU and entry-level GPU systems.",
        minimum_memory_gib=8,
        recommended_memory_gib=12,
        context_size=4096,
    ),
    "default": ModelPack(
        name="default",
        chat=QWEN_CHAT.identifier,
        embedding=NOMIC_EMBEDDING.identifier,
        speech=FASTER_WHISPER_SMALL.identifier,
        description="Arena's verified default local inference pack.",
        minimum_memory_gib=12,
        recommended_memory_gib=16,
        context_size=8192,
    ),
    "pro": ModelPack(
        name="pro",
        chat=QWEN_CHAT_PRO.identifier,
        embedding=NOMIC_EMBEDDING.identifier,
        speech=FASTER_WHISPER_MEDIUM.identifier,
        description="Higher-quality verified pack for GPU or high-memory workstations.",
        minimum_memory_gib=24,
        recommended_memory_gib=32,
        context_size=12_288,
    ),
})

DEFAULT_MODEL_BY_CAPABILITY: Mapping[ModelCapability, str] = MappingProxyType({
    "chat": QWEN_CHAT.identifier,
    "embedding": NOMIC_EMBEDDING.identifier,
    "speech": FASTER_WHISPER_SMALL.identifier,
})


def get_model(identifier: str) -> ModelSpec:
    try:
        return MODEL_SPECS[identifier]
    except KeyError as exc:
        raise KeyError(f"Unknown verified model: {identifier}") from exc


def find_model(identifier_or_install_name: str) -> Optional[ModelSpec]:
    direct = MODEL_SPECS.get(identifier_or_install_name)
    if direct is not None:
        return direct
    for spec in MODEL_SPECS.values():
        if spec.install_name == identifier_or_install_name:
            return spec
    return None


def chat_model_context_size(identifier_or_install_name: str) -> Optional[int]:
    """Return Arena's verified context limit for a registered chat model."""
    spec = find_model(identifier_or_install_name)
    if spec is None or spec.capability != "chat":
        return None
    sizes = [
        pack.context_size
        for pack in MODEL_PACKS.values()
        if pack.chat == spec.identifier
    ]
    return min(sizes) if sizes else None
