# Docker Compose Flask + MySQL Demo

A lightweight multi-container application built with **Docker Compose**, **Python Flask**, and **MySQL**. This project demonstrates practical Docker and DevOps fundamentals: building a custom image, service discovery, private bridge networking, environment-based configuration, health checks, and persistent database storage.

## Features

- **Flask REST API** with `/`, `/health`, and `/products` endpoints
- **MySQL 8.4** database service
- **Docker Compose** orchestration from a single YAML file
- **Private bridge network** for app-to-database communication
- **Named volume** to persist database files across container recreation
- **Health checks** for MySQL and the API
- **Startup dependency** that waits for MySQL to become healthy
- **Local-only port binding** for the API (`127.0.0.1:5000`)
- **Docker build cache-friendly** Dockerfile layout

## Architecture

```text
Browser / curl
      |
      | http://127.0.0.1:5000
      v
+-------------------------+
| Flask API service: app  |
| Container port: 5000    |
+-------------------------+
      |
      | Docker private network
      | DB_HOST=db:3306
      v
+-------------------------+
| MySQL service: db       |
| Container port: 3306    |
+-------------------------+
      |
      v
  Named volume: mysql_data
  Mounted at /var/lib/mysql
```

The MySQL port is **not published to the host**. The Flask application reaches MySQL through the Compose network using the service name `db`.

## Project structure

```text
docker-compose-lab/
├── compose.yaml
├── .env                  # Local configuration; do not commit
├── .dockerignore
└── app/
    ├── Dockerfile
    ├── requirements.txt
    └── app.py
```

## Prerequisites

- Ubuntu 24.04 (instructions below use Ubuntu/Linux shell commands)
- Docker Engine
- Docker Compose v2 plugin (`docker compose`)
- Internet access to pull the base images and Python packages

Check your installation:

```bash
docker --version
docker compose version
docker info
```

If the Compose plugin is missing on a system using Docker's official Ubuntu repository:

```bash
sudo apt update
sudo apt install docker-compose-plugin
```

## Quick start

### 1. Clone your repository

Replace the example URL with your repository URL:

```bash
git clone https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git
cd <YOUR-REPOSITORY>
```

### 2. Create the environment file

Create a local `.env` file in the project root:

```dotenv
MYSQL_ROOT_PASSWORD=change_this_local_root_password
MYSQL_DATABASE=appdb
MYSQL_USER=appuser
MYSQL_PASSWORD=change_this_local_app_password
```

These values are for local development only. Use strong credentials and an appropriate secret-management solution for shared or production environments.

### 3. Validate and build

```bash
docker compose config
docker compose build
```

Be careful when sharing the output of `docker compose config`: resolved configuration can include environment values.

### 4. Start the application

```bash
docker compose up -d
```

Check service status and health:

```bash
docker compose ps
docker compose logs -f
```

Press `Ctrl+C` to stop following logs; this does not stop the containers.

### 5. Call the API

The API is bound to loopback, so it is available from the Docker host:

```bash
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/products
```

Example response from `/`:

```json
{
  "message": "Docker Compose API is running",
  "endpoints": ["/health", "/products"]
}
```

Example response from `/health` when the database is reachable:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

Example response from `/products`:

```json
[
  {
    "id": 1,
    "name": "Docker Compose Demo"
  }
]
```

The product ID can differ if the database has been used before.

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Returns API status and available endpoint names |
| `GET` | `/health` | Checks connectivity to MySQL |
| `GET` | `/products` | Returns product rows from MySQL |

## How the Compose setup works

### Services

- `app` builds the Flask image from `app/Dockerfile`.
- `db` uses the `mysql:8.4` image.

### Networking

Both services join the `backend` bridge network. Inside the application container, `DB_HOST=db` resolves to the MySQL service through Docker's internal DNS.

Only the API is published to the host, and it is bound to `127.0.0.1:5000`. MySQL's port `3306` is internal to the Docker network.

### Environment variables

Compose reads the local `.env` file for variable substitution. The app receives `DB_HOST`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`; MySQL receives its initialization variables.

### Health checks

- MySQL's health check uses `mysqladmin ping`.
- The API's health check requests `/health`.
- `depends_on` with `condition: service_healthy` waits for the database health check to pass before starting the app.

Health checks help with startup and status reporting; they do not eliminate the need for application-level error handling and recovery.

### Persistent storage

The `mysql_data` named volume is mounted at `/var/lib/mysql`. Database files therefore persist when containers are stopped or recreated.

## Common commands

```bash
# Show services and health
docker compose ps

# Follow all logs
docker compose logs -f

# Show only application logs
docker compose logs -f app

# Show only database logs
docker compose logs -f db

# Restart the API
docker compose restart app

# Rebuild the application image and recreate the API
docker compose up -d --build app

# Open a shell in the app container
docker compose exec app sh

# Inspect the resolved Compose configuration
docker compose config

# Stop and remove containers and the project network
docker compose down
```

### Persistence test

Stop and remove the containers:

```bash
docker compose down
```

Start them again:

```bash
docker compose up -d
```

After both services are healthy, check the products:

```bash
curl http://127.0.0.1:5000/products
```

Existing product data should remain because the named volume is preserved by default.

> **Warning:** `docker compose down -v` removes Compose-managed named volumes and can permanently delete the demo database data. Use it only when you intentionally want to reset the database.

## Troubleshooting

### The API is unhealthy

```bash
docker compose ps
docker compose logs app
docker compose logs db
```

Confirm that the database is healthy and that the `.env` credentials match the values used when the database volume was first initialized.

### The API cannot connect to MySQL

- Confirm both services are on the `backend` network.
- Confirm `DB_HOST` is `db`, not `localhost`.
- Check the app and database logs.
- Remember that `localhost` inside a container refers to that same container.

### Port 5000 is already in use

Change the host side of the port mapping in `compose.yaml`, for example:

```yaml
ports:
  - "127.0.0.1:5001:5000"
```

Then recreate the app service:

```bash
docker compose up -d
```

Call the API at `http://127.0.0.1:5001`.

### MySQL credentials were changed but login still fails

MySQL initialization environment variables such as `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD` generally apply when the data directory is initialized for the first time. Changing `.env` does not automatically change users or passwords in an existing database volume.

For a disposable local lab, you can intentionally reset the database with:

```bash
docker compose down -v
docker compose up -d
```

**This deletes the named volume and its data. Do not use this reset on data you need to keep.**

## Security and production notes

This repository is a learning/demo project, not a production-ready deployment.

Before production use:

- Replace the Flask development server with a production WSGI server such as Gunicorn.
- Pin Python dependencies to reviewed versions.
- Use secrets management instead of committing credentials or baking them into images.
- Keep `.env` out of Git; commit a sanitized `.env.example` instead if helpful.
- Use least-privilege database accounts and strong credentials.
- Keep the database private; publish only required services.
- Consider a non-root application user, image scanning, and resource limits.
- Configure logging, monitoring, backups, and tested restore procedures.
- Use TLS and a suitable reverse proxy when exposing an application beyond the host.
- Back up the database separately; a Docker volume is persistence, not a backup.

## Learning objectives

By working through this project, you can practice:

- Dockerfiles and custom image builds
- Compose services and YAML configuration
- Bridge networking and service-name DNS
- Environment variable substitution
- Named volumes and database persistence
- Health checks and service startup dependencies
- Logs, troubleshooting, and container lifecycle management

## License

Choose a license before publishing this repository (for example, MIT) and add a corresponding `LICENSE` file if you want others to reuse the code under explicit terms.

