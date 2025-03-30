# Вказуємо базовий образ Python
FROM python:3.11-slim

# Оновлення списку та встановлення ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Копіюємо requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код
COPY . /app

# Встановлюємо робочий каталог
WORKDIR /app

# Команда для запуску бота
CMD ["python", "voice.py"]
