"""Тесты аудиодвижка на dummy-драйвере SDL (без реального звука)."""
import math
import os
import shutil
import struct
import tempfile
import time
import unittest
import uuid
import wave
from pathlib import Path

os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from PyQt6.QtCore import QCoreApplication

from audio_engine import AudioEngine
from models import Sound


def make_temp_dir() -> Path:
    path = Path(tempfile.gettempdir()) / f"soundboard-audio-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _make_wav(path: Path, seconds: float = 1.0, frequency: float = 440.0) -> None:
    rate = 44100
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for index in range(int(rate * seconds)):
            value = int(12000 * math.sin(2 * math.pi * frequency * index / rate))
            frames += struct.pack("<hh", value, value)
        wf.writeframes(bytes(frames))


APP = None
TMP = None
ENGINE = None
SOUND = None


def setUpModule():
    global APP, TMP, ENGINE, SOUND
    APP = QCoreApplication.instance() or QCoreApplication([])
    TMP = make_temp_dir()
    path = TMP / "tone.wav"
    _make_wav(path)
    ENGINE = AudioEngine.instance()
    ENGINE.set_master_volume(0)          # беззвучно
    SOUND = Sound(name="Тест", path=str(path), id="test-tone")


def tearDownModule():
    global ENGINE, TMP
    if ENGINE:
        ENGINE.stop_all()
        ENGINE.shutdown()
    if TMP:
        shutil.rmtree(TMP, ignore_errors=True)


def pump(ms: int) -> None:
    deadline = time.time() + ms / 1000
    while time.time() < deadline:
        APP.processEvents()
        time.sleep(0.005)


class AudioEngineTests(unittest.TestCase):
    def setUp(self):
        ENGINE.stop_all()
        ENGINE.set_loop(SOUND.id, False)
        pump(30)

    def test_play_and_stop(self):
        self.assertTrue(ENGINE.play(SOUND))
        self.assertTrue(ENGINE.is_playing(SOUND.id))
        ENGINE.stop(SOUND.id)
        self.assertFalse(ENGINE.is_playing(SOUND.id))

    def test_duration_and_seek(self):
        length = ENGINE.load_duration(SOUND)
        self.assertAlmostEqual(length, 1.0, places=2)
        self.assertTrue(ENGINE.play(SOUND))
        ENGINE.seek(SOUND, 0.5)
        position = ENGINE.position(SOUND.id)
        self.assertAlmostEqual(position, 0.5, delta=0.2)
        ENGINE.stop(SOUND.id)

    def test_loop_without_restart(self):
        self.assertTrue(ENGINE.play(SOUND))
        before = ENGINE.position(SOUND.id)
        ENGINE.set_loop(SOUND.id, True)
        after = ENGINE.position(SOUND.id)
        self.assertGreaterEqual(after, before - 0.1)
        self.assertTrue(ENGINE.is_playing(SOUND.id))
        ENGINE.set_loop(SOUND.id, False)
        ENGINE.stop(SOUND.id)

    def test_volume(self):
        ENGINE.play(SOUND)
        ENGINE.set_sound_volume(SOUND.id, 0.3)
        self.assertAlmostEqual(ENGINE._volumes[SOUND.id], 0.3)
        ENGINE.stop(SOUND.id)


if __name__ == "__main__":
    unittest.main()
