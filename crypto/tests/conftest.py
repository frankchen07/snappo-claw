"""Shared pytest configuration."""

import sys
import os

# workspace/ — so `from crypto.cli import ...` resolves to workspace/crypto/cli.py
_workspace = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _workspace)
# workspace/crypto/ — so `from tests.fixtures import ...` resolves inside this package
sys.path.insert(0, os.path.join(_workspace, "crypto"))
