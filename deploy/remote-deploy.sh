#!/usr/bin/env bash
# Se ejecuta DENTRO del VPS via SSH desde GitHub Actions.
# Asume que `VPS_PATH` viene exportada (default: /var/www/skiltak).
# El repo ya debe estar clonado en $VPS_PATH y el .env presente en $VPS_PATH/.env

set -euo pipefail

VPS_PATH="${VPS_PATH:-/var/www/skiltak}"
cd "$VPS_PATH"

# El repo es propiedad del usuario `skiltak` (creado por provision.sh) pero el
# deploy corre como root via SSH. Git rechaza operar si el dueño difiere.
git config --global --add safe.directory "$VPS_PATH"

echo "==> Pulling latest code"
git fetch --quiet origin main
git reset --hard origin/main

echo "==> Updating Python deps"
# shellcheck disable=SC1091
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements-prod.txt

# El build de Angular corre en el VPS para evitar el rsync runner→VPS que
# Hostinger filtra intermitentemente (TCP timeout en :22 sin patrón claro).
# Build local + git pull es 100% confiable; tradeoff: ~2 min más por deploy.
echo "==> Building Angular frontend"
cd frontend
npm ci --silent --no-audit --no-fund
NODE_OPTIONS="--max-old-space-size=2048" npm run build:prod
cd ..

echo "==> Running Django migrate + collectstatic"
cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput
cd ..

echo "==> Restarting services"
sudo systemctl restart skiltak-gunicorn
sudo systemctl restart skiltak-celery

echo "==> Health check"
sleep 2
sudo systemctl is-active skiltak-gunicorn
sudo systemctl is-active skiltak-celery

echo "==> Deploy OK"
