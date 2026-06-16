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

echo "==> Pulling latest backend code"
git fetch --quiet origin main
git reset --hard origin/main

echo "==> Updating Python deps"
# shellcheck disable=SC1091
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements-prod.txt

echo "==> Running Django migrate"
cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput
cd ..

echo "==> Publishing frontend build"
# El artifact lo subió rsync a $VPS_PATH/frontend-dist
# Lo movemos a la ubicación que sirve Nginx.
rm -rf frontend/dist/skill-bridge-front
mkdir -p frontend/dist
mv frontend-dist frontend/dist/skill-bridge-front

echo "==> Restarting services"
sudo systemctl restart skiltak-gunicorn
sudo systemctl restart skiltak-celery

echo "==> Health check"
sleep 2
sudo systemctl is-active skiltak-gunicorn
sudo systemctl is-active skiltak-celery

echo "==> Deploy OK"
