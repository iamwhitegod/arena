"""arena process - Run full pipeline"""

import sys
from pathlib import Path

# Import the existing pipeline function
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from arena_process import run_arena_pipeline


def run_process(args):
    """Run the process command"""
    return run_arena_pipeline(
        video_path=args.video,
        output_dir=args.output,
        num_clips=args.num_clips,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        use_cached_transcript=not args.no_cache,
        fast_mode=args.fast,
        padding=args.padding,
        max_adjustment=args.max_adjustment
    )
