"""Функции-заглушки для приложения «Труды учёных».

Сейчас все данные берутся из фейковых словарей, определённых ниже.
В дальнейшем каждая функция заменяется реальным вызовом
``sru_client.py`` (SRU-запрос → парсинг MARC → возврат объектов),
при этом сигнатуры функций и структура возвращаемых данных остаются прежними,
чтобы ``routes.py`` не требовал изменений.

Правило обработки ошибок:
- Если БД недоступна, функция возвращает ``None`` вместо данных.
- Роуты в ``routes.py`` знают об этом и показывают блок «Ошибка БД».
"""

from dataclasses import dataclass, field
from .models import Author, AuthorRef, Department, Publication

# ---------------------------------------------------------------------------
# Фейковые данные
# ---------------------------------------------------------------------------

AUTHORS: dict[str, Author] = {
    "AUTH-001": Author(
        id="AUTH-001",
        main_name="Абрамов И. П.",
        main_name_full="Абрамов Иван Петрович",
        birth_year=1950,
        description="Специалист по математической физике, доктор физико-математических наук.",
        orcid=None,
        photo_url=None,
        alternative_names=[],
        codes_035=["(RuTPU)RU\\TPU\\pers\\10001"],
    ),
    "AUTH-002": Author(
        id="AUTH-002",
        main_name="Белова Н. С.",
        main_name_full="Белова Наталья Сергеевна",
        birth_year=1965,
        description="Историк науки, исследователь наследия М. В. Ломоносова.",
        orcid="0000-0002-1825-0097",
        photo_url="https://i.pravatar.cc/180x220?img=47",
        alternative_names=[],
        codes_035=["(RuTPU)RU\\TPU\\pers\\10002"],
    ),
    "AUTH-003": Author(
        id="AUTH-003",
        main_name="Волкова Д. А.",
        main_name_full="Волкова Дарья Александровна",
        birth_year=1978,
        description="Лингвист, специалист по древним языкам.",
        orcid=None,
        photo_url=None,
        alternative_names=[
            {"name": "Смирнова Д. А.", "full": "Смирнова Дарья Александровна", "note": "девичья фамилия"},
        ],
        codes_035=["(RuTPU)RU\\TPU\\pers\\10003"],
    ),
    "AUTH-004": Author(
        id="AUTH-004",
        main_name="Иванов Ю. Ф.",
        main_name_full="Иванов Юрий Федорович",
        birth_year=1955,
        description="Физик, профессор Томского политехнического университета.",
        orcid=None,
        photo_url=None,
        alternative_names=[
            {"name": "Ivanov Yu. F.", "full": "Ivanov Yuriy Fedorovich", "note": "транслитерация"},
        ],
        # Два кода 035 — как в реальном примере. Для поиска берём первый.
        codes_035=["(RuTPU)RU\\TPU\\pers\\33559", "RU\\TPU\\pers\\28208"],
    ),
    "AUTH-005": Author(
        id="AUTH-005",
        main_name="Кузнецов А. В.",
        main_name_full="Кузнецов Алексей Викторович",
        birth_year=1942,
        death_year=2020,
        description="Инженер-механик, заслуженный деятель науки.",
        orcid=None,
        photo_url=None,
        alternative_names=[],
        codes_035=["(RuTPU)RU\\TPU\\pers\\10005"],
    ),
    "AUTH-006": Author(
        id="AUTH-006",
        main_name="Смирнова А. П.",
        main_name_full="Смирнова Анна Павловна",
        birth_year=1965,
        description="Литературовед, специалист по русской литературе Серебряного века.",
        orcid="0000-0003-1415-9265",
        photo_url=None,
        alternative_names=[],
        codes_035=["(RuTPU)RU\\TPU\\pers\\10006"],
    ),
}

DEPARTMENTS: dict[str, Department] = {
    "DEP-001": Department(
        id="DEP-001",
        name="Институт физики",
        description="Ведущее подразделение в области теоретической и экспериментальной физики.",
        alternative_names=[
            ("Физико-технический факультет", "1930–1995"),
        ],
    ),
    "DEP-002": Department(
        id="DEP-002",
        name="Кафедра высшей математики",
        description="Обеспечивает математическую подготовку студентов всех факультетов.",
        alternative_names=[],
    ),
    "DEP-003": Department(
        id="DEP-003",
        name="Факультет истории",
        description="Историческое подразделение (временно недоступно в БД).",
        alternative_names=[
            ("Исторический факультет", "1920–2005"),
        ],
    ),
}

