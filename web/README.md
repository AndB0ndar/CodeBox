## Worker Service

The worker is a **Python** process (using **RQ**) that:
- Listens to the Redis queue for pending tasks.
- Executes user code inside isolated Docker containers.
- Applies resource limits (CPU, memory, timeout) and security constraints.
- Collects stdout/stderr logs and uploads them to MinIO.
- Gathers CPU/memory metrics during execution.
- Updates the task status in MongoDB and publishes updates via Redis Pub/Sub.

### Directory Structure

```
worker/
├── app/
│   ├── core/
│   │   ├── config.py              # Environment variables
│   │   ├── mongo.py                # MongoDB connection
│   │   ├── docker_client.py        # Docker client
│   │   └── minio_client.py         # MinIO client
│   ├── tasks.py                     # Main task execution function
│   └── worker.py                    # RQ worker entry point
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Configuration

| Variable            | Description                          | Default               |
|---------------------|--------------------------------------|-----------------------|
| `MONGO_URI`         | MongoDB connection string            | `mongodb://localhost:27017` |
| `MONGO_DB_NAME`     | Database name                        | `taskrunner`          |
| `REDIS_URL`         | Redis URL (queue + pub/sub)          | `redis://localhost:6379` |
| `DOCKER_HOST`       | Docker daemon socket                 | `unix://var/run/docker.sock` |
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
2. Ensure MongoDB, Redis, and Docker are running.
3. Start the worker:
   ```bash
   python -m app.worker
   ```
   (By default, it listens to the `default` queue.)

### Task Execution

The worker function `run_task(task_id)` performs the following steps:

1. Fetch task from MongoDB.
2. Update status to `running`.
3. Create a Docker container with:
   - Resource limits: `cpu_quota`, `mem_limit`
   - Security: `read_only=true`, `cap_drop=ALL`, `no-new-privileges`, `network_disabled=true`
   - Temporary `/tmp` as tmpfs.
4. Start a background thread to collect `docker stats` every second.
5. Wait for container completion (with timeout).
6. Gather logs and upload to MinIO.
7. Aggregate metrics (max/avg CPU, max/avg memory).
8. Update task in MongoDB with final status, exit code, logs reference, and metrics.
9. Publish status change to Redis Pub/Sub.

### Security Notes

- Containers are run with **no privileges** and **no network** (by default).
- All Linux capabilities are dropped.
- The root filesystem is read‑only; only `/tmp` is writable (tmpfs).
- CPU, memory, and process limits are enforced.
- Containers are always removed after execution.

