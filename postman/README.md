# Pruebas de recuperación de contraseña

La colección `students-collection.json` conserva las solicitudes originales y agrega **Password Reset (One-Time JWT)**. La carpeta trabaja con una cuenta temporal en `http://localhost:3000` y divide el flujo en dos fases porque el correo se simula en el log del servidor.

## Preparación

1. Levanta PostgreSQL y la API, aplica las migraciones y confirma que las implementaciones de JWT, repositorio, servicio y endpoints del equipo ya estén integradas. La configuración y los DTOs por sí solos no habilitan el flujo.
2. Importa `students-collection.json` y `password-reset-local.postman_environment.json` en Postman.
3. Selecciona el entorno **Password Reset - Local**. `baseUrl` debe ser `http://localhost:3000` o `http://127.0.0.1:3000`, sin barra final y sin `/api` al final. Los requests agregan `/api/auth`.
4. Mantén las variables generadas únicamente en los valores locales del entorno. El archivo compartido deja en blanco contraseñas, JWT y cookies. No subas un entorno exportado después de ejecutar pruebas sin borrar esos valores.

## A. Solicitar el enlace

Ejecuta únicamente **A - Solicitud (pausa para copiar token)** en el Collection Runner, con una iteración y conservación de los valores del entorno. También puedes enviar sus requests en orden, del `00` al `04`.

La fase crea un correo único y dos contraseñas aleatorias, registra una cuenta temporal, inicia sesión y demuestra que su cookie funciona. Después solicita recuperación con el correo registrado y con otro correo que no se registró. Las pruebas exigen `200` y la misma respuesta genérica; excluyen `timestamp` de la comparación porque cambia entre solicitudes.

El request `04` termina el Runner deliberadamente mediante `pm.execution.setNextRequest(null)`. Ejecutar toda la carpeta **Password Reset (One-Time JWT)** también se detiene aquí: ese resultado todavía no demuestra el restablecimiento.

Con la API local aún en ejecución, busca en su log el enlace de recuperación de la cuenta indicada en `resetEmail`. Copia **solo el JWT completo** que sigue a `token=` en la variable local `resetToken`: sin la URL, comillas ni prefijo `Bearer`. Completa la fase B antes de los 15 minutos de vigencia. El endpoint público de solicitud nunca debe devolver el token para facilitar las pruebas.

## B. Restablecer y verificar seguridad

Ejecuta únicamente **B - Restablecimiento y seguridad**, en orden, del `05` al `12`, conservando el mismo entorno. No vuelvas a ejecutar A entre ambas fases: borraría las variables y crearía otra cuenta.

| Request | Verificación | Resultado esperado |
| --- | --- | --- |
| 03 y 04 | Correo registrado e inexistente | `200`, misma respuesta funcional sin datos del usuario |
| 05 | Cambiar un carácter del payload del JWT original, conservando la firma | `400` o `401` |
| 06 | Consumir el JWT válido con la contraseña nueva | `200` |
| 07 | Reutilizar exactamente el JWT de 06 e intentar recuperar la contraseña antigua | `400` o `401` |
| 08 | Volver a usar la cookie que funcionó antes del cambio | `401` |
| 09 | Login con contraseña antigua | `401` |
| 10 y 11 | Login con contraseña nueva y consulta de la nueva sesión | `200`, misma identidad |
| 12 | Cerrar la sesión temporal nueva | `200` |

El caso 05 cubre la alternativa de **token manipulado** de la matriz. No afirma haber probado expiración real. Para comprobarla además, prepara otra cuenta/enlace, espera más que su vigencia sin cambiar el reloj ni la firma y comprueba su rechazo por `400` o `401`.

Las cookies automáticas están desactivadas en estos requests. Las consultas de sesión envían explícitamente el `sid` capturado en `Set-Cookie`; así el caso 08 comprueba revocación de una sesión previamente válida. No depende de una cookie ausente ni de otra sesión abierta en Postman.

## Interpretación y repetición

- Un JWT ausente o incompleto genera una **precondición fallida** y un error de script. No se omite silenciosamente ni cuenta como caso aprobado. Revisa tanto los resultados de tests como los errores de scripts; no basta con ver un estado HTTP aislado.
- La reutilización y las comprobaciones posteriores exigen que `06` haya respondido `200`. Una respuesta `404` indica endpoints ausentes o URL incorrecta; `500` indica un error del servidor. Ninguno demuestra seguridad del token.
- La API usa un envelope: la confirmación específica está en `data.message`, mientras `message` en el nivel superior describe la operación. Las pruebas reflejan ese contrato.
- Los errores de validación del proyecto base usan actualmente `400`; la guía menciona `422`. Esa discrepancia debe resolverse con la responsable de los endpoints y reflejarse en OpenAPI. La matriz de tokens acepta únicamente `400` o `401`.
- Cada ejecución de A crea otra cuenta y descarta el token anterior del entorno. Para repetir todo el flujo, comienza de nuevo por A y copia el enlace recién emitido. No ejecutes B con un JWT ya consumido esperando que 06 vuelva a pasar.
- El request 12 cierra la sesión nueva; las cuentas de prueba permanecen en la base local. No hay borrado automático de usuarios ni de bases de datos. Usa una base desechable separada si necesitas limpiar todos los datos después.
- Después de las pruebas, vacía las variables del entorno salvo `baseUrl`, especialmente contraseñas, `resetToken`, `oldSessionCookie` y `newSessionCookie`. No compartas logs con enlaces válidos ni capturas que muestren esos valores.

## Evidencia

Guarda los resultados reales del Runner de A y B cuando el backend completo esté disponible. Importar la colección, validar JSON o comprobar la sintaxis de sus scripts no equivale a haber probado la API ni autoriza a declarar la integración aprobada.

Referencias de Postman: [orden de ejecución y pausa del Runner](https://learning.postman.com/docs/tests-and-scripts/write-scripts/postman-sandbox-reference/pm-execution/) y [manejo de cookies y opción Disable cookie jar](https://learning.postman.com/docs/use/send-requests/response-data/cookies/).
