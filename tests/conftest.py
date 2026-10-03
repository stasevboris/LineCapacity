from __future__ import annotations

import pytest

from tests.helpers import ROOT, SCHEMES, act


@pytest.fixture
def root():
    return ROOT


@pytest.fixture
def scheme_files():
    return SCHEMES


@pytest.fixture
def new_scheme():
    return act(None, kind="new")
