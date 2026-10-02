# GameCenter — serveur de direct (version légère : les semaines sont calculées par GitHub, voir .github/workflows)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY serveur.py gamecenter_source.html ./
COPY data/weeks /app/semaines_initiales
# Les semaines et la base des paris vivent dans /data : il FAUT y monter un disque persistant
# (Railway : « Volume » monté sur /data ; docker run : -v gamecenter-data:/data).
# À chaque mise à jour du dépôt (nouvelle semaine poussée par GitHub), les semaines nouvelles sont copiées sur /data.
# Pas d'instruction VOLUME ici : Railway la refuse.
ENV GC_DATA=/data GC_AUTOGEN=0 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "mkdir -p /data/weeks && cp -rn /app/semaines_initiales/. /data/weeks/ && exec uvicorn serveur:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
