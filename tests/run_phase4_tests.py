"""
Test Runner for Phase 4
=======================
Run all Phase 4 unit and integration tests.

Usage:
    # Run all Phase 4 tests
    python tests/run_phase4_tests.py
    
    # Run specific test file
    python tests/run_phase4_tests.py --meta-labeler
    python tests/run_phase4_tests.py --gpu-var
    python tests/run_phase4_tests.py --position-manager
    python tests/run_phase4_tests.py --integration
    
    # Run with verbose output
    python tests/run_phase4_tests.py -v
"""

import sys
import subprocess
from pathlib import Path

# Test files
TEST_FILES = {
    "meta_labeler": "tests/test_meta_labeler.py",
    "gpu_var": "tests/test_gpu_var.py",
    "position_manager": "tests/test_position_manager.py",
    "integration": "tests/test_position_lifecycle_integration.py",
}


def run_tests(test_names=None, verbose=False):
    """
    Run specified tests using pytest.
    
    Args:
        test_names: List of test names to run (or None for all)
        verbose: Whether to use verbose output (-v flag)
    """
    # Determine which tests to run
    if test_names is None or "all" in test_names:
        test_files = list(TEST_FILES.values())
    else:
        test_files = []
        for name in test_names:
            if name in TEST_FILES:
                test_files.append(TEST_FILES[name])
            else:
                print(f"Unknown test: {name}")
                print(f"Available: {', '.join(TEST_FILES.keys())}")
                return 1
    
    # Build pytest command
    cmd = ["pytest"] + test_files
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "--tb=short",
        "-ra",  # Show summary of all test results
        "--color=yes",
    ])
    
    print(f"Running: {' '.join(cmd)}\n")
    
    # Run tests
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run Phase 4 tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "tests",
        nargs="*",
        default=["all"],
        help="Tests to run: all, meta-labeler, gpu-var, position-manager, integration",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    sys.exit(run_tests(args.tests, args.verbose))
