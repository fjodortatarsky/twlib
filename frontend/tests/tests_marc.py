"""Golden-тесты MarcBibFormatter: текущее форматирование зафиксировано константами.

Структура проекта:
    <root>/app/marc.py          — исходники (не меняются)
    <root>/tests/test_marc.py   — этот файл
    <root>/tests/records/*.xml  — записи

Запуск из корня проекта:
    python -m unittest discover -s tests -v
или напрямую:
    python tests/test_marc.py -v

Обновление эталона после СОЗНАТЕЛЬНОГО изменения формата:
    python tests/test_marc.py --dump   (вывод вставить в константы ниже)
"""
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TESTS_DIR.parent
RECORDS_DIR = TESTS_DIR / "records"

# Корень проекта в sys.path — чтобы "from app.marc import ..." работал
# при любом запуске: unittest, pytest, python tests/test_marc.py, из любого cwd.
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.marc import MarcBibFormatter

# Что сравниваем: cite целиком + его составные части,
# чтобы при расхождении было видно, какой именно домен "поехал".
CHECKED_FIELDS = ("cite", "type", "id", "header", "url") + tuple(f"domain{i}" for i in range(1, 11))

# --- Эталон: records/684564.xml — статья из журнала («Теплоэнергетика») ---
EXPECTED_684564 = {
    "cite": "Федяева, О. Н. Обезвреживание сточных вод и опасных отходов в сверхкритическом водокислородном флюиде (обзор) = Neutralization of effluent water and dangerous waste in supercritical water-oxygen fluid (review) / О. Н. Федяева, П. А. Стрижак // Теплоэнергетика. — 2026. — № 1. — С. 3-17. — URL: https://elibrary.ru/item.asp?id=88778788",
    "type": "analytics",
    "id": "684564",
    "header": "Федяева, О. Н.",
    "url": "https://elibrary.ru/item.asp?id=88778788",
    "domain1": "Обезвреживание сточных вод и опасных отходов в сверхкритическом водокислородном флюиде (обзор) = Neutralization of effluent water and dangerous waste in supercritical water-oxygen fluid (review) / О. Н. Федяева, П. А. Стрижак",
    "domain2": "Теплоэнергетика. — 2026. — № 1. — С. 3-17",
    "domain3": "",
    "domain4": "",
    "domain5": "",
    "domain6": "",
    "domain7": "",
    "domain8": "",
    "domain9": "",
    "domain10": "URL: https://elibrary.ru/item.asp?id=88778788",
}

# --- Эталон: records/685147.xml — статья из сборника конференции ---
EXPECTED_685147 = {
    "cite": "Школа, М. В. Определение оптимальных условий регазификации газового гидрата / М. В. Школа, Н. Е. Шлегель, П. А. Стрижак // Добыча, подготовка, транспорт нефти и газа : материалы XI Международной конференции, посвященной 55-летию Института химии нефти СО РАН, Томск, 29 Сентября-3 Октября 2025. — 2025. — С. 230-231. — URL: https://www.elibrary.ru/item.asp?id=83018260",
    "type": "analytics",
    "id": "685147",
    "header": "Школа, М. В.",
    "url": "https://www.elibrary.ru/item.asp?id=83018260",
    "domain1": "Определение оптимальных условий регазификации газового гидрата / М. В. Школа, Н. Е. Шлегель, П. А. Стрижак",
    "domain2": "Добыча, подготовка, транспорт нефти и газа : материалы XI Международной конференции, посвященной 55-летию Института химии нефти СО РАН, Томск, 29 Сентября-3 Октября 2025. — 2025. — С. 230-231",
    "domain3": "",
    "domain4": "",
    "domain5": "",
    "domain6": "",
    "domain7": "",
    "domain8": "",
    "domain9": "",
    "domain10": "URL: https://www.elibrary.ru/item.asp?id=83018260",
}


class GoldenFormattingTests(unittest.TestCase):
    """Сравнивает вывод форматера с зафиксированными эталонами, символ в символ."""

    maxDiff = None  # показывать полный diff длинных строк

    def _check_record(self, filename, expected):
        path = RECORDS_DIR / filename
        self.assertTrue(path.is_file(), f"Нет файла с записью: {path}")
        data = MarcBibFormatter(path.read_text(encoding="utf-8")).process_response()
        self.assertEqual(len(data), 1, f"В {filename} ожидалась ровно одна запись")
        actual = data[0]
        for field in CHECKED_FIELDS:
            with self.subTest(record=filename, field=field):
                self.assertEqual(actual[field], expected[field])

    def test_684564_journal_article(self):
        self._check_record("684564.xml", EXPECTED_684564)

    def test_685147_conference_paper(self):
        self._check_record("685147.xml", EXPECTED_685147)


def _dump_current_output():
    """Печатает текущий вывод в виде готовых констант (для осознанного обновления эталона)."""
    for filename in ("684564.xml", "685147.xml"):
        rec = MarcBibFormatter((RECORDS_DIR / filename).read_text(encoding="utf-8")).process_response()[0]
        print(f"EXPECTED_{filename.split('.')[0]} = {{")
        for field in CHECKED_FIELDS:
            print(f"    {field!r}: {rec[field]!r},")
        print("}\n")


if __name__ == "__main__":
    if "--dump" in sys.argv:
        _dump_current_output()
    else:
        unittest.main()
