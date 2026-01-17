#!/usr/bin/env python3
"""
Arena - End-to-End Video Clip Generation Pipeline

This script runs the complete Arena pipeline:
1. Transcribe video with OpenAI Whisper
2. Analyze audio energy for speaker enthusiasm
3. Combine AI content analysis with energy detection (hybrid analysis)
4. Generate video clips from top-ranked segments
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional
import argparse

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("⚠️  Install 'tqdm' for progress bars: pip install tqdm\n")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.audio.enhance import AudioEnhancer
from arena.ai.analyzer import TranscriptAnalyzer
from arena.ai.hybrid import HybridAnalyzer
from arena.editorial import FourLayerAdapter
from arena.clipping.generator import ClipGenerator
from arena.clipping.professional import ProfessionalClipAligner
from arena.ai.sentence_detector import SentenceBoundaryDetector


def run_arena_pipeline(
    video_path: str,
    output_dir: str = "output",
    num_clips: int = 5,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None,
    use_cached_transcript: bool = True,
    fast_mode: bool = False,
    padding: float = 0.0,
    max_adjustment: float = 10.0,
    enhance_audio: bool = True,
    use_scene_detection: bool = False,
    use_4layer: bool = False,
    export_editorial_layers: bool = False,
    editorial_model: str = "gpt-4o"
):
    """
    Run the complete Arena pipeline

    Args:
        video_path: Path to input video file
        output_dir: Directory for output files (relative to project root or absolute path)
        num_clips: Number of clips to generate
        min_duration: Optional minimum clip duration in seconds (None = no constraint)
        max_duration: Optional maximum clip duration in seconds (None = no constraint)
        use_cached_transcript: Use cached transcript if available
        fast_mode: Use fast clip extraction (stream copy)
        padding: Seconds to add before/after each clip
        max_adjustment: Max seconds to adjust clip boundaries for sentence alignment
        enhance_audio: Apply AI-powered audio enhancement (default: True)
        use_scene_detection: Enable scene detection for cut point optimization (default: False)
    """

    print(f"\n{'='*70}")
    print("🎬 ARENA - AI-Powered Video Clip Generation")
    print(f"{'='*70}\n")

    # Validate inputs
    video_file = Path(video_path)
    if not video_file.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        return 1

    # Resolve output directory
    output_path = Path(output_dir)

    # If relative path, resolve from project root (not engine/)
    if not output_path.is_absolute():
        # Get project root (parent of engine/)
        engine_dir = Path(__file__).parent
        project_root = engine_dir.parent
        output_path = project_root / output_dir

    output_path.mkdir(parents=True, exist_ok=True)

    cache_dir = output_path / ".cache"
    cache_dir.mkdir(exist_ok=True)

    clips_dir = output_path / "clips"
    clips_dir.mkdir(exist_ok=True)

    print(f"📹 Input:  {video_file.name}")
    print(f"📁 Output: {output_path}")

    # Show duration constraints if specified
    if min_duration is not None and max_duration is not None:
        print(f"🎯 Target: {num_clips} clips ({min_duration}-{max_duration}s each)")
    elif min_duration is not None:
        print(f"🎯 Target: {num_clips} clips (at least {min_duration}s each)")
    elif max_duration is not None:
        print(f"🎯 Target: {num_clips} clips (at most {max_duration}s each)")
    else:
        print(f"🎯 Target: {num_clips} clips (content-driven length)")
    print()

    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY='your-key'")
        print("   Get one at: https://platform.openai.com/api-keys\n")
        return 1

    # Pipeline progress tracking
    total_steps = 4  # Added professional alignment step
    current_step = 0

    # =========================================================================
    # STEP 1: Transcription
    # =========================================================================
    current_step += 1
    print(f"{'='*70}")
    print(f"[{current_step}/{total_steps}] 📝 Transcription")
    print(f"{'='*70}\n")

    transcript_cache = cache_dir / f"{video_file.stem}_transcript.json"
    enhanced_audio_path = cache_dir / f"{video_file.stem}_enhanced.wav"

    # Check if we should enhance audio
    audio_to_transcribe = video_file

    if enhance_audio:
        # Check if enhanced audio exists in cache
        if enhanced_audio_path.exists():
            print(f"✓ Using cached enhanced audio: {enhanced_audio_path.name}\n")
            audio_to_transcribe = enhanced_audio_path
        else:
            print("🎧 Enhancing audio quality...")
            print("   Applying noise reduction and volume normalization...")

            try:
                # Initialize audio enhancer (local mode)
                enhancer = AudioEnhancer(provider="local")

                # Extract and enhance audio
                temp_audio = cache_dir / f"{video_file.stem}_temp.wav"

                # Extract audio from video first
                import subprocess
                subprocess.run([
                    "ffmpeg", "-i", str(video_file),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "44100", "-ac", "2",
                    "-y", str(temp_audio)
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

                # Enhance the extracted audio
                enhancer.enhance(temp_audio, enhanced_audio_path)

                # Clean up temp file
                temp_audio.unlink()

                audio_to_transcribe = enhanced_audio_path

                print(f"✓ Audio enhanced and cached")
                print(f"  Enhanced audio: {enhanced_audio_path.name}\n")

            except Exception as e:
                print(f"⚠️  Audio enhancement failed: {e}")
                print(f"   Continuing with original audio...\n")
                audio_to_transcribe = video_file

    if use_cached_transcript and transcript_cache.exists():
        print(f"✓ Using cached transcript: {transcript_cache.name}")
        with open(transcript_cache) as f:
            transcript_data = json.load(f)
        print(f"  Duration: {transcript_data.get('duration', 0):.1f}s")
        print(f"  Words:    {len(transcript_data.get('words', []))}\n")
    else:
        if HAS_TQDM:
            with tqdm(total=100, desc="🎤 Transcribing", bar_format='{l_bar}{bar}| {elapsed}') as pbar:
                try:
                    transcriber = Transcriber(api_key=api_key, mode='api')
                    pbar.update(20)
                    transcript_data = transcriber.transcribe(
                        audio_to_transcribe,
                        cache_dir=cache_dir
                    )
                    pbar.update(80)

                    # Save transcript
                    with open(transcript_cache, 'w') as f:
                        json.dump(transcript_data, f, indent=2)

                    print(f"\n✓ Transcription complete")
                    print(f"  Duration: {transcript_data.get('duration', 0):.1f}s")
                    print(f"  Words:    {len(transcript_data.get('words', []))}")
                    print(f"  Saved to: {transcript_cache.name}\n")

                except Exception as e:
                    print(f"\n❌ Transcription failed: {e}")
                    return 1
        else:
            print("🎤 Transcribing video with OpenAI Whisper...")
            print("   This may take a few minutes...\n")

            try:
                transcriber = Transcriber(api_key=api_key, mode='api')
                transcript_data = transcriber.transcribe(
                    audio_to_transcribe,  # Use enhanced audio if available
                    cache_dir=cache_dir
                )

                # Save transcript
                with open(transcript_cache, 'w') as f:
                    json.dump(transcript_data, f, indent=2)

                print(f"✓ Transcription complete")
                print(f"  Duration: {transcript_data.get('duration', 0):.1f}s")
                print(f"  Words:    {len(transcript_data.get('words', []))}")
                print(f"  Saved to: {transcript_cache.name}\n")

            except Exception as e:
                print(f"❌ Transcription failed: {e}")
                return 1

    # =========================================================================
    # STEP 2: Hybrid Analysis (AI + Energy)
    # =========================================================================
    current_step += 1
    print(f"{'='*70}")
    print(f"[{current_step}/{total_steps}] 🧠 Hybrid Analysis (AI + Energy)")
    print(f"{'='*70}\n")

    try:
        # Initialize analyzers
        if HAS_TQDM:
            with tqdm(total=100, desc="🔧 Initializing", bar_format='{l_bar}{bar}') as pbar:
                # Choose analyzer based on use_4layer flag
                if use_4layer:
                    ai_analyzer = FourLayerAdapter(
                        api_key=api_key,
                        model=editorial_model,
                        export_layers=export_editorial_layers
                    )
                else:
                    ai_analyzer = TranscriptAnalyzer(api_key=api_key)
                pbar.update(33)
                energy_analyzer = AudioEnergyAnalyzer(video_path=video_file)
                pbar.update(33)
                hybrid_analyzer = HybridAnalyzer(
                    ai_analyzer=ai_analyzer,
                    energy_analyzer=energy_analyzer,
                    energy_weight=0.3  # 30% boost from energy
                )
                pbar.update(34)
            print()
        else:
            print("🔧 Initializing analyzers...")
            # Choose analyzer based on use_4layer flag
            if use_4layer:
                print(f"   Using 4-layer editorial system (model: {editorial_model})")
                ai_analyzer = FourLayerAdapter(
                    api_key=api_key,
                    model=editorial_model,
                    export_layers=export_editorial_layers
                )
            else:
                ai_analyzer = TranscriptAnalyzer(api_key=api_key)
            energy_analyzer = AudioEnergyAnalyzer(video_path=video_file)
            hybrid_analyzer = HybridAnalyzer(
                ai_analyzer=ai_analyzer,
                energy_analyzer=energy_analyzer,
                energy_weight=0.3  # 30% boost from energy
            )
            analyzer_type = "4-layer editorial" if use_4layer else "single-layer"
            print(f"   ✓ AI analyzer ready ({analyzer_type})")
            print("   ✓ Energy analyzer ready")
            print("   ✓ Hybrid analyzer ready\n")

        # Run hybrid analysis
        if HAS_TQDM:
            print("Running hybrid analysis...")
        analysis_results = hybrid_analyzer.analyze_video(
            video_path=video_file,
            transcript_data=transcript_data,
            target_clips=num_clips * 2,  # Analyze more, select best
            min_duration=min_duration,
            max_duration=max_duration
        )

        # Save analysis results
        analysis_file = output_path / "analysis_results.json"
        hybrid_analyzer.export_results(analysis_results, analysis_file)

        # Print summary
        hybrid_analyzer.print_summary(analysis_results)

        # Get top clips (before alignment)
        top_clips = analysis_results['clips'][:num_clips * 2]  # Get more for alignment selection

        print(f"\n✓ Analysis complete")
        print(f"  Results saved: {analysis_file.name}")
        print(f"  Selected {len(top_clips)} candidates for professional alignment\n")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # STEP 3: Professional Clip Alignment
    # =========================================================================
    current_step += 1
    print(f"{'='*70}")
    print(f"[{current_step}/{total_steps}] 🎬 Professional Editing (Sentence Alignment)")
    print(f"{'='*70}\n")

    try:
        # Initialize professional aligner
        aligner = ProfessionalClipAligner(
            max_adjustment=max_adjustment,
            use_scene_detection=use_scene_detection
        )

        print(f"📝 Aligning clips to sentence boundaries...")
        print(f"   Max adjustment: {max_adjustment}s")
        if use_scene_detection:
            print(f"   Scene detection: enabled")
        print(f"   Regenerating titles for adjusted clips...\n")

        # Align clips to sentence boundaries and regenerate titles
        aligned_clips = aligner.align_clips(
            clips=top_clips,
            transcript_segments=transcript_data.get('segments', []),
            min_duration=min_duration,
            max_duration=max_duration,
            analyzer=ai_analyzer,
            video_path=video_file if use_scene_detection else None
        )

        # Select top N after alignment
        top_clips = aligned_clips[:num_clips]

        # Print alignment report
        print(aligner.generate_alignment_report(top_clips, top_n=min(5, len(top_clips))))
        print()

        # Save alignment stats
        alignment_stats = aligner.get_alignment_stats(top_clips)
        analysis_results['alignment_stats'] = alignment_stats

        # Update analysis file with alignment info
        hybrid_analyzer.export_results(analysis_results, analysis_file)

    except Exception as e:
        print(f"⚠️  Alignment failed, using original timestamps: {e}")
        print(f"   Continuing with clip generation...\n")
        # Continue with original clips if alignment fails

    # =========================================================================
    # STEP 4: Clip Generation
    # =========================================================================
    current_step += 1
    print(f"{'='*70}")
    print(f"[{current_step}/{total_steps}] ✂️  Video Clip Generation")
    print(f"{'='*70}\n")

    try:
        # Initialize clip generator with enhanced audio if available
        enhanced_audio_for_clips = None
        if enhance_audio and audio_to_transcribe != video_file:
            # Enhanced audio was used and is available
            enhanced_audio_for_clips = audio_to_transcribe
            print(f"🎧 Using enhanced audio for clips: {enhanced_audio_for_clips.name}\n")

        generator = ClipGenerator(video_file, enhanced_audio_path=enhanced_audio_for_clips)

        # Get video info
        video_info = generator.get_video_info()
        print(f"📊 Video Info:")
        print(f"   Duration:   {video_info['duration']:.1f}s")
        print(f"   Resolution: {video_info['width']}x{video_info['height']}")
        print(f"   FPS:        {video_info['fps']:.2f}")
        print(f"   Codec:      {video_info['video_codec']}\n")

        mode = "fast (stream copy)" if fast_mode else "quality (re-encode)"
        print(f"🎬 Generating {len(top_clips)} clips ({mode})...")
        print(f"   Padding: {padding}s before/after each clip\n")

        # Progress callback with tqdm
        if HAS_TQDM:
            pbar = tqdm(total=len(top_clips), desc="✂️  Generating clips", unit="clip")

            def on_progress(current, total, clip_info):
                if clip_info.get('success'):
                    pbar.set_postfix_str(f"{clip_info['clip_id']} - {clip_info['duration']:.1f}s")
                pbar.update(1)
        else:
            def on_progress(current, total, clip_info):
                if clip_info.get('success'):
                    print(f"   [{current}/{total}] ✓ {clip_info['clip_id']}")
                    print(f"           {clip_info['duration']:.1f}s, "
                          f"{clip_info['size_mb']}MB - "
                          f"{clip_info.get('title', 'Untitled')[:50]}")
                else:
                    print(f"   [{current}/{total}] ✗ {clip_info['clip_id']} "
                          f"- {clip_info.get('error', 'Unknown error')}")

        # Generate all clips
        clip_results = generator.generate_multiple_clips(
            segments=top_clips,
            output_dir=clips_dir,
            padding=padding,
            fast_mode=fast_mode,
            progress_callback=on_progress
        )

        if HAS_TQDM:
            pbar.close()
            print()

        # Calculate successful clips count
        successful = sum(1 for r in clip_results if r.get('success'))

        # Generate thumbnails and metadata
        if HAS_TQDM:
            print(f"\n📸 Generating thumbnails and metadata...")
            thumb_pbar = tqdm(total=successful, desc="📸 Thumbnails", unit="thumb")
        else:
            print(f"\n📸 Generating thumbnails and metadata...")

        for i, (clip, result) in enumerate(zip(top_clips, clip_results), 1):
            if result.get('success'):
                try:
                    # Generate thumbnail at clip midpoint
                    midpoint = (clip['start_time'] + clip['end_time']) / 2
                    clip_id = result['clip_id']
                    thumb_path = clips_dir / f"{clip_id}_thumb.jpg"

                    generator.generate_thumbnail(
                        timestamp=midpoint,
                        output_path=thumb_path,
                        width=640
                    )

                    # Save metadata
                    metadata = {
                        **result,
                        'clip_number': i,
                        'title': clip.get('title', 'Untitled'),
                        'description': clip.get('reason', ''),
                        'content_type': clip.get('content_type', 'general'),
                        'scores': {
                            'ai_score': clip.get('interest_score', 0),
                            'hybrid_score': clip.get('hybrid_score', 0),
                            'energy_score': clip.get('max_energy', 0)
                        },
                        'thumbnail': str(thumb_path.name)
                    }

                    metadata_path = clips_dir / f"{clip_id}_metadata.json"
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)

                    if HAS_TQDM:
                        thumb_pbar.update(1)

                except Exception as e:
                    print(f"   ⚠️  Failed to generate thumbnail for {clip_id}: {e}")
                    if HAS_TQDM:
                        thumb_pbar.update(1)

        if HAS_TQDM:
            thumb_pbar.close()
            print()

        # Summary
        failed = len(clip_results) - successful
        total_size = sum(r.get('size_mb', 0) for r in clip_results if r.get('success'))

        print(f"\n✓ Clip generation complete")
        print(f"  Successful: {successful}/{len(clip_results)}")
        print(f"  Failed:     {failed}")
        print(f"  Total size: {total_size:.1f} MB\n")

    except Exception as e:
        print(f"❌ Clip generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print(f"{'='*70}")
    print("✅ ARENA PIPELINE COMPLETE")
    print(f"{'='*70}\n")

    print("📂 Output Structure:")
    print(f"   {output_path}/")
    print(f"   ├── clips/")
    print(f"   │   ├── *_*.mp4            ({successful} video clips)")
    print(f"   │   ├── *_*_thumb.jpg      (thumbnails)")
    print(f"   │   └── *_*_metadata.json  (metadata)")
    print(f"   ├── analysis_results.json  (full analysis)")
    print(f"   └── .cache/")
    print(f"       └── *_transcript.json  (cached transcript)\n")

    print("🎯 Top 3 Clips Generated:")
    for i, clip in enumerate(top_clips[:3], 1):
        clip_id = clip.get('id', f'clip_{i}')
        print(f"   {i}. {clip_id}.mp4")
        print(f"      {clip.get('title', 'Untitled')}")
        print(f"      Time: {format_time(clip['start_time'])} → {format_time(clip['end_time'])}")
        print(f"      Scores: AI={clip.get('interest_score', 0):.2f}, "
              f"Hybrid={clip.get('hybrid_score', 0):.2f}\n")

    print("🚀 Next Steps:")
    print("   1. Review clips in the clips/ directory")
    print("   2. Check analysis_results.json for all segments")
    print("   3. Edit clips or run again with different parameters")
    print("   4. Share your clips on social media!\n")

    print(f"{'='*70}\n")

    return 0


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def main():
    parser = argparse.ArgumentParser(
        description="Arena - AI-Powered Video Clip Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python arena_process.py video.mp4

  # Generate 10 clips, 20-60 seconds each
  python arena_process.py video.mp4 -n 10 --min 20 --max 60

  # Fast mode (stream copy, no re-encoding)
  python arena_process.py video.mp4 --fast

  # Custom output directory
  python arena_process.py video.mp4 -o my_clips

Environment:
  OPENAI_API_KEY    Required. Get from https://platform.openai.com
        """
    )

    parser.add_argument(
        'video',
        help='Path to input video file'
    )
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '-n', '--num-clips',
        type=int,
        default=5,
        help='Number of clips to generate (default: 5)'
    )
    parser.add_argument(
        '--min',
        type=int,
        default=30,
        help='Minimum clip duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=90,
        help='Maximum clip duration in seconds (default: 90)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Ignore cached transcript and re-transcribe'
    )
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Use fast mode (stream copy, no re-encoding)'
    )
    parser.add_argument(
        '--padding',
        type=float,
        default=0.5,
        help='Seconds of padding before/after clips (default: 0.5)'
    )
    parser.add_argument(
        '--use-4layer',
        action='store_true',
        help='Use 4-layer editorial system (higher quality, slower, more expensive)'
    )
    parser.add_argument(
        '--export-editorial-layers',
        action='store_true',
        help='Export intermediate results from each editorial layer for debugging (requires --use-4layer)'
    )
    parser.add_argument(
        '--editorial-model',
        choices=['gpt-4o', 'gpt-4o-mini'],
        default='gpt-4o',
        help='Model to use for Layers 1-2 (default: gpt-4o, mini saves ~60%% cost but may reduce quality)'
    )

    args = parser.parse_args()

    # Run pipeline
    sys.exit(run_arena_pipeline(
        video_path=args.video,
        output_dir=args.output,
        num_clips=args.num_clips,
        min_duration=args.min,
        max_duration=args.max,
        use_cached_transcript=not args.no_cache,
        fast_mode=args.fast,
        padding=args.padding,
        use_4layer=args.use_4layer,
        export_editorial_layers=args.export_editorial_layers,
        editorial_model=args.editorial_model
    ))


if __name__ == "__main__":
    main()
