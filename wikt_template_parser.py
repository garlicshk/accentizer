import copy
import re

import wikitextparser as wtp
from bs4 import BeautifulSoup

from itertools import product

split_regex = r'\n| |<br\/>|<br \/>'

def table_to_2d(table_tag):
    rowspans = []  # track pending rowspans
    rows = table_tag.find_all('tr')

    # first scan, see how many columns we need
    colcount = 0
    for r, row in enumerate(rows):
        cells = row.find_all(['td', 'th'], recursive=False)
        # count columns (including spanned).
        # add active rowspans from preceding rows
        # we *ignore* the colspan value on the last cell, to prevent
        # creating 'phantom' columns with no actual cells, only extended
        # colspans. This is achieved by hardcoding the last cell width as 1.
        # a colspan of 0 means “fill until the end” but can really only apply
        # to the last cell; ignore it elsewhere.
        colcount = max(
            colcount,
            sum(int(c.get('colspan', 1)) or 1 for c in cells[:-1]) + len(cells[-1:]) + len(rowspans))
        # update rowspan bookkeeping; 0 is a span to the bottom.
        rowspans += [int(c.get('rowspan', 1)) or len(rows) - r for c in cells]
        rowspans = [s - 1 for s in rowspans if s > 1]

    # it doesn't matter if there are still rowspan numbers 'active'; no extra
    # rows to show in the table means the larger than 1 rowspan numbers in the
    # last table row are ignored.

    # build an empty matrix for all possible cells
    table = [[None] * colcount for row in rows]

    # fill matrix from row data
    rowspans = {}  # track pending rowspans, column number mapping to count
    for row, row_elem in enumerate(rows):
        span_offset = 0  # how many columns are skipped due to row and colspans
        for col, cell in enumerate(row_elem.find_all(['td', 'th'], recursive=False)):
            # adjust for preceding row and colspans
            col += span_offset
            while rowspans.get(col, 0):
                span_offset += 1
                col += 1

            # fill table data
            rowspan = rowspans[col] = int(cell.get('rowspan', 1)) or len(rows) - row
            colspan = int(cell.get('colspan', 1)) or colcount - col
            # next column is offset by the colspan
            span_offset += colspan - 1
            value = cell.get_text()
            for drow, dcol in product(range(rowspan), range(colspan)):
                try:
                    table[row + drow][col + dcol] = value
                    rowspans[col + dcol] = rowspan
                except IndexError:
                    # rowspan or colspan outside the confines of the table
                    pass

        # update rowspan bookkeeping
        rowspans = {c: s - 1 for c, s in rowspans.items() if s > 1}

    return table

