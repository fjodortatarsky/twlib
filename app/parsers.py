"""Парсеры SRU-ответов (MARC21 XML) в типы данных приложения.

Используется совместно с ``sru_client.py``: клиент получает
тело ответа как строку, парсер превращает её в объекты ``models.py``.

Форматы, с которыми работаем:
- ``searchRetrieve``: обёртка ``zs:searchRetrieveResponse``, внутри
  ``zs:records/zs:record/zs:recordData/record`` (MARC21).
- ``scan``: обёртка ``zs:scanResponse``, внутри ``zs:terms/zs:term``.
"""

import xml.etree.ElementTree as ET

from .models import Author, AuthorRef, Department, Publication

# Пространства имён
NS = {
    'zs': 'http://docs.oasis-open.org/ns/search-ws/sruResponse',
    'scan': 'http://docs.oasis-open.org/ns/search-ws/scan',
    'marc': 'http://www.loc.gov/MARC21/slim',
}

MARC = '{http://www.loc.gov/MARC21/slim}'
ZS = '{http://docs.oasis-open.org/ns/search-ws/sruResponse}'
SCAN = '{http://docs.oasis-open.org/ns/search-ws/scan}'


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _get_first_subfield(datafield, code):
    """Возвращает текст первого подполя с указанным кодом или ``None``."""
    for sf in datafield.findall(f'{MARC}subfield'):
        if sf.get('code') == code:
            return sf.text or ''
    return None


def _get_all_subfields(datafield, code):
    """Возвращает список текстов всех подполей с указанным кодом."""
    result = []
    for sf in datafield.findall(f'{MARC}subfield'):
        if sf.get('code') == code:
            result.append(sf.text or '')
    return result


def _get_controlfield(record, tag):
    """Возвращает текст контрольного поля или ``None``."""
    cf = record.find(f'{MARC}controlfield[@tag="{tag}"]')
    return cf.text if cf is not None else None


def _find_datafields(record, tag):
    """Возвращает список всех полей с указанным тегом."""
    return record.findall(f'{MARC}datafield[@tag="{tag}"]')


def _parse_name_from_field(df):
    """Извлекает имя из поля авторитетной записи (200 / 500 / 700)."""
    a = _get_first_subfield(df, 'a')   # фамилия
    b = _get_first_subfield(df, 'b')   # инициалы
    g = _get_first_subfield(df, 'g')   # полное имя
    f = _get_first_subfield(df, 'f')   # годы жизни
    name = ' '.join(filter(None, [a, b]))
    full = ' '.join(filter(None, [a, g]))
    return {
        'name': name,
        'full': full,
        'years': f,
    }


def _parse_years_range(years_str):
    """Разбирает строку вида ``1955-`` или ``1942-2020`` в два числа."""
    if not years_str:
        return None, None
    parts = years_str.split('-')
    birth = None
    death = None
    try:
        if parts[0]:
            birth = int(parts[0])
        if len(parts) > 1 and parts[1]:
            death = int(parts[1])
    except ValueError:
        pass
    return birth, death


# ---------------------------------------------------------------------------
# Парсинг оболочек (searchRetrieve / scan)
# ---------------------------------------------------------------------------

def parse_search_retrieve(xml_string: str) -> tuple[int, list]:
    """Разбирает ответ ``searchRetrieve``.

    Возвращает ``(общее число записей, список XML-элементов записей)``.
    Каждый элемент списка — это ``<record>`` из пространства имён MARC21,
    готовый к передаче в ``parse_author_record`` / ``parse_publication_record``
    / ``parse_department_record``.
    """
    root = ET.fromstring(xml_string)

    num_elem = root.find(f'{ZS}numberOfRecords')
    num_records = int(num_elem.text) if num_elem is not None else 0

    records = []
    for record_wrapper in root.findall(f'{ZS}records/{ZS}record'):
        record_data = record_wrapper.find(f'{ZS}recordData')
        if record_data is not None:
            marc_record = record_data.find(f'{MARC}record')
            if marc_record is not None:
                records.append(marc_record)

    return num_records, records


def parse_scan(xml_string: str) -> list[dict]:
    """Разбирает ответ ``scan``.

    Возвращает список терминов вида
    ``[{'value': 'Ива', 'count': 5}, ...]``.
    """
    root = ET.fromstring(xml_string)
    terms = []
    for term in root.findall(f'{SCAN}terms/{SCAN}term'):
        value_elem = term.find(f'{SCAN}value')
        count_elem = term.find(f'{SCAN}numberOfRecords')
        terms.append({
            'value': value_elem.text if value_elem is not None else '',
            'count': int(count_elem.text) if count_elem is not None else 0,
        })
    return terms


# ---------------------------------------------------------------------------
# Парсинг авторитетной записи автора
# ---------------------------------------------------------------------------

