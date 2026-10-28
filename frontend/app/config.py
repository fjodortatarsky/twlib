import os

class Config:
    # Строковые значения: берем из окружения, если нет — используем дефолт
    KOHA_URL_PREFIX = os.getenv(
        "KOHA_URL_PREFIX", 
        "https://koha.lib.tpu.ru/cgi-bin/koha/opac-detail.pl?biblionumber="
    )
    BIBLIOGRAPHIC_URL = os.getenv(
        "BIBLIOGRAPHIC_URL", 
        "http://localhost:9991/"
    )
    AUTHOR_AUTHORITY_URL = os.getenv(
        "AUTHOR_AUTHORITY_URL", 
        "http://localhost:9999/"
    )
    DEPARTMENT_AUTHORITY_URL = os.getenv(
        "DEPARTMENT_AUTHORITY_URL", 
        "http://localhost:9999/"
    )

    # Числовые значения: обязательно оборачиваем в int(), так как getenv возвращает строку
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "10"))
    DEFAULT_MAX_RECORDS = int(os.getenv("DEFAULT_MAX_RECORDS", "500"))
    DEFAULT_MAX_TERMS = int(os.getenv("DEFAULT_MAX_TERMS", "500"))
