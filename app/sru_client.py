"""Низкоуровневый клиент для SRU (Search/Retrieve via URL).

Делает HTTP-запросы к SRU-серверам, парсит XML-ответы через
``parsers.py`` и возвращает объекты ``models.py``.

При любой ошибке (сеть, таймаут, невалидный XML, HTTP-ошибка)
возвращает ``None`` или пустой список — приложение не падает,
а роуты показывают блок «Ошибка БД».

Адреса серверов и точки доступа здесь захардкожены как предположения;
в дальнейшем уточняются пользователем.
"""

import logging

import requests

from . import parsers

logger = logging.getLogger(__name__)

# Адреса SRU-серверов (предположения)
BIBLIOGRAPHIC_URL = 'http://localhost:9991/'
AUTHOR_AUTHORITY_URL = 'http://localhost:9999/'
DEPARTMENT_AUTHORITY_URL = 'http://localhost:9999/'  # предположение

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_RECORDS = 500


class SRUClient:
    """Базовый клиент для одного SRU-сервера."""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def search_retrieve(self, query: str, maximum_records: int = DEFAULT_MAX_RECORDS,
                        start_record: int = 1) -> tuple[int, list] | None:
        """Выполняет ``operation=searchRetrieve``.

        Возвращает ``(общее число записей, список XML-элементов записей)``
        или ``None`` при ошибке.
        """
        params = {
            'operation': 'searchRetrieve',
            'query': query,
            'maximumRecords': maximum_records,
            'startRecord': start_record,
        }
        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return parsers.parse_search_retrieve(resp.content)
        except Exception as e:
            logger.warning('SRU searchRetrieve failed for %s: %s', self.base_url, e)
            return None

    def scan(self, scan_clause: str, maximum_terms: int = 100) -> list | None:
        """Выполняет ``operation=scan``.

        Возвращает список терминов ``[{'value': ..., 'count': ...}, ...]``
        или ``None`` при ошибке.
        """
        params = {
            'operation': 'scan',
            'scanClause': scan_clause,
            'maximumTerms': maximum_terms,
        }
        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return parsers.parse_scan(resp.content)
        except Exception as e:
            logger.warning('SRU scan failed for %s: %s', self.base_url, e)
            return None


# Экземпляры клиентов для разных баз
bibliographic = SRUClient(BIBLIOGRAPHIC_URL)
author_authority = SRUClient(AUTHOR_AUTHORITY_URL)
department_authority = SRUClient(DEPARTMENT_AUTHORITY_URL)


# ---------------------------------------------------------------------------
# Индексы авторов
# ---------------------------------------------------------------------------

