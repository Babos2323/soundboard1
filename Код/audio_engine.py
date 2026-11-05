"""AudioEngine (Singleton): воспроизведение через pygame.mixer.

Сигналы (Observer) сообщают интерфейсу о начале, конце и текущей позиции звука.
Маленький буфер (512 сэмплов ≈ 12 мс) обеспечивает задержку заметно меньше 100 мс.

Перемотка реализована без внешних зависимостей: у `pygame.mixer.Sound` нет
позиции, поэтому нужный фрагмент вырезается из сырых PCM-данных (`Sound.get_raw`)
и проигрывается как отдельный Sound с начала фрагмента.
"""
import os
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal

from models import Sound

CHANNELS = 16
PROGRESS_MS = 100          # как часто обновлять позицию в интерфейсе


class AudioEngine(QObject):
    """Движок воспроизведения на pygame.mixer (Singleton).

    Управляет каналами, громкостью, перемоткой и зацикливанием, сообщает
    интерфейсу о событиях через сигналы Qt."""
    started = pyqtSignal(str)                   # sound_id — звук пошёл
    finished = pyqtSignal(str)                  # sound_id — звук закончился/остановлен
    progress = pyqtSignal(str, float, float)    # sound_id, позиция (с), длительность (с)
    error = pyqtSignal(str)                     # текст ошибки

    _instance = None

    @classmethod
    def instance(cls) -> "AudioEngine":
        """Возвращает единственный экземпляр движка."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(CHANNELS)

        freq, _fmt, channels = pygame.mixer.get_init() or (44100, -16, 2)
        self._freq = freq
        self._bytes_per_frame = 4 if channels == 2 else 2

        self.master_volume = 0.7
        self.allow_overlap = True
        self.loop_all = False

        self._cache: dict[str, tuple[str, pygame.mixer.Sound]] = {}
        self._durations: dict[str, float] = {}
        self._volumes: dict[str, float] = {}
        self._channels: dict[str, pygame.mixer.Channel] = {}
        self._sounds: dict[str, Sound] = {}
        self._starts: dict[str, tuple[float, float]] = {}   # id -> (смещение, monotonic)
        self._looped: dict[str, bool] = {}                  # цикл включён у канала
        self._loop_override: dict[str, bool] = {}           # ручное переключение цикла
        self._pending: dict[str, float] = {}                # позиция до первого play
        self._loop_gen: dict[str, int] = {}                 # защита от устаревших таймеров

        self._ticks = 0
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    # --- управление ------------------------------------------------------
    def play(self, sound: Sound) -> bool:
        """Запускает звук с учётом настроек наложения и позиции.

        Args:
        sound: Звук из библиотеки.

        Returns:
        ``True``, если воспроизведение началось."""
        try:
            self._load(sound)
        except (pygame.error, FileNotFoundError) as exc:
            self.error.emit(f"Не удалось загрузить «{sound.name}»: {exc}")
            return False

        if not self.allow_overlap:
            self.stop_all()
        elif sound.id in self._channels:
            self._stop_channel(sound.id, emit=False)

        self._volumes[sound.id] = sound.volume
        start = self._pending.pop(sound.id, 0.0)
        self._begin(sound, start)
        return sound.id in self._channels

    def _begin(self, sound: Sound, start: float, emit_started: bool = True) -> None:
        """Запустить звук с позиции `start` (секунды)."""
        snd = self._load(sound)
        duration = self._durations[sound.id]
        start = max(0.0, min(start, duration))
        if duration - start < 0.05:              # почти конец — начинаем сначала
            start = 0.0
        playable = self._slice(snd, start) if start > 0.001 else snd
        # Бесшовный цикл возможен только с начала трека; после перемотки сначала
        # доигрываем до конца, а на следующем проходе включаем цикл с начала.
        loops = -1 if (start <= 0.001 and self._effective_loop(sound)) else 0
        channel = playable.play(loops=loops)
        if channel is None:
            self.error.emit("Нет свободных аудиоканалов")
            return
        channel.set_volume(self._volumes.get(sound.id, sound.volume) * self.master_volume)
        self._channels[sound.id] = channel
        self._sounds[sound.id] = sound
        self._starts[sound.id] = (start, time.monotonic())
        self._looped[sound.id] = loops != 0
        self._loop_gen[sound.id] = self._loop_gen.get(sound.id, 0) + 1
        if emit_started:
            self.started.emit(sound.id)
        self.progress.emit(sound.id, start, duration)

    def stop(self, sound_id: str) -> None:
        """Останавливает звук по идентификатору."""
        self._pending.pop(sound_id, None)
        self._stop_channel(sound_id, emit=True)

    def stop_all(self) -> None:
        """Останавливает все воспроизводимые звуки."""
        for sound_id in list(self._channels):
            self.stop(sound_id)

    def is_playing(self, sound_id: str) -> bool:
        """Проверяет, воспроизводится ли звук сейчас."""
        return sound_id in self._channels

    def _stop_channel(self, sound_id: str, emit: bool) -> None:
        self._loop_gen[sound_id] = self._loop_gen.get(sound_id, 0) + 1
        channel = self._channels.pop(sound_id, None)
        self._starts.pop(sound_id, None)
        self._looped.pop(sound_id, None)
        self._sounds.pop(sound_id, None)
        if channel is not None:
            channel.stop()
        if emit:
            self.finished.emit(sound_id)

    # --- перемотка -------------------------------------------------------
    def position(self, sound_id: str) -> float:
        """Текущая позиция звука в секундах."""
        if sound_id not in self._channels:
            return self._pending.get(sound_id, 0.0)
        duration = self._durations.get(sound_id, 0.0)
        offset, started_at = self._starts[sound_id]
        elapsed = max(0.0, time.monotonic() - started_at)
        if self._looped.get(sound_id) and duration > 0.01:
            span = max(duration - offset, 0.01)
            return offset + elapsed % span
        position = offset + elapsed
        return min(position, duration) if duration else position

    def duration(self, sound_id: str) -> float:
        """Возвращает известную длительность звука в секундах."""
        return self._durations.get(sound_id, 0.0)

    def load_duration(self, sound: Sound) -> float:
        """Длительность звука (при необходимости загружает файл). 0 при ошибке."""
        if sound.id in self._durations:
            return self._durations[sound.id]
        try:
            self._load(sound)
        except (pygame.error, FileNotFoundError):
            return 0.0
        return self._durations.get(sound.id, 0.0)

    def seek(self, sound: Sound, fraction: float) -> None:
        """Перемотать звук на долю `fraction` (0..1) его длительности."""
        duration = self.load_duration(sound)
        if duration <= 0:
            return
        seconds = max(0.0, min(duration, fraction * duration))
        if duration - seconds < 0.05:           # перемотка в самый конец — останавливаемся
            self.stop(sound.id)
            self.progress.emit(sound.id, 0.0, duration)
            return
        if sound.id in self._channels:
            self._stop_channel(sound.id, emit=False)
            self._begin(sound, seconds, emit_started=False)
        else:
            self._pending[sound.id] = seconds
            self.progress.emit(sound.id, seconds, duration)

    # --- зацикливание ----------------------------------------------------
    def _effective_loop(self, sound: Sound) -> bool:
        return bool(self.loop_all or self._loop_override.get(sound.id, sound.is_loop))

    def set_loop(self, sound_id: str, loop: bool) -> None:
        """Включить/выключить цикл без перезапуска и без «прыжка» позиции."""
        self._loop_override[sound_id] = loop
        self._loop_gen[sound_id] = self._loop_gen.get(sound_id, 0) + 1
        if sound_id not in self._channels:
            return
        if loop:
            # Не трогаем текущий канал: звук доиграет и на следующем проходе
            # зациклится с начала трека (обычно мгновенно для коротких звуков).
            return
        if self._looped.get(sound_id):
            # Сейчас играет бесшовный цикл — даём доиграть текущий проход
            # и останавливаемся в его конце, не перезапуская звук.
            self._schedule_stop_after_cycle(sound_id)

    def _schedule_stop_after_cycle(self, sound_id: str) -> None:
        duration = self._durations.get(sound_id, 0.0)
        if duration <= 0:
            self.stop(sound_id)
            return
        remaining = max(0.0, duration - self.position(sound_id))
        gen = self._loop_gen.get(sound_id, 0)
        QTimer.singleShot(int(remaining * 1000) + 20, Qt.TimerType.PreciseTimer,
                          lambda: self._stop_after_cycle(sound_id, gen))

    def _stop_after_cycle(self, sound_id: str, gen: int) -> None:
        if self._loop_gen.get(sound_id) != gen:
            return                          # звук уже перезапустили/остановили
        if sound_id in self._channels:
            self.stop(sound_id)

    # --- громкость -------------------------------------------------------
    def set_master_volume(self, percent: int) -> None:
        """Устанавливает общую громкость в процентах (0–100)."""
        self.master_volume = max(0.0, min(1.0, percent / 100))
        for sound_id, channel in self._channels.items():
            channel.set_volume(self._volumes.get(sound_id, 1.0) * self.master_volume)

    def set_sound_volume(self, sound_id: str, volume: float) -> None:
        """Устанавливает громкость отдельного звука (0.0–1.0)."""
        self._volumes[sound_id] = max(0.0, min(1.0, volume))
        channel = self._channels.get(sound_id)
        if channel is not None:
            channel.set_volume(self._volumes[sound_id] * self.master_volume)

    # --- служебное -------------------------------------------------------
    def invalidate(self, sound_id: str) -> None:
        """Сбрасывает кэш звука (например, перед удалением)."""
        self.stop(sound_id)
        for store in (self._cache, self._durations, self._volumes,
                      self._loop_override, self._pending, self._loop_gen):
            store.pop(sound_id, None)

    def shutdown(self) -> None:
        """Останавливает все каналы и освобождает аудиосистему."""
        self.stop_all()
        pygame.mixer.quit()

    def _load(self, sound: Sound) -> "pygame.mixer.Sound":
        cached = self._cache.get(sound.id)
        if cached and cached[0] == sound.path:
            return cached[1]
        if not os.path.isfile(sound.path):
            raise FileNotFoundError(sound.path)
        snd = pygame.mixer.Sound(sound.path)
        self._cache[sound.id] = (sound.path, snd)
        self._durations[sound.id] = snd.get_length()
        return snd

    def _slice(self, snd: "pygame.mixer.Sound", start: float) -> "pygame.mixer.Sound":
        """Sound, начинающийся со смещения `start` секунд."""
        raw = snd.get_raw()
        offset = int(start * self._freq) * self._bytes_per_frame
        offset -= offset % self._bytes_per_frame
        offset = min(offset, len(raw))
        return pygame.mixer.Sound(buffer=raw[offset:])

    # --- таймер ----------------------------------------------------------
    def _poll(self) -> None:
        for sound_id, channel in list(self._channels.items()):
            if channel.get_busy():
                continue
            # Канал освободился: проход закончился.
            sound = self._sounds.get(sound_id)
            if sound is not None and self._effective_loop(sound):
                # Цикл включён (в т.ч. во время воспроизведения): начинаем
                # следующий проход с начала трека. Дальше он уже бесшовный.
                self._stop_channel(sound_id, emit=False)
                self._begin(sound, 0.0, emit_started=False)
                continue
            self._stop_channel(sound_id, emit=True)

        self._ticks += 1
        if self._ticks * self._timer.interval() >= PROGRESS_MS:
            self._ticks = 0
            for sound_id in list(self._channels):
                self.progress.emit(sound_id, self.position(sound_id),
                                   self._durations.get(sound_id, 0.0))
