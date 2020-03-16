import re
from pprint import pprint
import wiktextract
from lxml import etree
from requests import get
import wikitextparser as wtp

from wikt_template_parser import parse_template, known_template
from utilities import count_vovels

replacements_opencorpora = {'adv ru': 'ADVB',
                            'деепр ru': 'GRND',
                            'Форма-сущ': 'NOUN',
                            'сущ ru': 'NOUN',
                            'Форма-гл': 'VERB',
                            'Форма-прил': 'ADJS',
                            'part ru': 'PRCL',
                            'предикатив': 'PRED',
                            'предикативы': 'PRED',
                            }
replacements_universalD = {'adv ru': 'ADV',
                           'деепр ru': 'VERB',  # VerbForm=Conv
                           'Форма-сущ': 'NOUN',
                           'сущ ru': 'NOUN',
                           'Форма-гл': 'VERB',
                           'Форма-прил': 'ADJ',
                           'part ru': 'PART',
                           'предикатив': 'ADV',
                           'предикативы': 'ADV',
                           }
r_gender = {
    'м': 'Masc',
    'ж': 'Fem',
    'с': 'Neut',
}
r_case_opencorpora = {
    'предложного': 'loct',
}
r_case_universalD = {
    'предложного': 'Loc',
}
r_number = {
    'ед': 'Sing',
    'мн': 'Plur',
}
r_degree = {

}
r_aspect_opencorpora = {
    'сов': 'perf',
    'несов': 'impf',
}
r_aspect_universalD = {
    'сов': 'Perf',
    'несов': 'Imp',
}
r_tense_opencorpora = {
    'наст': 'pres',
    'прош': 'past',
    'будущ': 'futr',
}
r_tense_universalD = {
    'наст': 'Pres',
    'прош': 'Past',
    'будущ': 'Fut',
}
r_person_opencorpora = {
    '1': '1per',
    '2': '2per',
    '3': '3per',
}
r_person_universalD = {
    '1': '1',
    '2': '2',
    '3': '3',
}


def get_wikitext_api(word, language='ru'):
    resp = get('https://{}.wiktionary.org/w/api.php'.format(language), {
        'action': 'query',
        'titles': word,
        'languages': language,
        'prop': 'revisions',
        'rvprop': 'content',
        'format': 'json',
    }).json()

    pages = resp['query']['pages']
    page = list(pages.values())[0]
    if 'revisions' in page:
        data = page['revisions'][0]['*']
    else:
        data = ''

    if 'redirect' in data.lower() or 'перенаправление' in data.lower():
        new_word = re.search('\[\[([́а-яёА-ЯЁ]+)\]\]', data).group(1)
        return get_wikitext_api(new_word, language)

    return data

def get_wikitext_api_expandtemplates(text, language='ru'):
    resp = get('https://{}.wiktionary.org/w/api.php'.format(language), {
        'action': 'expandtemplates',
        'text': text,
        'prop': 'wikitext',
        'format': 'json',
    }).json()

    data = resp['expandtemplates']['wikitext']
    return data

def accent(*words):
    return all(['́' in w or 'ё' in w or count_vovels(w) == 1 for w in words])


def search_template_for_argument(template, name):
    for a in template.arguments:
        if a.name.strip() == name:
            return a

    return None

repl = ['по-слогам', '{', '}', '|']

def parse_slogi(value):
    word_acc = []
    # if 2 variants
    match = re.fullmatch(r'[{}а-яА-Я́\-\|]+(( и )|(, ))[{}а-яА-Я́\-\|]+', value)
    if match is not None:
        var1, var2 = value.split(match.group(1))



        for r in repl:
            var1 = var1.replace(r, '')
            var2 = var2.replace(r, '')

        word_acc = [var1, var2]

    else:
        for r in repl:
            value = value.replace(r, '')

        word_acc = [value]

    return word_acc

def get_word_from_slogi(section):
    template = search_section_for_template(section, 'по-слогам')
    if template is None: template = search_section_for_template(section, 'по слогам')

    if template is None: return None

    word_acc = []
    t = ''

    for argument in template.arguments:
        if re.fullmatch(r'[́а-яёА-ЯЁ]+', argument.value.strip()):
            t += argument.value.strip()

        if "\'\'и\'\'" in argument.value:
            parts = [x.strip() for x in argument.value.split('\'\'и\'\'')]
            t += parts[0]
            word_acc.append(t)
            t = parts[1]

    word_acc.append(t)

    return word_acc

def search_template_for_argument_value(template, name):
    a = search_template_for_argument(template, name)
    if a is not None:
        v = a.value.strip()
        if len(v) > 0: return v
    return None


