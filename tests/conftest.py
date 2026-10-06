from __future__ import annotations

import os

import pytest

from tests.helpers import ROOT, SCHEMES, act
from voltplan import consultant

os.environ.pop(consultant.KEY_VARIABLE, None)
consultant.winreg = None


@pytest.fixture
def root():
    return ROOT


@pytest.fixture
def scheme_files():
    return SCHEMES


@pytest.fixture
def new_scheme():
    return act(None, kind="new")
