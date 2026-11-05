Примеры использования
=====================

Ниже собраны типовые сценарии работы с приложением и фрагменты кода,
которые помогают понять устройство проекта.

Пользовательские сценарии
-------------------------

**Сценарий 1. Подготовка к мероприятию**

#. Добавьте 5–10 звуков через «+ Добавить звук» (WAV/OGG/MP3).
#. Назначьте каждому звуку клавишу: правой кнопкой по карточке →
   «Назначить клавишу…» → нажмите нужную клавишу → «Сохранить».
#. Настройте общую громкость в верхней панели.
#. Для фоновой музыки включите ⟲ на карточке.
#. Закройте программу — библиотека сохранится.

**Сценарий 2. Проведение мероприятия**

#. Запускайте звуки клавишами или кликами по карточкам.
#. Перематывайте трек и меняйте громкость прямо на карточке.
#. При ошибке нажмите ``Esc`` или «Стоп все» — звук мгновенно прекратится.
#. Включённый цикл не прерывает трек при нажатии ⟲ — он доигрывает
   и начинается сначала.

**Сценарий 3. Управление коллекцией**

#. Откройте «Библиотеку».
#. Найдите звук через поиск или выберите категорию.
#. Удалите ненужные звуки через контекстное меню (с подтверждением).

Работа с моделью из кода
------------------------

.. code-block:: python

   import sys
   from pathlib import Path

   sys.path.insert(0, str(Path("Код").resolve()))

   from config_repository import ConfigRepository
   from models import Sound
   from sound_manager import SoundManager

   manager = SoundManager(ConfigRepository(Path("config.json")))
   sound = manager.add(name="Аплодисменты", path="sounds/applause.wav")
   print(sound.id, sound.hotkey, sound.category)

   manager.update(sound.id, silent=True, volume=0.8)
   manager.save()

Сериализация звука:

.. code-block:: python

   from models import Sound

   sound = Sound(name="Смех", path="laugh.mp3", hotkey="q")
   data = sound.to_dict()
   restored = Sound.from_dict(data)
   assert restored.name == "Смех"

Фрагмент настройки аудиодвижка:

.. code-block:: python

   from audio_engine import AudioEngine

   engine = AudioEngine.instance()
   engine.set_master_volume(70)
   engine.set_sound_volume("sound-id", 0.5)
   engine.set_loop("sound-id", True)
   engine.seek(sound, 0.5)   # перемотка на половину длительности

Настройки приложения
--------------------

.. code-block:: python

   settings = {
       "master_volume": 70,
       "allow_overlap": True,
       "loop_all": False,
       "remember_settings": True,
       "global_hotkeys": False,
   }

   manager.set_settings(**settings)

Полный список настроек и их назначение — в разделе
:doc:`functionality` и :doc:`user_manual`.
