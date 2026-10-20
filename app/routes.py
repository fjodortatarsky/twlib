"""Маршруты приложения «Труды учёных».

Все данные берутся из функций-заглушек (см. ``stubs.py``).
В дальнейшем заглушки заменяются реальными вызовами
SRU-клиента из ``sru_client.py`` без изменения самих роутов.
"""

from flask import Blueprint, render_template, request, jsonify

#from . import stubs
from . import sru_client as stubs
from . import models


bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Главная
# ---------------------------------------------------------------------------

@bp.route("/")
def index():
    """Главная: окно поиска, приветствие и два указателя (авторы, подразделения)."""
    # Теперь просто отдаём список букв без проверки наличия данных.
    # Проверка делала 118 HTTP-запросов на каждый показ главной страницы.
    letters = stubs.get_author_index_letters()
    author_letters = [{"letter": letter} for letter in letters]

    dep_letters = stubs.get_department_index_letters()
    department_letters = [{"letter": letter} for letter in dep_letters]

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

    total, results = stubs.search_entities(query, attr)
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

@bp.route("/author-index/<letter>")
def author_index(letter):
    """Одна буква → список авторов."""
    letter = letter.upper()

    authors = stubs.get_authors_by_letter(letter)
    if authors is None:
        return render_template("error.html", message="Ошибка БД"), 503
    return render_template(
        "author_index.html",
        letter=letter,
        authors=authors,
    )

# ---------------------------------------------------------------------------
# Связанные авторы
# ---------------------------------------------------------------------------
@bp.route("/linkedauthors/<authority_id>")
def linkedauthors(authority_id):
    """Возвращает JSON с ID автора и всех его альтернативных (связанных) записей."""
    # 1. Делаем ровно один сетевой запрос к SRU (внутри stubs.get_author)
    author_obj = stubs.get_author(authority_id)
    if not author_obj:
        return jsonify({"error": "Автор не найден"}), 404

    # 2. Собираем основной ID
    all_author_ids = [author_obj.id]
    
    # 3. Добавляем ID из связанных записей (поле 500 $9 / $3)
    if author_obj.alternative_names:
        alt_ids = [
            alt['id'] for alt in author_obj.alternative_names 
            if alt.get('id')
        ]
        all_author_ids.extend(alt_ids)
        
    # 4. Удаляем возможные дубликаты, сохраняя порядок (основной ID останется первым)
    all_author_ids = list(dict.fromkeys(all_author_ids))

    # 5. Возвращаем легковесный JSON
    return jsonify({
        "authority_id": authority_id,
        "author_ids": all_author_ids
    })

# ---------------------------------------------------------------------------
# Автор
# ---------------------------------------------------------------------------

@bp.route("/author/<authority_id>")
def author(authority_id):
    """Экран автора: фото, метаданные, публикации (с группировкой по категориям),
    публикации об авторе."""
    author_obj = stubs.get_author(authority_id)
    if not author_obj:
        return render_template("error.html", message="Автор не найден"), 404

    # --- Собираем все ID автора (основной + альтернативные) ---
    all_author_ids = [author_obj.id]
    if author_obj.alternative_names:
        all_author_ids.extend([
            alt['id'] for alt in author_obj.alternative_names if alt.get('id')
        ])
    # Удаляем возможные дубликаты, сохраняя порядок
    all_author_ids = list(dict.fromkeys(all_author_ids))

    # --- Параметры пагинации и сортировки ---
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "date")
    category = request.args.get("category")  # выбранная категория
    per_page = 10

    # Сортировка на сервере:
    # date → по убыванию (сначала новые)
    # title → по возрастанию (по алфавиту)
    direction = "asc" if sort == "title" else "desc"

    # --- Получаем общее количество публикаций (учитывая все ID) ---
    total_all = stubs.get_publications_count_by_author_code(all_author_ids)


    # --- Собираем фасеты (категории) ---
    categories = []
    if total_all > 0:
        for content_type_key, content_type_name in models.CONTENT_TYPES.items():
            count = stubs.get_publications_count_by_content_type(all_author_ids, content_type_key)
            if count > 0:
                categories.append({
                    'key': content_type_key,
                    'name': content_type_name,
                    'count': count,
                })

    # --- Считаем публикации об авторе для фасета ---
    about_count = stubs.get_publications_about_author_count(all_author_ids)

    # --- Запрос публикаций (всегда) ---
    publications = []
    total = 0

    if category == 'about':
        # Публикации об авторе с пагинацией
        total, publications = stubs.get_publications_about_author(
            all_author_ids,
            page=page,
            per_page=per_page,
        )
    elif category and category in models.CONTENT_TYPES:
        # Публикации автора выбранной категории
        total, publications = stubs.get_publications_by_author_code(
            all_author_ids,
            page=page,
            per_page=per_page,
            sort=direction,
            content_type=category,
        )
    else:
        # Все публикации автора (по умолчанию или category='all')
        total, publications = stubs.get_publications_by_author_code(
            all_author_ids,
            page=page,
            per_page=per_page,
            sort=direction,
        )
        if total == 0:
            total = total_all

    # --- Добавляем специальные фасеты ---
    categories.insert(0, {
        'key': 'all',
        'name': 'Все',
        'count': None,
    })
    if about_count > 0:
        categories.append({
            'key': 'about',
            'name': 'Об авторе',
            'count': about_count,
        })

    # --- Построение диапазонов для пагинатора ---
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    page_ranges = []
    for p in range(1, total_pages + 1):
        r_start = (p - 1) * per_page + 1
        r_end = min(p * per_page, total)
        page_ranges.append({
            'page': p,
            'label': f"{r_start}-{r_end}",
            'current': p == page,
        })

    return render_template(
        "author.html",
        author=author_obj,
        publications=publications,
        sort=sort,
        category=category,
        categories=categories,
        total_all=total_all,
        about_count=about_count,
        pagination={
            'current': page,
            'total': total,
            'ranges': page_ranges,
        },
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

@bp.route("/department-index/<letter>")
def department_index(letter):
    """Одна буква → список подразделений."""
    letter = letter.upper()

    departments = stubs.get_departments_by_letter(letter)
    if departments is None:
        return render_template("error.html", message="Ошибка БД"), 503
    return render_template(
        "department_index.html",
        letter=letter,
        departments=departments,
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
