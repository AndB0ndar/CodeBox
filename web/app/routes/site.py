from flask import Blueprint, redirect, render_template, request, url_for

from app.core.backend_client import BackendClient


site_bp = Blueprint('site', __name__)


@site_bp.route('/')
def index():
    return render_template('index.html')


@site_bp.route('/submit', methods=['POST'])
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
    return redirect(url_for('site.task_detail', task_id=task_id))


@site_bp.route('/task/<task_id>')
def task_detail(task_id):
    return render_template('task.html', task_id=task_id)

