"""Модель данных: один звук в библиотеке."""
import uuid
from dataclasses import dataclass, field, asdict, fields

DEFAULT_CATEGORY = "Без категории"


@dataclass
class Sound:
    """Модель звука в библиотеке.

    Attributes:
    name: Отображаемое название.
    path: Путь к аудиофайлу.
    hotkey: Назначенная клавиша в нижнем регистре.
    volume: Громкость звука (0.0–1.0).
    is_loop: Зацикливать ли звук.
    category: Категория для фильтра.
    id: Уникальный идентификатор (8 hex-символов)."""
    name: str
    path: str
    hotkey: str = ""
    volume: float = 1.0          # 0.0 .. 1.0, громкость конкретного звука
    is_loop: bool = False
    category: str = DEFAULT_CATEGORY
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict:
        """Преобразует звук в словарь для сохранения в JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Sound":
        """Создаёт звук из словаря, игнорируя неизвестные поля."""
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})
