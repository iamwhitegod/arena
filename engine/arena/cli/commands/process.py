"""arena process - Run full pipeline"""

import sys
from contextlib import redirect_stdout
from pathlib import Path
from arena.cli.protocol import PipelineEventStream, result

# Import the existing pipeline function
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from arena_process import run_arena_pipeline


def run_process(args):
    """Run the process command (supports URLs)"""
    event_stream = PipelineEventStream()
    with redirect_stdout(event_stream):
        exit_code = run_arena_pipeline(
        video_path=args.video,
        output_dir=args.output,
        num_clips=args.num_clips,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        use_cached_transcript=not args.no_cache,
        fast_mode=args.fast,
        padding=args.padding,
        max_adjustment=args.max_adjustment,
        enhance_audio=not args.no_enhance,
        use_scene_detection=args.scene_detection,
        export_editorial_layers=getattr(args, 'export_editorial_layers', False),
        editorial_model=getattr(args, 'editorial_model', 'gpt-4o'),
        platform=getattr(args, 'platform', None),
        crop_strategy=getattr(args, 'crop', 'center'),
        pad_strategy=getattr(args, 'pad', 'blur'),
        pad_color=getattr(args, 'pad_color', '#000000'),
        captions=getattr(args, 'captions', False),
        caption_style={
            k: v for k, v in {
                'font_size': getattr(args, 'caption_font_size', None),
                'color': getattr(args, 'caption_color', None),
                'position': getattr(args, 'caption_position', None),
            }.items() if v is not None
        } if getattr(args, 'captions', False) else None,
        cookies_from_browser=getattr(args, 'cookies_from_browser', None),
        provider=getattr(args, 'provider', None),
        chat_provider=getattr(args, 'chat_provider', None),
        chat_model=getattr(args, 'chat_model', None),
        overview_chat_provider=getattr(args, 'overview_chat_provider', None),
        overview_chat_model=getattr(args, 'overview_chat_model', None),
        embedding_provider=getattr(args, 'embedding_provider', None),
        embedding_model=getattr(args, 'embedding_model', None),
        transcription_provider=getattr(args, 'transcription_provider', None),
        transcription_model=getattr(args, 'transcription_model', None),
        )
    if exit_code == 0:
        result({"success": True, "outputDir": str(Path(args.output).resolve())})
    return exit_code
