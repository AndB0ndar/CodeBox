from flask import render_template

def register_error_handlers(app):
    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('error.html', error_message="Неверное имя пользователя или пароль"), 401

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html', error_message="Доступ запрещён"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', error_message="Страница не найдена"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('error.html', error_message="Внутренняя ошибка сервера. Попробуйте позже."), 500

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return render_template('error.html', error_message="Слишком много запросов. Подождите немного."), 429
