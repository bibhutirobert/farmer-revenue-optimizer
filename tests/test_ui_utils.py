"""
Tests for shared UI helpers — the video source resolution and the written
walkthrough. Rendering itself needs a Streamlit runtime, so what's covered
here is the logic that decides *what* gets rendered.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils import ui_utils
from utils.ui_utils import _steps, get_help_video


# ── Video source resolution ────────────────────────────────────────────────────

def test_no_video_configured_by_default():
    """No secret and no committed file -> written steps only."""
    source, kind = get_help_video()
    assert source is None
    assert kind == "none"


def test_local_file_used_when_present(monkeypatch, tmp_path):
    fake = tmp_path / "how_to_use.mp4"
    fake.write_bytes(b"not really a video")
    monkeypatch.setattr(ui_utils, "LOCAL_VIDEO", str(fake))

    source, kind = get_help_video()
    assert kind == "file"
    assert source == str(fake)


def test_secret_url_takes_priority_over_local_file(monkeypatch, tmp_path):
    fake = tmp_path / "how_to_use.mp4"
    fake.write_bytes(b"not really a video")
    monkeypatch.setattr(ui_utils, "LOCAL_VIDEO", str(fake))

    class FakeSecrets:
        def get(self, key, default=None):
            if key == "help":
                return {"video_url": "https://youtu.be/example"}
            return default

    monkeypatch.setattr(ui_utils.st, "secrets", FakeSecrets())

    source, kind = get_help_video()
    assert kind == "url"
    assert source == "https://youtu.be/example"


def test_blank_secret_is_ignored(monkeypatch):
    class FakeSecrets:
        def get(self, key, default=None):
            if key == "help":
                return {"video_url": "   "}
            return default

    monkeypatch.setattr(ui_utils.st, "secrets", FakeSecrets())
    assert get_help_video() == (None, "none")


# ── Written walkthrough ────────────────────────────────────────────────────────

def test_steps_cover_the_whole_flow():
    steps = _steps("en")
    assert len(steps) >= 5
    joined = " ".join(title + detail for title, detail in steps).lower()
    for expected in ("sign in", "confirm", "pdf"):
        assert expected in joined


def test_steps_are_numbered_in_order():
    for index, (title, _) in enumerate(_steps("en"), start=1):
        assert title.startswith(f"{index}.")


def test_steps_mention_the_locate_shortcut():
    """The one-tap path is the whole point of the mobile work — it must be
    the first thing the walkthrough teaches about picking a field."""
    detail = dict(_steps("en"))["2. Select your field"].lower()
    assert "show me where i am" in detail


def test_hindi_steps_exist_and_differ():
    hindi = _steps("hi")
    assert len(hindi) == len(_steps("en"))
    assert hindi != _steps("en")
    joined = " ".join(t + d for t, d in hindi)
    assert any("ऀ" <= ch <= "ॿ" for ch in joined)


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_every_step_has_a_detail(lang):
    for title, detail in _steps(lang):
        assert title.strip()
        assert detail.strip()
