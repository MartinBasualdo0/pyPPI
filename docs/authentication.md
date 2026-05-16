# Autenticación

La autenticación con PPI ocurre automáticamente al instanciar la clase `PPI`. La librería gestiona el flujo completo: obtención del token, actualización de headers y resolución del ID de cuenta.

## Autenticación básica

```python
from py_ppi_arg import PPI

app = PPI(user="tu@email.com", password="tu_contraseña")
```

Si las credenciales son correctas, el objeto `app` queda listo para hacer consultas. Si fallan, se lanza una `ApiException`.

## Cuentas con doble factor (2FA)

Si tu cuenta tiene 2FA activado, PPI enviará un código a tu email al iniciar sesión. La librería lo maneja de dos formas:

### Modo interactivo (por defecto)

Sin configurar nada extra, la librería pausará y pedirá el código por consola:

```text
Ingresá el código de 2FA enviado por PPI: _
```

### Modo automático con `otp_provider`

Podés pasar una función que retorne el código. Esto es útil para automatizaciones o cuando el código viene de un sistema externo (por ejemplo, TOTP con `pyotp`):

```python
import pyotp

totp = pyotp.TOTP("tu_secret_totp")

app = PPI(
    user="tu@email.com",
    password="tu_contraseña",
    otp_provider=totp.now,  # función sin argumentos que retorna el código
)
```

Cualquier callable que no reciba argumentos y retorne un string con el código funciona:

```python
def get_code_from_api():
    # lógica para obtener el código desde donde sea
    return "123456"

app = PPI(user="tu@email.com", password="tu_contraseña", otp_provider=get_code_from_api)
```

## Recordar dispositivo

Con `remember_device=True`, la sesión no requerirá 2FA en futuros inicios desde el mismo dispositivo (comportamiento idéntico al checkbox en la web):

```python
app = PPI(
    user="tu@email.com",
    password="tu_contraseña",
    remember_device=True,
)
```

## Caché de sesión

Por defecto, la librería guarda el token en `~/.py_ppi_arg_session.json` después del primer login exitoso. En los siguientes usos:

1. Si el token sigue vigente → lo reutiliza directamente (sin login, sin 2FA)
2. Si venció pero hay refresh token → lo renueva silenciosamente (sin 2FA)
3. Si el refresh también falló → hace login completo (puede pedir 2FA)

El resultado es que el 2FA solo se pide la primera vez, o cuando la sesión expira completamente.

Para desactivar el caché (útil en entornos CI o donde no se quiere estado en disco):

```python
app = PPI(user="tu@email.com", password="tu_contraseña", cache_session=False)
```

El archivo de caché tiene permisos `600` (solo lectura/escritura del usuario).

## Parámetros del constructor

| Parámetro | Tipo | Requerido | Default | Descripción |
| --------- | ---- | --------- | ------- | ----------- |
| `user` | `str` | Sí | — | Email de la cuenta PPI |
| `password` | `str` | Sí | — | Contraseña de la cuenta |
| `otp_provider` | `Callable[[], str]` | No | `None` | Función que retorna el código 2FA |
| `remember_device` | `bool` | No | `False` | Recordar el dispositivo para saltear 2FA futuro |
| `cache_session` | `bool` | No | `True` | Guardar el token en disco para evitar 2FA en cada uso |

## Errores de autenticación

| Error | Causa |
| ----- | ----- |
| `ApiException: Login failed` | Credenciales incorrectas |
| `ApiException: 2FA validation failed` | Código 2FA inválido o expirado |
| `ApiException: Access token not found` | Respuesta inesperada del servidor |

!!! warning "Seguridad"
    No hardcodees tus credenciales en el código. Usá variables de entorno:
    ```python
    import os
    app = PPI(user=os.environ["PPI_USER"], password=os.environ["PPI_PASSWORD"])
    ```
