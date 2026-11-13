# Image de l'outil (D-20). Construire depuis la RACINE du dépôt : docker build -f bulletin/Dockerfile .
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 OUTIL_COOKIE_SECURISE=1
WORKDIR /srv
COPY bulletin/requirements.txt bulletin/requirements.txt
RUN pip install --no-cache-dir -r bulletin/requirements.txt
COPY data/prix/wfp_cmr_panier.csv data/prix/wfp_cmr_panier.csv
COPY bulletin/coeur bulletin/coeur
COPY bulletin/modeles bulletin/modeles
COPY bulletin/web bulletin/web
RUN useradd --create-home outil && mkdir -p bulletin/instance && chown -R outil /srv
USER outil
CMD gunicorn --chdir bulletin/web app:server --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 180
