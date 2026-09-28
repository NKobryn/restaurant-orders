"""Experiment 5: a flaky test that depends on randomness and its deterministic version."""

import buggy_pricing
import pytest


def test_random_bad() -> None:
    assert buggy_pricing.free_table() == 1


def test_random_fixed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(buggy_pricing.random, "randint", lambda low, high: 1)
    assert buggy_pricing.free_table() == 1
