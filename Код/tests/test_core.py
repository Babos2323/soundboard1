"""Модульные тесты базовой логики Soundboard (unittest, без сторонних зависимостей)."""
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtGui import QKeyEvent

from config_repository import ConfigRepository, DEFAULT_SETTINGS, default_config_path
from keys import from_qt_event, pretty
from models import Sound
from sound_manager import SoundManager
import theme

APP = None


def make_temp_dir() -> Path:
    """Создаёт временный каталог с обычными правами (совместимо с песочницами)."""
    path = Path(tempfile.gettempdir()) / f"soundboard-test-{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setUpModule():
    global APP
    APP = QCoreApplication.instance() or QCoreApplication([])


class SoundModelTests(unittest.TestCase):
    def test_defaults(self):
        sound = Sound(name="Смех", path="laugh.mp3")
        self.assertTrue(sound.id)
        self.assertEqual(len(sound.id), 8)
        self.assertEqual(sound.volume, 1.0)
        self.assertFalse(sound.is_loop)
        self.assertEqual(sound.category, "Без категории")

    def test_roundtrip(self):
        sound = Sound(name="Аплодисменты", path="applause.wav", hotkey="q",
                      volume=0.5, is_loop=True, category="Сцена")
        restored = Sound.from_dict(sound.to_dict())
        self.assertEqual(restored, sound)

    def test_unknown_fields_ignored(self):
        restored = Sound.from_dict({"name": "Мем", "path": "meme.wav", "unknown": 1})
        self.assertEqual(restored.name, "Мем")
        self.assertFalse(hasattr(restored, "unknown"))


class ConfigRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = make_temp_dir()
        self.path = self.tmp / "config.json"
        self.repo = ConfigRepository(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empty_file_returns_defaults(self):
        sounds, settings = self.repo.load()
        self.assertEqual(sounds, [])
        self.assertEqual(settings["master_volume"], DEFAULT_SETTINGS["master_volume"])

    def test_save_and_load(self):
        sound = Sound(name="Труба", path="trumpet.ogg", hotkey="1")
        settings = dict(DEFAULT_SETTINGS, master_volume=55, loop_all=True)
        self.repo.save([sound], settings)
        self.assertTrue(self.path.exists())
        self.assertFalse(self.path.with_suffix(".tmp").exists())
        sounds, loaded = self.repo.load()
        self.assertEqual(len(sounds), 1)
        self.assertEqual(sounds[0].name, "Труба")
        self.assertEqual(loaded["master_volume"], 55)
        self.assertTrue(loaded["loop_all"])

    def test_invalid_json_is_ignored(self):
        self.path.write_text("{not json", encoding="utf-8")
        sounds, settings = self.repo.load()
        self.assertEqual(sounds, [])
        self.assertEqual(settings["master_volume"], DEFAULT_SETTINGS["master_volume"])

    def test_default_path_is_in_appdata(self):
        import os
        old = os.environ.get("APPDATA")
        os.environ["APPDATA"] = str(self.tmp)
        try:
            path = default_config_path()
            self.assertEqual(path.parent, self.tmp / "Soundboard")
            self.assertEqual(path.name, "config.json")
        finally:
            if old is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = old


class SoundManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = make_temp_dir()
        self.path = self.tmp / "config.json"
        self.manager = SoundManager(ConfigRepository(self.path))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_add_and_find(self):
        sound = self.manager.add(name="Дождь", path="rain.wav")
        self.assertEqual(self.manager.get(sound.id), sound)
        self.assertEqual(self.manager.find_by_hotkey(sound.hotkey), sound)
        self.assertEqual(self.manager.find_by_hotkey("unknown"), None)

    def test_autohotkey_and_categories(self):
        first = self.manager.add(name="Птицы", path="birds.wav", category="Природа")
        second = self.manager.add(name="Кот", path="cat.wav", category="Животные")
        self.assertNotEqual(first.hotkey, second.hotkey)
        self.assertEqual(self.manager.categories(), ["Животные", "Природа"])
        self.assertEqual(first.category, "Природа")

    def test_update_silent_does_not_emit_changed(self):
        sound = self.manager.add(name="Взрыв", path="boom.wav")
        changes = []
        self.manager.changed.connect(lambda: changes.append(1))
        self.manager.update(sound.id, silent=True, volume=0.2)
        self.assertEqual(changes, [])
        self.assertAlmostEqual(self.manager.get(sound.id).volume, 0.2)
        self.manager.update(sound.id, silent=False, volume=0.3)
        self.assertEqual(len(changes), 1)

    def test_remove(self):
        sound = self.manager.add(name="Временный", path="tmp.wav")
        self.manager.remove(sound.id)
        self.assertIsNone(self.manager.get(sound.id))


class KeysAndThemeTests(unittest.TestCase):
    def test_pretty(self):
        self.assertEqual(pretty("q"), "Q")
        self.assertEqual(pretty("f5"), "F5")
        self.assertEqual(pretty(""), "")

    def test_from_qt_event(self):
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Q,
                          Qt.KeyboardModifier.NoModifier, "q")
        self.assertEqual(from_qt_event(event), "q")

    def test_theme_palette(self):
        self.assertEqual(theme.BG, "#0f1116")
        self.assertEqual(theme.CARD, "#1a1d24")
        self.assertIn("QFrame#card", theme.STYLE)


if __name__ == "__main__":
    unittest.main()
