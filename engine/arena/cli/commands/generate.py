"""arena generate - Generate clips from analysis"""

import json
from pathlib import Path
from arena.clipping.generator import ClipGenerator
from arena.cli.protocol import progress as emit_progress, result as emit_result


def run_generate(args):
    """Generate video clips from analysis results"""

    video_path = Path(args.video)
    analysis_path = Path(args.analysis)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {args.video}")
        return 1

    if not analysis_path.exists():
        print(f"❌ Error: Analysis file not found: {args.analysis}")
        return 1

    print(f"\n🎬 Generating clips from analysis\n")
    print(f"📹 Video:    {video_path.name}")
    print(f"📊 Analysis: {analysis_path.name}\n")

    # Load analysis results
    with open(analysis_path) as f:
        analysis = json.load(f)

    clips = analysis.get('clips', [])

    if not clips:
        print("❌ Error: No clips found in analysis file")
        return 1

    # Determine how many clips to generate
    if args.num_clips:
        clips = clips[:args.num_clips]

    print(f"🎯 Generating {len(clips)} clips\n")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize generator
        generator = ClipGenerator(video_path)

        # Progress callback
        def progress(current, total, clip_info):
            emit_progress("generation", current / total * 100, f"Generated clip {current} of {total}")
            if clip_info.get('success'):
                print(f"   [{current}/{total}] ✓ {clip_info['clip_id']}")
                print(f"           {clip_info['duration']:.1f}s, {clip_info['size_mb']}MB")
            else:
                print(f"   [{current}/{total}] ✗ {clip_info['clip_id']} - {clip_info.get('error')}")

        # Generate clips
        results = generator.generate_multiple_clips(
            segments=clips,
            output_dir=output_dir,
            padding=args.padding,
            fast_mode=args.fast,
            progress_callback=progress
        )

        # Generate thumbnails
        if not args.no_thumbs:
            print(f"\n📸 Generating thumbnails...")
            for clip, result in zip(clips, results):
                if result.get('success'):
                    try:
                        midpoint = (clip['start_time'] + clip['end_time']) / 2
                        thumb_path = output_dir / f"{result['clip_id']}_thumb.jpg"
                        generator.generate_thumbnail(midpoint, thumb_path, width=640)

                        # Save metadata
                        metadata = {
                            **result,
                            'title': clip.get('title', 'Untitled'),
                            'scores': {
                                'ai_score': clip.get('interest_score', 0),
                                'hybrid_score': clip.get('hybrid_score', 0)
                            }
                        }
                        metadata_path = output_dir / f"{result['clip_id']}_metadata.json"
                        with open(metadata_path, 'w') as f:
                            json.dump(metadata, f, indent=2)

                    except Exception as e:
                        from arena.cli.public_errors import format_public_error
                        print(f"   {format_public_error(e, 'Thumbnail generation failed')}")

        # Summary
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful
        total_size = sum(r.get('size_mb', 0) for r in results if r.get('success'))

        print(f"\n✅ Clip generation complete!")
        print(f"   Successful: {successful}/{len(results)}")
        print(f"   Failed:     {failed}")
        print(f"   Total size: {total_size:.1f} MB")
        print(f"   Output:     {output_dir}\n")

        successful_clips = [r for r in results if r.get('success')]
        emit_result({"success": successful > 0, "clips": successful_clips, "failed": failed, "totalSizeMb": total_size, "outputDir": str(output_dir)})
        return 0

    except Exception as e:
        from arena.cli.public_errors import format_public_error
        print(f"\n{format_public_error(e, 'Generation failed')}")
        return 1
