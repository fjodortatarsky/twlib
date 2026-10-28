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

from .marc import MarcBibFormatter

import concurrent.futures

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

def _sort_letters(letters: list[str]) -> list[str]:
    """Сортирует список букв: сначала кириллица, потом латиница.

    Очищает список от дублей, спецсимволов и приводит к верхнему регистру.
    """
    cyrillic = list('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
    latin = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

    clean_letters = []
    for l in letters:
        upper_l = l.upper()
        if (upper_l in cyrillic or upper_l in latin) and upper_l not in clean_letters:
            clean_letters.append(upper_l)

    def sort_key(letter):
        if letter in cyrillic:
            return (0, cyrillic.index(letter))
        elif letter in latin:
            return (1, latin.index(letter))
        return (2, letter)

    return sorted(clean_letters, key=sort_key)

def get_author_index_letters() -> list[str]:
    letters_to_check = list('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ') + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

    def check_letter(letter):
        # Ищем хотя бы одну запись. maximum_records=1 достаточно, чтобы узнать total.
        query = f'cuba.AuthorSurname="{letter}*"'
        result = author_authority.search_retrieve(query, maximum_records=1)

        # Возвращаем букву, если сервер ответил и количество записей > 0
        if result and result[0] > 0:
            return letter
        return None

    # Параллельное выполнение в 15 потоков
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        # executor.map сохраняет порядок, но мы все равно будем сортировать
        results = executor.map(check_letter, letters_to_check)

    active_letters = [letter for letter in results if letter]
    return _sort_letters(active_letters)


#def get_author_index_letters() -> list[str]:
#    """Список букв для верхнего уровня индекса авторов.
#
#    Статический список, не требует запроса к серверу.
#    """
#    latin = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
#    cyrillic = list('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
#    return  cyrillic + latin

def get_authors_by_letter(letter: str) -> list | None:
    """Список авторов, чья фамилия начинается с буквы."""
    # Ищем по полю фамилии (cuba.AuthorSurname) с маской * в конце
    query = f'cuba.AuthorSurname="{letter}*"'
    result = author_authority.search_retrieve(query, maximum_records=DEFAULT_MAX_RECORDS)
    if result is None:
        return None
    total, records = result
    return [parsers.parse_author_record(r) for r in records]

def _enrich_publications(publications: list, xml_records: list) -> list:
    """Обогащает объекты публикаций полями cite и header на основе MARCXML."""
    for pub, xml_rec in zip(publications, xml_records):
        try:
            # Передаем сам XML-элемент записи в форматтер
            formatter = MarcBibFormatter(xml_rec)
            fmt_data = formatter.process_response()
            if fmt_data:
                fmt = fmt_data[0]
                # Поддержка как словарей, так и объектов (dataclass/NamedTuple)
                if isinstance(pub, dict):
                    pub['cite'] = fmt.get('cite', '')
                    pub['header'] = fmt.get('header', '')
                else:
                    setattr(pub, 'cite', fmt.get('cite', ''))
                    setattr(pub, 'header', fmt.get('header', ''))
        except Exception as e:
            logger.warning('Ошибка форматирования MARCXML: %s', e)
    return publications

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

def _build_author_ccl_query(ids: list[str], sort_attr: str, content_type: str | None = None) -> str:
    """Формирует CCL-запрос для одного или нескольких ID автора, сохраняя оригинальную структуру."""
    if not ids:
        return ""
    
    # Собираем условия для всех ID через @or
    # Для одного ID: @attr 1=Authority-author-code ID
    # Для двух: @or @attr 1=Authority-author-code ID1 @attr 1=Authority-author-code ID2
    # Для трёх: @or @or @attr 1=Authority-author-code ID1 @attr 1=Authority-author-code ID2 @attr 1=Authority-author-code ID3
    id_query = f"@attr 1=Authority-author-code {ids[0]}"
    for i in range(1, len(ids)):
        id_query = f"@or {id_query} @attr 1=Authority-author-code {ids[i]}"
        
    res = ""
    if content_type:
        res = f"@or @and {id_query} @attr 1=Content-type {content_type} @attr 7={sort_attr} @attr 1=31 0"
    else:
        res = f"@or {id_query} @attr 7={sort_attr} @attr 1=31 0"
    return res

def get_publications_by_author_code(
    code_001: str | list[str],
    page: int = 1,
    per_page: int = 10,
    sort: str = 'desc',
    content_type: str | None = None,
) -> tuple[int, list]:
    if isinstance(code_001, str):
        ids = [code_001]
    else:
        ids = list(dict.fromkeys(code_001))  # Убираем дубликаты, сохраняя порядок

    sort_attr = '1' if sort == 'asc' else '2'
    ccl = _build_author_ccl_query(ids, sort_attr, content_type)

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
    return total, _enrich_publications(publications, records)


def get_publications_count_by_author_code(code_001: str | list[str]) -> int:
    if isinstance(code_001, str):
        ids = [code_001]
    else:
        ids = list(dict.fromkeys(code_001))
        
    ccl = _build_author_ccl_query(ids, '1', None)
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


def get_publications_count_by_content_type(code_001: str | list[str], content_type: str) -> int:
    if isinstance(code_001, str):
        ids = [code_001]
    else:
        ids = list(dict.fromkeys(code_001))
        
    ccl = _build_author_ccl_query(ids, '1', content_type)
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

def get_publications_about_author_count(author_id: str | list[str]) -> int:
    """Возвращает количество публикаций об авторе."""
    if isinstance(author_id, str):
        ids = [author_id]
    else:
        ids = list(dict.fromkeys(author_id))

    if not ids:
        return 0

    has_code_035 = False
    for aid in ids:
        author = get_author(aid)
        if author and author.code_035:
            has_code_035 = True
            break

    if not has_code_035:
        return 0

    about_query = ' or '.join([f'cuba.authorityAboutCode="{aid}"' for aid in ids])
    result = bibliographic.search_retrieve(about_query, maximum_records=0)
    if result is None:
        return 0
    total, _ = result
    return total

def get_publications_about_author(
    author_id: str | list[str],
    page: int = 1,
    per_page: int = 10,
) -> tuple[int, list]:
    """Возвращает (общее число, список публикаций) об авторе с пагинацией."""
    if isinstance(author_id, str):
        ids = [author_id]
    else:
        ids = list(dict.fromkeys(author_id))

    if not ids:
        return 0, []

    # Проверяем наличие code_035 хотя бы у одной из записей автора
    has_code_035 = False
    for aid in ids:
        author = get_author(aid)
        if author and author.code_035:
            has_code_035 = True
            break

    if not has_code_035:
        return 0, []

    # Формируем CQL-запрос с OR для нескольких ID
    about_query = ' or '.join([f'cuba.authorityAboutCode="{aid}"' for aid in ids])

    start_record = (page - 1) * per_page + 1
    result = bibliographic.search_retrieve(
        about_query,
        maximum_records=per_page,
        start_record=start_record,
    )
    if result is None:
        return 0, []
    total, records = result
    publications = [parsers.parse_publication_record(r) for r in records]
    return total, _enrich_publications(publications, records)

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
    publications = [parsers.parse_publication_record(r) for r in records]
    return _enrich_publications(publications, records)[0]


# ---------------------------------------------------------------------------
# Индексы подразделений
# ---------------------------------------------------------------------------

#def get_department_index_letters() -> list[str]:
#    """Список букв для верхнего уровня индекса подразделений."""
#    return get_author_index_letters()
def get_department_index_letters() -> list[str]:
    """Список первых букв названий подразделений."""
    letters_to_check = list('АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ') + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    
    def check_letter(letter):
        query = f'cuba.CorpAuthor="{letter}*"'
        result = department_authority.search_retrieve(query, maximum_records=1)
        if result and result[0] > 0:
            return letter
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(check_letter, letters_to_check)
        
    active_letters = [letter for letter in results if letter]
    return _sort_letters(active_letters)

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
        # ...
    total, records = result
    publications = [parsers.parse_publication_record(r) for r in records]
    return total, _enrich_publications(publications, records)


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
    return total, _enrich_publications(publications, records)

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

    if parser == parsers.parse_publication_record:
        entities = _enrich_publications(entities, records)
    return total, entities

