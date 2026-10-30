# Entorno reproducible del proyecto. Las versiones salen de requirements.lock (las que se usaron al desarrollar).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Código y parámetros. Los datos (data/) y las salidas (outputs/) NO van en la imagen: se montan como volúmenes.
COPY config.yaml ./
COPY src ./src
COPY notebooks ./notebooks
COPY docs ./docs
COPY scripts ./scripts

CMD ["bash", "scripts/run_all.sh"]
