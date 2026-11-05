# Документация Soundboard

Исходники документации в формате reStructuredText для Sphinx.
Генерация API выполняется автоматически из docstrings
(`sphinx.ext.autodoc` + `sphinx.ext.napoleon`).

## Сборка HTML

Из папки `Документация\Sphinx`:

```bat
build_docs.bat
```

Или вручную:

```bat
..\..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\..\.venv\Scripts\python.exe -m sphinx -b html . ..\HTML
```

Результат: `Документация\HTML\index.html`.

## Структура

- `index.rst` — титульная страница и оглавление;
- `architecture.rst` — слои, паттерны, модель данных;
- `functionality.rst` — функции и особенности;
- `user_manual.rst` — руководство пользователя;
- `developer_manual.rst` — руководство разработчика;
- `examples.rst` — примеры и сценарии;
- `api.rst` — автоматический API-справочник;
- `support.rst` — поддержка, бэклог, известные ограничения;
- `changelog.rst` — история версий.

## Добавление модуля в API

Добавьте в `api.rst`:

```rst
.. automodule:: имя_модуля
   :members:
   :show-inheritance:
```

и убедитесь, что у модуля, классов и публичных функций есть docstrings
в стиле Google.
