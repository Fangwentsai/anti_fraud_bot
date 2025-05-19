FROM python:3.9-slim

WORKDIR /app

COPY anti-fraud-clean/ /app/
COPY linebot-anti-fraud/.env /app/../linebot-anti-fraud/.env

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python", "app.py"] 