"""
Arena Editorial Module

4-Layer Editorial Architecture for AI-powered video clip generation.

Layers:
    1. MomentDetector - Find interesting moments
    2. ThoughtBoundaryAnalyzer - Expand to complete thoughts
    3. StandaloneContextRefiner - Validate standalone context (quality gate)
    4. PackagingLayer - Generate titles, descriptions, metadata

Usage:
    from arena.editorial import FourLayerAdapter

    analyzer = FourLayerAdapter(api_key="your-key")
    clips = analyzer.analyze_transcript(transcript_data, target_clips=10)
"""

from .adapter import FourLayerAdapter
from .layer1_moment_detector import MomentDetector
from .layer2_boundary_analyzer import ThoughtBoundaryAnalyzer
from .layer3_context_refiner import StandaloneContextRefiner
from .layer4_packaging import PackagingLayer

__all__ = [
    'FourLayerAdapter',
    'MomentDetector',
    'ThoughtBoundaryAnalyzer',
    'StandaloneContextRefiner',
    'PackagingLayer'
]
