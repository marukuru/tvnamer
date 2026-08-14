#!/usr/bin/env python

"""Tests the current system for things that might cause problems
"""

import os


import pytest

def test_nosavedconfig():
    """A config at ~/.tvnamer.json could cause problems with some tests
    """
    if os.path.isfile(os.path.expanduser("~/.tvnamer.json")):
        pytest.skip("~/.tvnamer.json exists, which could cause problems with some tests")
    if os.path.isfile(os.path.expanduser("~/.config/tvnamer/tvnamer.json")):
        pytest.skip("~/.config/tvnamer/tvnamer.json exists, which could cause problems with some tests")