PUBLICATIONS: dict[str, Publication] = {
    "PUB-001": Publication(
        id="PUB-001",
        title="Основы математической физики",
        subtitle="Учебное пособие",
        authors=[AuthorRef("Абрамов И. П.", "AUTH-001")],
        year=2010,
        city="Томск",
        publisher="Изд-во ТПУ",
        pages="320 с.",
        isbn="978-5-4387-0001-1",
        fulltext_url=None,
        department_id="DEP-002",
    ),
    "PUB-002": Publication(
        id="PUB-002",
        title="Уравнения с частными производными",
        subtitle="Курс лекций",
        authors=[AuthorRef("Абрамов И. П.", "AUTH-001")],
        year=2015,
        city="Томск",
        publisher="Изд-во ТПУ",
        pages="210 с.",
        isbn="978-5-4387-0002-8",
        fulltext_url="https://library.tpu.ru/fulltext/PUB-002.pdf",
        department_id="DEP-002",
    ),
    "PUB-003": Publication(
        id="PUB-003",
        title="М. В. Ломоносов и становление российской науки",
        subtitle="Монография",
        authors=[AuthorRef("Белова Н. С.", "AUTH-002")],
        year=2018,
        city="Санкт-Петербург",
        publisher="Наука",
        pages="456 с.",
        isbn="978-5-02-038001-2",
        fulltext_url=None,
        department_id="DEP-003",
    ),
    "PUB-004": Publication(
        id="PUB-004",
        title="Древнегреческий язык для начинающих",
        subtitle="Учебник",
        authors=[AuthorRef("Волкова Д. А.", "AUTH-003")],
        year=2020,
        city="Москва",
        publisher="Высшая школа",
        pages="288 с.",
        isbn="978-5-06-007001-3",
        fulltext_url=None,
        department_id="DEP-003",
    ),
    "PUB-005": Publication(
        id="PUB-005",
        title="Квантовая механика в задачах",
        subtitle="Учебное пособие",
        authors=[AuthorRef("Иванов Ю. Ф.", "AUTH-004")],
        year=2012,
        city="Томск",
        publisher="Изд-во ТПУ",
        pages="256 с.",
        isbn="978-5-4387-0003-5",
        fulltext_url="https://library.tpu.ru/fulltext/PUB-005.pdf",
        department_id="DEP-001",
    ),
    "PUB-006": Publication(
        id="PUB-006",
        title="Физика плазмы и управляемый термоядерный синтез",
        subtitle="Монография",
        authors=[
            AuthorRef("Иванов Ю. Ф.", "AUTH-004"),
            AuthorRef("Кузнецов А. В.", "AUTH-005"),
        ],
        year=2016,
        city="Москва",
        publisher="Энергоатомиздат",
        pages="412 с.",
        isbn="978-5-283-0004-6",
        fulltext_url=None,
        department_id="DEP-001",
    ),
    "PUB-007": Publication(
        id="PUB-007",
        title="Детали машин и основы конструирования",
        subtitle="Учебник",
        authors=[AuthorRef("Кузнецов А. В.", "AUTH-005")],
        year=2008,
        city="Томск",
        publisher="Изд-во ТПУ",
        pages="380 с.",
        isbn="978-5-4387-0004-2",
        fulltext_url=None,
        department_id="DEP-001",
    ),
    "PUB-008": Publication(
        id="PUB-008",
        title="Русская литература Серебряного века",
        subtitle="Антология",
        authors=[AuthorRef("Смирнова А. П.", "AUTH-006")],
        year=2019,
        city="Москва",
        publisher="Художественная литература",
        pages="512 с.",
        isbn="978-5-280-03005-7",
        fulltext_url=None,
        department_id="DEP-003",
    ),
    "PUB-009": Publication(
        id="PUB-009",
        title="Поэтика символизма",
        subtitle="Исследование",
        authors=[AuthorRef("Смирнова А. П.", "AUTH-006")],
        year=2022,
        city="Санкт-Петербург",
        publisher="Академический проект",
        pages="296 с.",
        isbn="978-5-8291-0006-8",
        fulltext_url=None,
        department_id="DEP-003",
    ),
    "PUB-010": Publication(
        id="PUB-010",
        title="Сборник задач по теоретической механике",
        subtitle="Учебное пособие",
        authors=[
            AuthorRef("Абрамов И. П.", "AUTH-001"),
            AuthorRef("Кузнецов А. В.", "AUTH-005"),
        ],
        year=2021,
        city="Томск",
        publisher="Изд-во ТПУ",
        pages="180 с.",
        isbn="978-5-4387-0007-3",
        fulltext_url="https://library.tpu.ru/fulltext/PUB-010.pdf",
        department_id="DEP-001",
    ),
}

# Публикации об авторах (ключ — id автора, значение — список id публикаций)
PUBLICATIONS_ABOUT_AUTHOR: dict[str, list[str]] = {
    "AUTH-004": ["PUB-006"],
    "AUTH-002": ["PUB-003"],
}


# ---------------------------------------------------------------------------
# Индексы (двухуровневые)
# ---------------------------------------------------------------------------

