# Deploy de SkilTak en VPS

Despliegue en `skiltak.com` (Hostinger VPS Ubuntu 25.10) compartiendo recursos con el proyecto `optimads.online` sin pisarlo.

## Arquitectura

```
Internet ──► Nginx ──┬─► skiltak.com / www.skiltak.com  (estáticos Angular)
                     │
                     └─► api.skiltak.com  ──► Gunicorn (unix socket) ──► Django
                                                 │
                                                 ├─► PostgreSQL (DB: skiltak_db)
                                                 └─► Redis (DB 0/1 broker+cache)

Celery worker (systemd) ──► Redis ◄──► Django
```

## Primer despliegue (one-shot)

Hay que hacer esto **una sola vez** para preparar el VPS.

### 1. DNS

Configurar registros A para apuntar al VPS:

| Host | Tipo | Valor |
|---|---|---|
| `skiltak.com` | A | `72.61.75.116` |
| `www.skiltak.com` | A | `72.61.75.116` |
| `api.skiltak.com` | A | `72.61.75.116` |

Esperar a que propague (`dig +short skiltak.com` debe devolver la IP del VPS).

### 2. Clonar el repo en el VPS

```bash
ssh root@72.61.75.116
mkdir -p /var/www/skiltak
git clone https://github.com/WalterNights/SkillBridge.git /var/www/skiltak
```

### 3. Crear el `.env` de producción

En tu máquina local tenés [`.env.prod`](../.env.prod) (gitignored) con los valores de producción ya listos.
Copialo al VPS:

```bash
# Desde tu máquina local (PowerShell):
scp -i $env:USERPROFILE\.ssh\id_ed25519_skiltak .env.prod root@72.61.75.116:/var/www/skiltak/.env
```

O alternativamente, editá directo en el VPS:

```bash
nano /var/www/skiltak/.env
```

Valores mínimos a setear:

```bash
ENVIRONMENT=production
SECRET_KEY=<generar uno nuevo>
DEBUG=False
ALLOWED_HOSTS=skiltak.com,www.skiltak.com,api.skiltak.com

DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=skiltak_db
DATABASE_USER=skiltak_user
DATABASE_PASSWORD=<password fuerte>
DATABASE_HOST=localhost
DATABASE_PORT=5432

CORS_ALLOWED_ORIGINS=https://skiltak.com,https://www.skiltak.com

# Usar DB lógicas separadas de Redis para no chocar con otros proyectos.
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/2
REDIS_CACHE_URL=redis://127.0.0.1:6379/3

GEMINI_API_KEY=<rotar la actual>
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<app password>

FRONTEND_API_URL=https://api.skiltak.com/api
```

Generar `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4. Correr provisión

```bash
chmod +x /var/www/skiltak/deploy/provision.sh
bash /var/www/skiltak/deploy/provision.sh
```

Esto instala paquetes, crea el usuario `skiltak`, prepara DB, venv, migra, configura systemd y prepara Nginx.

### 5. Emitir certificados SSL

```bash
certbot --nginx \
  -d skiltak.com -d www.skiltak.com -d api.skiltak.com \
  --redirect --agree-tos -m tu-email@gmail.com
```

### 6. Habilitar sites de Nginx

```bash
ln -s /etc/nginx/sites-available/skiltak.com     /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/api.skiltak.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 7. Configurar GitHub Actions

En **Settings → Secrets and variables → Actions → New repository secret**:

| Nombre | Valor |
|---|---|
| `VPS_SSH_KEY` | Contenido de `C:\Users\walte\.ssh\id_ed25519_skiltak` (la clave privada) |

A partir de ahí, todo push a `main` despliega automáticamente.

---

## Despliegues posteriores (automático)

Solo `git push origin main`. El workflow [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) hace:

1. Build de Angular en runner de GitHub.
2. Rsync del `dist/` al VPS.
3. SSH al VPS → `git pull` del backend → `pip install` → `migrate` → `collectstatic` → `systemctl restart`.

Ver progreso en la pestaña **Actions** del repo.

## Operación

```bash
# Estado de los servicios
systemctl status skiltak-gunicorn skiltak-celery

# Logs en vivo
journalctl -u skiltak-gunicorn -f
journalctl -u skiltak-celery -f

# Restart manual
systemctl restart skiltak-gunicorn
systemctl restart skiltak-celery

# Recargar Nginx tras cambios de config
nginx -t && systemctl reload nginx
```

## Rollback

```bash
cd /var/www/skiltak
git log --oneline -n 5
git reset --hard <commit-sha-anterior>
source venv/bin/activate
pip install -r backend/requirements-prod.txt
cd backend && python manage.py migrate && python manage.py collectstatic --noinput
systemctl restart skiltak-gunicorn skiltak-celery
```
