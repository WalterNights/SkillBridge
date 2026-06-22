#!/usr/bin/env bash
# Provisión inicial del VPS para SkilTak.
# Idempotente: podés correrlo varias veces sin romper nada.
#
# Uso (como root en el VPS):
#   bash /var/www/skiltak/deploy/provision.sh

set -euo pipefail

APP_USER="skiltak"
APP_DIR="/var/www/skiltak"
DB_NAME="skiltak_db"
DB_USER="skiltak_user"
DOMAIN="skiltak.com"
API_DOMAIN="api.skiltak.com"

[[ $EUID -eq 0 ]] || { echo "Correr como root"; exit 1; }
[[ -f "$APP_DIR/.env" ]] || { echo "Falta $APP_DIR/.env"; exit 1; }

echo "==> 1/8 Instalando paquetes del sistema"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3-venv python3-pip python3-dev \
    build-essential libpq-dev postgresql-client \
    redis-server \
    poppler-utils tesseract-ocr \
    rsync

echo "==> 2/8 Habilitando Redis"
systemctl enable --now redis-server

echo "==> 3/8 Usuario de aplicación: $APP_USER"
id -u "$APP_USER" &>/dev/null || useradd --system --shell /bin/bash --home "$APP_DIR" "$APP_USER"
usermod -aG www-data "$APP_USER"
chown -R "$APP_USER":www-data "$APP_DIR"

echo "==> 4/8 Base de datos PostgreSQL"
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE ROLE $DB_USER LOGIN PASSWORD '$(grep ^DATABASE_PASSWORD= "$APP_DIR/.env" | cut -d= -f2-)';
   END IF;
END
\$\$;
SQL
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
  || sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo "==> 5/8 Virtualenv y dependencias Python"
sudo -u "$APP_USER" bash <<EOF
set -e
cd "$APP_DIR"
[[ -d venv ]] || python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements-prod.txt
EOF

echo "==> 6/8 Django migrate + collectstatic"
sudo -u "$APP_USER" bash <<EOF
set -e
cd "$APP_DIR/backend"
source ../venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
EOF

echo "==> 7/8 Servicios systemd"
install -m 644 "$APP_DIR/deploy/systemd/skiltak-gunicorn.socket"   /etc/systemd/system/
install -m 644 "$APP_DIR/deploy/systemd/skiltak-gunicorn.service"  /etc/systemd/system/
install -m 644 "$APP_DIR/deploy/systemd/skiltak-celery.service"    /etc/systemd/system/
install -m 644 "$APP_DIR/deploy/systemd/skiltak-celerybeat.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now \
    skiltak-gunicorn.socket skiltak-gunicorn.service \
    skiltak-celery.service skiltak-celerybeat.service

cat >/etc/sudoers.d/skiltak-deploy <<EOF
$APP_USER ALL=(root) NOPASSWD: /bin/systemctl restart skiltak-gunicorn, /bin/systemctl restart skiltak-celery, /bin/systemctl restart skiltak-celerybeat
EOF
chmod 440 /etc/sudoers.d/skiltak-deploy

echo "==> 8/8 Nginx"
install -m 644 "$APP_DIR/deploy/nginx/skiltak.com.conf"     /etc/nginx/sites-available/skiltak.com
install -m 644 "$APP_DIR/deploy/nginx/api.skiltak.com.conf" /etc/nginx/sites-available/api.skiltak.com

# Para el primer certbot necesitamos vhosts HTTP-only temporales.
# Comentamos los bloques :443 hasta tener cert.
if [[ ! -f /etc/letsencrypt/live/skiltak.com/fullchain.pem ]]; then
  echo "    [!] Falta cert para $DOMAIN. Corré después:"
  echo "        certbot --nginx -d $DOMAIN -d www.$DOMAIN -d $API_DOMAIN --redirect"
  # No enlazamos los sites aún para no romper Nginx.
else
  ln -sf /etc/nginx/sites-available/skiltak.com     /etc/nginx/sites-enabled/skiltak.com
  ln -sf /etc/nginx/sites-available/api.skiltak.com /etc/nginx/sites-enabled/api.skiltak.com
  nginx -t && systemctl reload nginx
fi

echo ""
echo "==> Provisión completa."
echo "    Próximo paso si es la primera vez:"
echo "    1) Apuntar DNS de skiltak.com, www.skiltak.com y api.skiltak.com a este VPS."
echo "    2) certbot --nginx -d skiltak.com -d www.skiltak.com -d api.skiltak.com --redirect"
echo "    3) ln -s sites-available/{skiltak.com,api.skiltak.com} sites-enabled/  && nginx -t && systemctl reload nginx"
