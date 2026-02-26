# Task Runner Service

A secure, containerized code execution service with real-time monitoring and resource isolation.  
Run arbitrary code in isolated Docker containers, collect logs and metrics, and stream status updates via Server-Sent Events.

## Features

- **Isolated execution** – each task runs in a fresh Docker container with strict resource limits (CPU, memory, timeout).
- **Multiple languages** – Python, JavaScript (Node.js), Bash (easily extensible).
- **Real-time updates** – task status streamed via SSE, no polling needed.
- **Logs & Metrics** – stdout/stderr saved to MinIO, CPU/memory usage collected and displayed.
- **REST API** – create tasks, retrieve status, logs, and metrics.
- **Web UI** – simple interface to submit code and monitor execution.
- **Security** – containers run with read‑only rootfs, no privileges, dropped capabilities, and disabled network (optional).

## Architecture

The system consists of four main components:

- **Backend (FastAPI)** – handles task creation, stores tasks in MongoDB, pushes tasks to Redis queue.
- **Worker (Python + RQ)** – pulls tasks from Redis, executes them in Docker, collects logs and metrics, updates MongoDB, and publishes status updates via Redis Pub/Sub.
- **Web (Flask)** – provides a user interface and proxies API requests to the backend.
- **Infrastructure** – MongoDB (data), Redis (queue + pub/sub), MinIO (log storage).

```
User → Web UI → Backend → Redis Queue → Worker → Docker
          ↑                      ↓
          └────── SSE stream ←───┘
```

## Technology Stack

- **Backend**: FastAPI, Motor (async MongoDB), RQ (Redis Queue), aioredis, SSE-Starlette
- **Worker**: Python, Docker SDK, RQ, pymongo, minio-py
- **Web**: Flask, Jinja2, requests, JavaScript (SSE client)
- **Database**: MongoDB
- **Queue & Pub/Sub**: Redis
- **Object Storage**: MinIO
- **Containerization**: Docker, Docker Compose

## Prerequisites

- Docker and Docker Compose installed
- Git

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/task-runner.git
   cd task-runner
   ```

2. Copy environment example files:
   ```bash
   cp backend/.env.example backend/.env
   cp worker/.env.example worker/.env
   cp web/.env.example web/.env
   ```
   (Default values work out-of-the-box.)

3. Start all services:
   ```bash
   docker-compose up --build
   ```

4. Access the web UI at [http://localhost:5000](http://localhost:5000)

5. MinIO console: [http://localhost:9001](http://localhost:9001) (login: `minioadmin` / `minioadmin`)

## Usage

### Web Interface

- Open `http://localhost:5000`
- Select language, paste your code, set resource limits, and click "Run".
- You will be redirected to the task page where status updates appear instantly (via SSE).
- After completion, logs and resource metrics are displayed.

### REST API

The backend exposes a REST API on port `8000`.  
Example endpoints:

- `POST /api/v1/tasks` – create a new task  
  Body:
  ```json
  {
    "code": "print('hello')",
    "language": "python",
    "cpu_limit": 1.0,
    "memory_limit": "256m",
    "timeout": 30
  }
  ```
  Response: `{ "task_id": "uuid" }`

- `GET /api/v1/tasks/{task_id}` – get task details
- `GET /api/v1/tasks/{task_id}/logs` – get a presigned URL for logs stored in MinIO
- `GET /api/v1/tasks/{task_id}/metrics` – get execution metrics (CPU, memory)
- `GET /api/v1/tasks/{task_id}/stream` – SSE stream for real‑time status updates
- `GET /api/v1/tasks` – list tasks (with `?limit=`)

## Testing

Run unit and integration tests with pytest (inside a dedicated virtual environment or directly if dependencies are installed).

```bash
pip install -r requirements-dev.txt   # pytest, mongomock, mockredis, etc.
pytest tests/ -v
```

The test suite mocks external services (MongoDB, Redis, Docker, MinIO) so no actual containers are required.

## Project Structure

```
.
├── backend/           # FastAPI application
├── web/               # Flask web UI
├── worker/            # RQ worker that runs Docker containers
├── shared/            # (optional) shared models
├── tests/             # Unit and integration tests
├── docker-compose.yml # Main compose file
└── README.md
```

## Configuration

Each service reads configuration from environment variables.  
See the respective `.env.example` files for all options.

- `MONGO_URI`, `MONGO_DB_NAME`
- `REDIS_URL`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`
- `BACKEND_URL` (for web service)
- `SECRET_KEY` (for Flask)
- `DOCKER_HOST` (for worker, usually unix socket)

## Security Considerations

- Containers are created with:
  - `read_only=true` (root filesystem read‑only, except `/tmp` as tmpfs)
  - `cap_drop=ALL` (no Linux capabilities)
  - `security_opt=no-new-privileges:true`
  - `network_disabled=true` (network disabled by default – can be overridden)
  - CPU, memory, and PID limits
  - Automatic removal after execution
- All inter‑service communication is internal (Docker network).  
- Logs are stored in MinIO and can be accessed only via presigned URLs (short‑lived).

## Future Enhancements

- Support for uploading archives (multiple files, dependencies)
- WebSocket for even lower latency updates
- Persistent storage of metrics for historical analysis (Prometheus/Grafana)
- Kubernetes deployment manifests
- User authentication and quotas

## License

MIT

