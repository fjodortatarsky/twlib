"""Точка входа приложения «Труды учёных».

Запуск:
    python run.py

По умолчанию: http://127.0.0.1:5000
Для разработки включён debug-режим (автоперезагрузка при изменении кода).
"""

from app import create_app


def main():
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)


if __name__ == "__main__":
    main()
