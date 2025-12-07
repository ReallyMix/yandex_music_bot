"""
Точка входа для запуска бота (альтернативная)
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import main

if __name__ == "__main__":
    asyncio.run(main())
