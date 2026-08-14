import sys
from argparse import Namespace
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import arena.cli.commands.process as process_command


def test_process_forwards_browser_cookies_to_pipeline(monkeypatch):
    pipeline_options = {}
    results = []

    def run_pipeline(**options):
        pipeline_options.update(options)
        return 0

    monkeypatch.setattr(process_command, 'PipelineEventStream', StringIO)
    monkeypatch.setattr(process_command, 'run_arena_pipeline', run_pipeline)
    monkeypatch.setattr(process_command, 'result', results.append)

    exit_code = process_command.run_process(
        Namespace(
            video='https://www.youtube.com/watch?v=example',
            output='.arena/output',
            num_clips=8,
            min_duration=30,
            max_duration=90,
            no_cache=False,
            fast=False,
            padding=0.0,
            max_adjustment=5.0,
            no_enhance=False,
            scene_detection=False,
            captions=False,
            cookies_from_browser='brave',
        )
    )

    assert exit_code == 0
    assert pipeline_options['cookies_from_browser'] == 'brave'
    assert results == [{'success': True, 'outputDir': str(Path('.arena/output').resolve())}]
