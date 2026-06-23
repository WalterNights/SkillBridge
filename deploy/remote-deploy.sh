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

# Chromium para Playwright. `playwright install chromium` es
# idempotente (skip si ya está instalado). El `|| true` evita que
# tumbe el deploy si falla — los scrapers que lo necesitan degradan
# a vacío sin romper a los demás.
echo "==> Ensuring Playwright Chromium is installed"
python -m playwright install chromium 2>/dev/null || \
    echo "  [!] playwright chromium install failed, run manually if Magneto/Indeed scrapers are needed"

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
# Beat es opcional — si el unit no está instalado, no fallar el deploy.
# El usuario corre el provision.sh una vez para enable+start el unit.
if systemctl list-unit-files skiltak-celerybeat.service &>/dev/null; then
    sudo systemctl restart skiltak-celerybeat || true
fi

echo "==> Health check"
sleep 2
sudo systemctl is-active skiltak-gunicorn
sudo systemctl is-active skiltak-celery

echo "==> Deploy OK"
