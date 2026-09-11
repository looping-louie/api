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

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "2000"]