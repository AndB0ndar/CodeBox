## Backend Service

The backend is a **FastAPI** application responsible for:
- Accepting task submissions via REST API.
- Storing task metadata in MongoDB.
- Pushing tasks to the Redis queue for processing.
- Serving task status, logs, and metrics to clients.
- Streaming real‑time status updates via Server‑Sent Events (SSE).

### Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── tasks.py          # API endpoints
│   ├── core/
│   │   ├── config.py              # Environment variables & settings
│   │   ├── database.py            # MongoDB connection
│   │   ├── minio.py                # MinIO client
│   │   └── redis_pubsub.py        # Redis Pub/Sub manager
│   ├── models/
│   │   └── task.py                 # Pydantic models
│   └── main.py                     # FastAPI app creation
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Configuration

The backend reads configuration from environment variables (or a `.env` file).  
Key variables:

| Variable            | Description                          | Default               |
|---------------------|--------------------------------------|-----------------------|
| `MONGO_URI`         | MongoDB connection string            | `mongodb://localhost:27017` |
| `MONGO_DB_NAME`     | Database name                        | `taskrunner`          |
| `REDIS_URL`         | Redis URL (queue + pub/sub)          | `redis://localhost:6379` |
| `MINIO_ENDPOINT`    | MinIO server endpoint                | `localhost:9000`      |
| `MINIO_ACCESS_KEY`  | MinIO access key                     | `minioadmin`          |
| `MINIO_SECRET_KEY`  | MinIO secret key                     | `minioadmin`          |
| `MINIO_BUCKET`      | Bucket for logs                      | `task-logs`           |
| `MINIO_USE_SSL`     | Use SSL for MinIO                    | `false`               |

### Running Locally (without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure MongoDB and Redis are running.
3. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```
4. API will be available at `http://localhost:8000`.

### API Endpoints

- `POST /api/v1/tasks` – create a new task (see [API docs](#) for payload)
- `GET /api/v1/tasks/{task_id}` – get task details
- `GET /api/v1/tasks` – list tasks (with `?limit=`)
- `GET /api/v1/tasks/{task_id}/logs` – returns a presigned URL for logs
- `GET /api/v1/tasks/{task_id}/metrics` – returns execution metrics
- `GET /api/v1/tasks/{task_id}/stream` – SSE stream for status updates

Interactive API documentation is available at `/docs` (Swagger UI) when the server is running.

### Integration with Worker

When a task is created, the backend:
- Inserts the task into MongoDB with status `queued`.
- Enqueues a job in Redis using **RQ** with the task ID.
- The worker (see `worker/`) picks up the job, executes it, and updates the task.

### Real‑time Updates

The backend subscribes to Redis Pub/Sub channels (`task:{task_id}`).  
When the worker publishes a status change, the backend broadcasts it to all connected SSE clients.

