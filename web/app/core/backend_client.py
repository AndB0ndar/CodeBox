import requests

from flask import current_app


class BackendClient:
    @staticmethod
    def create_task(code, language):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks"
        payload = {"code": code, "language": language}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()["task_id"]


    @staticmethod
    def get_task(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}"
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()


    @staticmethod
    def get_task_log(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}/logs"
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()["url"]


    @staticmethod
    def get_task_metrics(task_id):
        url = f"{current_app.config['BACKEND_URL']}/api/v1/tasks/{task_id}/metrics"
        response = requests.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