def get_name_value(argument):
    name = argument.name.strip()
    value = argument.value.strip()
    return name, value if len(value) > 0 else None

def parse_tags_from_template(template, opencorpora_tag, universalD_tag):
    opencorpora_tag['pos'] = replacements_opencorpora[get_pos_from_template_name(template)]
    if 'tag' not in opencorpora_tag: opencorpora_tag['tag'] = {}

    universalD_tag['pos'] = replacements_universalD[get_pos_from_template_name(template)]
    if 'tag' not in universalD_tag: universalD_tag['tag'] = {}

    opencorpora_tag['norm'] = get_name_value(template.arguments[0])[1]
    universalD_tag['norm'] = get_name_value(template.arguments[0])[1]

    for argument in template.arguments:
        name, value = get_name_value(argument)

        if name == 'база':
            opencorpora_tag['base'] = value
            universalD_tag['base'] = value
            continue

        if name == 'род':
            opencorpora_tag['tag']['Gender'] = r_gender.get(value)
            universalD_tag['tag']['Gender'] = r_gender.get(value)
            continue



        if name == 'падеж':
            opencorpora_tag['tag']['Case'] = r_case_opencorpora.get(value)
            universalD_tag['tag']['Case'] = r_case_universalD.get(value)
            continue

        if name == 'предложного':
            opencorpora_tag['tag']['Case'] = r_case_opencorpora.get(name)
            universalD_tag['tag']['Case'] = r_case_universalD.get(name)
            continue

        if name == 'кр':
            if value == '1':
                opencorpora_tag['tag']['Degree'] = 'Short'
                universalD_tag['tag']['Degree'] = 'Short'
            continue

        if name == 'или':
            if value is None: continue
            opencorpora_tag['pos-or'] = replacements_opencorpora[value]
            v = replacements_universalD[argument.value.strip()]
            if v != universalD_tag['pos']:
                universalD_tag['pos-or'] = v
            continue

        if name == 'степень':
            if value is None: continue
            opencorpora_tag['tag']['Degree'] = r_degree.get(value)
            universalD_tag['tag']['Degree'] = r_degree.get(value)
            continue

        if name == 'вид':
            if value is None: continue
            opencorpora_tag['tag']['Aspect'] = r_aspect_opencorpora.get(value)
            universalD_tag['tag']['Aspect'] = r_aspect_universalD.get(value)
            continue

        if name == 'время':
            if value is None: continue
            opencorpora_tag['tag']['Tense'] = r_tense_opencorpora.get(value)
            universalD_tag['tag']['Tense'] = r_tense_universalD.get(value)
            continue



        if name == 'возвратность':
            if value == 'возвр':
                # Refl
                pass



        if value is not None:
            if value == '1':
                opencorpora_tag['tag']['Number'] = r_number.get('ед')
                universalD_tag['tag']['Number'] = r_number.get('ед')
                continue

            if value == '3':
                opencorpora_tag['tag']['Person'] = r_person_opencorpora.get(value)
                universalD_tag['tag']['Person'] = r_person_universalD.get(value)
                continue

            fl = False
            for v in r_tense_opencorpora:
                if value == v:
                    opencorpora_tag['tag']['Tense'] = r_tense_opencorpora.get(value)
                    universalD_tag['tag']['Tense'] = r_tense_universalD.get(value)
                    fl = True
                    continue

            for v in r_number:
                if value == v:
                    opencorpora_tag['tag']['Number'] = r_number.get(value)
                    universalD_tag['tag']['Number'] = r_number.get(value)
                    fl = True
                    continue

            if fl: continue

        if name == 'слоги':
            continue

        print('argument not used', name, value)


def search_section_for_template(section, name):
    for template in section.templates:
        if template.name.strip() == name:
            return template

    return None


def get_pos_from_template_name(template,):
    name = template.name.strip()
    for key in replacements_opencorpora:
        if key in name:
            return key


