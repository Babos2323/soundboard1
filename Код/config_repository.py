"""ConfigRepository (Singleton): хранение библиотеки и настроек в JSON."""
import json
import os
from pathlib import Path

from models import Sound

DEFAULT_SETTINGS = {
    "master_volume": 70,          # %
    "allow_overlap": True,        # разрешить одновременное воспроизведение
    "loop_all": False,            # зацикливать все звуки
    "remember_settings": True,    # запоминать настройки между запусками
    "global_hotkeys": False,      # горячие клавиши, когда окно не в фокусе
}

LEGACY_CONFIG_PATH = Path.home() / ".config" / "soundboard" / "config.json"


def default_config_path() -> Path:
    """Путь к файлу конфигурации в профиле Windows (``%APPDATA%``).

    Если переменная ``APPDATA`` недоступна, используется
    ``C:\\Users\\<пользователь>\\AppData\\Roaming\\Soundboard\\config.json``.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Soundboard" / "config.json"
    return Path.home() / "AppData" / "Roaming" / "Soundboard" / "config.json"


class ConfigRepository:
    """Хранилище библиотеки и настроек в JSON (Singleton)."""

    _instance = None

    @classmethod
    def instance(cls) -> "ConfigRepository":
        """Возвращает единственный экземпляр хранилища."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_config_path()
        # путь старой версии приложения: нужен для миграции библиотеки
        self.legacy_path = None if path else LEGACY_CONFIG_PATH

    def load(self) -> tuple[list[Sound], dict]:
        """Загружает список звуков и настройки из файла.

        Если новый файл ещё не создан, но существует конфигурация старой
        версии, данные читаются из неё; при первом сохранении они будут
        записаны по новому пути в ``%APPDATA%``.

        Returns:
            Кортеж ``(sounds, settings)``; при ошибках возвращает значения
            по умолчанию.
        """
        settings = dict(DEFAULT_SETTINGS)
        sounds: list[Sound] = []
        source = self.path
        if not source.is_file() and self.legacy_path and self.legacy_path.is_file():
            source = self.legacy_path
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return sounds, settings
        sounds = [Sound.from_dict(item) for item in data.get("sounds", [])
                  if "name" in item and "path" in item]
        settings.update(data.get("settings", {}))
        return sounds, settings

    def save(self, sounds: list[Sound], settings: dict) -> None:
        """Атомарно сохраняет звуки и настройки в JSON."""
        to_store = settings if settings.get("remember_settings") else {
            **DEFAULT_SETTINGS, "remember_settings": False}
        data = {"settings": to_store, "sounds": [sound.to_dict() for sound in sounds]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
