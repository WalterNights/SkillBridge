# SkilTak

Plataforma inteligente de desarrollo profesional potenciada con IA para conectar talento con oportunidades perfectas.

## 🚀 Inicio Rápido

### Ejecutar ambos proyectos simultáneamente

```bash
npm start
```

Este comando levantará automáticamente:
- ✅ Frontend (Angular) en http://localhost:4200
- ✅ Backend (Django) en http://localhost:8000

### Comandos disponibles

```bash
# Iniciar frontend y backend juntos
npm start

# Iniciar solo el frontend
npm run frontend

# Iniciar solo el backend
npm run backend

# Instalar todas las dependencias
npm run install:all
```

## 📋 Requisitos Previos

- Node.js 18+ y npm
- Python 3.10+
- PostgreSQL (para backend)

## 🛠️ Instalación Manual

### 1. Instalar dependencias raíz
```bash
npm install
```

### 2. Configurar Frontend
```bash
cd frontend
npm install
```

### 3. Configurar Backend
```bash
cd backend
python -m venv env
source env/bin/activate  # En Windows: env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
```

## 📁 Estructura del Proyecto

```
SkilTak/
├── frontend/          # Aplicación Angular
├── backend/           # API Django REST
├── docs/              # Documentación
└── package.json       # Scripts del proyecto
```

## 🔧 Tecnologías

**Frontend:**
- Angular 19
- TailwindCSS
- TypeScript

**Backend:**
- Django 5.1
- Django REST Framework
- Celery + Redis
- PostgreSQL

## 📄 Licencia

MIT License - © 2025 WalterNights