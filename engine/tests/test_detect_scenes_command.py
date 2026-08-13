import json
from argparse import Namespace
from pathlib import Path

from arena.cli.commands.detect_scenes import run_detect_scenes
from arena.video.scene_detector import SceneDetector


def test_detect_scenes_emits_bridge_result_and_zero_exit(tmp_path, monkeypatch, capsys):
    video_path = tmp_path / 'fixture.mp4'
    output_path = tmp_path / 'scenes.json'
    video_path.write_bytes(b'fixture')
    monkeypatch.setattr(
        SceneDetector,
        'detect_scenes',
        lambda self, video, min_scene_duration: [
            {'time': 0.5, 'score': 0.8},
            {'time': 2.5, 'score': 0.9},
        ],
    )

    exit_code = run_detect_scenes(
        Namespace(
            video=str(video_path),
            output=str(output_path),
            threshold=0.4,
            min_duration=0.2,
            report=False,
        )
    )

    lines = capsys.readouterr().out.splitlines()
    protocol = json.loads(lines[-1])
    saved = json.loads(Path(output_path).read_text())

    assert exit_code == 0
    assert protocol['type'] == 'result'
    assert protocol['data']['scene_count'] == 2
    assert saved['scene_count'] == 2
