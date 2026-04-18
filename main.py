import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"

# Перезапускаем через venv-интерпретатор, если он существует и не активен
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)
    sys.exit(1)  # не достигается, но для ясности

if not VENV_PYTHON.exists():
    print(
        "Ошибка: виртуальное окружение не найдено.\n"
        "Создайте его:\n"
        "  python3.13 -m venv .venv\n"
        "  source .venv/bin/activate\n"
        "  pip install -r project/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

sys.path.insert(0, str(ROOT))

# Подключаем вендорные зависимости только если пакет не установлен в окружении
VENDOR = ROOT / "project" / "vendor"
try:
    import ortools  # type: ignore[import]  # noqa: F401
except ModuleNotFoundError:
    if VENDOR.exists():
        sys.path.insert(0, str(VENDOR))

from project.main import main

if __name__ == "__main__":
    main()
