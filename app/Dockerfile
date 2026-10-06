FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

Env Enviorment=docker
Env APP_Version=1.0.0

ENTRYPOINT ["gunicorn"]

CMD ["--bind", "0.0.0.0:5000", "src.app:app"]
