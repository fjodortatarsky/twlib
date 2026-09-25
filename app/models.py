"""Типы данных приложения.

Используются и заглушками (``stubs.py``), и парсерами (``parsers.py``).
"""

from dataclasses import dataclass, field


@dataclass
class Author:
    id: str
    main_name: str
    main_name_full: str
    birth_year: int | None = None
    death_year: int | None = None
    description: str | None = None          # биография из 830
    titles: list = field(default_factory=list)  # регалии из 200$c
    orcid: str | None = None
    photo_url: str | None = None
    alternative_names: list = field(default_factory=list)
    codes_001: list = field(default_factory=list)
    codes_035: list = field(default_factory=list)

    @property
    def code_001(self):
        return self.codes_001[0] if self.codes_001 else None
    @property
    def code_035(self):
        return self.codes_035[0] if self.codes_035 else None


@dataclass
class AuthorRef:
    """Ссылка на автора внутри библиографической записи."""
    name: str
    authority_id: str | None = None


@dataclass
class Publication:
    id: str
    title: str
    subtitle: str | None = None
    authors: list = field(default_factory=list)  # list[AuthorRef]
    year: int | None = None
    city: str | None = None
    publisher: str | None = None
    pages: str | None = None
    isbn: str | None = None
    fulltext_url: str | None = None
    department_id: str | None = None


@dataclass
class Department:
    id: str
    name: str
    description: str | None = None
    alternative_names: list = field(default_factory=list)  # list[(name, dates)]