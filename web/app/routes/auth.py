import requests

from flask import (
    Blueprint,
    render_template, request, redirect, url_for, session, jsonify, current_app
)

from app import limiter
from app.core.backend_client import BackendClient


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        try:
            status_code, data = BackendClient.register(username, email, password)
            if status_code == 200:
                return redirect(url_for('auth.login'))
            else:
                return render_template(
                    'register.html', error=data.get('detail', 'Error')
                )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                return render_template(
                    'login.html', error='Некорректные значения в форме')
            else:
                return render_template(
                    'error.html', error_message='Ошибка связи с сервером'
                ), 500
        except Exception:
            return render_template(
                'error.html', error_message='Непредвиденная ошибка'
            ), 500
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            token = BackendClient.login(username, password)
            session['access_token'] = token
            return redirect(url_for('site.index'))
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return render_template(
                    'login.html', error='Неверное имя пользователя или пароль')
            else:
                return render_template(
                    'error.html', error_message='Ошибка связи с сервером'
                ), 500
        except Exception as e:
            return render_template(
                'error.html', error_message='Непредвиденная ошибка'
            ), 500
    return render_template('login.html')

@auth_bp.route('/logout')
@limiter.limit("10 per minute")
def logout():
    session.pop('access_token', None)
    return redirect(url_for('site.index'))

