# Використовуємо офіційний образ Python
FROM python:3.9-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файл з залежностями
COPY requirements.txt .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту файлів додатку
COPY . .

# Відкриваємо порти
EXPOSE 3000
EXPOSE 5000

# Команда для запуску додатку
CMD ["python", "main.py"]
