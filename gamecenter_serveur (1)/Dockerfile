# GameCenter — serveur de direct (version légère : les semaines sont calculées par GitHub, voir .github/workflows)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY serveur.py gamecenter_source.html ./
# moteur/histoire.py : histoire de la ligue, records, carrières (bloc 2, étape 5 ; bibliothèque standard seulement)
COPY moteur ./moteur
COPY static ./static
COPY audio ./audio
COPY data/weeks /app/semaines_initiales
COPY data/exhibitions ./data/exhibitions
# Les semaines et la base des paris vivent dans /data : il FAUT y monter un disque persistant
# (Railway : « Volume » monté sur /data ; docker run : -v gamecenter-data:/data).
# À chaque démarrage, les semaines du dépôt remplacent celles de /data (le dépôt fait foi ; la base des paris n'est pas touchée).
# Pas d'instruction VOLUME ici : Railway la refuse.
ENV GC_DATA=/data GC_AUTOGEN=0 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "mkdir -p /data/weeks && for d in /app/semaines_initiales/week_*; do rm -rf /data/weeks/$(basename $d) && cp -r $d /data/weeks/; done && exec uvicorn serveur:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
