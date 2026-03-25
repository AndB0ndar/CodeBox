import requests
import requests.exceptions as rex

from flask import current_app, stream_with_context


class BackendClient:
    @staticmethod
    def create_task(
        token, code, language, cpu_limit=1.0, memory_limit='256m', timeout=30
    ):
        url = f"{current_app.config['BACKEND_URL']}/api/tasks"
        payload = {
            "code": code,
            "language": language,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
            "timeout": timeout
        }
        current_app.logger.info(f"Sending to {url} with payload: {payload} and header {BackendClient._auth_headers(token)}")
        response = requests.post(url, json=payload, headers=BackendClient._auth_headers(token))
        current_app.logger.info(f"Response status: {response.status_code}, body: {response.text}")
        response.raise_for_status()
        return response.json()["task_id"]


    @staticmethod
    def get_task(token, task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/tasks/{task_id}"
        response = requests.get(url, headers=BackendClient._auth_headers(token))
        if response.status_code == 401:
            raise PermissionError("Invalid or expired token")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


    @staticmethod
    def get_task_log(token, task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/tasks/{task_id}/logs"
        response = requests.get(url, headers=BackendClient._auth_headers(token))
        if response.status_code == 401:
            raise PermissionError("Invalid or expired token")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()["url"]

    @staticmethod
    def get_task_metrics(token, task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/tasks/{task_id}/metrics"
        response = requests.get(url, headers=BackendClient._auth_headers(token))
        if response.status_code == 401:
            raise PermissionError("Invalid or expired token")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_task_stream(token, task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/tasks/{task_id}/stream"
        def generate():
            try:
                with requests.get(url, headers=BackendClient._auth_headers(token), stream=True) as resp:
                    if resp.status_code == 401:
                        yield "event: error\ndata: Unauthorized\n\n"
                        return
                    if resp.status_code != 200:
                        yield f"event: error\ndata: Backend error (status {resp.status_code})\n\n"
                        return

                    for line in resp.iter_lines():
                        try:
                            if line:
                                yield line.decode('utf-8') + '\n'
                            else:
                                yield '\n'
                        except (GeneratorExit, BrokenPipeError, ConnectionError):
                            print(f"Client disconnected for task {task_id}")
                            break

            except requests.exceptions.RequestException as e:
                print(f"Backend connection error for task {task_id}: {e}")
                yield f"event: error\ndata: Cannot connect to backend for task {task_id}\n\n"

            except Exception as e:
                print(f"Proxy error: {e}")
                yield f"event: error\ndata: Internal error\n\n"

        return current_app.response_class(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )

    @staticmethod
    def register(username, email, password):
        url = f"{current_app.config['BACKEND_URL']}/api/auth/register"
        response = requests.post(url, json={
            "username": username, 
            "email": email, 
            "password": password}
        )
        response.raise_for_status()
        return response.status_code, response.json()

    @staticmethod
    def login(username, password):
        backend_url = f"{current_app.config['BACKEND_URL']}/api/auth/token"
        # OAuth2 form wait form-data
        response = requests.post(backend_url, data={
            'username': username,
            'password': password
        })
        response.raise_for_status()

        return response.json().get('access_token')

    @staticmethod
    def _auth_headers(token):
        if token:
            return {'Authorization': f'Bearer {token}'}
        return {}

