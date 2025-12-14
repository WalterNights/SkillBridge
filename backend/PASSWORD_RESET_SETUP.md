# Sistema de Restablecimiento de Contraseña

## 📧 Configuración de Email

El sistema de restablecimiento de contraseña envía códigos de verificación por correo electrónico.

### Configuración en Desarrollo

Por defecto, el sistema usa `console.EmailBackend` que imprime los emails en la consola del servidor Django:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Configuración en Producción (Gmail)

Para usar Gmail en producción, actualiza tu archivo `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=noreply@skillbridge.com
```

**⚠️ Importante:** Para Gmail, debes generar una "Contraseña de aplicación":
1. Ve a tu cuenta de Google → Seguridad
2. Activa la verificación en dos pasos
3. Genera una contraseña de aplicación
4. Usa esa contraseña en `EMAIL_HOST_PASSWORD`

### Otras opciones de Email

- **SendGrid**: Servicio profesional de emails
- **Amazon SES**: Servicio de AWS
- **Mailgun**: API para envío de emails
- **SMTP propio**: Servidor SMTP corporativo

## 🔐 Flujo del Sistema

### 1. Solicitud de Restablecimiento

**Endpoint:** `POST /api/users/password-reset/request/`

**Payload:**
```json
{
  "email": "user@example.com"
}
```

**Respuesta exitosa:**
```json
{
  "message": "Código de verificación enviado a tu correo",
  "email": "user@example.com"
}
```

**Proceso:**
1. Valida que el email exista en el sistema
2. Genera un código de 6 dígitos aleatorios
3. Crea un registro en la tabla `PasswordResetToken`
4. Envía el código por email
5. El código expira en 10 minutos

### 2. Verificación y Cambio de Contraseña

**Endpoint:** `POST /api/users/password-reset/verify/`

**Payload:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "NuevaContraseña123!"
}
```

**Respuesta exitosa:**
```json
{
  "message": "Contraseña restablecida exitosamente"
}
```

**Validaciones:**
- El código debe ser de 6 dígitos
- El código no debe estar usado
- El código no debe estar expirado (10 minutos)
- La nueva contraseña debe cumplir requisitos de seguridad:
  - Mínimo 8 caracteres
  - Al menos una letra
  - Al menos un número
  - Al menos un carácter especial

## 📱 Flujo Frontend

### Páginas Creadas

1. **Forgot Password** (`/auth/forgot-password`)
   - Formulario para ingresar email
   - Envía solicitud de código
   - Redirige a página de reset con email en query params

2. **Reset Password** (`/auth/reset-password`)
   - Formulario para código de 6 dígitos
   - Campos para nueva contraseña y confirmación
   - Botón para reenviar código
   - Validación de coincidencia de contraseñas
   - Toggles para mostrar/ocultar contraseñas

### Integración en Login

Enlace "¿Olvidaste tu contraseña?" agregado en el formulario de login que redirige a `/auth/forgot-password`.

## 🗄️ Modelo de Base de Datos

```python
class PasswordResetToken(models.Model):
    user = ForeignKey(User)
    code = CharField(max_length=6)  # Código de 6 dígitos
    created_at = DateTimeField(auto_now_add=True)
    is_used = BooleanField(default=False)
    
    def is_valid(self):
        # Verifica si no está usado y no ha expirado
        return not self.is_used and timezone.now() < self.created_at + timedelta(seconds=600)
```

**Migración creada:** `users/migrations/0004_passwordresettoken.py`

## 🔧 Configuración de Seguridad

### Timeout de Código

Definido en `settings.py`:
```python
PASSWORD_RESET_TIMEOUT = 600  # 10 minutos en segundos
```

### Generación de Código

El código se genera de forma aleatoria con el método:
```python
@staticmethod
def generate_code():
    return ''.join(random.choices(string.digits, k=6))
```

## 📝 Ejemplos de Uso

### Desarrollo (Console Backend)

1. El usuario ingresa su email en `/auth/forgot-password`
2. El código se imprime en la terminal del servidor Django
3. Copia el código de la terminal
4. Ingrésalo en `/auth/reset-password`

**Ejemplo de salida en consola:**
```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Subject: Código de restablecimiento de contraseña - SkillBridge
From: noreply@skillbridge.com
To: user@example.com

Hola username,

Has solicitado restablecer tu contraseña en SkillBridge.

Tu código de verificación es: 123456

Este código expirará en 10 minutos.
```

### Producción (SMTP)

1. El usuario recibe el código por email real
2. Ingresa el código en la interfaz
3. Sistema valida y actualiza la contraseña

## 🚀 Testing

### Caso 1: Email no existe
```bash
curl -X POST http://localhost:8000/api/users/password-reset/request/ \
  -H "Content-Type: application/json" \
  -d '{"email": "noexiste@example.com"}'

# Respuesta: {"email": ["No existe un usuario con este correo electrónico"]}
```

### Caso 2: Código expirado
- Esperar 11 minutos después de solicitar código
- Intentar verificar
- Sistema responderá: "El código ha expirado. Solicita uno nuevo"

### Caso 3: Código ya usado
- Usar un código exitosamente
- Intentar usarlo de nuevo
- Sistema responderá: "Código inválido o ya utilizado"

## 🔄 Limpieza de Tokens

Los tokens antiguos se quedan en la base de datos. Para producción, considera:

1. **Tarea de Celery periódica** (recomendado):
```python
@shared_task
def cleanup_expired_reset_tokens():
    """Elimina tokens expirados de más de 24 horas"""
    cutoff = timezone.now() - timedelta(hours=24)
    PasswordResetToken.objects.filter(created_at__lt=cutoff).delete()
```

2. **Comando de Django**:
```python
# management/commands/cleanup_reset_tokens.py
from django.core.management.base import BaseCommand
from users.models import PasswordResetToken

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        deleted = PasswordResetToken.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=1)
        ).delete()
        self.stdout.write(f"Eliminados {deleted[0]} tokens")
```

## 🛡️ Mejoras de Seguridad Recomendadas

1. **Rate Limiting**: Limitar solicitudes por IP/email
2. **Captcha**: Agregar reCAPTCHA en formulario
3. **Intentos fallidos**: Bloquear después de N intentos
4. **Logs de auditoría**: Registrar todos los intentos
5. **Notificación de cambio**: Email confirmando cambio de contraseña

## 📊 Métricas

Para monitorear el sistema:
- Solicitudes de reset por día
- Tasa de éxito vs expiración
- Tiempo promedio entre solicitud y verificación
- Emails fallidos

## 🐛 Troubleshooting

### El email no llega

1. **Revisa configuración SMTP**
   ```python
   # En Django shell
   from django.core.mail import send_mail
   send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
   ```

2. **Verifica firewall/puertos**
   - Puerto 587 debe estar abierto para TLS
   - Puerto 465 para SSL

3. **Revisa logs**
   - Busca errores en terminal Django
   - Revisa logs de email provider

### El código dice que está expirado

- Verifica que el servidor tenga la hora correcta
- Revisa `PASSWORD_RESET_TIMEOUT` en settings
- Asegúrate de usar timezone-aware datetimes

### Error CSRF en producción

- Agrega dominio a `CSRF_TRUSTED_ORIGINS`
- Verifica CORS settings

## 📚 Referencias

- [Django Email Documentation](https://docs.djangoproject.com/en/stable/topics/email/)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)
- [SendGrid Django Integration](https://docs.sendgrid.com/for-developers/sending-email/django)
