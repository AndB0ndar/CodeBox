import requests

from flask import Blueprint, jsonify, Response, stream_with_context

from app.core.backend_client import BackendClient


api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health():
    return jsonify({"status": "ok!!1!"})


@api_bp.route('/tasks/<task_id>')
def api_task(task_id):
    task = BackendClient.get_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@api_bp.route('/tasks/<task_id>/logs')
def api_task_logs(task_id):
    log_url = BackendClient.get_task_log(task_id)
    if log_url is None:
        return jsonify({"error": "Logs not found"}), 404

    try:
        resp = requests.get(log_url, stream=True)
        if resp.status_code != 200:
            return jsonify(
                {"error": f"MinIO returned {resp.status_code}"}
            ), resp.status_code

        return Response(
            stream_with_context(resp.iter_content(chunk_size=8192)),
            content_type=resp.headers.get('Content-Type', 'text/plain'),
            status=resp.status_code
        )
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to retrieve logs"}), 502


@api_bp.route('/tasks/<task_id>/metrics')
def api_task_metrics(task_id):
    metrics = BackendClient.get_task_metrics(task_id)
    if metrics is None:
        return jsonify({"error": "Metrics not found"}), 404
    return jsonify(metrics)


@api_bp.route('/tasks/<task_id>/stream')
def stream_task_status(task_id):
    return BackendClient.get_task_stream(task_id)

