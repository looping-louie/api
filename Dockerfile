FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY migrations ./migrations

RUN mkdir -p runtime/db

EXPOSE 2000

HEALTHCHECK --interval=30s --start-period=10s --timeout=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:2000/openapi.json', timeout=3)"]

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "2000"]