r_case_opencorpora = {
    'и': 'nomn',
    'р': 'gent',
    'д': 'datv',
    'в': 'accs',
    'т': 'ablt',
    'п': 'loct',
    'м': 'loc2',
    'им.': 'nomn',
    'род.': 'gent',
    'дат.': 'datv',
    'вин.': 'accs',
    'твор.': 'ablt',
    'пр.': 'loct',
    'именительный': 'nomn',
    'родительный': 'gent',
    'дательный': 'datv',
    'винительный': 'accs',
    'творительный': 'ablt',
    'предложный': 'loct',
    'именительного': 'nomn',
    'родительного': 'gent',
    'дательного': 'datv',
    'винительного': 'accs',
    'творительного': 'ablt',
    'предложного': 'loct',
    'разделительный': 'gen2',
}
r_case_universalD = {
    'и': 'Nom',
    'р': 'Gen',
    'д': 'Dat',
    'в': 'Acc',
    'т': 'Ins',
    'п': 'Loc',
    'м': 'Loc',
    'им.': 'Nom',
    'род.': 'Gen',
    'дат.': 'Dat',
    'вин.': 'Acc',
    'твор.': 'Ins',
    'пр.': 'Loc',
    'именительный': 'Nom',
    'родительный': 'Gen',
    'дательный': 'Dat',
    'винительный': 'Acc',
    'творительный': 'Ins',
    'предложный': 'Loc',
    'именительного': 'Nom',
    'родительного': 'Gen',
    'дательного': 'Dat',
    'винительного': 'Acc',
    'творительного': 'Ins',
    'предложного': 'Loc',
    'разделительный': 'Gen',
}
r_number_opencorpora = {
    'ед': 'sing',
    '1': 'sing',
    'мн': 'plur',
    '2': 'sing',
    '3': 'sing',
    'я': 'sing',
    'ты': 'sing',
    'он': 'sing',
    'мы': 'plur',
    'вы': 'plur',
    'они': 'plur',
}
r_number_universalD = {
    'ед': 'Sing',
    '1': 'Sing',
    'мн': 'Plur',
    '2': 'Sing',
    '3': 'Sing',
    'я': 'Sing',
    'ты': 'Sing',
    'он': 'Sing',
    'мы': 'Plur',
    'вы': 'Plur',
    'они': 'Plur',
}
r_tense_opencorpora = {
    'наст': 'pres',
    'пр': 'past',
    'буд': 'futr',
}
r_tense_universalD = {
    'наст': 'Pres',
    'пр': 'Past',
    'буд': 'Fut',
}
r_gender_opencorpora = {
    'м': 'masc',
    'ж': 'femn',
    'с': 'neut',
    'm': 'masc',
    'f': 'femn',
    'n': 'neut',
    'он': 'masc',
    'она': 'femn',
    'оно': 'neut',
}
r_gender_universalD = {
    'м': 'Masc',
    'ж': 'Fem',
    'с': 'Neut',
    'm': 'Masc',
    'f': 'Fem',
    'n': 'Neut',
    'он': 'Masc',
    'она': 'Fem',
    'оно': 'Neut',
}
r_person_opencorpora = {
    '1': '1per',
    '2': '2per',
    '3': '3per',
    'я': '1per',
    'ты': '2per',
    'он': '3per',
    'мы': '1per',
    'вы': '2per',
    'они': '3per',
}
r_person_universalD = {
    '1': '1',
    '2': '2',
    '3': '3',
    'я': '1',
    'ты': '2',
    'он': '3',
    'мы': '1',
    'вы': '2',
    'они': '3',
}
r_anim_opencorpora = {
    'a': 'anim',
    'ina': 'inan',
    'одушевлённый': 'anim',
    'неодушевлённый': 'inan',
}
r_anim_universalD = {
    'a': 'Anim',
    'ina': 'Inan',
    'одушевлённый': 'Anim',
    'неодушевлённый': 'Inan',
}
r_degree_opencorpora = {
    'качественное': 'Qual',
}
r_degree_universalD = {
    'качественное': 'Pos',
}
r_mood_opencorpora = {
    'повелительное': 'impr',
}
r_mood_universalD = {
    'повелительное': 'Imp',
}

known_templates = ['Форма-сущ', 'Форма-гл', 'Форма-прил', 'conj ru', 'сущ-ru', 'adv ru']
advansed_templates = ['сущ ru', 'прил ru', 'Фам ru', 'гл ru', 'мест ru', 'прич ru']

PRESENT = ('настоящего', 'настоящее')
PAST = ('прошедшего', 'прошедшее')

def known_template(template):
    template_name = template.name.strip()
    if template_name in known_templates:
        return True

    for i in advansed_templates:
        if i in template_name:
            return True
    return False

def get_name_value(argument):
    name = argument.name.strip()
    value = argument.value.strip()
    value = clean_comments(value)
    return name, value if len(value) > 0 else None


def get_words_from_text(row):
    if re.fullmatch(r'[^а-яА-ЯёЁ]*—[^а-яА-ЯёЁ]*', row):
        return None

    row = row.replace('̀', '')
    m = re.fullmatch(r'([́а-яёА-ЯЁ]+)', row)

    if m is None:
        m = re.fullmatch(r'[^<>]*<.+>([́а-яёА-ЯЁ]+)<\/[a-z]+>', row)

    if m is not None:
        words = [m.group(1)]
    else:
        splits = re.split(split_regex, row)
        splits = [re.search(r'([́а-яёА-ЯЁ.]+)', x).group(1) for x in splits if len(x) > 0]
        splits = [x for x in splits if 'устар.' not in x]
        if len(splits) > 1:
            words = splits
        else:
            if re.match(r'([́а-яёА-ЯЁ]+)', splits[0]):
                words = splits
            else:
                raise Exception

    for word in words:
        assert re.match(r'([́а-яёА-ЯЁ]+)', word)

    words = [x for x in words if 'ё' in x or '́' in x]

    assert words is not None
    return words


