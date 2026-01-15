"""arena demo - Run demo with test data"""

import sys
from pathlib import Path

# Import the existing demo function
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from arena_process_demo import run_demo as run_demo_impl


def run_demo(args):
    """Run the demo command"""
    return run_demo_impl()
