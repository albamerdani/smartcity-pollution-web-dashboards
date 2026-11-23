FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/ /app/
COPY ml_forecast/ /ml_forecast/
RUN mkdir -p /app/staticfiles
EXPOSE 8000
CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]
