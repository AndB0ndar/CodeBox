import requests

from flask import Blueprint
from flask import jsonify, redirect, render_template, request, url_for
from flask import Response, stream_with_context

from app.core.backend_client import BackendClient


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/submit', methods=['POST'])
def submit():
    code = request.form.get('code')
    language = request.form.get('language')
    if not code or not language:
        return "Missing code or language", 400

    cpu_limit = float(request.form.get('cpu_limit', 1.0))
    memory_limit = request.form.get('memory_limit', '256m')
    timeout = int(request.form.get('timeout', 30))

    task_id = BackendClient.create_task(
        code, language, cpu_limit, memory_limit, timeout
    )
    return redirect(url_for('main.task_detail', task_id=task_id))


@main_bp.route('/task/<task_id>')
def task_detail(task_id):
    return render_template('task.html', task_id=task_id)


@main_bp.route('/api/tasks/<task_id>')
def api_task(task_id):
    task = BackendClient.get_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@main_bp.route('/api/tasks/<task_id>/logs')
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


@main_bp.route('/api/tasks/<task_id>/metrics')
def api_task_metrics(task_id):
    metrics = BackendClient.get_task_metrics(task_id)
    if metrics is None:
        return jsonify({"error": "Metrics not found"}), 404
    return jsonify(metrics)

