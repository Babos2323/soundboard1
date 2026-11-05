"""Диалоги: добавление звука, назначение клавиши, настройки, библиотека."""
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSlider, QVBoxLayout,
)

import keys
from models import DEFAULT_CATEGORY
from sound_manager import SoundManager

AUDIO_FILTER = "Аудио (*.wav *.ogg *.mp3);;Все файлы (*)"
AUDIO_EXT = {".wav", ".ogg", ".mp3"}


def _button(text: str, name: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setAutoDefault(False)
    if name:
        btn.setObjectName(name)
    return btn


def _ok_cancel(ok_text: str, dialog: QDialog, ok_slot) -> QHBoxLayout:
    row = QHBoxLayout()
    ok, cancel = _button(ok_text, "green"), _button("Отмена", "red")
    ok.clicked.connect(ok_slot)
    cancel.clicked.connect(dialog.reject)
    row.addWidget(ok, 1)
    row.addWidget(cancel, 1)
    return row


class HotkeyEdit(QLineEdit):
    """Поле, которое запоминает нажатую клавишу. Backspace/Delete — очистить."""

    def __init__(self, placeholder: str = "Нажмите клавишу для назначения", key: str = ""):
        super().__init__()
        self.setObjectName("hotkeyEdit")
        self.setReadOnly(True)
        self.setPlaceholderText(placeholder)
        self.key = ""
        self.set_key(key)

    def set_key(self, key: str) -> None:
        """Устанавливает и отображает назначенную клавишу."""
        self.key = key
        self.setText(keys.pretty(key))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.set_key("")
            return
        key = keys.from_qt_event(event)
        if key and key != "esc":
            self.set_key(key)
        else:
            event.ignore()      # Esc/Enter обрабатывает сам диалог


class AddSoundDialog(QDialog):
    """Диалог добавления нового звука в библиотеку."""
    def __init__(self, manager: SoundManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.path = ""
        self.setWindowTitle("Добавление звука")
        self.setAcceptDrops(True)
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        title = QLabel("Добавление звука")
        title.setStyleSheet("font-size: 18px;")
        hint = QLabel("Выберите аудиофайл и настройте параметры звука.")
        root.addWidget(title)
        root.addWidget(hint)

        zone = QFrame()
        zone.setObjectName("dropZone")
        zl = QVBoxLayout(zone)
        self.file_label = QLabel("Перетащите файл сюда или выберите")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pick = _button("Выбрать файл", "green")
        pick.clicked.connect(self.choose_file)
        zl.addWidget(self.file_label)
        zl.addWidget(pick, alignment=Qt.AlignmentFlag.AlignCenter)
        zone.setMinimumHeight(110)
        root.addWidget(zone)

        root.addWidget(QLabel("Название звука"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Новый звук")
        root.addWidget(self.name_edit)

        root.addWidget(QLabel("Категория"))
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(sorted({DEFAULT_CATEGORY, *manager.categories()}))
        root.addWidget(self.category)

        root.addWidget(QLabel("Горячая клавиша (если пусто — назначится автоматически)"))
        self.hotkey = HotkeyEdit()
        root.addWidget(self.hotkey)

        root.addLayout(_ok_cancel("Добавить", self, self.validate))

    # --- файл -----------------------------------------------------------
    def choose_file(self):
        """Открывает диалог выбора аудиофайла."""
        path, _ = QFileDialog.getOpenFileName(self, "Выберите аудиофайл", str(Path.home()), AUDIO_FILTER)
        if path:
            self.set_path(path)

    def set_path(self, path: str):
        """Заполняет путь к файлу и подставляет название из имени файла."""
        self.path = path
        self.file_label.setText(os.path.basename(path))
        if not self.name_edit.text():
            self.name_edit.setText(Path(path).stem)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in AUDIO_EXT:
                self.set_path(path)
                break

    # --- результат --------------------------------------------------------
    def validate(self):
        """Проверяет введённые данные и закрывает диалог при успехе."""
        if not self.path or not os.path.isfile(self.path):
            QMessageBox.warning(self, "Звук", "Выберите аудиофайл (WAV, OGG или MP3).")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Звук", "Введите название звука.")
            return
        other = self.manager.find_by_hotkey(self.hotkey.key)
        if other:
            QMessageBox.warning(self, "Клавиша занята",
                                f"Клавиша {keys.pretty(self.hotkey.key)} уже назначена звуку «{other.name}».")
            return
        self.accept()

    def values(self) -> dict:
        """Возвращает значения полей диалога в виде словаря."""
        return {"name": self.name_edit.text().strip(), "path": self.path,
                "hotkey": self.hotkey.key,
                "category": self.category.currentText().strip() or DEFAULT_CATEGORY}


class HotkeyDialog(QDialog):
    """Диалог назначения горячей клавиши существующему звуку."""
    def __init__(self, manager: SoundManager, sound, parent=None):
        super().__init__(parent)
        self.manager, self.sound = manager, sound
        self.setWindowTitle("Назначение клавиши")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        title = QLabel("Назначение клавиши")
        title.setStyleSheet("font-size: 18px;")
        root.addWidget(title)
        root.addWidget(QLabel(f"Звук: {sound.name}"))
        root.addWidget(QLabel(f"Текущая клавиша: {keys.pretty(sound.hotkey) or '—'}"))
        note = QLabel("Нажмите новую клавишу на клавиатуре (Backspace — убрать клавишу)")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(note)
        self.edit = HotkeyEdit("Ожидание нажатия…", sound.hotkey)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.edit)
        root.addLayout(_ok_cancel("Сохранить", self, self.validate))
        self.edit.setFocus()

    def validate(self):
        """Проверяет, что клавиша не занята другим звуком."""
        other = self.manager.find_by_hotkey(self.edit.key, exclude_id=self.sound.id)
        if other:
            QMessageBox.warning(self, "Клавиша занята",
                                f"Клавиша {keys.pretty(self.edit.key)} уже назначена звуку «{other.name}».")
            return
        self.accept()

    def key(self) -> str:
        """Возвращает выбранную пользователем клавишу."""
        return self.edit.key


class SettingsDialog(QDialog):
    """Диалог настроек воспроизведения и горячих клавиш."""
    def __init__(self, settings: dict, open_hotkeys, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)
        title = QLabel("Настройки")
        title.setStyleSheet("font-size: 18px;")
        root.addWidget(title)
        root.addWidget(QLabel("Настройка воспроизведения звуков"))

        # звук
        box, bl = self._group("Звук")
        row = QHBoxLayout()
        row.addWidget(QLabel("Общая громкость"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(settings["master_volume"]))
        self.value_label = QLabel()
        self.slider.valueChanged.connect(lambda v: self.value_label.setText(f"{v}%"))
        self.value_label.setText(f"{self.slider.value()}%")
        row.addWidget(self.slider, 1)
        row.addWidget(self.value_label)
        bl.addLayout(row)
        root.addWidget(box)

        # поведение
        box, bl = self._group("Поведение звуков")
        self.overlap = QCheckBox("Разрешить одновременное воспроизведение")
        self.loop_all = QCheckBox("Зацикливать звуки")
        self.remember = QCheckBox("Запоминать настройки")
        self.global_keys = QCheckBox("Горячие клавиши работают, когда окно не в фокусе")
        self.overlap.setChecked(settings["allow_overlap"])
        self.loop_all.setChecked(settings["loop_all"])
        self.remember.setChecked(settings["remember_settings"])
        self.global_keys.setChecked(settings["global_hotkeys"])
        for cb in (self.overlap, self.loop_all, self.remember, self.global_keys):
            bl.addWidget(cb)
        root.addWidget(box)

        # горячие клавиши
        box, bl = self._group("Горячие клавиши")
        row = QHBoxLayout()
        row.addWidget(QLabel("Управление клавишами"))
        row.addStretch()
        configure = _button("Настроить", "green")
        configure.clicked.connect(open_hotkeys)
        row.addWidget(configure)
        bl.addLayout(row)
        root.addWidget(box)

        root.addLayout(_ok_cancel("Сохранить", self, self.accept))

    @staticmethod
    def _group(title: str):
        box = QFrame()
        box.setObjectName("group")
        layout = QVBoxLayout(box)
        head = QLabel(f"<b>{title}</b>")
        layout.addWidget(head)
        return box, layout

    def values(self) -> dict:
        """Возвращает настройки из полей диалога."""
        return {"master_volume": self.slider.value(),
                "allow_overlap": self.overlap.isChecked(),
                "loop_all": self.loop_all.isChecked(),
                "remember_settings": self.remember.isChecked(),
                "global_hotkeys": self.global_keys.isChecked()}


class HotkeysListDialog(QDialog):
    """Управление клавишами: выбрать звук и открыть окно «Назначение клавиши»."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main = main_window
        self.setWindowTitle("Управление клавишами")
        self.setMinimumWidth(440)

        root = QVBoxLayout(self)
        title = QLabel("Управление клавишами")
        title.setStyleSheet("font-size: 18px;")
        root.addWidget(title)
        root.addWidget(QLabel("Выберите звук и нажмите «Назначить клавишу»."))
        self.list = QListWidget()
        self.list.setMinimumHeight(260)
        self.list.itemDoubleClicked.connect(lambda _: self.assign())
        root.addWidget(self.list)

        row = QHBoxLayout()
        assign = _button("Назначить клавишу", "green")
        assign.clicked.connect(self.assign)
        close = _button("Закрыть", "red")
        close.clicked.connect(self.accept)
        row.addWidget(assign, 1)
        row.addWidget(close, 1)
        root.addLayout(row)
        self.refresh()

    def refresh(self):
        """Обновляет список звуков и назначенных им клавиш."""
        row = self.list.currentRow()
        self.list.clear()
        for sound in self.main.manager.sounds:
            item = QListWidgetItem(f"{sound.name}      [{keys.pretty(sound.hotkey) or '—'}]")
            item.setData(Qt.ItemDataRole.UserRole, sound.id)
            self.list.addItem(item)
        if 0 <= row < self.list.count():
            self.list.setCurrentRow(row)

    def assign(self):
        """Открывает диалог назначения клавиши для выбранного звука."""
        item = self.list.currentItem()
        if item is None:
            QMessageBox.information(self, "Клавиши", "Сначала выберите звук в списке "
                                    "(если список пуст — добавьте звук).")
            return
        self.main.change_hotkey(item.data(Qt.ItemDataRole.UserRole))
        self.refresh()
