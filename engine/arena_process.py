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
import hashlib
import json
import time
from pathlib import Path
from typing import Optional
import argparse

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

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
    export_editorial_layers: bool = False,
    editorial_model: Optional[str] = None,
    platform: Optional[str] = None,
    crop_strategy: str = "center",
    pad_strategy: str = "blur",
    pad_color: str = "#000000",
    captions: bool = False,
    caption_style: Optional[dict] = None,
    cookies_from_browser: Optional[str] = None,
    provider: Optional[str] = None,
    chat_provider: Optional[str] = None,
    chat_model: Optional[str] = None,
    overview_chat_provider: Optional[str] = None,
    overview_chat_model: Optional[str] = None,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None,
    transcription_provider: Optional[str] = None,
    transcription_model: Optional[str] = None,
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

    # Validate inputs (supports URLs via yt-dlp)
    from arena.video.downloader import resolve_input, is_url

    try:
        video_file = resolve_input(video_path, mode='video', cookies_from_browser=cookies_from_browser)
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return 1

    if not video_file.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        return 1

    # Resolve output directory
    output_path = Path(output_dir)

    # If relative path, resolve from current working directory
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_dir

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

    # Resolve inference providers
    from arena.providers import resolve_inference, Capability, RuntimeProfile
    from arena.providers.base import ProviderAuthError

    try:
        runtime_profile = RuntimeProfile.from_args(
            provider=provider,
            chat_provider=chat_provider,
            chat_model=chat_model or editorial_model,
            overview_chat_provider=overview_chat_provider,
            overview_chat_model=overview_chat_model,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            transcription_provider=transcription_provider,
            transcription_model=transcription_model,
        )
    except ValueError as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Provider configuration failed"))
        return 1
    effective_editorial_model = runtime_profile.binding_for(Capability.CHAT).model

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

    speech_binding_fingerprint = runtime_profile.fingerprint(
        {Capability.SPEECH}, namespace="arena-transcription-v1"
    )
    speech_fingerprint = hashlib.sha256(
        (
            f"arena-transcript-cache-v2:{speech_binding_fingerprint}:"
            f"enhance_audio={enhance_audio}"
        ).encode("utf-8")
    ).hexdigest()[:20]
    transcript_cache = cache_dir / f"{video_file.stem}_transcript_{speech_fingerprint}.json"
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
                from arena.providers.subprocess_env import scrubbed_env
                subprocess.run([
                    "ffmpeg", "-i", str(video_file),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", "44100", "-ac", "2",
                    "-y", str(temp_audio)
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                   env=scrubbed_env())

                # Enhance the extracted audio
                enhancer.enhance(temp_audio, enhanced_audio_path)

                # Clean up temp file
                temp_audio.unlink()

                audio_to_transcribe = enhanced_audio_path

                print(f"✓ Audio enhanced and cached")
                print(f"  Enhanced audio: {enhanced_audio_path.name}\n")

            except Exception as e:
                from arena.cli.public_errors import format_public_error
                print(format_public_error(e, "Audio enhancement failed"))
                print(f"   Continuing with original audio...\n")
                audio_to_transcribe = video_file

    speech_bundle = None
    transcriber = None
    if use_cached_transcript and transcript_cache.exists():
        print(f"✓ Using cached transcript: {transcript_cache.name}")
        with open(transcript_cache) as f:
            transcript_data = json.load(f)
        print(f"  Duration: {transcript_data.get('duration', 0):.1f}s")
        print(f"  Words:    {len(transcript_data.get('words', []))}\n")
    else:
        # Resolve speech provider only when transcription is actually needed
        try:
            speech_bundle = resolve_inference(
                required={Capability.SPEECH}, profile=runtime_profile,
            )
        except ProviderAuthError as e:
            from arena.cli.public_errors import format_public_error
            print(format_public_error(e, "Transcription provider setup failed"))
            return 1

        if HAS_TQDM:
            with tqdm(total=100, desc="🎤 Transcribing", bar_format='{l_bar}{bar}| {elapsed}') as pbar:
                try:
                    transcriber = Transcriber(speech=speech_bundle.require_speech())
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
                    from arena.cli.public_errors import format_public_error
                    print(f"\n{format_public_error(e, 'Transcription failed')}")
                    return 1
        else:
            print("🎤 Transcribing audio...")
            print("   This may take a few minutes...\n")

            try:
                transcriber = Transcriber(speech=speech_bundle.require_speech())
                transcript_data = transcriber.transcribe(
                    audio_to_transcribe,
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
                from arena.cli.public_errors import format_public_error
                print(format_public_error(e, "Transcription failed"))
                return 1

    # Release the speech runtime before loading local chat and embedding
    # models. On unified-memory systems, keeping both model families resident
    # can significantly increase pressure during the analysis handoff.
    if speech_bundle is not None:
        speech_bundle.close()
    transcriber = None
    speech_bundle = None
    import gc
    gc.collect()

    # =========================================================================
    # STEP 2: Hybrid Analysis (AI + Energy)
    # =========================================================================
    current_step += 1
    print(f"{'='*70}")
    print(f"[{current_step}/{total_steps}] 🧠 Hybrid Analysis (AI + Energy)")
    print(f"{'='*70}\n")

    # Chat and embedding are not needed until analysis. Deferring them avoids
    # loading the llama runtime (and emitting its native startup diagnostics)
    # while local speech transcription is still running.
    print("🔧 Loading inference models...")
    try:
        inference = resolve_inference(
            required={Capability.CHAT, Capability.EMBEDDING},
            profile=runtime_profile,
        )
    except ProviderAuthError as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Provider setup failed"))
        print("   Set it with: export OPENAI_API_KEY='your-key'")
        print("   Get one at: https://platform.openai.com/api-keys\n")
        return 1
    except Exception as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Provider setup failed"))
        return 1

    try:
        # Initialize analyzers
        if HAS_TQDM:
            with tqdm(total=100, desc="🔧 Initializing", bar_format='{l_bar}{bar}') as pbar:
                ai_analyzer = FourLayerAdapter(
                    inference=inference,
                    model=effective_editorial_model,
                    export_layers=export_editorial_layers,
                )
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
            print(f"   Using 4-layer editorial system (model: {effective_editorial_model})")
            ai_analyzer = FourLayerAdapter(
                inference=inference,
                model=effective_editorial_model,
                export_layers=export_editorial_layers,
            )
            energy_analyzer = AudioEnergyAnalyzer(video_path=video_file)
            hybrid_analyzer = HybridAnalyzer(
                ai_analyzer=ai_analyzer,
                energy_analyzer=energy_analyzer,
                energy_weight=0.3  # 30% boost from energy
            )
            print("   ✓ AI analyzer ready (4-layer editorial)")
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
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Analysis failed"))
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
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Alignment failed; using original timestamps"))
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
                    from arena.cli.public_errors import format_public_error
                    print(f"   {format_public_error(e, 'Thumbnail generation failed')}")
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

        # Generate SRT files for captions
        srt_paths = {}
        if captions and successful > 0:
            from arena.subtitles.burner import SubtitleBurner

            style = caption_style or {}
            burner = SubtitleBurner(
                font=style.get('font', 'Arial'),
                font_size=style.get('font_size', style.get('size', 24)),
                color=style.get('color', 'white'),
                bg_color=style.get('bg_color', 'black'),
                position=style.get('position', 'bottom')
            )

            segments = transcript_data.get('segments', [])
            for clip, result in zip(top_clips, clip_results):
                if result.get('success'):
                    clip_id = result['clip_id']
                    srt_path = clips_dir / f"{clip_id}.srt"
                    burner.generate_srt(
                        segments=segments,
                        output_path=srt_path,
                        clip_start=clip['start_time'],
                        clip_end=clip['end_time']
                    )
                    srt_paths[clip_id] = srt_path

            print(f"📝 Generated {len(srt_paths)} subtitle files\n")

    except Exception as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Clip generation failed"))
        return 1

    # =========================================================================
    # STEP 5 (Optional): Platform Formatting
    # =========================================================================
    formatted_count = 0
    formatted_dir = None
    if platform and successful > 0:
        print(f"{'='*70}")
        print(f"[5/5] 📐 Platform Formatting ({platform})")
        print(f"{'='*70}\n")

        try:
            from arena.export.platform_formatter import PlatformFormatter

            formatter = PlatformFormatter()
            spec = formatter.get_platform_spec(platform)
            formatted_dir = output_path / "formatted"
            formatted_dir.mkdir(parents=True, exist_ok=True)

            print(f"Target: {spec.name} ({spec.width}x{spec.height}, {spec.aspect_ratio})")
            print(f"Output: {formatted_dir}\n")

            video_files = list(clips_dir.glob('*.mp4'))
            for i, vf in enumerate(video_files, 1):
                out_name = f"{vf.stem}_{platform}.mp4"
                out_path = formatted_dir / out_name

                # Find matching SRT file for captions
                srt_file = vf.with_suffix('.srt') if captions else None
                if srt_file and not srt_file.exists():
                    srt_file = None

                try:
                    result = formatter.format_for_platform(
                        vf, out_path, platform,
                        crop_strategy=crop_strategy,
                        pad_strategy=pad_strategy,
                        pad_color=pad_color,
                        subtitle_path=srt_file,
                        subtitle_style=caption_style
                    )
                    if result['success']:
                        formatted_count += 1
                        print(f"  [{i}/{len(video_files)}] ✅ {out_name}")
                    else:
                        print(f"  [{i}/{len(video_files)}] ❌ Failed")
                except Exception as e:
                    from arena.cli.public_errors import format_public_error
                    print(f"  [{i}/{len(video_files)}] {format_public_error(e, 'Formatting failed')}")

            print(f"\n✓ Formatted {formatted_count}/{len(video_files)} clips for {spec.name}\n")

        except Exception as e:
            from arena.cli.public_errors import format_public_error
            print(format_public_error(e, "Platform formatting failed"))
            print(f"   Original clips are still available in clips/\n")

    # Standalone caption burning (when no platform formatting)
    elif captions and srt_paths and successful > 0:
        print(f"{'='*70}")
        print(f"📝 Burning captions into clips")
        print(f"{'='*70}\n")

        from arena.subtitles.burner import SubtitleBurner
        style = caption_style or {}
        burner = SubtitleBurner(
            font=style.get('font', 'Arial'),
            font_size=style.get('font_size', style.get('size', 24)),
            color=style.get('color', 'white'),
            bg_color=style.get('bg_color', 'black'),
            position=style.get('position', 'bottom')
        )

        captioned_dir = output_path / "captioned"
        captioned_dir.mkdir(parents=True, exist_ok=True)

        for clip_id, srt_path in srt_paths.items():
            clip_file = clips_dir / f"{clip_id}.mp4"
            if clip_file.exists():
                out_path = captioned_dir / f"{clip_id}_captioned.mp4"
                try:
                    burner.burn_subtitles(clip_file, srt_path, out_path)
                    print(f"  ✅ {out_path.name}")
                except Exception as e:
                    from arena.cli.public_errors import format_public_error
                    print(f"  {clip_id}: {format_public_error(e, 'Caption rendering failed')}")

        print(f"\n✓ Captioned clips saved to {captioned_dir}\n")

    # =========================================================================
    # COPY ARTIFACTS TO OUTPUT
    # =========================================================================
    # Copy enhanced audio, transcript, and analysis to main output directory
    import shutil

    artifacts_copied = []

    # Copy enhanced audio if it exists
    if enhanced_audio_path.exists():
        dest_audio = output_path / enhanced_audio_path.name
        shutil.copy2(enhanced_audio_path, dest_audio)
        artifacts_copied.append(f"audio: {enhanced_audio_path.name}")

    # Copy transcript
    if transcript_cache.exists():
        dest_transcript = output_path / "transcript.json"
        shutil.copy2(transcript_cache, dest_transcript)
        artifacts_copied.append(f"transcript: transcript.json")

    # analysis_results.json is already in output_path, no need to copy

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
    if formatted_dir and formatted_count > 0:
        print(f"   ├── formatted/")
        print(f"   │   └── *_{platform}.mp4   ({formatted_count} formatted clips)")
    print(f"   ├── transcript.json        (word-level transcript)")
    print(f"   ├── analysis_results.json  (full analysis)")
    if enhanced_audio_path.exists():
        print(f"   ├── {enhanced_audio_path.name}")
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
    print("   2. Check transcript.json for word-level timestamps")
    print("   3. Check analysis_results.json for all segments")
    print("   4. Edit clips or run again with different parameters")
    print("   5. Share your clips on social media!\n")

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
        '--export-editorial-layers',
        action='store_true',
        help='Export intermediate results from each editorial layer for debugging'
    )
    parser.add_argument(
        '--editorial-model',
        choices=['gpt-4o', 'gpt-4o-mini'],
        default=None,
        help='Backward-compatible alias for --chat-model'
    )
    parser.add_argument(
        '-p', '--platform',
        choices=['tiktok', 'instagram-reels', 'youtube-shorts', 'youtube', 'instagram-feed', 'twitter', 'linkedin'],
        default=None,
        help='Auto-format clips for platform after generation'
    )
    parser.add_argument(
        '--crop',
        default='center',
        choices=['center', 'smart', 'top', 'bottom'],
        help='Crop strategy for platform formatting (default: center)'
    )
    parser.add_argument(
        '--pad',
        default='blur',
        choices=['blur', 'black', 'white', 'color'],
        help='Pad strategy for platform formatting (default: blur)'
    )
    parser.add_argument(
        '--pad-color',
        default='#000000',
        help='Padding color for platform formatting (default: #000000)'
    )
    parser.add_argument(
        '--captions',
        action='store_true',
        help='Burn subtitle captions into generated clips'
    )
    parser.add_argument(
        '--caption-font-size',
        type=int,
        default=None,
        help='Caption font size (default: 24)'
    )
    parser.add_argument(
        '--caption-color',
        type=str,
        default=None,
        help='Caption text color: white, yellow, red, black (default: white)'
    )
    parser.add_argument(
        '--caption-position',
        type=str,
        default=None,
        choices=['bottom', 'top', 'middle'],
        help='Caption position (default: bottom)'
    )
    parser.add_argument(
        '--cookies-from-browser',
        type=str,
        default=None,
        help='Browser to extract cookies from for URL downloads (chrome, firefox, safari, brave, edge)'
    )

    args = parser.parse_args()

    # Run pipeline
    # Build caption style from args
    caption_style = None
    if args.captions:
        caption_style = {}
        if args.caption_font_size:
            caption_style['font_size'] = args.caption_font_size
        if args.caption_color:
            caption_style['color'] = args.caption_color
        if args.caption_position:
            caption_style['position'] = args.caption_position

    sys.exit(run_arena_pipeline(
        video_path=args.video,
        output_dir=args.output,
        num_clips=args.num_clips,
        min_duration=args.min,
        max_duration=args.max,
        use_cached_transcript=not args.no_cache,
        fast_mode=args.fast,
        padding=args.padding,
        export_editorial_layers=args.export_editorial_layers,
        editorial_model=args.editorial_model,
        platform=args.platform,
        crop_strategy=args.crop,
        pad_strategy=args.pad,
        pad_color=args.pad_color,
        captions=args.captions,
        caption_style=caption_style,
        cookies_from_browser=args.cookies_from_browser
    ))


if __name__ == "__main__":
    main()
