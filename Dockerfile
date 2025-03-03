FROM python:3.11-slim

COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
#CMD ["uvicorn", "blogueandoAndoAPI.main:app", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]
CMD ["uvicorn", "blogueandoAndoAPI.main:app", "--host", "0.0.0.0", "--port", "8000"]