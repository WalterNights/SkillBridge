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

echo "==> Syncing nginx configs"
# Los .conf del repo son la fuente de verdad. Si difieren de los
# instalados, copiar, validar con `nginx -t` y hacer reload (sin downtime).
# Si `nginx -t` falla, abortamos el deploy antes de tumbar el servidor.
#
# Compatibilidad de nombres: el repo usa `<name>.conf` (convención
# genérica de nginx en conf.d/), pero el VPS usa la convención Debian
# `sites-available/<name>` + symlink desde `sites-enabled/<name>`,
# SIN extensión. Detectamos cuál nombre existe en el server y copiamos
# a ese. Si no existe ninguno (primera instalación), asumimos convención
# Debian sin `.conf` y creamos + enlazamos.
NGINX_CHANGED=0
for conf in deploy/nginx/*.conf; do
    stem="$(basename "$conf" .conf)"  # api.skiltak.com.conf → api.skiltak.com
    if [ -f "/etc/nginx/sites-available/$stem" ]; then
        dest="/etc/nginx/sites-available/$stem"        # Debian sin .conf
    elif [ -f "/etc/nginx/sites-available/$stem.conf" ]; then
        dest="/etc/nginx/sites-available/$stem.conf"   # con .conf
    else
        # Primera vez: asumimos convención Debian sin .conf.
        dest="/etc/nginx/sites-available/$stem"
        echo "  [+] $stem: instalando por primera vez"
    fi
    if ! sudo cmp -s "$conf" "$dest" 2>/dev/null; then
        echo "  [+] $stem cambio — copiando a $dest"
        sudo cp "$conf" "$dest"
        # Enable si aun no lo esta.
        if [ ! -e "/etc/nginx/sites-enabled/$(basename "$dest")" ]; then
            sudo ln -s "$dest" "/etc/nginx/sites-enabled/$(basename "$dest")"
            echo "  [+] $stem enabled"
        fi
        NGINX_CHANGED=1
    fi
done
if [ "$NGINX_CHANGED" = "1" ]; then
    echo "==> Validando nginx config"
    if sudo nginx -t; then
        sudo systemctl reload nginx
        echo "  [OK] nginx recargado"
    else
        echo "  [!] nginx -t fallo — abortando deploy sin recargar"
        exit 1
    fi
fi

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
