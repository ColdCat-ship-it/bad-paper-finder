FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirement.txt /app/requirement.txt
RUN pip install --no-cache-dir -r /app/requirement.txt

COPY . /app

ENV PORT=8080
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8080"]
