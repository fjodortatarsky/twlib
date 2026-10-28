import lxml.etree as ET
from typing import List, Dict, Any, Union, Optional

class MarcBibFormatter:
    # Пространства имен, используемые в MARCXML и вашем XSLT
    NS = {
        'slim': 'http://www.loc.gov/MARC21/slim',
        'marc': 'http://www.loc.gov/MARC21/slim',
        'zs': 'http://www.loc.gov/zing/srw/',
        'bib': 'http://www.komlog.ru/ns/bib-1.0'
    }

    # Словарь для шаблона dictionary.371a
    DICT_371A = {
        'AM_Agreement': 'Режим доступа: по договору с организацией-держателем ресурса',
        'AM_AgreementTPU': 'Режим доступа: по договору с организацией-держателем ресурса. При регистрации указывать корпоративную почту ТПУ',
        'AM_alexhom': 'Режим доступа: по логину и паролю. Запросить по адресу: alexhom06@tpu.ru',
        'AM_Library_network': 'Режим доступа: из сети НТБ ТПУ',
        'AM_Login_teacher': 'Режим доступа: по логину и паролю, выданному преподавателем',
        'AM_Login_TPU': 'Режим доступа: по корпоративным логину и паролю ТПУ',
        'AM_TPU_network': 'Режим доступа: из корпоративной сети ТПУ',
        'For_staff_use': 'Для получения документов с грифом ДСП пользователь оформляет заявление… Правила оформления смотрите https://lib.tpu.ru/html/catalog-instructions в разделе "Электронный заказ документов"',
        'Not_Home': 'На дом не выдаётся',
        'Foreign_agent': 'Данное сообщение (материал) создано и (или) распространено иностранным СМИ, выполняющим функции иностранного агента, и (или) российским юридическим лицом, выполняющим функции иностранного агента'
    }

    def __init__(self, xml_input: Union[str, bytes, ET._Element]):
        if isinstance(xml_input, (str, bytes)):
            self.root = ET.fromstring(xml_input if isinstance(xml_input, bytes) else xml_input.encode('utf-8'))
        else:
            self.root = xml_input

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---

    def _find_datafields(self, rec: ET._Element, tag: str) -> List[ET._Element]:
        res = []
        # Ищем во всех возможных неймспейсах (slim и marc)
        for df in rec.findall('.//slim:datafield', self.NS) + rec.findall('.//marc:datafield', self.NS):
            if df.get('tag') == tag:
                res.append(df)
        return res

    def get_controlfield(self, rec: ET._Element, tag: str) -> Optional[str]:
        for cf in rec.findall('.//slim:controlfield', self.NS) + rec.findall('.//marc:controlfield', self.NS):
            if cf.get('tag') == tag and cf.text:
                return cf.text.strip()
        return None

    def get_subfield(self, rec: ET._Element, tag: str, code: str, ind1: Optional[str] = None, ind2: Optional[str] = None) -> Optional[str]:
        for df in self._find_datafields(rec, tag):
            if ind1 is not None and df.get('ind1') != ind1: continue
            if ind2 is not None and df.get('ind2') != ind2: continue
            for sf in df.findall('slim:subfield', self.NS) + df.findall('marc:subfield', self.NS):
                if sf.get('code') == code and sf.text:
                    return sf.text.strip()
        return None

    def get_subfields(self, rec: ET._Element, tag: str, code: str, ind1: Optional[str] = None, ind2: Optional[str] = None) -> List[str]:
        res = []
        for df in self._find_datafields(rec, tag):
            if ind1 is not None and df.get('ind1') != ind1: continue
            if ind2 is not None and df.get('ind2') != ind2: continue
            for sf in df.findall('slim:subfield', self.NS) + df.findall('marc:subfield', self.NS):
                if sf.get('code') == code and sf.text:
                    res.append(sf.text.strip())
        return res

    def get_subfield_by_index(self, rec: ET._Element, tag: str, code: str, index: int, ind1: Optional[str] = None, ind2: Optional[str] = None) -> Optional[str]:
        count = 0
        for df in self._find_datafields(rec, tag):
            if ind1 is not None and df.get('ind1') != ind1: continue
            if ind2 is not None and df.get('ind2') != ind2: continue
            for sf in df.findall('slim:subfield', self.NS) + df.findall('marc:subfield', self.NS):
                if sf.get('code') == code and sf.text:
                    if count == index:
                        return sf.text.strip()
                    count += 1
        return None

    def get_leader(self, rec: ET._Element) -> str:
        lead = rec.find('.//slim:leader', self.NS) or rec.find('.//marc:leader', self.NS)
        if lead is not None and lead.text:
            return lead.text
        cf000 = self.get_controlfield(rec, '000')
        return cf000 or ""

    # --- МЕТОДЫ ОПРЕДЕЛЕНИЯ ТИПА ДОКУМЕНТА ---

    def is_patent(self, rec: ET._Element) -> bool:
        return self.get_subfield(rec, '029', 'c') is not None

    def is_monograph(self, rec: ET._Element) -> bool:
        leader = self.get_leader(rec)
        cf001 = self.get_controlfield(rec, '001') or ""
        if len(leader) >= 9:
            # В XSLT: substring(leader, 8, 1) -> индекс 7 в Python (1-based to 0-based)
            if leader[7] == 'm' and leader[8] == '0':
                return True
            if leader[7] == 'm' and leader[8] == ' ' and cf001.startswith('RU/URAIT'):
                return True
        return False

    def is_analytics(self, rec: ET._Element) -> bool:
        return self.get_subfield(rec, '463', 't') is not None

    def is_multilevel_volume(self, rec: ET._Element) -> bool:
        leader = self.get_leader(rec)
        if len(leader) >= 9:
            if leader[7] == 'm' and leader[8] == '2':
                return True
        return False

    # --- ГЕНЕРАЦИЯ ПОЛЕЙ (DOMAINS) ---

    def get_bib_id(self, rec: ET._Element) -> Optional[str]:
        cf001 = self.get_controlfield(rec, '001')
        if cf001: return cf001
        
        for val in self.get_subfields(rec, '035', 'a'):
            if not val.startswith('('): return val
            
        for val in self.get_subfields(rec, '035', 'a'):
            if val.startswith('('): return val.split(')', 1)[1]
        return None

    def get_header(self, rec: ET._Element, link: bool = False) -> str:
        val = ""
        if self.is_patent(rec):
            c = self.get_subfield(rec, '029', 'c') or ""
            b = self.get_subfield(rec, '029', 'b') or ""
            a = self.get_subfield(rec, '029', 'a') or ""
            d = self.get_subfield(rec, '029', 'd') or ""
            val = f"{c} № {b} {a} , {d}".strip()
        elif self.is_monograph(rec) or self.is_analytics(rec) or self.is_multilevel_volume(rec):
            a = self.get_subfield(rec, '700', 'a', ind1=' ', ind2='1')
            b = self.get_subfield(rec, '700', 'b', ind1=' ', ind2='1')
            if a:
                val = f"{a}, {b}" if b else a
            else:
                val = self.get_subfield(rec, '700', 'a', ind1=' ', ind2='0') or ""
                
        if link:
            nine = self.get_subfield(rec, '700', '9')
            if nine and val:
                return f"[{val}](https://koha.lib.tpu.ru/cgi-bin/koha/opac-authoritiesdetail.pl?authid={nine})"
        return val

    def domain1(self, rec: ET._Element) -> str:
        parts = []
        if self.is_patent(rec):
            if a := self.get_subfield(rec, '200', 'a'): parts.append(a)
            if d := self.get_subfield(rec, '200', 'd'): parts.append(f" = {d}")
            for i in range(3):
                if e := self.get_subfield_by_index(rec, '200', 'e', i): parts.append(f" : {e}")
            if f := self.get_subfield(rec, '200', 'f'): parts.append(f" / {f}")
            if g := self.get_subfield(rec, '200', 'g'): parts.append(f" ; {g}")
            
        elif self.is_monograph(rec) or self.is_analytics(rec):
            if a := self.get_subfield(rec, '200', 'a', ind1='1'): parts.append(a)
            if self.is_monograph(rec):
                if h := self.get_subfield(rec, '200', 'h', ind1='1'): parts.append(f". {h}")
                if i := self.get_subfield(rec, '200', 'i', ind1='1'): parts.append(f". {i}")
            if d := self.get_subfield(rec, '200', 'd', ind1='1'): parts.append(f" = {d}")
            if (e := self.get_subfield(rec, '200', 'e', ind1='1')) and e != "-": parts.append(f" : {e}")
            if f := self.get_subfield(rec, '200', 'f', ind1='1'): parts.append(f" / {f}")
            if g := self.get_subfield(rec, '200', 'g', ind1='1'): parts.append(f" ; {g}")
        return "".join(parts)

    def domain2(self, rec: ET._Element) -> str:
        parts = []
        if self.is_patent(rec):
            if a := self.get_subfield(rec, '215', 'a'): parts.append(a)
            if c := self.get_subfield(rec, '215', 'c'): parts.append(f", {c}")
        elif self.is_monograph(rec):
            if a := self.get_subfield(rec, '205', 'a'): parts.append(a)
            if f := self.get_subfield(rec, '205', 'f'): parts.append(f" / {f}")
        elif self.is_analytics(rec):
            t461 = self.get_subfield(rec, '461', 't')
            if t461:
                parts.append(t461)
                if o := self.get_subfield(rec, '461', 'o'): parts.append(f" : {o}")
                if f := self.get_subfield(rec, '461', 'f'): parts.append(f" / {f}")
                if g := self.get_subfield(rec, '461', 'g'): parts.append(f" ; {g}")
                if e := self.get_subfield(rec, '461', 'e'): parts.append(f". — {e}")
                c463, d463 = self.get_subfield(rec, '463', 'c'), self.get_subfield(rec, '463', 'd')
                if d463:
                    s = ". — " + (f"{c463}, " if c463 else "") + d463
                    parts.append(s)
                if t463 := self.get_subfield(rec, '463', 't'): parts.append(f". — {t463}")
                if v463 := self.get_subfield(rec, '463', 'v'): parts.append(f". — {v463}")
            else:
                if t463 := self.get_subfield(rec, '463', 't'): parts.append(t463)
                if o := self.get_subfield(rec, '463', 'o'): parts.append(f" : {o}")
                if f := self.get_subfield(rec, '463', 'f'): parts.append(f" / {f}")
                if g := self.get_subfield(rec, '463', 'g'): parts.append(f" ; {g}")
                if e := self.get_subfield(rec, '463', 'e'): parts.append(f". — {e}")
                c463, d463 = self.get_subfield(rec, '463', 'c'), self.get_subfield(rec, '463', 'd')
                if d463:
                    s = ". — " + (f"{c463}, " if c463 else "") + d463
                    parts.append(s)
                if v463 := self.get_subfield(rec, '463', 'v'): parts.append(f". — {v463}")
            if a371 := self.get_subfield(rec, '371', 'a'):
                if val := self.DICT_371A.get(a371): parts.append(f". — {val}")
        elif self.is_multilevel_volume(rec):
            if t := self.get_subfield(rec, '461', 't'): parts.append(t)
            if l := self.get_subfield(rec, '461', 'l'): parts.append(f". {l.capitalize()}")
            if o := self.get_subfield(rec, '461', 'o'): parts.append(f". {o.capitalize()}")
            if v := self.get_subfield(rec, '461', 'v'): parts.append(f". {v.capitalize()}")
            if f := self.get_subfield(rec, '461', 'f'): parts.append(f" / {f}")
            if g := self.get_subfield(rec, '461', 'g'): parts.append(f" ; {g}")
        return "".join(parts)


    def domain3(self, rec: ET._Element) -> str:
        parts = []
        if self.is_patent(rec):
            if a := self.get_subfield(rec, '317', 'a'): parts.append(a)
        elif self.is_monograph(rec):
            a1 = self.get_subfield_by_index(rec, '210', 'a', 0)
            a2 = self.get_subfield_by_index(rec, '210', 'a', 1)
            c = self.get_subfield(rec, '210', 'c')
            d = self.get_subfield(rec, '210', 'd')
            
            if a1:
                parts.append(a1)
            if a2 and a2 != a1:
                parts.append(f" : {a2}")
            if c:
                parts.append(f" : {c}")
                
            if d:
                # Исправление: добавляем запятую только если уже есть место издания или издательство
                if parts:
                    parts.append(f", {d}")
                else:
                    parts.append(d)
                    
        elif self.is_multilevel_volume(rec):
            if e := self.get_subfield(rec, '461', 'e'): parts.append(e)
        return "".join(parts)

    def domain4(self, rec: ET._Element) -> str:
        parts = []
        if self.is_monograph(rec):
            if a := self.get_subfield(rec, '215', 'a'): parts.append(a)
            if c := self.get_subfield(rec, '215', 'c'): parts.append(f" : {c}")
            if e := self.get_subfield(rec, '215', 'e'): parts.append(f" + {e}")
        elif self.is_multilevel_volume(rec):
            c = self.get_subfield(rec, '461', 'c')
            n = self.get_subfield(rec, '461', 'n')
            d = self.get_subfield(rec, '210', 'd')
            
            if c: parts.append(c)
            if n: parts.append(f" : {n}")
            
            if d:
                # То же исправление для многотомных изданий
                if parts:
                    parts.append(f", {d}")
                else:
                    parts.append(d)
        return "".join(parts)

    def domain5(self, rec: ET._Element) -> str:
        parts = []
        if self.is_monograph(rec):
            a = self.get_subfield(rec, '225', 'a', ind1='1')
            v = self.get_subfield(rec, '225', 'v', ind1='1')
            x = self.get_subfield(rec, '225', 'x', ind1='1')
            val = (a or "") + (f"; {v}" if v else "") + (f", {x}" if x else "")
            if val: parts.append(f"({val})")
        elif self.is_multilevel_volume(rec):
            if a := self.get_subfield(rec, '215', 'a'): parts.append(a)
            if c := self.get_subfield(rec, '215', 'c'): parts.append(f" : {c}")
            if e := self.get_subfield(rec, '215', 'e'): parts.append(f" + {e}")
        return "".join(parts)

    def domain6(self, rec: ET._Element) -> str:
        has_029 = any(df.get('tag') == '029' for df in self._find_datafields(rec, '029')) # Проверка наличия поля 029
        if has_029 or self.get_subfield(rec, '029', 'a'): 
            if a := self.get_subfield(rec, '300', 'a'): return a
        return ""

    def domain7(self, rec: ET._Element) -> str:
        return self.get_subfield(rec, '333', 'a') or "" if self.is_monograph(rec) else ""

    def domain8(self, rec: ET._Element) -> str:
        parts = []
        if self.is_monograph(rec):
            if a := self.get_subfield(rec, '371', 'a'):
                if val := self.DICT_371A.get(a): parts.append(val)
            if b := self.get_subfield(rec, '371', 'b'): parts.append(f", {b}")
            if c := self.get_subfield(rec, '371', 'c'): parts.append(f", {c}")
        return "".join(parts)

    def domain9(self, rec: ET._Element) -> str:
        if self.is_multilevel_volume(rec):
            if a := self.get_subfield(rec, '371', 'a'): return self.DICT_371A.get(a, "")
        return ""

    def domain10(self, rec: ET._Element) -> str:
        if u := self.get_subfield(rec, '856', 'u'): return f"URL: {u}"
        return ""

    def get_other_authors(self, rec: ET._Element) -> List[str]:
        res = []
        for df in self._find_datafields(rec, '702'):
            a = self.get_subfield_from_df(df, 'a')
            g = self.get_subfield_from_df(df, 'g')
            three = self.get_subfield_from_df(df, '3')
            val = f"[{a}, {g}]"
            if three:
                idx = three.find(')')
                if idx != -1:
                    val += f"(names/document/{three[idx+1:]})"
            res.append(val)
        return res

    def get_subjects(self, rec: ET._Element) -> List[str]:
        res = []
        for df in self._find_datafields(rec, '606'):
            a = self.get_subfield_from_df(df, 'a')
            x = self.get_subfield_from_df(df, 'x')
            three = self.get_subfield_from_df(df, '3')
            two = self.get_subfield_from_df(df, '2')
            
            val = f"[{a}"
            if a: val += f" - {x}"
            val += "]"
            if three:
                idx = three.find('(RuTPU)')
                if idx != -1: val += f"(subje/document/{three[idx+7:]})"
            if two: val += f" ({two})"
            res.append(val)
            
        for df in self._find_datafields(rec, '610'):
            if a := self.get_subfield_from_df(df, 'a'): res.append(a)
        return res

    def get_subfield_from_df(self, df: ET._Element, code: str) -> str:
        for sf in df.findall('slim:subfield', self.NS) + df.findall('marc:subfield', self.NS):
            if sf.get('code') == code and sf.text:
                return sf.text.strip()
        return ""

    def get_cite(self, rec: ET._Element) -> str:
        header = self.get_header(rec)
        domains = [
            self.domain2(rec), self.domain3(rec), self.domain4(rec), self.domain5(rec),
            self.domain6(rec), self.domain7(rec), self.domain8(rec), self.domain9(rec), self.domain10(rec)
        ]
        
        content = ""
        if header:
            content += header
            if not content.endswith('.'): content += "."
            content += " "
            
        content += self.domain1(rec)
        if self.is_analytics(rec): content += " // "
            
        valid_domains = [d for d in domains if d]
        if valid_domains:
            if content and not(self.is_analytics(rec)) and not(self.is_multilevel_volume(rec)):
                content += ". — "
            content += ". — ".join(valid_domains)
            
        # Реализация шаблона dedot
        while ".." in content:
            content = content.replace("..", ".")
            
        return content.strip()

    # --- ГЛАВНЫЕ МЕТОДЫ ОБРАБОТКИ ---

    def process_single_record(self, rec: ET._Element) -> Dict[str, Any]:
        """Возвращает данные по одной записи в виде словаря"""
        return {
            'id': self.get_bib_id(rec),
            'header': self.get_header(rec),
            'domain1': self.domain1(rec),
            'domain2': self.domain2(rec),
            'domain3': self.domain3(rec),
            'domain4': self.domain4(rec),
            'domain5': self.domain5(rec),
            'domain6': self.domain6(rec),
            'domain7': self.domain7(rec),
            'domain8': self.domain8(rec),
            'domain9': self.domain9(rec),
            'domain10': self.domain10(rec),
            'other_authors': self.get_other_authors(rec),
            'subjects': self.get_subjects(rec),
            'cite': self.get_cite(rec),
            'url': self.get_subfield(rec, '856', 'u'),
            'referat': self.get_subfield(rec, '330', 'a')
        }

    def process_response(self) -> List[Dict[str, Any]]:
        """Парсит весь SRU ответ (или одиночные записи) и возвращает список словарей"""
        records_data = []
        # Пытаемся найти записи внутри zs:searchRetrieveResponse
        records = self.root.findall('.//zs:recordData/slim:record', self.NS)
        if not records:
            # Фоллбек, если передан просто один slim:record или другая структура
            records = self.root.findall('.//slim:record', self.NS) or [self.root]

        for rec in records:
            records_data.append(self.process_single_record(rec))
            
        return records_data

    def to_xml_string(self) -> str:
        """
        Генерирует XML-строку, полностью идентичную выводу вашего XSLT.
        """
        response = ET.Element("response")
        ET.SubElement(response, "numberOfRecords").text = str(len(self.root.findall('.//zs:recordData', self.NS)))
        ET.SubElement(response, "recordConversionType").text = "bibliography"
        
        records_nodes = self.root.findall('.//zs:records/zs:record', self.NS)
        if not records_nodes:
            records_nodes = self.root.findall('.//slim:record', self.NS)

        for r_node in records_nodes:
            rec_data = r_node.find('zs:recordData/slim:record', self.NS) or r_node
            rec_dict = self.process_single_record(rec_data)
            
            records_el = ET.SubElement(response, "records")
            rd_el = ET.SubElement(records_el, "recordData")
            bib_rec = ET.SubElement(rd_el, "{http://www.komlog.ru/ns/bib-1.0}record")
            
            # Заполнение bib:record
            ET.SubElement(bib_rec, "{http://www.komlog.ru/ns/bib-1.0}id").text = rec_dict['id']
            ET.SubElement(bib_rec, "{http://www.komlog.ru/ns/bib-1.0}header").text = rec_dict['header']
            for i in range(1, 11):
                ET.SubElement(bib_rec, f"{{http://www.komlog.ru/ns/bib-1.0}}domain{i}").text = rec_dict[f'domain{i}']
                
            for author in rec_dict['other_authors']:
                ET.SubElement(bib_rec, "{http://www.komlog.ru/ns/bib-1.0}other-authors").text = author
            for subj in rec_dict['subjects']:
                ET.SubElement(bib_rec, "{http://www.komlog.ru/ns/bib-1.0}subjects").text = subj
                
            ET.SubElement(bib_rec, "{http://www.komlog.ru/ns/bib-1.0}cite").text = rec_dict['cite']
            if rec_dict['url']:
                ET.SubElement(bib_rec, "{http://www.komlog.ru/ns/bib-1.0}url").text = rec_dict['url']
                
            # Служебные поля records
            pos = r_node.findtext('zs:recordPosition', namespaces=self.NS)
            ET.SubElement(records_el, "recordPosition").text = pos
            ET.SubElement(records_el, "recordSchema").text = "bib"
            ET.SubElement(records_el, "recordPacking").text = "json"
            ET.SubElement(records_el, "recordIdentifier").text = rec_dict['id']

        return ET.tostring(response, encoding='unicode', pretty_print=True)


# ==========================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ==========================================
def format_marcxml(xml_input: Union[str, bytes]) -> Dict[str, Any]:
    """
    Быстрая функция-обертка для получения результата.
    Возвращает словарь с двумя ключами: 'data' (список python-объектов) и 'xml' (строка).
    """
    formatter = MarcBibFormatter(xml_input)
    return {
        'data': formatter.process_response(),
        'xml': formatter.to_xml_string()
    }

# if __name__ == "__main__":
#     with open("marc_response.xml", "r", encoding="utf-8") as f:
#         result = format_marcxml(f.read())
#         print(result['data'][0]['cite'])