def parse_author_record(record) -> Author:
    """Разбирает авторитетную запись автора (формат ``<record>`` MARC21).

    Логика извлечения имени:
    - основная форма — из поля 700 (предпочтительно) или 200;
    - альтернативные имена — из полей 500 (параллельные формы).
    """
    record_id = _get_controlfield(record, '001') or ''

    # Коды 035 (может быть несколько; первый — ключ для поиска публикаций)
    codes_035 = []
    for df in _find_datafields(record, '035'):
        a = _get_first_subfield(df, 'a')
        if a:
            codes_035.append(a)

    # --- Основная форма имени: из поля 200 ---
    main_name = ''
    main_name_full = ''
    birth_year = None
    death_year = None

    df_200_list = _find_datafields(record, '200')
    if df_200_list:
        parsed = _parse_name_from_field(df_200_list[0])
        main_name = parsed['name']
        main_name_full = parsed['full']
        birth_year, death_year = _parse_years_range(parsed['years'])

    # --- Альтернативные имена: из полей 500 ---
    # --- Альтернативные имена: из полей 500 ---
    alternative_names = []
    for df in _find_datafields(record, '500'):
        parsed = _parse_name_from_field(df)
        # Пропускаем, если форма совпадает с основной
        if parsed['name'] == main_name or parsed['full'] == main_name_full:
            continue
        alt_id = _get_first_subfield(df, '3')  # ← ID связанной авторитетной записи
        alternative_names.append({
            'name': parsed['name'],
            'full': parsed['full'],
            'note': 'связанная форма имени',
            'id': alt_id,  # ← None, если $3 отсутствует
        })

    # --- Регалии: повторяющиеся подполя 200$c ---
    titles = []
    for df in df_200_list:  # df_200_list уже собран выше
        titles.extend(_get_all_subfields(df, 'c'))

    # --- Биографическая информация: 830$a ---
    description = None
    df_830_list = _find_datafields(record, '830')
    if df_830_list:
        description = _get_first_subfield(df_830_list[0], 'a')
    # Фото / профиль: 856$u
    photo_url = None
    for df in _find_datafields(record, '856'):
        u = _get_first_subfield(df, 'u')
        if u:
            photo_url = u
            break

    # ORCID: обычно в 024 с подполем $2 = "orcid" или в $a
    orcid = None
    for df in _find_datafields(record, '024'):
        a = _get_first_subfield(df, 'a')
        ind = df.get('ind1')
        if a and (ind == '2' or 'orcid' in a.lower()):
            orcid = a
            break

    return Author(
        id=record_id,
        main_name=main_name,
        main_name_full=main_name_full,
        birth_year=birth_year,
        death_year=death_year,
        description=description,      # ← из 830
        titles=titles,                # ← из 200$c
        orcid=orcid,
        photo_url=photo_url,
        alternative_names=alternative_names,
        codes_035=codes_035,
    )

# ---------------------------------------------------------------------------
# Парсинг библиографической записи
# ---------------------------------------------------------------------------

def parse_publication_record(record) -> Publication:
    """Разбирает библиографическую запись (формат ``<record>`` MARC21)."""
    record_id = _get_controlfield(record, '001') or ''

    # Заглавие и подзаголовок: 200
    title = ''
    subtitle = None
    df_200_list = _find_datafields(record, '200')
    if df_200_list:
        df_200 = df_200_list[0]
        title = _get_first_subfield(df_200, 'a') or ''
        subtitle = _get_first_subfield(df_200, 'e')

    # Авторы: 700, 701, 702
    authors = []
    for tag in ('700', '701', '702'):
        for df in _find_datafields(record, tag):
            a = _get_first_subfield(df, 'a')
            b = _get_first_subfield(df, 'b')
            name = ' '.join(filter(None, [a, b]))
            authority_id = _get_first_subfield(df, '3')
            authors.append(AuthorRef(name=name, authority_id=authority_id))

    # Издательские данные: 210
    city = None
    publisher = None
    year = None
    df_210_list = _find_datafields(record, '210')
    if df_210_list:
        df_210 = df_210_list[0]
        city = _get_first_subfield(df_210, 'a')
        publisher = _get_first_subfield(df_210, 'c')
        year_str = _get_first_subfield(df_210, 'd')
        if year_str:
            try:
                year = int(year_str[:4])
            except ValueError:
                year = None

    # Объём: 215$a
    pages = None
    df_215_list = _find_datafields(record, '215')
    if df_215_list:
        pages = _get_first_subfield(df_215_list[0], 'a')

    # ISBN: 010$a
    isbn = None
    df_010_list = _find_datafields(record, '010')
    if df_010_list:
        isbn = _get_first_subfield(df_010_list[0], 'a')

    # URL полного текста: 856$u
    fulltext_url = None
    for df in _find_datafields(record, '856'):
        u = _get_first_subfield(df, 'u')
        if u:
            fulltext_url = u
            break

    # Подразделение: 910$3 (ссылка на авторитетную запись подразделения)
    department_id = None
    df_910_list = _find_datafields(record, '910')
    if df_910_list:
        department_id = _get_first_subfield(df_910_list[0], '3')

    return Publication(
        id=record_id,
        title=title,
        subtitle=subtitle,
        authors=authors,
        year=year,
        city=city,
        publisher=publisher,
        pages=pages,
        isbn=isbn,
        fulltext_url=fulltext_url,
        department_id=department_id,
    )


# ---------------------------------------------------------------------------
# Парсинг авторитетной записи подразделения
# ---------------------------------------------------------------------------

def parse_department_record(record) -> Department:
    """Разбирает авторитетную запись подразделения.

    Пока заглушка — формат БД подразделений ещё не определён.
    Извлекаем базовые поля по аналогии с авторами.
    """
    record_id = _get_controlfield(record, '001') or ''

    # Название: 200$a
    name = ''
    df_200_list = _find_datafields(record, '200')
    if df_200_list:
        name = _get_first_subfield(df_200_list[0], 'a') or ''

    # Прежние названия: 500 (параллельные формы)
    alternative_names = []
    for df in _find_datafields(record, '500'):
        a = _get_first_subfield(df, 'a')
        if a:
            alternative_names.append((a, ''))

    return Department(
        id=record_id,
        name=name,
        description=None,
        alternative_names=alternative_names,
    )