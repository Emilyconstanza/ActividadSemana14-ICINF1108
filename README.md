# Students & Pets: recuperación de contraseña con JWT de un solo uso

Proyecto de ICINF1108 con autenticación por sesiones, CRUD de estudiantes y mascotas y persistencia en **PostgreSQL mediante SQLAlchemy**. Alembic administra el esquema y el volumen `pgdata` conserva los datos al reiniciar los contenedores.

La rama `feat/isidora-frontend-and-docs` incorpora la interfaz de recuperación, la matriz de pruebas de Postman y los diagramas de secuencia. Su base es `main` en `29a3226`: solo está integrada la configuración de Emily (PR #1). **Los casos de uso, la utilidad JWT, la persistencia del consumo y los endpoints de recuperación todavía dependen de los cambios de Camila, Francisca Alvarado y Francisca Salazar.** Las pantallas y pruebas de esta rama describen el contrato de integración; no equivalen a un flujo completo ya aprobado.

## Tecnologías

- Python 3.13
- FastAPI + SQLAlchemy + PostgreSQL
- Alembic, PyJWT y autenticación mediante cookie de sesión
- HTML + JS + Tailwind CSS (frontend estático)

## Resumen funcional

La API expone operaciones CRUD completas sobre estudiantes y mascotas:

**Estudiantes** — `/api/students`

- **Crear**: `POST /api/students` (opcionalmente con `pets[]` para crear el estudiante y sus mascotas en una sola petición)
- **Listar**: `GET /api/students`
- **Buscar por id**: `GET /api/students/:id`
- **Actualizar**: `PATCH /api/students/:id`
- **Eliminar**: `DELETE /api/students/:id` (elimina también sus mascotas)

**Mascotas** — `/api/students/:studentId/pets`

- **Listar**: `GET /api/students/:studentId/pets`
- **Crear**: `POST /api/students/:studentId/pets`
- **Actualizar**: `PATCH /api/students/:studentId/pets/:petId`
- **Eliminar**: `DELETE /api/students/:studentId/pets/:petId`

### Alta de estudiante con mascotas

`POST /api/students` acepta un arreglo opcional `pets`:

```json
{
	"name": "Ana Pérez",
	"username": "ana_perez",
	"email": "ana@example.com",
	"age": 21,
	"pets": [
		{ "name": "Firulais", "species": "perro", "age": 3 },
		{ "name": "Michi", "species": "gato" }
	]
}
```

Si no se envía `pets` (o se envía vacío), el comportamiento es exactamente el mismo de antes.

> **Transacción:** el servicio inserta el estudiante y sus mascotas, realiza `flush` y confirma con un solo `commit`. Si falla una inserción antes de confirmar, el cierre de la sesión descarta la transacción. Las restricciones de unicidad también se verifican en PostgreSQL.

### Modelo de datos

| Estudiante | Mascota        |
| ---------- | -------------- |
| id (UUID)  | id (UUID)      |
| name       | studentId      |
| username   | name           |
| email      | species        |
| age        | age (opcional) |
| createdAt  | createdAt      |
| updatedAt  | updatedAt      |

### Validación y unicidad

La validación se realiza con Pydantic v2:

- `name` (estudiante): texto de 3 a 100 caracteres, sin etiquetas HTML.
- `username`: texto de 3 a 30 caracteres, solo minúsculas, números y guiones bajos (`^[a-z0-9_]+$`).
- `email`: dirección de correo electrónico válida.
- `age` (estudiante): entero entre 18 y 99.
- `name` / `species` (mascota): texto de 1 a 50 caracteres, sin etiquetas HTML.
- `age` (mascota): entero entre 0 y 100 (opcional).

Unicidad (rechazado con `409 Conflict`):

- Estudiante: `email` y `username` deben ser únicos.
- Mascota: `name` debe ser único dentro de un mismo estudiante.

## Estándar de respuesta JSON

Toda respuesta de la API — exitosa o de error — usa el mismo **envelope** `ApiResponse`, definido en [`app/shared/api_response.py`](app/shared/api_response.py). Esto permite que el frontend interprete cualquier respuesta de forma uniforme.

### Envelope común

| Campo       | Tipo                | Descripción                                                               |
| ----------- | ------------------- | ------------------------------------------------------------------------- |
| `code`      | `number`            | Código de estado HTTP (coincide con el status de la respuesta).           |
| `success`   | `boolean`           | `true` si la operación se completó, `false` si hubo error.                |
| `message`   | `string`            | Resumen legible del resultado (varía según el método HTTP).               |
| `timestamp` | `string`            | Fecha/hora en ISO 8601 de la respuesta.                                   |
| `data`      | `object \| null`    | Datos de la operación. Presente en éxito; `null` en errores.              |
| `error`     | `string` (opcional) | Mensaje de error para errores simples (404, 500).                         |
| `errors`    | `object` (opcional) | Errores por campo para validación (400) y conflicto (409). Ver más abajo. |

### Respuestas de éxito

Un middleware global ([`api_response.py`](app/shared/api_response.py)) envuelve el retorno de los controladores en `data`:

- **Recurso único** (`GET :id`, `POST`, `PATCH`, `DELETE`): `data` contiene la entidad directamente.
- **Listado** (`GET` colección): `data` contiene `{ total, items }`.

```json
{
  "code": 201,
  "success": true,
  "message": "Recurso creado",
  "timestamp": "2026-09-09T16:49:33.368Z",
  "data": {
    "id": "c3600646-abe8-4be3-8096-d6ad629388e2",
    "name": "Juan Pérez",
    "username": "juanperez",
    "email": "juan@example.com",
    "age": 20,
    "createdAt": "2026-09-09T16:49:33.000Z",
    "updatedAt": "2026-09-09T16:49:33.000Z"
  }
}
```

`message` según el método HTTP:

| Método   | `message`             | `code` |
| -------- | --------------------- | ------ |
| `GET`    | `Operación exitosa`   | 200    |
| `POST`   | `Recurso creado`      | 201    |
| `PATCH`  | `Recurso actualizado` | 200    |
| `DELETE` | `Recurso eliminado`   | 200    |

### Errores simples (404, 500)

Los errores sin detalle por campo usan el campo `error`:

```json
{
  "code": 404,
  "success": false,
  "message": "Estudiante no encontrado",
  "timestamp": "2026-09-09T16:49:53.816Z",
  "data": null,
  "error": "Estudiante no encontrado"
}
```

### Validación (400) y conflicto (409)

Ambos casos comparten el **mismo esquema** para que el frontend los trate igual: el campo `errors` es un mapa `{ campo: { message } }`, donde la clave es el nombre del campo que falla.

```json
{
  "code": 400,
  "success": false,
  "message": "Error de validación",
  "timestamp": "2026-09-09T16:39:30.397Z",
  "data": null,
  "errors": {
    "name": { "message": "El nombre debe tener entre 3 y 100 caracteres" },
    "email": { "message": "El correo electrónico no es válido" }
  }
}
```

```json
{
  "code": 409,
  "success": false,
  "message": "Conflicto con datos existentes",
  "timestamp": "2026-09-09T16:49:45.110Z",
  "data": null,
  "errors": {
    "email": { "message": "El correo electrónico ya está en uso" }
  }
}
```

- `400 Bad Request`: cuando falla la validación. Los DTOs replican las reglas y mensajes de class-validator (NestJS) en español; el handler global ([`exceptions.py`](app/shared/exceptions.py)) convierte los errores al mapa `{ campo: { message } }` (si un campo falla varias reglas, los mensajes se concatenan con `", "`; las propiedades no permitidas devuelven `errors: {}`).
- `409 Conflict`: cuando se viola una restricción de unicidad. Los servicios lanzan una `HTTPException` con el mismo mapa `errors`, por lo que es indistinguible de una validación a nivel de estructura.

### Interpretación en el frontend

El cliente estático (`public/`) consume este estándar de forma uniforme:

- `public/js/api.js` expone `api()` (hace `fetch` y devuelve `data` en éxito o lanza el envelope en error) y `normalizeErrors()` (convierte `{ campo: { message } }` en `{ campo: message }`).
- En los formularios, si la respuesta trae `errors`, cada mensaje se muestra bajo su input correspondiente; si trae `error`, se muestra como notificación global (toast).

## Contexto técnico

- **Backend**: FastAPI
- **Persistencia**: PostgreSQL, repositorios SQLAlchemy y migraciones Alembic
- **Validación**: Pydantic v2
- **Frontend**: archivos estáticos en `public/` (Alpine.js + Tailwind CSS + vanilla-sonner, vía CDN)
- **Gestor de dependencias**: uv
- **Documentación**: Swagger en `/docs`

## Ejecución local

1. Desde la carpeta del repositorio, copiar la configuración local e iniciar PostgreSQL (requiere Docker Desktop en ejecución):

    ```powershell
    Copy-Item .env.example .env
    docker compose up -d db
    ```

    En Linux/macOS se puede usar `cp .env.example .env`. Revisar `DB_PORT` y `DATABASE_URL` si el puerto 5432 está ocupado.

2. Instalar dependencias con Python 3.13 y aplicar ambas migraciones (`0001` y `0002`):

    ```bash
    uv sync --frozen
    uv run alembic upgrade head
    uv run alembic current
    ```

3. Levantar el servidor en modo desarrollo:

    ```bash
    make dev
    ```

    O usando uv:

    ```bash
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
    ```

La aplicación queda disponible en:

- `http://localhost:3000`
- `http://localhost:3000/docs`

También puede ejecutarse todo con `docker compose up --build`; la imagen aplica las migraciones antes de iniciar Uvicorn. `docker compose down` conserva el volumen. `docker compose down -v` elimina los datos y debe reservarse para una base de pruebas descartable.

## Recuperación de contraseña: contrato de integración

El router de este repositorio usa **`/api/auth`**. Las rutas `/auth/...` de la guía se publican con el prefijo `/api`. En Swagger (`/docs`) deben aparecer los dos endpoints cuando se integren los cambios de backend.

| Método y ruta | Cuerpo JSON | Resultado esperado |
| --- | --- | --- |
| `POST /api/auth/forgot-password` | `{ "email": "prueba@example.com" }` | `200`: mismo mensaje para correo registrado e inexistente; nunca devuelve el token. |
| `POST /api/auth/reset-password` | `{ "token": "<JWT del enlace>", "newPassword": "NuevaClave123!" }` | `200`: actualiza la contraseña, consume el enlace y revoca las sesiones anteriores en una transacción. |
| `POST /api/auth/login` | `{ "email": "prueba@example.com", "password": "NuevaClave123!" }` | `200` con la contraseña nueva; `401` con la antigua. |

La respuesta funcional esperada del primer endpoint es:

```json
{
  "message": "Si el correo está registrado, recibirás un enlace de recuperación válido por 15 minutos."
}
```

La del segundo es `{ "message": "Contraseña actualizada exitosamente." }`. El middleware existente envuelve estos objetos: el mensaje funcional queda en **`data.message`**, junto a los campos superiores `code`, `success`, `message` y `timestamp`. El `message` superior es el texto general del middleware.

| Estado | Significado |
| --- | --- |
| `200 OK` | Solicitud genérica de recuperación o cambio completado. |
| `400 Bad Request` / `401 Unauthorized` | Token inválido, manipulado, expirado o ya usado, según la traducción del controlador. |
| `422 Unprocessable Entity` | Validación de cuerpo requerida por la guía y su documentación OpenAPI. **Pendiente de acordar:** el manejador global actual transforma la validación en `400`; añadir `422` a Swagger por sí solo no cambia ese comportamiento. |
| `404 Not Found` | Endpoint aún no integrado o ruta incorrecta; nunca cuenta como prueba de rechazo de token aprobada. |

### Configuración JWT y enlace

| Variable / ajuste | Estado en la base actual |
| --- | --- |
| `JWT_SECRET_KEY` | Se lee del entorno o de `.env`; usar un valor privado y aleatorio fuera del desarrollo. No exportarlo a Postman ni versionarlo. |
| `JWT_ALGORITHM` | `HS256`, constante en `app/shared/config.py`. Aún no se lee del entorno; escribirla en `.env` no cambia el algoritmo. La verificación debe usar una lista fija de algoritmos permitidos. |
| `PASSWORD_RESET_EXPIRE_MINUTES` | `15`, constante en `app/shared/config.py`. Aún no se lee del entorno. |
| `FRONTEND_URL` | Configuración pendiente del servicio de recuperación. Para desarrollo, el origen esperado es `http://localhost:3000`, sin `/` final. |

El servicio deberá simular el envío del enlace `FRONTEND_URL/reset-password?token=...` en el log de desarrollo. El JWT contiene `sub`, `jti`, `type=password_reset`, `iat` y `exp`; su contenido es legible, por lo que no debe incluir contraseñas. La contraseña se almacena solo como hash y nunca se escribe en logs. El enlace se consume una vez y la comprobación definitiva ocurre en la transacción de la base de datos.

### Pantallas

- Desde `/login.html`, abrir **¿Olvidaste tu contraseña?** o ir a `/forgot-password/`.
- Enviar el correo y mostrar siempre la confirmación genérica cuando el servidor responda `200`.
- Abrir el enlace recibido en `/reset-password?token=...`. `StaticFiles(html=True)` redirige a `/reset-password/` conservando la consulta.
- Introducir y confirmar una contraseña de 8 a 72 caracteres. Un enlace rechazado permite solicitar otro; un cambio exitoso permite volver a iniciar sesión.

El token se conserva únicamente en memoria durante la página de cambio; se retira de la URL con `history.replaceState`. Las pantallas de recuperación no guardan tokens en `localStorage` ni `sessionStorage` y usan una política `no-referrer`. Los errores `401` del cambio se muestran en esa pantalla, sin redirigir al login con el token dentro de `next`.

### Pruebas en Postman

Importar [la colección](postman/students-collection.json) y seguir [las instrucciones de ejecución](postman/README.md). La carpeta **Password Reset (One-Time JWT)** cubre:

1. Correo registrado: `200` y respuesta genérica.
2. Correo inexistente: `200` y la misma respuesta funcional.
3. Token manipulado: `400/401` antes de consumir el original.
4. Token válido: `200`.
5. Reutilización exacta del mismo token: `400/401`.
6. Contraseña antigua: login `401`; contraseña nueva: login `200`.

Usar una cuenta descartable y pegar el token del log solo en la variable local indicada por la colección. No debe añadirse un endpoint para exponerlo ni adjuntar tokens/cookies a capturas o exportaciones. La emisión del enlace y su consumo se ejecutan en etapas para poder introducir el token real entre ambas.

### Diagramas UML

- [Secuencia 0: solicitud del enlace](docs/diagrams/00-solicitud-recuperacion.puml).
- [Secuencia 1: restablecimiento de contraseña](docs/diagrams/01-restablecimiento-contrasena.puml).

Los diagramas representan el contrato esperado y las responsabilidades de cada capa. Incluyen líneas de vida tipadas, llamadas síncronas, retornos punteados, autollamadas y alternativas con guardas; el segundo muestra la transacción de consumo, actualización de hash y revocación de sesiones. Las instrucciones de visualización están en [docs/diagrams](docs/diagrams/README.md).

### Pendientes para cerrar la integración

- Integrar, en orden, utilidad JWT y repositorio (Camila), servicio (Francisca Alvarado) y endpoints/Swagger (Francisca Salazar).
- Confirmar `FRONTEND_URL`, prefijo `/api/auth`, formato `data.message`, traducción de errores y diferencia de validación `400/422`.
- Levantar PostgreSQL, aplicar migraciones y ejecutar las etapas de Postman con un enlace real. Comprobar también la revocación de una sesión anterior antes de volver a hacer login.
- Mantener la rama/PR de Isidora pendiente de la validación real del flujo. Las pruebas de interfaz con respuestas simuladas verifican su comportamiento, pero no demuestran firma JWT, persistencia ni consumo atómico.

### Validación de esta rama

- JSON y sintaxis de los 26 scripts de Postman verificados; las 13 solicitudes nuevas se comprobaron con respuestas de prueba. Las comprobaciones detectaron token ausente, respuesta de reutilización indebidamente exitosa, mensajes de recuperación distintos y respuestas `404/500` en lugar de un rechazo de token.
- Interfaz revisada en navegador con un servidor de prueba: correo obligatorio, confirmación genérica, contraseñas distintas, cambio exitoso, `401` sin redirección y errores de campo `422`. El token desaparece de la URL antes de enviar el formulario.
- FastAPI real: ambas pantallas se sirven con `200` y `/reset-password?token=...` conserva la consulta en la redirección a `/reset-password/`. Ambos endpoints de recuperación devuelven `404` en esta base; **la matriz contra la API real sigue pendiente**.
- Diagramas renderizados localmente y revisados visualmente; enlaces relativos de documentación y ausencia de secretos en el entorno compartido comprobados.

## Comandos útiles

- `make install` — sincroniza dependencias con uv
- `make dev` — arranca uvicorn en modo reload
- `make lint` — ejecuta Ruff (con autocorrección)
- `make format` — formatea el código con Ruff
- `make format-check` — verifica el formato
- `make clean` — elimina `.venv`, cachés y artefactos