def get_author_index_letters() -> list[str]:
    """Список букв для верхнего уровня индекса авторов.

    Статический список, не требует запроса к серверу.
    """
    latin = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    cyrillic = list('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    return  cyrillic + latin


def get_author_prefixes_for_letter(letter: str) -> list[dict] | None:
    """Трёхбуквенные префиксы фамилий авторов, начинающихся на ``letter``.

    Использует ``scan`` по точке доступа ``cuba.Author3idx``.
    Результат адаптируется под формат, ожидаемый шаблоном: ключ ``prefix``.
    
    Фильтрует только термины, начинающиеся с указанной буквы,
    потому что SRU scan возвращает все термины после точки старта.
    """
    scan_clause = f'cuba.Author3idx={letter}'
    terms = author_authority.scan(scan_clause, maximum_terms=100)
    if terms is None:
        return None
    # Фильтруем: оставляем только префиксы, начинающиеся на запрошенную букву
    letter_lower = letter.lower()
    filtered = [
        {'prefix': t['value'], 'count': t['count']}
        for t in terms
        if t['value'].lower().startswith(letter_lower)
    ]
    return filtered

def get_authors_by_prefix(prefix: str) -> list | None:
    """Список авторов, чья фамилия начинается с трёхбуквенного префикса."""
    query = f'cuba.Author3idx="{prefix}"'
    result = author_authority.search_retrieve(query, maximum_records=100)
    if result is None:
        return None
    total, records = result
    return [parsers.parse_author_record(r) for r in records]


# ---------------------------------------------------------------------------
# Автор
# ---------------------------------------------------------------------------

def get_author(authority_id: str):
    """Возвращает автора по ``id`` (поле 001 авторитетной записи)."""
    query = f'rec.id={authority_id}'
    result = author_authority.search_retrieve(query, maximum_records=1)
    if result is None:
        return None
    total, records = result
    if not records:
        return None
    return parsers.parse_author_record(records[0])


def get_publications_by_author_code(code_001: str) -> list:
    """Публикации автора по первому коду 035 из авторитетной записи.

    Ищет в библиографической базе по точке доступа ``cuba.AuthorityAuthorCode``.
    """
    query = f'cuba.AuthorityAuthorCode="{code_001}"'
    result = bibliographic.search_retrieve(query, maximum_records=DEFAULT_MAX_RECORDS)
    if result is None:
        return []
    total, records = result
    return [parsers.parse_publication_record(r) for r in records]


def get_publications_about_author(author_id: str) -> list:
    """Публикации об авторе.

    Точка доступа в библио-БД пока не определена; предполагается
    ``cuba.AboutAuthorCode``, ищется по значению 035 авторитетной записи.
    """
    author = get_author(author_id)
    if not author or not author.code_035:
        return []
    query = f'cuba.authorityAboutCode="{author_id}"'
    result = bibliographic.search_retrieve(query, maximum_records=100)
    if result is None:
        return []
    total, records = result
    return [parsers.parse_publication_record(r) for r in records]


# ---------------------------------------------------------------------------
# Публикация
# ---------------------------------------------------------------------------

def get_publication(publication_id: str):
    """Возвращает публикацию по ``id`` (поле 001 библиографической записи)."""
    query = f'rec.id="{publication_id}"'
    result = bibliographic.search_retrieve(query, maximum_records=1)
    if result is None:
        return None
    total, records = result
    if not records:
        return None
    return parsers.parse_publication_record(records[0])


# ---------------------------------------------------------------------------
# Индексы подразделений
# ---------------------------------------------------------------------------

def get_department_index_letters() -> list[str]:
    """Список букв для верхнего уровня индекса подразделений."""
    return get_author_index_letters()


def get_department_prefixes_for_letter(letter: str) -> list[dict] | None:
    """Трёхбуквенные префиксы названий подразделений, начинающихся на ``letter``.

    Точка доступа для подразделений пока не определена; предполагается
    ``cuba.Department3idx``.
    
    Фильтрует только термины, начинающиеся с указанной буквы.
    """
    scan_clause = f'cuba.Department3idx={letter}'
    terms = department_authority.scan(scan_clause, maximum_terms=100)
    if terms is None:
        return None
    # Фильтруем: оставляем только префиксы, начинающиеся на запрошенную букву
    letter_lower = letter.lower()
    filtered = [
        {'prefix': t['value'], 'count': t['count']}
        for t in terms
        if t['value'].lower().startswith(letter_lower)
    ]
    return filtered

def get_departments_by_prefix(prefix: str) -> list | None:
    """Список подразделений, чьё название начинается с префикса."""
    query = f'cuba.Department3idx="{prefix}"'
    result = department_authority.search_retrieve(query, maximum_records=100)
    if result is None:
        return None
    total, records = result
    return [parsers.parse_department_record(r) for r in records]


# ---------------------------------------------------------------------------
# Подразделение
# ---------------------------------------------------------------------------

def get_department(department_id: str):
    """Возвращает подразделение по ``id``.

    При недоступности БД возвращает ``None`` — роут покажет «Ошибка БД».
    """
    query = f'rec.id="{department_id}"'
    result = department_authority.search_retrieve(query, maximum_records=1)
    if result is None:
        return None
    total, records = result
    if not records:
        return None
    return parsers.parse_department_record(records[0])


def get_publications_by_department(department_id: str) -> tuple[int, list]:
    """Публикации подразделения.

    Предполагается, что в библио-БД поле 910$3 содержит ``department_id``
    (поле 001 авторитетной записи подразделения), и есть точка доступа
    ``cuba.DepartmentCode``.
    """
    query = f'cuba.DepartmentCode="{department_id}"'
    result = bibliographic.search_retrieve(query, maximum_records=DEFAULT_MAX_RECORDS)
    if result is None:
        return 0, []
    total, records = result
    publications = [parsers.parse_publication_record(r) for r in records]
    return total, publications


# ---------------------------------------------------------------------------
# Поиск
# ---------------------------------------------------------------------------

def search_publications(query: str, attr: str) -> tuple[int, list]:
    """Поиск публикаций по запросу и атрибуту.

    Используются контексты:
    - ``cql.title`` — заглавие
    - ``cql.author`` — автор
    - ``cuba.DepartmentName`` — подразделение (предположение)
    """
    if attr == 'title':
        cql = f'cql.title="{query}"'
    elif attr == 'author':
        cql = f'cql.author="{query}"'
    elif attr == 'department':
        cql = f'cuba.DepartmentName="{query}"'
    else:
        cql = f'cql.anywhere="{query}"'

    result = bibliographic.search_retrieve(cql, maximum_records=100)
    if result is None:
        return 0, []
    total, records = result
    publications = [parsers.parse_publication_record(r) for r in records]
    return total, publications