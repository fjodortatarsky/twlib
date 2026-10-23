import hmac
import secrets
from datetime import datetime

from flask import (
    Flask, abort, flash, redirect, render_template,
    request, send_file, session, url_for,
)
from werkzeug.utils import secure_filename

import auth
import storage
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

storage.init_storage()


# --- CSRF ---------------------------------------------------------------

def _csrf_token() -> str:
    token = session.get("_csrf")
    if not token:
        token = secrets.token_hex(32)
        session["_csrf"] = token
    return token


@app.before_request
def _verify_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    expected = session.get("_csrf")
    submitted = request.form.get("_csrf", "")
    if not expected or not hmac.compare_digest(
        submitted.encode("utf-8"), expected.encode("utf-8")
    ):
        abort(400, description="Форма устарела или cookies отключены. Обновите страницу.")


@app.context_processor
def inject_globals():
    def authority_url(authorityid: str) -> str:
        return Config.AUTHORITY_BASE_URL.format(authorityid=authorityid)

    return {
        "current_user": auth.current_user,
        "csrf_token": _csrf_token,
        "authority_url": authority_url,
    }


# --- вспомогательное ----------------------------------------------------

def _form(mode, authorityid="", title="", description="", error=None):
    return render_template(
        "image_form.html",
        mode=mode,
        authorityid=authorityid,
        form={"title": title, "description": description},
        error=error,
    )


def _validate(title, description, file_storage, *, file_required):
    if not title:
        return "Укажите название."
    if len(title) > Config.MAX_TITLE_LENGTH:
        return f"Название длиннее {Config.MAX_TITLE_LENGTH} символов."
    if len(description) > Config.MAX_DESCRIPTION_LENGTH:
        return f"Описание длиннее {Config.MAX_DESCRIPTION_LENGTH} символов."
    if file_storage is None or not file_storage.filename:
        return "Выберите файл изображения." if file_required else None
    if not storage.allowed_file(file_storage.filename):
        return "Неподдерживаемый формат. Доступны: JPG, PNG, WebP, BMP, TIFF."
    return None


@app.template_filter("fmt_date")
def fmt_date(value):
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y, %H:%M UTC")
    except (TypeError, ValueError):
        return value


# --- публичная часть ----------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html", pictures=storage.list_pictures())


@app.get("/pictures/<picture_id>")
def picture_view(picture_id):
    record = storage.load_picture(picture_id)
    if record is None:
        abort(404)
    return render_template("picture.html", picture=record)


@app.get("/pictures/<picture_id>/image.jpg")
def picture_image(picture_id):
    path = storage.image_path_with_fallback(picture_id)
    if path is None:
        abort(404)
    response = send_file(path, mimetype="image/jpeg", conditional=True)
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# --- защищённая часть ---------------------------------------------------

@app.route("/upload", methods=["GET", "POST"])
@auth.login_required
def upload():
    if request.method == "GET":
        authorityid = request.args.get("authorityid", "").strip()
        name = request.args.get("name", "").strip()  # Новый параметр

        if authorityid:
            if not storage.valid_authorityid(authorityid):
                flash("Некорректный идентификатор источника.", "error")
                return redirect(url_for("index"))
            existing = storage.load_picture(authorityid)
            if existing is not None:
                flash(
                    "Картинка с таким authorityid уже загружена. "
                    "Можете её отредактировать.",
                    "info",
                )
                return redirect(url_for("picture_edit", picture_id=existing.authorityid))

        # Передаём name как prefill для title
        return _form("create", authorityid=authorityid, title=name)

    # POST остаётся без изменений
    authorityid = request.form.get("authorityid", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    file_storage = request.files.get("file")

    if not storage.valid_authorityid(authorityid):
        return _form(
            "create",
            authorityid=authorityid,
            title=title,
            description=description,
            error="Некорректный идентификатор источника.",
        ), 400

    if storage.load_picture(authorityid) is not None:
        return _form(
            "create",
            authorityid=authorityid,
            title=title,
            description=description,
            error="Картинка с этим authorityid уже существует.",
        ), 409

    error = _validate(title, description, file_storage, file_required=True)
    if error:
        return _form(
            "create",
            authorityid=authorityid,
            title=title,
            description=description,
            error=error,
        ), 400

    try:
        record = storage.create_picture(
            authorityid=authorityid,
            title=title,
            description=description,
            stream=file_storage.stream,
            original_filename=secure_filename(file_storage.filename) or "image",
        )
    except storage.StorageError as exc:
        return _form(
            "create",
            authorityid=authorityid,
            title=title,
            description=description,
            error=str(exc),
        ), 400

    flash("Картинка загружена.", "success")
    return redirect(url_for("picture_view", picture_id=record.authorityid))

@app.route("/pictures/<picture_id>/edit", methods=["GET", "POST"])
@auth.login_required
def picture_edit(picture_id):
    record = storage.load_picture(picture_id)
    if record is None:
        abort(404)

    if request.method == "GET":
        return _form("edit", record.authorityid, record.title, record.description)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    file_storage = request.files.get("file")

    error = _validate(title, description, file_storage, file_required=False)
    if error:
        return _form("edit", record.authorityid, title, description, error), 400

    has_file = bool(file_storage and file_storage.filename)
    try:
        storage.update_picture(
            picture_id,
            title,
            description,
            stream=file_storage.stream if has_file else None,
            original_filename=(
                secure_filename(file_storage.filename) if has_file else None
            ),
        )
    except storage.StorageError as exc:
        return _form("edit", record.authorityid, title, description, str(exc)), 400

    flash("Изменения сохранены.", "success")
    return redirect(url_for("picture_view", picture_id=picture_id))


# --- аутентификация -----------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if auth.current_user():
        return redirect(url_for("index"))

    next_url = request.values.get("next", "")
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if auth.authenticate(username, password):
            auth.login_user(username)
            flash("Добро пожаловать.", "success")
            return redirect(auth.safe_next_url(next_url) or url_for("index"))
        error = "Неверное имя или пароль."

    return render_template("login.html", error=error)


@app.post("/logout")
@auth.login_required
def logout():
    auth.logout_user()
    flash("Вы вышли.", "info")
    return redirect(url_for("index"))


# --- ошибки -------------------------------------------------------------

@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(413)
def handle_error(error):
    return (
        render_template("error.html", code=error.code, message=error.description),
        error.code,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
