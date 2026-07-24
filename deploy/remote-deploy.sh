#!/usr/bin/env bash
# Se ejecuta DENTRO del VPS via SSH desde GitHub Actions.
# Asume que `VPS_PATH` viene exportada (default: /var/www/skiltak).
# El repo ya debe estar clonado en $VPS_PATH.
#
# `.env` se materializa desde el GitHub Secret `ENV_FILE` en cada deploy (ver
# el step "Run remote deploy script" en .github/workflows/deploy.yml). El
# archivo del VPS deja de ser fuente de verdad — la única fuente ahora es el
# secret. Si `ENV_FILE` no está seteado, respetamos el `.env` que ya viva en
# el VPS (fallback para primer bootstrap o deploys manuales).

set -euo pipefail

VPS_PATH="${VPS_PATH:-/var/www/skiltak}"
cd "$VPS_PATH"

# ────────────────────────────────────────────────────────────────────────────
# 0. Materializar .env desde ENV_FILE_B64 (source-of-truth es el GitHub Secret).
#    Llega base64-encoded desde el workflow para sobrevivir el shell escape
#    del SSH inline (el contenido literal tiene newlines/quotes/`=`/`$`).
# ────────────────────────────────────────────────────────────────────────────
if [ -n "${ENV_FILE_B64:-}" ]; then
  echo "==> Syncing .env from GitHub Secret ENV_FILE"
  # Backup del .env anterior antes de sobreescribir, por si hay que auditar
  # qué cambió entre deploys o hacer rollback manual.
  if [ -f .env ]; then
    cp .env ".env.bak.$(date +%Y%m%d_%H%M%S)"
    # Retener solo los últimos 5 backups para no llenar el disco.
    ls -t .env.bak.* 2>/dev/null | tail -n +6 | xargs -r rm -f
  fi
  printf '%s' "$ENV_FILE_B64" | base64 -d > .env
  chmod 600 .env
  echo "  [OK] .env actualizado ($(wc -l < .env) líneas)"
else
  echo "==> ENV_FILE_B64 no seteado; conservando .env existente en el VPS"
  [ -f .env ] || { echo "  [!] Falta $VPS_PATH/.env y ENV_FILE_B64 no vino en el secret. Abortando."; exit 1; }
fi

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

echo "==> Syncing systemd units"
# provision.sh instala los units en el primer bootstrap, pero después
# ningún cambio del repo (por ejemplo `--timeout` de gunicorn) llegaba
# al VPS sin correr provision.sh a mano. Igual que con nginx, dejamos
# que el repo sea la fuente de verdad: si difiere, copiar y daemon-reload
# antes del restart de más abajo — así el restart ya toma el unit nuevo.
SYSTEMD_CHANGED=0
for unit in deploy/systemd/*.service deploy/systemd/*.socket; do
    [ -f "$unit" ] || continue
    name="$(basename "$unit")"
    dest="/etc/systemd/system/$name"
    if ! sudo cmp -s "$unit" "$dest" 2>/dev/null; then
        echo "  [+] $name cambio — copiando a $dest"
        sudo install -m 644 "$unit" "$dest"
        SYSTEMD_CHANGED=1
    fi
done
if [ "$SYSTEMD_CHANGED" = "1" ]; then
    sudo systemctl daemon-reload
    echo "  [OK] systemd daemon-reload"
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

# ────────────────────────────────────────────────────────────────────────────
# End-to-end CORS smoke test.
#
# Nace del incidente de julio 2026: se agregó `https://skiltak.com` al
# CORS_ALLOWED_ORIGINS del .env.prod local pero nadie hizo el scp manual al
# VPS, y prod quedó rechazando los requests con "No 'Access-Control-Allow-
# Origin' header" — que el navegador reporta como error de URL pero es
# CORS. Automatizamos la detección: si el backend no devuelve el header CORS
# esperado para el origin del frontend, fallamos el deploy antes de que el
# usuario lo note.
#
# El check usa un preflight OPTIONS (no requiere auth y siempre debería
# devolver headers CORS si el origin está permitido). Testear cada origin
# permitido asegura que si mañana se agrega un dominio y alguien se olvida
# de propagarlo, el deploy también falla.
# ────────────────────────────────────────────────────────────────────────────
echo "==> CORS smoke test"
API_HOST="${API_HOST:-https://api.skiltak.com}"
CORS_TEST_PATH="${CORS_TEST_PATH:-/api/jobs/jobs/}"
# Lee CORS_ALLOWED_ORIGINS del .env recién sincronizado y prueba cada uno.
CORS_LIST="$(grep -E '^CORS_ALLOWED_ORIGINS=' .env | cut -d= -f2- | tr -d '"')"
if [ -z "$CORS_LIST" ]; then
  echo "  [!] CORS_ALLOWED_ORIGINS vacío en .env — smoke test skip (pero deberías setearlo)"
else
  FAILED_ORIGINS=""
  IFS=',' read -ra ORIGINS <<< "$CORS_LIST"
  for origin in "${ORIGINS[@]}"; do
    origin="$(echo "$origin" | xargs)"  # trim whitespace
    [ -z "$origin" ] && continue
    # curl -o /dev/null tira el body, -D - imprime headers a stdout para grep.
    headers="$(curl -fsS -o /dev/null -D - -X OPTIONS \
      -H "Origin: $origin" \
      -H "Access-Control-Request-Method: GET" \
      "$API_HOST$CORS_TEST_PATH" 2>&1 || true)"
    if echo "$headers" | grep -qiE "^access-control-allow-origin:\s*$origin"; then
      echo "  [OK] $origin"
    else
      echo "  [FAIL] $origin — respuesta sin header CORS esperado"
      FAILED_ORIGINS="$FAILED_ORIGINS $origin"
    fi
  done
  if [ -n "$FAILED_ORIGINS" ]; then
    echo "  [!] Los siguientes origins están declarados en .env pero prod los rechaza:"
    echo "     $FAILED_ORIGINS"
    echo "     Revisá CORS_ALLOWED_ORIGINS y CSRF_TRUSTED_ORIGINS. Abortando el deploy."
    exit 1
  fi
fi

echo "==> Deploy OK"