def parse_table_declension(table, base, opencorpora_tag, universalD_tag):
    variants = []

    _header = table.pop(0)
    assert _header[0].strip() == '[[падеж]]'
    assert _header[1].strip() == '[[падеж]]'
    assert _header[2].strip() == '[[единственное число|ед. ч.]]'
    assert _header[3].strip() == '[[единственное число|ед. ч.]]'
    assert _header[4].strip() == '[[единственное число|ед. ч.]]'
    assert _header[5].strip() == '[[множественное число|мн. ч.]]'
    _header = table.pop(0)
    assert _header[0].strip() == '[[падеж]]'
    assert _header[1].strip() == '[[падеж]]'
    assert 'мужской' in _header[2]
    assert 'средний' in _header[3]
    assert 'женский' in _header[4]
    assert _header[5].strip() == '[[множественное число|мн. ч.]]'

    for row_index, row in enumerate(table):
        case = re.search(r'\[\[([а-яё. ]+)(\||\]\])', row[0]).group(1)
        assert case in r_case_opencorpora or 'краткая' in case

        for i in range(4):
            anim = re.search(r'\[\[([а-яё. ]+)(\||\]\])', row[1]).group(1)
            assert anim in r_anim_opencorpora or anim in r_case_opencorpora or 'краткая' in case

            # if cell is merged
            if row_index > 0 and row[0] != row[1] and table[row_index - 1][0] != table[row_index - 1][1] and row[
                2 + i] == table[row_index - 1][2 + i]:
                continue

            if row_index < len(table) - 1 and row[0] != row[1] and table[row_index + 1][0] != table[row_index + 1][
                1] and row[2 + i] == table[row_index + 1][2 + i]:
                anim = None

            words = get_words_from_text(row[2 + i])

            opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
            universalD_tag_copy = copy.deepcopy(universalD_tag)

            if 'краткая' not in case:
                opencorpora_tag_copy['tag']['Case'] = r_case_opencorpora[case]
                universalD_tag_copy['tag']['Case'] = r_case_universalD[case]
            else:
                opencorpora_tag_copy['pos'] = 'ADJS'
                universalD_tag_copy['tag']['Variant'] = 'Short'
            opencorpora_tag_copy['tag']['Number'] = r_number_opencorpora['ед'] if i < 3 else r_number_opencorpora['мн']
            universalD_tag_copy['tag']['Number'] = r_number_universalD['ед'] if i < 3 else r_number_universalD['мн']
            if i < 3:
                genders = {0: 'м', 1: 'с', 2: 'ж'}
                opencorpora_tag_copy['tag']['Gender'] = r_gender_opencorpora[genders[i]]
                universalD_tag_copy['tag']['Gender'] = r_gender_universalD[genders[i]]

            if anim in r_anim_opencorpora:
                opencorpora_tag_copy['tag']['Animacy'] = r_anim_opencorpora[anim]
                universalD_tag_copy['tag']['Animacy'] = r_anim_universalD[anim]

            last_variant = [words, base, opencorpora_tag_copy, universalD_tag_copy]
            variants.append(last_variant)

    return variants


def expand_cases(word_acc, base, opencorpora_tag, universalD_tag):
    variants = []
    for case in opencorpora_tag['Case']:
        opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
        universalD_tag_copy = copy.deepcopy(universalD_tag)

        opencorpora_tag_copy['Case'] = case
        universalD_tag_copy['Case'] = case

        variants.append([word_acc, base, opencorpora_tag_copy, universalD_tag_copy])

    return variants


def get_variants_from_custom_table(table, base, opencorpora_tag, universalD_tag):
    variants = []
    raise NotImplemented()
    return variants


def clean_comments(value):
    return re.sub(r'<!--.*-->', '', value)


