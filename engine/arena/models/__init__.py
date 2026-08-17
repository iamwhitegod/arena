"""Verified local-model metadata, installation, and hardware recommendations."""

from .hardware import (
    MINIMUM_LOCAL_SPEC,
    RECOMMENDED_LOCAL_SPEC,
    HardwareInfo,
    RuntimeRecommendation,
    SpecAssessment,
    assess_system,
    detect_hardware,
    recommend_runtime,
)
from .locator import ModelLocator
from .manager import ModelManager
from .registry import MODEL_PACKS, MODEL_SPECS, ModelPack, ModelSpec

__all__ = [
    "HardwareInfo",
    "MINIMUM_LOCAL_SPEC",
    "RECOMMENDED_LOCAL_SPEC",
    "RuntimeRecommendation",
    "SpecAssessment",
    "assess_system",
    "detect_hardware",
    "recommend_runtime",
    "ModelLocator",
    "ModelManager",
    "MODEL_PACKS",
    "MODEL_SPECS",
    "ModelPack",
    "ModelSpec",
]
