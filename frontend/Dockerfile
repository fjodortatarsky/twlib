FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости системы (если нужны для компиляции пакетов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir gunicorn

COPY . .

# Создаем non-root пользователя для безопасности
RUN useradd -m -r appuser && \
    chown -R appuser:appuser /app
USER appuser

# Переменные окружения
ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Порт, который слушает контейнер (документация)
EXPOSE 5000

# Healthcheck
#HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Запуск через Gunicorn (4 воркера, привязка к 0.0.0.0)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "wsgi:app"]