def get_author_index_letters() -> list[str]:
    """Список букв для верхнего уровня индекса авторов (латиница + кириллица)."""
    latin = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    cyrillic = list("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
    return latin + cyrillic


def get_author_prefixes_for_letter(letter: str) -> list[dict]:
    """Трёхбуквенные префиксы фамилий авторов, начинающихся на ``letter``,
    с количеством авторов на каждый префикс."""
    prefixes: dict[str, int] = {}
    for author in AUTHORS.values():
        surname = author.main_name.split()[0] if author.main_name else ""
        if surname.startswith(letter):
            prefix = surname[:3]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return [{"prefix": p, "count": c} for p, c in sorted(prefixes.items())]


def get_authors_by_prefix(prefix: str) -> list[Author]:
    """Список авторов, чья фамилия начинается с трёхбуквенного префикса."""
    result = []
    for author in AUTHORS.values():
        surname = author.main_name.split()[0] if author.main_name else ""
        if surname.startswith(prefix):
            result.append(author)
    return sorted(result, key=lambda a: a.main_name)


def get_department_index_letters() -> list[str]:
    """Список букв для верхнего уровня индекса подразделений."""
    return get_author_index_letters()


def get_department_prefixes_for_letter(letter: str) -> list[dict]:
    """Трёхбуквенные префиксы названий подразделений, начинающихся на ``letter``."""
    prefixes: dict[str, int] = {}
    for dep in DEPARTMENTS.values():
        if dep.name.startswith(letter):
            prefix = dep.name[:3]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return [{"prefix": p, "count": c} for p, c in sorted(prefixes.items())]


def get_departments_by_prefix(prefix: str) -> list[Department]:
    """Список подразделений, чьё название начинается с префикса."""
    result = [dep for dep in DEPARTMENTS.values() if dep.name.startswith(prefix)]
    return sorted(result, key=lambda d: d.name)


# ---------------------------------------------------------------------------
# Получение отдельных записей
# ---------------------------------------------------------------------------

def get_author(authority_id: str) -> Author | None:
    """Возвращает автора по ``id`` или ``None``, если не найден."""
    return AUTHORS.get(authority_id)


def get_department(department_id: str) -> Department | None:
    """Возвращает подразделение или ``None``, если БД недоступна.

    Симуляция недоступности: для ``DEP-003`` возвращаем ``None``,
    чтобы продемонстрировать блок «Ошибка БД» на экране подразделения.
    """
    if department_id == "DEP-003":
        return None  # симулируем, что БД подразделений недоступна
    return DEPARTMENTS.get(department_id)


def get_publication(publication_id: str) -> Publication | None:
    """Возвращает публикацию по ``id`` или ``None``."""
    return PUBLICATIONS.get(publication_id)


# ---------------------------------------------------------------------------
# Публикации автора / об авторе / подразделения
# ---------------------------------------------------------------------------

def get_publications_by_author_code(code_035: str) -> list[Publication]:
    """Публикации автора по первому коду 035 из авторитетной записи.

    В реальной реализации здесь будет поиск в библио-БД
    по точке доступа ``cuba.AuthorityAuthorCode``.
    """
    author = next((a for a in AUTHORS.values() if code_035 in a.codes_035), None)
    if not author:
        return []
    result = []
    for pub in PUBLICATIONS.values():
        if any(ref.authority_id == author.id for ref in pub.authors):
            result.append(pub)
    return result


def get_publications_about_author(author_id: str) -> list[Publication]:
    """Публикации об авторе (пока берём из отдельного фейкового словаря)."""
    pub_ids = PUBLICATIONS_ABOUT_AUTHOR.get(author_id, [])
    return [PUBLICATIONS[pid] for pid in pub_ids if pid in PUBLICATIONS]


def get_publications_by_department(department_id: str) -> tuple[int, list[Publication]]:
    """Публикации подразделения. Возвращает ``(количество, список)``."""
    if department_id == "DEP-003":
        return 0, []  # БД недоступна
    result = [p for p in PUBLICATIONS.values() if p.department_id == department_id]
    return len(result), result


# ---------------------------------------------------------------------------
# Поиск
# ---------------------------------------------------------------------------

def search_publications(query: str, attr: str) -> tuple[int, list[Publication]]:
    """Простой поиск по публикациям. Возвращает ``(количество, список)``."""
    q = query.lower()
    results = []
    for pub in PUBLICATIONS.values():
        if attr == "title":
            if q in pub.title.lower() or (pub.subtitle and q in pub.subtitle.lower()):
                results.append(pub)
        elif attr == "author":
            if any(q in ref.name.lower() for ref in pub.authors):
                results.append(pub)
        elif attr == "department":
            dep = DEPARTMENTS.get(pub.department_id)
            if dep and q in dep.name.lower():
                results.append(pub)
    return len(results), results