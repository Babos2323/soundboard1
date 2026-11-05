"""HotkeyManager: глобальные горячие клавиши (pynput) для Windows.

Клавиши работают, когда окно приложения не в фокусе; при свёрнутом окне
программа продолжает реагировать на назначенные клавиши.
"""
from PyQt6.QtCore import QObject, pyqtSignal

import keys


class HotkeyManager(QObject):
    """Перехват глобальных горячих клавиш через pynput."""
    pressed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._listener = None

    @property
    def active(self) -> bool:
        """Возвращает ``True``, если перехват клавиш запущен."""
        return self._listener is not None

    def start(self) -> bool:
        """Запускает слушатель клавиатуры.

        Returns:
        ``True`` при успешном запуске (pynput доступен)."""
        if self._listener is not None:
            return True
        try:
            from pynput import keyboard
            self._listener = keyboard.Listener(on_press=self._on_press)
            self._listener.daemon = True
            self._listener.start()
            return True
        except Exception:
            self._listener = None
            return False

    def stop(self) -> None:
        """Останавливает слушатель клавиатуры."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _on_press(self, key) -> None:
        name = keys.from_pynput(key)
        if name:
            self.pressed.emit(name)   # сигнал безопасно доставляется в поток Qt
