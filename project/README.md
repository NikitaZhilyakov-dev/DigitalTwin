## Maintenance scheduling (CP-SAT)

Проект оптимизирует загрузку станков и минимизирует простои через CP-SAT (`ortools.sat.python.cp_model`).

Поддерживаются два интерфейса:
- **Streamlit** (`app.py`)
- **Desktop GUI на PyQt5** (`python -m project.main`)

---

## 1) Требования

- Python 3.9+ (рекомендуется запуск в `venv`)
- `pip`

---

## 2) Установка

Из корня репозитория:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r project/requirements.txt
```

---

## 3) Запуск через Streamlit

Из корня репозитория:

```bash
source .venv/bin/activate
streamlit run app.py
```

После запуска приложение обычно доступно по адресу:
- `http://localhost:8501`

---

## 4) Запуск через PyQt5

Из корня репозитория:

```bash
source .venv/bin/activate
python -m project.main
```

Важно:
- запускать нужно именно модулем `python -m project.main`, а не файлом `project/main.py`,
  иначе не сработают относительные импорты.

---

## 5) Входные данные

Входной CSV должен быть с разделителем `;`.

Ключевые колонки для оптимизации:
- `product`
- `assembly`
- `part_number`
- `process_sequence`
- `process`
- `machine`
- `processing_hours`
- `working_hours_per_day`
- `assigned_staff`
- `maintenance_between_operations`
- `maintenance_time_hours`

---

## 6) Результат оптимизации

Основная таблица расписания содержит колонки:

`product, assembly, part_number, process, machine, start_time, end_time, start_datetime, end_datetime, duration`

Где:
- `start_time`, `end_time` — время в рабочих минутах от нулевой точки планирования
- `start_datetime`, `end_datetime` — календарные дата/время для визуализации и анализа

---

## 7) Возможные проблемы

### `No module named streamlit`

```bash
source .venv/bin/activate
pip install -r project/requirements.txt
```

### Ошибка PyQt5 / Qt plugin (`cocoa`) на macOS

- Запускайте через `python -m project.main` внутри `.venv`.
- В проекте уже есть настройка путей Qt-плагинов в `project/main.py` (`_configure_qt_plugin_paths()`).