def parse_template(word_acc, template):
    from wiktparser import search_section_for_template, get_word_from_slogi, get_wikitext_api_expandtemplates

    variants = []
    lookup_words = []
    template_name = template.name.strip()

    opencorpora_tag = {'tag': {}, 'pos-grammeme': set()}
    universalD_tag = {'tag': {}}
    base = None

    multiple_cases = False

    if template_name == 'Форма-сущ':
        opencorpora_tag['pos'] = 'NOUN'
        universalD_tag['pos'] = 'NOUN'

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name in ['база', '1'] and value is not None:
                base = value
                continue

            if name in ['падеж', '2'] and value is not None:
                if value in ['ив', 'рв', 'рдп']:
                    opencorpora_tag['tag']['Case'] = []
                    universalD_tag['tag']['Case'] = []
                    for v in value:
                        opencorpora_tag['tag']['Case'].append(r_case_opencorpora.get(v))
                        universalD_tag['tag']['Case'].append(r_case_universalD.get(v))
                    continue

                if ' и ' in value:
                    opencorpora_tag['tag']['Case'] = []
                    universalD_tag['tag']['Case'] = []
                    for v in value.split(' и '):
                        opencorpora_tag['tag']['Case'].append(r_case_opencorpora.get(v))
                        universalD_tag['tag']['Case'].append(r_case_universalD.get(v))
                    continue

                assert value in r_case_opencorpora
                opencorpora_tag['tag']['Case'] = r_case_opencorpora.get(value)
                universalD_tag['tag']['Case'] = r_case_universalD.get(value)
                continue

            if name in ['число', '3'] and value is not None:
                opencorpora_tag['tag']['Number'] = r_number_opencorpora[value]
                universalD_tag['tag']['Number'] = r_number_universalD[value]
                continue

            if name in ['помета', '5']:
                continue

            if name == 'число' and value is not None:
                opencorpora_tag['tag']['Number'] = r_number_opencorpora[value]
                universalD_tag['tag']['Number'] = r_number_universalD[value]
                continue

            if name == 'слоги':
                continue

        assert base is not None
        return [[word_acc, base, opencorpora_tag, universalD_tag]], lookup_words

    if template_name == 'Форма-гл':
        opencorpora_tag['pos'] = 'VERB'
        universalD_tag['pos'] = 'VERB'

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name in ['база', '1']:
                assert value is not None
                base = value
                continue

            if name in ['время', '2']:
                assert value is not None
                opencorpora_tag['tag']['Tense'] = r_tense_opencorpora.get(value)
                universalD_tag['tag']['Tense'] = r_tense_universalD.get(value)
                continue

            if name == 'залог':
                continue

            if name in ['род', '3'] and value is not None : # can be empty
                opencorpora_tag['tag']['Gender'] = r_gender_opencorpora[(value)]
                universalD_tag['tag']['Gender'] = r_gender_universalD[(value)]
                continue

            if name in ['лицо', '4']:
                assert value in r_person_opencorpora
                opencorpora_tag['tag']['Person'] = r_person_opencorpora.get(value)
                universalD_tag['tag']['Person'] = r_person_universalD.get(value)
                continue

            if name in ['число', '5']:
                assert value in r_number_opencorpora
                opencorpora_tag['tag']['Number'] = r_number_opencorpora[value]
                universalD_tag['tag']['Number'] = r_number_universalD[value]
                continue

            if name in ['накл', '6'] and value is not None:
                continue

            if name == 'деепр':
                raise Exception()

            if name == 'прич':
                raise Exception()

            if name == 'кр':
                raise Exception()

            if name in ['помета', '7'] and value is not None:
                continue

            if name == 'форма':
                continue

            if name == 'слоги':
                continue

        return [[word_acc, base, opencorpora_tag, universalD_tag]], lookup_words

    if template_name == 'Форма-прил':
        opencorpora_tag['pos'] = 'ADJF'
        universalD_tag['pos'] = 'ADJ'

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name in ['база', '1']:
                assert value is not None
                base = value
                continue

            if name in ['род', '2']:
                if value in r_gender_opencorpora:
                    opencorpora_tag['tag']['Gender'] = r_gender_opencorpora[value]
                    universalD_tag['tag']['Gender'] = r_gender_universalD[value]
                    continue
                else:
                    print('parsing error', word_acc)
                    return [], lookup_words

            if name in ['число', '3']:
                if value is not None:
                    opencorpora_tag['tag']['Number'] = r_number_opencorpora[value]
                    universalD_tag['tag']['Number'] = r_number_universalD[value]
                    continue
                else:
                    opencorpora_tag['tag']['Number'] = r_number_opencorpora['1']
                    universalD_tag['tag']['Number'] = r_number_universalD['1']
                    continue

            if name in ['падеж', '4']:
                if value in ['ив', 'рв', 'рдп']:
                    multiple_cases = True
                    opencorpora_tag['tag']['Case'] = []
                    universalD_tag['tag']['Case'] = []
                    for v in value:
                        opencorpora_tag['tag']['Case'].append(r_case_opencorpora.get(v))
                        universalD_tag['tag']['Case'].append(r_case_universalD.get(v))
                    continue

                if ' и ' in value:
                    multiple_cases = True
                    opencorpora_tag['tag']['Case'] = []
                    universalD_tag['tag']['Case'] = []
                    for v in value.split(' и '):
                        assert v in r_case_opencorpora
                        opencorpora_tag['tag']['Case'].append(r_case_opencorpora.get(v))
                        universalD_tag['tag']['Case'].append(r_case_universalD.get(v))
                    continue

                if value is not None:
                    assert value in r_case_opencorpora
                    opencorpora_tag['tag']['Case'] = r_case_opencorpora.get(value)
                    universalD_tag['tag']['Case'] = r_case_universalD.get(value)
                    continue
                else:
                    print('parsing error', word_acc)
                    return [], lookup_words

            if (name == 'кр' and value == '1') or value == 'кр':
                opencorpora_tag['pos'] = 'ADJS'
                universalD_tag['tag']['Variant'] = 'Short'
                continue

            if name == 'слоги':
                continue

        if multiple_cases:
            return expand_cases(word_acc, base, opencorpora_tag, universalD_tag), lookup_words
        else:
            return [[word_acc, base, opencorpora_tag, universalD_tag]], lookup_words

    if template_name == 'conj ru':
        opencorpora_tag['pos'] = 'CONJ'
        universalD_tag['pos'] = 'CONJ'

        raise Exception()

        base = get_word_from_slogi(template)[0].replace('́', '')

        assert base is not None
        return [[word_acc, base, opencorpora_tag, universalD_tag]], lookup_words

    if 'прил ru' in template_name:
        opencorpora_tag['pos'] = 'ADJF'
        universalD_tag['pos'] = 'ADJ'

        base = get_word_from_slogi(template)[0].replace('́', '')
        assert base is not None

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name == 'тип':
                if value is None: continue
                if value == 'качественное':
                    opencorpora_tag['pos-grammeme'].add(r_degree_opencorpora.get(value))
                    universalD_tag['tag']['Degree'] = r_degree_universalD.get(value)
                    continue
                if value == 'относительное':
                    continue
                raise Exception

            if name == 'степень' and value is not None: # can be None?
                assert value is not None
                for wikilink in wtp.parse(value).wikilinks:
                    lookup_words.append(wikilink.text)

                for w in re.search(r"\((.+)\)", value).group(1).split(','):
                    lookup_words.append(w.strip())

        # склонения по падежу / числу
        parsed = wtp.parse(get_wikitext_api_expandtemplates(template.string))
        table = table_to_2d(BeautifulSoup(parsed.string.replace('<br>','\n'), 'lxml').table)
        variants = parse_table_declension(table, base, opencorpora_tag, universalD_tag)

        return variants, lookup_words

    if template_name == 'сущ-ru':
        opencorpora_tag['pos'] = 'NOUN'
        universalD_tag['pos'] = 'NOUN'

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name in ['слово', '1'] and value is not None:
                base = value.replace('́', '')
                continue

            if name in ['индекс', '2'] and value is not None:
                data = value.split()[:-1]

                for d in data:
                    if d in r_gender_opencorpora:
                        opencorpora_tag['tag']['Gender'] = r_gender_opencorpora.get(d)
                        universalD_tag['tag']['Gender'] = r_gender_universalD.get(d)
                        continue

                    if d in r_anim_opencorpora:
                        opencorpora_tag['tag']['Animacy'] = r_anim_opencorpora.get(d)
                        universalD_tag['tag']['Animacy'] = r_anim_universalD.get(d)
                        continue
                continue

        # склонения по падежу / числу
        parsed = wtp.parse(get_wikitext_api_expandtemplates(template.string))
        table = parsed.tables[0].data()

        _header = table.pop(0)
        assert 'падеж' in _header[0]
        assert 'единственное' in _header[1]
        assert 'множественное' in _header[2]

        for row in table:
            case = re.search(r'\[\[([а-яё. ]+)(\||\]\])', row[0]).group(1)
            assert case in r_case_opencorpora

            for i in range(2):
                words = get_words_from_text(row[1 + i])

                opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
                universalD_tag_copy = copy.deepcopy(universalD_tag)

                opencorpora_tag_copy['tag']['Case'] = r_case_opencorpora[case]
                universalD_tag_copy['tag']['Case'] = r_case_universalD[case]

                opencorpora_tag_copy['tag']['Number'] = r_number_opencorpora['ед'] if i == 0 else r_number_opencorpora['мн']
                universalD_tag_copy['tag']['Number'] = r_number_universalD['ед'] if i == 0 else r_number_universalD['мн']

                variants.append([words, base, opencorpora_tag_copy, universalD_tag_copy])

        assert base is not None
        return variants, lookup_words

    if 'сущ ru' in template_name:
        opencorpora_tag['pos'] = 'NOUN'
        universalD_tag['pos'] = 'NOUN'

        slogi = get_word_from_slogi(template)
        if slogi is not None: base = slogi[0].replace('́', '')

        data = template_name.split()[2:-1]

        for d in data:
            if d in r_gender_opencorpora:
                opencorpora_tag['tag']['Gender'] = r_gender_opencorpora.get(d)
                universalD_tag['tag']['Gender'] = r_gender_universalD.get(d)
                continue

            if d in r_anim_opencorpora:
                opencorpora_tag['tag']['Animacy'] = r_anim_opencorpora.get(d)
                universalD_tag['tag']['Animacy'] = r_anim_universalD.get(d)
                continue

            print(template_name, d)

        # склонения по падежу / числу
        parsed = wtp.parse(get_wikitext_api_expandtemplates(template.string))
        table = parsed.tables[0].data()
        _header = table.pop(0)
        assert 'падеж' in _header[0]
        assert 'единственное' in _header[1]
        assert 'множественное' in _header[2]

        if base is None:
            base = table[0][1].replace('́', '')

        for row in table:
            case = re.match(r'\[\[([а-яё.]+)(\||\]\])', row[0]).group(1)
            assert case in r_case_opencorpora

            for i in range(2):
                if '<tr>' in row[1 + i]:
                    inner_table = table_to_2d(BeautifulSoup('<table>' + row[1 + i].replace('<br>', '\n') + '</table>', 'lxml'))
                    variants += get_variants_from_custom_table(inner_table, base, opencorpora_tag, universalD_tag)
                    row[1 + i] = row[1 + i][:row[1 + i].find('<tr>')]

                words = get_words_from_text(row[1 + i])

                opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
                universalD_tag_copy = copy.deepcopy(universalD_tag)

                opencorpora_tag_copy['tag']['Case'] = r_case_opencorpora[case]
                universalD_tag_copy['tag']['Case'] = r_case_universalD[case]

                opencorpora_tag_copy['tag']['Number'] = r_number_opencorpora['ед'] if i == 0 else r_number_opencorpora['мн']
                universalD_tag_copy['tag']['Number'] = r_number_universalD['ед'] if i == 0 else r_number_universalD['мн']

                variants.append([words, base, opencorpora_tag_copy, universalD_tag_copy])

        assert base is not None
        return variants, lookup_words

    if 'Фам ru' in template_name:
        # Фамилии, скип
        raise Exception()
        return [], lookup_words

    if 'гл ru' in template_name:
        opencorpora_tag['pos'] = 'INFN'
        universalD_tag['pos'] = 'VERB'
        universalD_tag['tag']['VerbForm'] = 'Inf'

        base = get_word_from_slogi(template)[0].replace('́', '')
        assert base is not None

        opencorpora_tag['pos-grammeme'].add('tran') # by default?

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name == 'НП':
                if value == '1':
                    opencorpora_tag['pos-grammeme'].discard('tran')
                    opencorpora_tag['pos-grammeme'].add('intr')
                else:
                    opencorpora_tag['pos-grammeme'].discard('intr')
                    opencorpora_tag['pos-grammeme'].add('tran')
                continue

            if name == 'соотв':
                if value is None:
                    opencorpora_tag['pos-grammeme'].add('perf')
                    universalD_tag['tag']['Aspect'] = 'Perf'
                else:
                    opencorpora_tag['pos-grammeme'].add('impf')
                    universalD_tag['tag']['Aspect'] = 'Imp'
                continue

        variants.append([word_acc, base, copy.deepcopy(opencorpora_tag), copy.deepcopy(universalD_tag)])
        opencorpora_tag['pos'] = 'VERB'
        universalD_tag['tag'].pop('VerbForm')

        # склонения по падежу / числу
        parsed = wtp.parse(get_wikitext_api_expandtemplates(template.string))
        table = parsed.tables[0].data()
        _header = table.pop(0)
        tenses = ('настоящее', 'прошедшее', 'повелительное')
        assert any(x in _header[1] for x in tenses)
        assert any(x in _header[2] for x in tenses)
        assert any(x in _header[3] for x in tenses)

        for row in table:
            person = re.match(r'\[\[([а-яё.]+)(\||\]\])', row[0]).group(1)
            assert person in r_person_opencorpora

            for i in range(3):
                words = get_words_from_text(row[1 + i])

                if words is not None:
                    opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
                    universalD_tag_copy = copy.deepcopy(universalD_tag)

                    opencorpora_tag_copy['tag']['Person'] = r_person_opencorpora[person]
                    universalD_tag_copy['tag']['Person'] = r_person_universalD[person]

                    opencorpora_tag_copy['tag']['Number'] = r_number_opencorpora[person]
                    universalD_tag_copy['tag']['Number'] = r_number_universalD[person]

                    tense = _header[1 + i]

                    if 'настоящее' in tense:
                        opencorpora_tag_copy['tag']['Tense'] = r_tense_opencorpora['наст']
                        universalD_tag_copy['tag']['Tense'] = r_tense_universalD['наст']

                    if 'прошедшее' in tense:
                        opencorpora_tag_copy['tag']['Tense'] = r_tense_opencorpora['пр']
                        universalD_tag_copy['tag']['Tense'] = r_tense_universalD['пр']

                    if 'будущее' in tense:
                        opencorpora_tag_copy['tag']['Tense'] = r_tense_opencorpora['буд']
                        universalD_tag_copy['tag']['Tense'] = r_tense_universalD['буд']

                    if 'повелительное' in tense:
                        opencorpora_tag_copy['tag']['Mood'] = r_mood_opencorpora['повелительное']
                        universalD_tag_copy['tag']['Mood'] = r_mood_universalD['повелительное']


                    if len(words) == 3:
                        genders = re.split(split_regex, row[0])
                        if len(genders) == 3:
                            for j in range(3):
                                gender = re.match(r'\[\[([а-яё.]+)(\||\]\])', genders[j]).group(1)
                                assert gender in r_gender_opencorpora

                                opencorpora_tag_copy2 = copy.deepcopy(opencorpora_tag_copy)
                                universalD_tag_copy2 = copy.deepcopy(universalD_tag_copy)

                                opencorpora_tag_copy2['tag']['Gender'] = r_gender_opencorpora[person]
                                universalD_tag_copy2['tag']['Gender'] = r_gender_universalD[person]

                                variants.append([[words[j]], base, opencorpora_tag_copy2, universalD_tag_copy2])

                    else:
                        variants.append([words, base, opencorpora_tag_copy, universalD_tag_copy])


        table = table_to_2d(BeautifulSoup('<table>' + parsed.string.replace('<br>', '\n') + '</table>', 'lxml').table)

        for row in table:
            if 'причастие' in row[0]:
                tense = None
                if any(x in row[0] for x in PRESENT): tense = 'наст'
                if any(x in row[0] for x in PAST): tense = 'пр'
                assert tense is not None

                opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
                universalD_tag_copy = copy.deepcopy(universalD_tag)

                opencorpora_tag_copy['pos'] = 'PRTF'
                universalD_tag_copy['VerbForm'] = 'Part'

                opencorpora_tag_copy['tag']['Tense'] = r_tense_opencorpora[tense]
                universalD_tag_copy['tag']['Tense'] = r_tense_universalD[tense]

            if 'деепричастие' in row[0]:
                tense = None
                if any(x in row[0] for x in PRESENT): tense = 'наст'
                if any(x in row[0] for x in PAST): tense = 'пр'
                assert tense is not None

                opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
                universalD_tag_copy = copy.deepcopy(universalD_tag)

                opencorpora_tag_copy['pos'] = 'GRND'
                universalD_tag_copy['tag']['VerbForm'] = 'Conv'

                opencorpora_tag_copy['tag']['Tense'] = r_tense_opencorpora[tense]
                universalD_tag_copy['tag']['Tense'] = r_tense_universalD[tense]

            if 'будущее' in row[0]:
                tense = 'буд'

                opencorpora_tag_copy = copy.deepcopy(opencorpora_tag)
                universalD_tag_copy = copy.deepcopy(universalD_tag)

                opencorpora_tag_copy['tag']['Tense'] = r_tense_opencorpora[tense]
                universalD_tag_copy['tag']['Tense'] = r_tense_universalD[tense]

                row[1] = row[1].replace('буду/будешь…', '').strip()

            words = []
            for w in re.split(split_regex, row[1]):
                m = re.search(r'\|?([́а-яёА-ЯЁ]+)\]\]', w)
                if m is None: m = re.fullmatch(r'([́а-яёА-ЯЁ]+)', w)
                words.append(m.group(1))

            variants.append([words, base, opencorpora_tag_copy, universalD_tag_copy])

        return variants, lookup_words

    if 'мест ru' in template_name:
        pos_found = False

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name == 'часть речи':
                if value == 'Местоимение (определительное)':
                    opencorpora_tag['pos'] = 'ADJF'
                    opencorpora_tag['pos-grammeme'].add('Apro')
                    universalD_tag['pos'] = 'DET'
                    pos_found = True

                if value == 'Прилагательное (относительное, притяжательное)':
                    opencorpora_tag['pos'] = 'ADJF'
                    opencorpora_tag['pos-grammeme'].add('Poss')
                    universalD_tag['pos'] = 'ADJ'
                    pos_found = True

        assert pos_found

        base = get_word_from_slogi(template)[0].replace('́', '')
        assert base is not None

        # склонения по падежу / числу
        parsed = wtp.parse(get_wikitext_api_expandtemplates(template.string))
        table = table_to_2d(BeautifulSoup(parsed.string.replace('<br>', '\n'), 'lxml').table)

        variants = parse_table_declension(table, base, opencorpora_tag, universalD_tag)

        return variants, lookup_words

    if template_name == 'adv ru':
        opencorpora_tag['pos'] = 'ADVB'
        universalD_tag['pos'] = 'ADV'

        base = get_word_from_slogi(template)[0].replace('́', '')
        assert base is not None

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name == 'м':
                raise NotImplemented()

            if name == 'класс' and value is not None:
                raise NotImplemented()

            if name == 'тип' and value is not None:
                raise NotImplemented()

            if name == 'степень' and value is not None:
                raise NotImplemented()

            if name == 'или' and value is not None:
                raise NotImplemented()

            if name == 'или-кат' and value is not None:
                raise NotImplemented()

            if name == 'или1' and value is not None:
                raise NotImplemented()

            if name == 'или-кат1' and value is not None:
                raise NotImplemented()

            if name == 'или2' and value is not None:
                raise NotImplemented()

            if name == 'или-кат2' and value is not None:
                raise NotImplemented()

        return [[word_acc, base, opencorpora_tag, universalD_tag]], lookup_words

    if 'прич ru' in template_name:
        opencorpora_tag['pos'] = 'PRTF'
        universalD_tag['pos'] = 'VERB'
        universalD_tag['VerbForm'] = 'Part'

        base = get_word_from_slogi(template)[0].replace('́', '')
        assert base is not None

        tense = None

        for argument in template.arguments:
            name, value = get_name_value(argument)

            if name == 'залог':
                raise NotImplemented()

            if name == 'вид' and value is not None:
                raise NotImplemented()

            if name == 'время':
                raise NotImplemented()



        return [[word_acc, base, opencorpora_tag, universalD_tag]], lookup_words