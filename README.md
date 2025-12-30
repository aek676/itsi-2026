# ITSI — Task Manager Microservices

[![Docker Build](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/) [![Language](https://img.shields.io/badge/language-Python%203.9-green.svg)](https://www.python.org/)

## Descripción profesional

Este repositorio es una práctica centrada en aprender y demostrar el uso de **n8n** como herramienta de orquestación e integración. Contiene un conjunto de microservicios (API Flask, RabbitMQ, PostgreSQL) preparados para integrarse desde workflows de n8n, varios ejemplos de workflows listos para importar y ejercicios prácticos que ilustran: creación/consumo de mensajes, orquestación con LLM (Google Gemini), interacción con bases de datos y manejo de errores.

**Propósito del proyecto:** facilitar el aprendizaje práctico de n8n mostrando cómo automatizar flujos entre servicios, cómo configurar credenciales y cómo versionar workflows en `workflows/`.

## Tabla de contenidos

- [Visión general](#visión-general)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Inicio rápido (Docker Compose)](#inicio-rápido-docker-compose)
- [Variables de entorno](#variables-de-entorno)
- [Ejecución local (sin Docker)](#ejecución-local-sin-docker)
- [API — referencia rápida](#api--referencia-rápida)
- [Colas y DLX (dead-letter)](#colas-y-dlx-dead-letter)
- [Depuración y troubleshooting](#depuración-y-troubleshooting)
- [Contribución y contacto](#contribución-y-contacto)

## Visión general

Componentes principales:

- **web**: API REST (Flask). Gestiona tareas (crear, listar, completar) y publica eventos en RabbitMQ.
- **worker**: Procesa mensajes de `task_created` y valida el contenido.
- **notifier**: Escucha `task_completed` y envía notificaciones via webhook.
- **error_handler**: Procesa la cola de errores (`tasks_failed`) y los persiste en `error_log.txt`.
- **n8n**: Herramienta de orquestación incluida en `docker-compose` (carpeta `workflows`).
- **db** y **mq**: PostgreSQL y RabbitMQ como infra base.

## Arquitectura

- Publicador (API) → RabbitMQ (colas `task_created` / `task_completed`) → Consumidores (`worker`, `notifier`).
- Mensajes no procesables o malformados se envían al exchange `dlx` y a la cola `tasks_failed`.

## n8n — Orquestación visual

**n8n** es una herramienta de automatización y orquestación visual incluida en este proyecto para facilitar integraciones y flujos de trabajo (workflows) entre servicios.

Qué hace aquí:

- Permite crear workflows que consumen o producen eventos (por ejemplo: recibir un webhook y llamar a la API `web` para crear tareas).
- Facilita pruebas y prototipado sin necesidad de programar nuevos consumidores.

Cómo está configurado (ver `docker-compose.yml`):

- Imagen: `docker.n8n.io/n8nio/n8n:latest`.
- Volúmenes montados:
  - `./local-files:/files` — carpeta de archivos accesible desde n8n.
  - `./database.sqlite:/home/node/.n8n/database.sqlite` — base de datos SQLite para persistencia de credenciales y workflows.
  - `./workflows:/home/node/workflows` — carpeta para persistir/exportar workflows locales.
- Variables de entorno útiles (definidas en `docker-compose.yml`): `N8N_RUNNERS_ENABLED`, `N8N_GIT_NODE_DISABLE_BARE_REPOS`, `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` y varias `SHEET_NAME_*` usadas por workflows de ejemplo.

Acceso y uso básico:

- UI: http://localhost:5678
- Importar/Exportar workflows: desde la UI puedes importar .json exportados y también colocar archivos en `./workflows` para mantenerlos con control de versión.

Ejemplo práctico rápido:

1. En n8n crea un workflow con nodo **HTTP Request** (método POST) apuntando a `http://task-manager-web:5000/tasks` (si ejecutas en Docker) o `http://localhost:5001/tasks` (si pruebas localmente).
2. Configura el body JSON con `{ "title": "Tarea desde n8n", "description": "...» }` y ejecuta el workflow.
3. Verás la tarea creada en la API y el mensaje publicado en RabbitMQ.

Persistencia y backups:

- El fichero `database.sqlite` en la raíz mantiene credenciales y datos de n8n; respáldalo si quieres conservar workflows y credenciales.
- Alternativamente, exporta workflows desde la UI y guárdalos en `workflows/`.

Seguridad (importante):

- Por defecto en este `docker-compose` no se habilita autenticación en n8n; **no** exponer el puerto 5678 en entornos públicos sin protegerlo (ej. `N8N_BASIC_AUTH_ACTIVE`, `N8N_BASIC_AUTH_USER`, `N8N_BASIC_AUTH_PASSWORD`, o usar un proxy con auth).

Workflows incluidos (resumen) 🗂️

En `workflows/` hay múltiples flujos n8n usados para prácticas y demos. A continuación un índice de los más relevantes, con su propósito y notas de uso:

- `ZD3zNntna6R07naM.json` — **Webhook productor de tareas** (Practica 6: Ejercicio 3)

  - Recibe POSTs (nodo `Webhook`), valida `title`, inserta la tarea en PostgreSQL y publica el mensaje en la cola `task_created` (nodo `RabbitMQ`). Útil como alternativa al endpoint `/tasks` del servicio `web`.
  - Requiere credenciales de **Postgres** y **RabbitMQ** en n8n.

- `deqnbAjKqlCU5qQy.json` — **Consumidor de `task_created`** (Practica 6)

  - Nodo `RabbitMQ Trigger` escuchando `task_created`, procesa mensajes y enriquece datos.
  - Requiere credenciales de **RabbitMQ**.

- `8akUngiiJ5LZGxhz.json` — **Clasificador de prioridad con LLM (Google Gemini)** (Practica 7)

  - Lee tareas desde Postgres, envía el JSON a Google Gemini para asignar `priority` y hace `upsert` en la tabla `task`. Si la prioridad es `ALTA`, envía una alerta por email (nodo `Gmail`).
  - Requiere credenciales: **Google Gemini (via n8n LangChain node)**, **Postgres**, **Gmail**.

- `Ph7rWTcOFLES84kd.json` — **Manejo de errores de workflows (Error Trigger)**

  - Nodo `Error Trigger` que escribe fallos en Google Sheets y envía notificaciones por email.
  - Requiere credenciales: **Google Sheets**, **Gmail**.

- `xpK0ULioW5TQjpON.json` y similares — **Ingestores / Jobs programados**

  - Ej.: peticiones HTTP periódicas (jokes, productos) y escritura en Google Sheets.
  - Uso de variables de entorno en n8n: `SHEET_ID_CHISTES`, `SHEET_NAME_PROG`, `SHEET_NAME_MISC`, `SHEET_NAME_DARK`.

- Sub-flujos y utilidades (ejemplos):
  - `GWuduERWrPMTaDe6.json` — sub-flujo descargador de imágenes
  - `ZY0gvOLS9fu7tvrT.json` — validador de producto (sub-flow)

Notas importantes sobre workflows

- Credenciales y permisos: Muchos workflows dependen de credenciales externas (RabbitMQ, PostgreSQL, Google Sheets, Gmail, Google Gemini). Configura estas credenciales desde la UI de n8n (todas las credenciales usadas están referenciadas en los JSON).
- Persistencia: Los workflows pueden guardarse en `workflows/` (montado por `docker-compose`). También puedes importar/exportar JSON desde la UI para versionado.
- Variables de entorno: Algunos workflows usan variables de entorno dentro de n8n (se muestran arriba). Añade estas variables a tu entorno de ejecución de n8n o configura `N8N_VARIABLES` si usas esa opción.
- Seguridad: no subir credenciales en texto plano al repositorio; usa la UI de n8n o secretos en el entorno.

## Requisitos

- Docker (>= 20.10) y Docker Compose (o `docker compose` v2).
- Opcional: Python 3.9+, `pip` y `virtualenv` para ejecución local.

## Inicio rápido (Docker Compose)

1. Clona el repo:

```bash
git clone <repo-url>
cd itsi-2026
```

2. Arranca los servicios (construye imágenes si es necesario):

```bash
docker compose up --build -d
```

3. Verifica los servicios clave:

- Web API: http://localhost:5001
- RabbitMQ management: http://localhost:15672 (guest / guest)
- PostgreSQL: escucha en el puerto del host 5433 → contenedor 5432
- n8n: http://localhost:5678

4. Logs y control

```bash
docker compose logs -f task-manager-web
docker compose logs -f task-manager-worker
docker compose down
```

## Variables de entorno

Las variables definidas en `docker-compose.yml` (valores por defecto):

- DATABASE_URL: `postgresql://user:password@db:5432/taskdb`
- RABBITMQ_URL: `amqp://guest:guest@mq:5672/%2F`
- WEBHOOK_URL: URL para recibir notificaciones del `notifier` (por defecto apuntado a webhook.site)

Sugerencia: crea un archivo `.env.example` con estas variables y su valor por defecto. ¿Quieres que lo añada automáticamente? (puedo generarlo).

## Ejecución local (sin Docker)

Requisitos locales: PostgreSQL y RabbitMQ accesibles desde tu máquina.

Desde la carpeta del servicio (por ejemplo `task-manager-service/web`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql://user:password@localhost:5433/taskdb'
export RABBITMQ_URL='amqp://guest:guest@localhost:5672/%2F'
python app.py
```

Para `worker`, `notifier` y `error_handler` exporta `RABBITMQ_URL` y ejecuta `python worker.py` desde su carpeta correspondiente.

## API — referencia rápida

- GET /tasks

  - Retorna todas las tareas.

- POST /tasks

  - Crea una tarea.
  - Body (JSON): `{"title":"Mi tarea","description":"...","priority":"ALTA"}`
  - `priority` admitido: `ALTA`, `MEDIA`, `BAJA` o `null`.

- PUT /tasks/<id>/complete

  - Marca como completada y publica evento `task_completed`.

- POST /tasks/test-malformed
  - Envía un mensaje malformado (útil para pruebas de DLX/error handling).

Ejemplos (curl):

```bash
curl -s -X POST http://localhost:5001/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Probar","description":"Desc","priority":"ALTA"}'

curl http://localhost:5001/tasks

curl -X PUT http://localhost:5001/tasks/1/complete

curl -X POST http://localhost:5001/tasks/test-malformed
```

## Colas y DLX (dead-letter)

- Las colas se declaran con `x-dead-letter-exchange: dlx`.
- Mensajes malformados o rechazados (NACK sin requeue) terminan en `tasks_failed` para su inspección por `error_handler`.

## Depuración y troubleshooting

- Si los workers no se conectan a RabbitMQ, revisa `RABBITMQ_URL` y la disponibilidad del servicio; los workers reintentan la conexión.
- Comprueba la interfaz de RabbitMQ en `http://localhost:15672` para inspeccionar colas y mensajes.
- `web` crea las tablas con `db.create_all()` al iniciarse; verifica logs para errores de migración/credenciales.

## Contribución y contacto

- Issues y Pull Requests son bienvenidos. Incluye información clara sobre pasos para reproducir bugs.
- ¿Quieres que añada una colección Postman o un `Makefile` con comandos `make up`/`make down`? Puedo generarlos.

## Licencia

- Sin licencia explícita en el repositorio. Recomiendo añadir un `LICENSE` (por ejemplo MIT) si deseas permitir contribuciones externas.

## Mantenedor

- Autor: Proyecto de práctica (ver commits para información del autor).
