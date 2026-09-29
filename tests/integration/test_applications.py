"""Integration tests of console applications of the previous laboratory works."""

import shutil
import sys
from pathlib import Path

import pytest

from restaurant_orders import analysis, console
from restaurant_orders.stream import main as stream_main

pytestmark = pytest.mark.integration

PROJECT = Path(__file__).resolve().parents[2]


def test_console_interactive_menu(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    answers = iter(
        [
            "1",
            "2",
            "abc",
            "201",
            "2",
            "201",
            "3",
            "201",
            "Суп",
            "Перші страви",
            "-5",
            "80",
            "3",
            "999",
            "Сік",
            "Напої",
            "50",
            "4",
            "5",
            "9",
            "0",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(sys, "argv", ["console", "--interactive"])
    console.main()
    output = capsys.readouterr().out
    assert "Введіть ціле додатне число." in output
    assert "Замовлення створено." in output
    assert "Замовлення №201 вже існує." in output
    assert "Введіть додатне число." in output
    assert "Страву додано." in output
    assert "Замовлення №999 не знайдено." in output
    assert "Невідома команда. Спробуйте ще раз." in output
    assert output.rstrip().endswith("До побачення!")


def test_analysis_report(capsys: pytest.CaptureFixture[str]) -> None:
    analysis.main()
    output = capsys.readouterr().out
    assert "Найпопулярніша страва: Борщ (4 рази)" in output
    assert "Середня вартість замовлення: 321.67 грн" in output


def test_stream_demo_in_temporary_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "data").mkdir()
    shutil.copy(PROJECT / "data" / "orders_sample.csv", tmp_path / "data" / "orders_sample.csv")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(stream_main, "LARGE_RECORDS", 2_000)
    stream_main.main()
    output = capsys.readouterr().out
    assert "Коректних позицій: 13, некоректних: 5" in output
    assert "groupby після сортування: [201, 202, 203, 204, 205, 206]" in output
    assert (tmp_path / "data" / "generated" / "orders_2000.csv").exists()
