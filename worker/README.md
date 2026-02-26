## Web Service

The web service is a **Flask** application that:
- Provides a simple user interface for submitting code and viewing results.
- Proxies API requests to the backend service.
- Implements a Server‑Sent Events (SSE) client to receive real‑time status updates.

### Directory Structure

```
web/
├── app/
│   ├── core/
│   │   ├── config.py              # Flask configuration
│   │   └── backend_client.py       # Helper to call backend API
│   ├── routes/
│   │   └── main.py                  # All routes (index, submit, task pages)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── task.js               # SSE client & UI updates
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── task.html
│   ├── __init__.py
│   └── main.py                       # Flask app factory
├── requirements.txt
├── Dockerfile
└── .env.example
```

### Configuration

| Variable        | Description                          | Default               |
|-----------------|--------------------------------------|-----------------------|
| `SECRET_KEY`    | Flask secret key (for sessions)      | `dev-key-change-in-production` |
| `BACKEND_URL`   | URL of the backend service           | `http://backend:8000` |
| `DEBUG`         | Enable Flask debug mode              | `True`                |

### Running Locally (without Docker)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure the backend is running (or set `BACKEND_URL` accordingly).
3. Start the Flask development server:
   ```bash
   flask run
   ```
4. Access the UI at `http://localhost:5000`.

### Routes

- `GET /` – main form for submitting code.
- `POST /submit` – processes form, calls backend to create task, redirects to `/task/<task_id>`.
- `GET /task/<task_id>` – displays task details (status, logs, metrics).
- `GET /api/tasks/<task_id>` – proxies `GET /api/v1/tasks/<task_id>` from backend.
- `GET /api/tasks/<task_id>/logs` – proxies logs endpoint.
- `GET /api/tasks/<task_id>/metrics` – proxies metrics endpoint.
- `GET /api/tasks/<task_id>/stream` – proxies SSE stream.

### Real‑time Updates

The page `task.html` includes JavaScript (`task.js`) that:
- Opens an SSE connection to `/api/tasks/<task_id>/stream`.
- Updates the status span immediately when a `status_update` event arrives.
- When the task finishes (status `completed` or `failed`), closes the SSE connection and fetches logs and metrics via the proxy endpoints.

If SSE fails, the script falls back to polling every 2 seconds.

### Static Assets

- `style.css` – basic styling.
- `task.js` – all client‑side logic for fetching and displaying task data.

