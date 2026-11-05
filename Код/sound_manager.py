"""SoundManager: бизнес-логика библиотеки звуков (Model)."""
from PyQt6.QtCore import QObject, pyqtSignal

from config_repository import ConfigRepository
from models import Sound, DEFAULT_CATEGORY

# Порядок автоназначения клавиш новым звукам (как в макете: 1 2 3 Q W E R T Y U I O ...)
AUTO_KEYS = "123qwertyuiopasdfghjklzxcvbnm4567890"


class SoundManager(QObject):
    """Бизнес-логика библиотеки звуков (Model)."""
    changed = pyqtSignal()

    def __init__(self, repo: ConfigRepository):
        super().__init__()
        self.repo = repo
        self.sounds, self.settings = repo.load()

    # --- доступ ---------------------------------------------------------
    def get(self, sound_id: str) -> Sound | None:
        """Находит звук по идентификатору."""
        return next((s for s in self.sounds if s.id == sound_id), None)

    def find_by_hotkey(self, key: str, exclude_id: str | None = None) -> Sound | None:
        """Находит звук, назначенный на указанную клавишу."""
        if not key:
            return None
        return next((s for s in self.sounds if s.hotkey == key and s.id != exclude_id), None)

    def categories(self) -> list[str]:
        """Возвращает отсортированный список категорий."""
        return sorted({s.category for s in self.sounds})

    def next_free_hotkey(self) -> str:
        """Возвращает первую свободную клавишу для автоназначения."""
        used = {s.hotkey for s in self.sounds}
        return next((k for k in AUTO_KEYS if k not in used), "")

    # --- изменение ------------------------------------------------------
    def add(self, name: str, path: str, hotkey: str = "", category: str = DEFAULT_CATEGORY) -> Sound:
        """Добавляет новый звук в библиотеку и сохраняет изменения."""
        sound = Sound(name=name, path=path,
                      hotkey=hotkey or self.next_free_hotkey(),
                      category=category or DEFAULT_CATEGORY)
        self.sounds.append(sound)
        self._commit()
        return sound

    def remove(self, sound_id: str) -> None:
        """Удаляет звук из библиотеки по идентификатору."""
        self.sounds = [s for s in self.sounds if s.id != sound_id]
        self._commit()

    def update(self, sound_id: str, silent: bool = False, **fields) -> None:
        """Изменить поля звука.

        silent=True — только сохранить в JSON, не перестраивая карточки:
        так делают встроенные регуляторы на главном экране, чтобы не сбрасывать
        прокрутку и не удалять виджет прямо под курсором.
        """
        sound = self.get(sound_id)
        if sound:
            for key, value in fields.items():
                setattr(sound, key, value)
            if silent:
                self.save()
            else:
                self._commit()

    def set_settings(self, **values) -> None:
        """Обновляет настройки приложения и сохраняет их."""
        self.settings.update(values)
        self.save()

    def save(self) -> None:
        """Сохраняет библиотеку и настройки через репозиторий."""
        self.repo.save(self.sounds, self.settings)

    def _commit(self) -> None:
        self.save()
        self.changed.emit()
