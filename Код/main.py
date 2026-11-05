"""Soundboard — точка входа. Запуск: python main.py"""
import sys
from pathlib import Path

from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWidgets import QApplication, QMessageBox

from theme import STYLE


def resource_path(relative: str) -> Path:
    """Путь к ресурсу и в исходниках, и внутри собранного PyInstaller бинарника."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).parent
    return base / relative


def main() -> int:
    """Создаёт приложение, применяет тему и запускает главное окно."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")                 # одинаковый вид на всех Windows-машинах
    app.setApplicationName("Soundboard")
    app.setApplicationDisplayName("Soundboard")
    icon_path = resource_path("assets/icon.png")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#0f1116"), (QPalette.ColorRole.WindowText, "#f2f2f2"),
        (QPalette.ColorRole.Base, "#15181e"), (QPalette.ColorRole.AlternateBase, "#1a1d24"),
        (QPalette.ColorRole.Text, "#f2f2f2"), (QPalette.ColorRole.Button, "#24272f"),
        (QPalette.ColorRole.ButtonText, "#f2f2f2"), (QPalette.ColorRole.Highlight, "#0a7a56"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"), (QPalette.ColorRole.ToolTipBase, "#15181e"),
        (QPalette.ColorRole.ToolTipText, "#f2f2f2"),
    ):
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)

    try:
        from audio_engine import AudioEngine
        engine = AudioEngine.instance()
    except Exception as exc:                      # нет звукового устройства и т.п.
        QMessageBox.critical(None, "Soundboard", f"Не удалось запустить аудиодвижок:\n{exc}")
        return 1

    from config_repository import ConfigRepository
    from hotkey_manager import HotkeyManager
    from main_window import MainWindow
    from sound_manager import SoundManager

    manager = SoundManager(ConfigRepository.instance())
    window = MainWindow(manager, engine, HotkeyManager())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
