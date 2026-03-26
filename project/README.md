## Maintenance scheduling (CP-SAT)

Проект оптимизирует загрузку станков и минимизирует простои через CP-SAT (`ortools.sat.python.cp_model`).

### Запуск

1. Установите зависимости:
```bash
pip install -r project/requirements.txt
```

2. Запустите:
```bash
python -m project.main --time-limit 30
```

### Выход

- `schedule_output.csv` — таблица расписания.
- `gantt.html` — интерактивная диаграмма `Ghant Chart machine` (загрузка станков).
- `gantt_product.html` — интерактивная диаграмма `Ghant Chart product` (жизненный цикл продукта).

### Формат таблицы расписания

Колонки:
`product, assembly, part_number, process, machine, start_time, end_time, start_datetime, end_datetime, duration`

Время в минутах от нулевого момента планирования; также доступны календарные даты.

