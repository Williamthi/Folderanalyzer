FROM python:3.13.2-slim

WORKDIR /app

RUN apt update && apt install -y libmagic-dev && rm -rf /var/lib/apt/lists/*

COPY docker-requirements.txt .
RUN pip install --no-cache-dir -r docker-requirements.txt

COPY . .
EXPOSE 5000
CMD ["python3", "web_app.py"]