def get_variants_from_section(section):
    variants = []
    word_acc = None



    # looking for word
    t = search_section_for_template(section, 'заголовок')
    if t is None: t = search_section_for_template(section, 'з')

    if t is not None:
        v = search_template_for_argument_value(t, 'ударение')
        if v is not None:
            word_acc = [v]

    if word_acc is None:
        word_acc = get_word_from_slogi(section)

    # # search for section
    # if word_acc is None or not accent(*word_acc):
    #     for section2 in section.sections:
    #         if section2.title == ' Морфологические и синтаксические свойства ':
    #             template = section2.templates[0]
    #             argument = search_template_for_argument(template, 'слоги')
    #             value = argument.value.rstrip()
    #             word_acc = parse_slogi(value)
    #             parse_tags_from_remplate(template, opencorpora_tag, universalD_tag)
    #             break

    # search in templates

    # for template in section.templates:
    #     pos = get_pos_from_template_name(template)
    #     if pos is not None:
    #         if word_acc is None or not accent(*word_acc):
    #             argument = search_template_for_argument(template, 'слоги')
    #             value = argument.value.rstrip()
    #             word_acc = parse_slogi(value)
    #
    #         parse_tags_from_template(template, opencorpora_tag, universalD_tag)
    #
    #         break

    if word_acc is None or not accent(*word_acc):
        return []

    found_templates = False
    for template in section.templates:
        if known_template(template):
            found_templates = True
            variants += parse_template(word_acc, template)

    if not found_templates:
        raise Exception

    return variants


def parse_wikt_ru(word, parsed=None):
    if parsed is None: parsed = wtp.parse(get_wikitext_api(word))

    variants = []

    for cur_section in parsed.sections:
        if len(cur_section.templates) > 0 and '-ru-' in cur_section.templates[0].name:
            for section in cur_section.sections:
                if len(section.templates) > 0 and (section.templates[0].name == 'заголовок' or section.templates[0].name == 'з'):
                    variants += get_variants_from_section(section)

            if len(variants) == 0:
                for section in cur_section.sections:
                    if section.title == ' Морфологические и синтаксические свойства ':
                        variants += get_variants_from_section(section)

    return variants

def parse_wikt_en(word):
    pass


def dict_to_tag_UD(data):
    tag = data['base'] + ' ' + data['pos']

    if len(data['tag']) > 0:
        tag += ' '
        for key in data['tag']:
            if isinstance(data['tag'][key], list):
                pass
            else:
                tag += key + '=' + data['tag'][key] + '|'

        tag = tag[:-1]

    if len(data['tag']) > 0:
        for key in data['tag']:
            if isinstance(data['tag'][key], list):
                dicts = []
                for i in data['tag'][key]:
                    td = data.copy()
                    td['tag'][key] = i
                    dicts.append(td)
                return dicts

    return tag

def add_variants_dict(word, data, p):
    m = dict_to_tag_UD(data)
    if isinstance(m, list):
        for d in m:
            add_variants_dict(word, d, p)
    else:
        parser.add_homograph(word, [p, m])

def add_variants(variants):
    for var in variants:
        for form in var[0]:
            p = form.find('́')
            word = form.replace('́', '')
            if count_vovels(word) < 2: continue
            if p != -1:
                if word in parser.homographs:
                    add_variants_dict(word, var[2], p)
                    continue

                if word in parser.accents and p != parser.accents[word]:
                    add_variants_dict(word, var[2], p)
                    add_variants(variants)
                    return

                if word not in parser.accents:
                    parser.add_accent(word, p)
                    continue

if __name__ == "__main__":
    from dict_parser import Parser, count_vovels

    # pprint(parse_wikt_ru('вдали'))
    parser = Parser()
    parser.load()

    skip = True
    def word_cb(word, data):
        global skip
        if word == 'прыгать': skip = False
        if skip: return

        if re.fullmatch(r'[а-яёА-ЯЁ]+', word):
            if count_vovels(word) < 2: return
            parsed = wtp.parse(data)
            variants = parse_wikt_ru(word, parsed)
            # acc_word = word[:parser.accents[word]] + '́' + word[parser.accents[word]:]
            print(word, len(variants))
            # pprint(variants)

            add_variants(variants)

    ctx = wiktextract.parse_wiktionary(
        r'C:\Users\Admin\Downloads\ruwiktionary-20191120-pages-articles-multistream.xml', word_cb,
        capture_cb=None,
        languages=["Russian", "Translingual"],
        translations=False,
        pronunciations=False,
        redirects=False)


    # for word in list(parser.accents):
    #     if word == 'абиетин': skip = False
    #     if skip: continue
    #     variants = parse_wikt_ru(word)
    #     acc_word = word[:parser.accents[word]] + '́' + word[parser.accents[word]:]
    #     print(acc_word, len(variants))
        # pprint(variants)

        # add_variants(variants)

        # for var in variants:
        #     if len(var[0]) > 1:
        #         print('Found error!')
        #         # parser.accents.pop(word)
        #         add_variants(variants)
        #         break
        #
        #     if var[0][0] != acc_word:
        #         print('Found error!')
        #         # parser.accents.pop(word)
        #         add_variants(variants)
        #         break
        #
        #     print('Ok!')




