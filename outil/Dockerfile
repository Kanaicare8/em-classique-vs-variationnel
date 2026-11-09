# Image de l'outil (D-20). Construire depuis la RACINE du dépôt : docker build -f outil/Dockerfile .
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 OUTIL_COOKIE_SECURISE=1
WORKDIR /srv
COPY outil/requirements.txt outil/requirements.txt
RUN pip install --no-cache-dir -r outil/requirements.txt
COPY data/prix/wfp_cmr_panier.csv data/prix/wfp_cmr_panier.csv
COPY outil/coeur outil/coeur
COPY outil/modeles outil/modeles
COPY outil/web outil/web
RUN useradd --create-home outil && mkdir -p outil/instance && chown -R outil /srv
USER outil
CMD gunicorn --chdir outil/web app:server --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 180
