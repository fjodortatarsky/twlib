"""Маршруты приложения «Труды учёных».

Все данные берутся из функций-заглушек (см. ``stubs.py``).
В дальнейшем заглушки заменяются реальными вызовами
SRU-клиента из ``sru_client.py`` без изменения самих роутов.
"""

from flask import Blueprint, render_template, request

#from . import stubs
from . import sru_client as stubs


bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Главная
# ---------------------------------------------------------------------------

@bp.route("/")
def index():
    """Главная: окно поиска, приветствие и два указателя (авторы, подразделения)."""
    letters = stubs.get_author_index_letters()
    author_letters = []
    for letter in letters:
        prefixes = stubs.get_author_prefixes_for_letter(letter)
        author_letters.append({
            "letter": letter,
            "has_authors": bool(prefixes),
        })

    dep_letters = stubs.get_department_index_letters()
    department_letters = []
    for letter in dep_letters:
        prefixes = stubs.get_department_prefixes_for_letter(letter)
        department_letters.append({
            "letter": letter,
            "has_depts": bool(prefixes),
        })

    return render_template(
        "index.html",
        author_letters=author_letters,
        department_letters=department_letters,
        show_welcome=True,
    )


# ---------------------------------------------------------------------------
# Поиск
# ---------------------------------------------------------------------------

@bp.route("/search")
def search():
    """Результаты поиска по запросу и выбранному атрибуту."""
    query = request.args.get("q", "").strip()
    attr = request.args.get("attr", "title")

    if not query:
        return render_template("search.html", query="", attr=attr, results=[], total=0)

    total, results = stubs.search_publications(query, attr)
    return render_template(
        "search.html",
        query=query,
        attr=attr,
        results=results,
        total=total,
    )


# ---------------------------------------------------------------------------
# Указатель авторов (двухуровневый, серверный, без JS)
# ---------------------------------------------------------------------------

@bp.route("/author-index/<prefix>")
def author_index(prefix):
    """Одна буква → список 3-буквенных префиксов;
    3 буквы → список авторов."""
    prefix = prefix.upper()

    if len(prefix) == 1:
        prefixes = stubs.get_author_prefixes_for_letter(prefix)
        if prefixes is None:  # задел на реальную замену: БД недоступна
            return render_template("error.html", message="Ошибка БД"), 503
        return render_template(
            "author_index.html",
            prefix=prefix,
            level="letter",
            prefixes=prefixes,
        )

    authors = stubs.get_authors_by_prefix(prefix)
    if authors is None:
        return render_template("error.html", message="Ошибка БД"), 503
    return render_template(
        "author_index.html",
        prefix=prefix,
        level="prefix",
        authors=authors,
    )


# ---------------------------------------------------------------------------
# Автор
# ---------------------------------------------------------------------------

@bp.route("/author/<authority_id>")
def author(authority_id):
    """Экран автора: фото, метаданные, публикации, публикации об авторе."""
    author_obj = stubs.get_author(authority_id)
    if not author_obj:
        return render_template("error.html", message="Автор не найден"), 404

    # Публикации автора — по первому коду 035 из авторитетной записи
    publications = stubs.get_publications_by_author_code(author_obj.code_035)
    # Публикации об авторе
    about = stubs.get_publications_about_author(author_obj.id)

    # Сортировка (через GET-параметр, без JS)
    sort = request.args.get("sort", "date")
    if sort == "date":
        publications = sorted(publications, key=lambda p: p.year or 0, reverse=True)
    elif sort == "title":
        publications = sorted(publications, key=lambda p: p.title)

    return render_template(
        "author.html",
        author=author_obj,
        publications=publications,
        about=about,
        sort=sort,
    )


# ---------------------------------------------------------------------------
# Публикация
# ---------------------------------------------------------------------------

@bp.route("/publication/<publication_id>")
def publication(publication_id):
    """Экран публикации: полное библиографическое описание."""
    pub = stubs.get_publication(publication_id)
    if not pub:
        return render_template("error.html", message="Публикация не найдена"), 404
    return render_template("publication.html", publication=pub)


# ---------------------------------------------------------------------------
# Указатель подразделений (двухуровневый, серверный, без JS)
# ---------------------------------------------------------------------------

@bp.route("/department-index/<prefix>")
def department_index(prefix):
    """Одна буква → список 3-буквенных префиксов;
    3 буквы → список подразделений."""
    prefix = prefix.upper()

    if len(prefix) == 1:
        prefixes = stubs.get_department_prefixes_for_letter(prefix)
        if prefixes is None:  # симуляция недоступности БД подразделений
            return render_template("error.html", message="Ошибка БД"), 503
        return render_template(
            "department_index.html",
            prefix=prefix,
            level="letter",
            prefixes=prefixes,
        )

    depts = stubs.get_departments_by_prefix(prefix)
    if depts is None:
        return render_template("error.html", message="Ошибка БД"), 503
    return render_template(
        "department_index.html",
        prefix=prefix,
        level="prefix",
        departments=depts,
    )


# ---------------------------------------------------------------------------
# Подразделение
# ---------------------------------------------------------------------------

@bp.route("/department/<department_id>")
def department(department_id):
    """Экран подразделения. При недоступности БД — блок «Ошибка БД»."""
    dep = stubs.get_department(department_id)
    if not dep:
        # БД недоступна или подразделение не найдено —
        # не рушим приложение, показываем диагностическое сообщение.
        return render_template(
            "department.html",
            department=None,
            error="Ошибка БД",
            publications=[],
        )

    total, publications = stubs.get_publications_by_department(department_id)
    return render_template(
        "department.html",
        department=dep,
        publications=publications,
        error=None,
    )