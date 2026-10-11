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
DEFAULT_MAX_TERMS = 500


class SRUClient:
    """Базовый клиент для одного SRU-сервера."""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout


    def search_retrieve(self, query: str, maximum_records: int = DEFAULT_MAX_RECORDS,
                        start_record: int = 1, query_param_name: str = 'query') -> tuple[int, list] | None:
        """Выполняет ``operation=searchRetrieve``.

        Возвращает ``(общее число записей, список XML-элементов записей)``
        или ``None`` при ошибке.

        Параметр ``query_param_name`` позволяет выбрать имя GET-параметра
        для передачи запроса: по умолчанию ``query`` (стандартный CQL),
        но можно задать ``x-pquery`` для CCL/PQF-запросов к серверам Aleph.
        """
        params = {
            'operation': 'searchRetrieve',
            query_param_name: query,
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

    def scan(self, scan_clause: str, maximum_terms: int = DEFAULT_MAX_TERMS) -> list | None:
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

def get_authors_by_letter(letter: str) -> list | None:
    """Список авторов, чья фамилия начинается с буквы."""
    # Ищем по полю фамилии (cuba.AuthorSurname) с маской * в конце
    query = f'cuba.AuthorSurname="{letter}*"'
    result = author_authority.search_retrieve(query, maximum_records=DEFAULT_MAX_RECORDS)
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


def get_publications_by_author_code(
    code_001: str,
    page: int = 1,
    per_page: int = 10,
    sort: str = 'desc',
    content_type: str | None = None,
) -> tuple[int, list]:
    """Публикации автора с серверной пагинацией и сортировкой.

    Использует CCL-запрос через параметр ``x-pquery``:
    поиск по ``@attr 1=Authority-author-code`` и сортировка по атрибуту 31.

    :param code_001: идентификатор авторитетной записи автора.
    :param page: номер страницы (начинается с 1).
    :param per_page: размер страницы (``maximumRecords``).
    :param sort: ``'asc'`` → ``@attr 7=1``, ``'desc'`` → ``@attr 7=2``.
    :return: ``(общее число публикаций, список записей на текущей странице)``.
    """

    sort_attr = '1' if sort == 'asc' else '2'
    
    if content_type:
        ccl = (
            f'@or @and @attr 1=Authority-author-code {code_001} '
            f'@attr 1=Content-type {content_type} @attr 7={sort_attr} @attr 1=31 0'
        )
    else:
        ccl = (
            f'@or @attr 1=Authority-author-code {code_001} '
            f'@attr 7={sort_attr} @attr 1=31 0'
        )

    start_record = (page - 1) * per_page + 1
    result = bibliographic.search_retrieve(
        ccl,
        maximum_records=per_page,
        start_record=start_record,
        query_param_name='x-pquery',
    )
    if result is None:
        return 0, []
    total, records = result
    publications = [parsers.parse_publication_record(r) for r in records]
    return total, publications


def get_publications_count_by_author_code(code_001: str) -> int:
    """Возвращает общее количество публикаций автора без самих записей."""
    ccl = f'@or @attr 1=Authority-author-code {code_001} @attr 7=1 @attr 1=31 0'
    result = bibliographic.search_retrieve(
        ccl,
        maximum_records=0,
        start_record=1,
        query_param_name='x-pquery',
    )
    if result is None:
        return 0
    total, _ = result
    return total

def get_publications_count_by_content_type(code_001: str, content_type: str) -> int:
    """Возвращает количество публикаций автора определенного типа контента."""
    ccl = (
        f'@or @and @attr 1=Authority-author-code {code_001} '
        f'@attr 1=Content-type {content_type} @attr 7=1 @attr 1=31 0'
    )
    result = bibliographic.search_retrieve(
        ccl,
        maximum_records=0,
        start_record=1,
        query_param_name='x-pquery',
    )
    if result is None:
        return 0
    total, _ = result
    return total


def get_publications_about_author(author_id: str) -> list:
    """Публикации об авторе.

    Точка доступа в библио-БД пока не определена; предполагается
    ``cuba.AboutAuthorCode``, ищется по значению 035 авторитетной записи.
    """
    author = get_author(author_id)
    if not author or not author.code_035:
        return []
    query = f'cuba.authorityAboutCode="{author_id}"'
    result = bibliographic.search_retrieve(query, maximum_records=DEFAULT_MAX_RECORDS)
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


def get_departments_by_letter(letter: str) -> list | None:
    """Список подразделений, чьё название начинается с буквы."""
    # Ищем по полю корпоративного автора (cuba.CorpAuthor) с маской * в конце
    query = f'cuba.CorpAuthor="{letter}*"'
    result = department_authority.search_retrieve(query, maximum_records=DEFAULT_MAX_RECORDS)
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
    query = f'cuba.AuthorityCorpCode={department_id}'
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

#bibliographic = SRUClient(BIBLIOGRAPHIC_URL)
#author_authority = SRUClient(AUTHOR_AUTHORITY_URL)
#department_authority = SRUClient(DEPARTMENT_AUTHORITY_URL)

    if attr == 'title':
        cql = f'dc.title="{query}"'
        target = bibliographic
    elif attr == 'author':
        cql = f'cuba.AuthorSurname="{query}"'
        target = author_authority
    elif attr == 'department':
        cql = f'cuba.CorpAuthor="{query}"'
        target = department_authority
    else:
        cql = f'cql.anywhere="{query}"'

    result = target.search_retrieve(cql, maximum_records=DEFAULT_MAX_RECORDS)
    if result is None:
        return 0, []
    total, records = result
    publications = [parsers.parse_publication_record(r) for r in records]
    return total, publications

# ---------------------------------------------------------------------------
# Поиск
# ---------------------------------------------------------------------------

def search_entities(query: str, attr: str) -> tuple[int, list]:
    """Поиск сущностей с применением корректного парсера для каждого типа."""
    
    if attr == 'title':
        cql = f'dc.title="{query}"'
        target = bibliographic
        parser = parsers.parse_publication_record
    elif attr == 'author':
        cql = f'cuba.AuthorSurname="{query}"'
        target = author_authority
        parser = parsers.parse_author_record
    elif attr == 'department':
        cql = f'cuba.CorpAuthor="{query}"'
        target = department_authority
        parser = parsers.parse_department_record
    else:
        cql = f'cql.anywhere="{query}"'
        target = bibliographic
        parser = parsers.parse_publication_record

    result = target.search_retrieve(cql, maximum_records=DEFAULT_MAX_RECORDS)
    if result is None:
        return 0, []
    
    total, records = result
    # Применяем нужный парсер к каждой записи
    entities = [parser(r) for r in records]
    return total, entities
