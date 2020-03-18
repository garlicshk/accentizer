import pickle
import re
from os import path
from pprint import pprint
from typing import Dict, Set, Tuple

import pymorphy2

from morph import Morph
from utilities import count_vovels
from wiktparser import parse_wikt_ru

POS_SET = 0
MORPHS = 1

class AccentDictionary:

    def __init__(self):
        self.accents: Dict[str, int] = {} # Word form : accent position
        self.homographs_old: Dict[str, Tuple[Set[int], Dict[str, int]]] = {} # Word form: [Set[accent positions], {morphological tag: position}]
        self.homographs: Dict[str, Tuple[Set[int], Dict[Morph, int]]] = {}
        self.homographs_unresolvable: Dict[str, Tuple[Set[int], Dict[Morph, Set[int]]]] = {} # Words
        self.changed = False

    def load(self):
        if path.exists(r'accents.pickle'):
            with open(r'accents.pickle', 'rb') as f:
                self.accents = pickle.load(f)
        if path.exists(r'homographs_old.pickle'):
            with open(r'homographs_old.pickle', 'rb') as f:
                self.homographs_old = pickle.load(f)
        if path.exists(r'homographs.pickle'):
            with open(r'homographs.pickle', 'rb') as f:
                self.homographs = pickle.load(f)
        if path.exists(r'homographs2.pickle'):
            with open(r'homographs2.pickle', 'rb') as f:
                self.homographs2 = pickle.load(f)
        if path.exists(r'homographs_unresolvable.pickle'):
            with open(r'homographs_unresolvable.pickle', 'rb') as f:
                self.homographs_unresolvable = pickle.load(f)

        self.start_size = (len(self.accents), len(self.homographs), len(self.homographs_unresolvable))
        print(*self.start_size)

    def save(self):
        with open(r'accents.pickle', 'wb') as f:
            pickle.dump(self.accents, f)
        with open(r'homographs.pickle', 'wb') as f:
            pickle.dump(self.homographs, f)
        with open(r'homographs_unresolvable.pickle', 'wb') as f:
            pickle.dump(self.homographs_unresolvable, f)

        print(len(self.accents) - self.start_size[0], len(self.homographs) - self.start_size[1], len(self.homographs_unresolvable) - self.start_size[2])

    def save_if_changed(self):
        if self.changed: self.save()

    def add_accent(self, word: str, pos: int):
        if count_vovels(word) < 2: return

        if word in self.homographs_unresolvable:
            print('add_accent: word in unresolvable:', word[:pos + 1] + '́' + word[pos + 1:])
            return

        if word in self.homographs:
            print('add_accent: word in homographs:', word[:pos + 1] + '́' + word[pos + 1:])
            # self.add_homograph(form, [pos, None], [self.accents[form], None])
            raise Exception()
            return

        if word in self.accents:
            if self.accents[word] != pos:
                print('add_accent: word is homograph:', word[:pos + 1] + '́' + word[pos + 1:])
                # self.add_homograph(form, [pos, None], [self.accents[form], None])
                raise Exception()
            return

        self.accents[word] = pos
        self.changed = True
        print('new accent', word[:pos + 1] + '́' + word[pos + 1:])

    def add_homograph(self, word: str, morph: Morph, pos: int):
        if count_vovels(word) < 2: return
        self.accents.pop(word, None)

        if word in self.homographs_unresolvable:
            print('add_homograph: word in unresolvable:', word[:pos + 1] + '́' + word[pos + 1:], morph)
            self.add_homograph_unresolvable(word, morph, pos)
            return

        if word in self.homographs:
            self.add_to_homograph(word, morph, pos)

        else:
            self.new_homograph(word, morph, pos)

    def new_homograph(self, word, morph, pos):
        self.homographs[word] = (set(), {})
        self.add_to_homograph(word, morph, pos)

    def add_to_homograph(self, word, morph, pos):
        assert morph is not None

        if morph in self.homographs[word][MORPHS]:
            if self.homographs[word][MORPHS][morph] != pos:
                self.move_to_unresolvable(word)
                self.add_homograph_unresolvable(word, morph, pos)
            else:
                print('homograph exists', word[:pos + 1] + '́' + word[pos + 1:], morph)
        else:
            self.homographs[word][POS_SET].add(pos)
            self.homographs[word][MORPHS][morph] = pos

            self.changed = True
            print('new homograph', word[:pos + 1] + '́' + word[pos + 1:], morph)

    def add_homograph_unresolvable(self, word, morph, pos):
        assert morph is not None

        if count_vovels(word) < 2: return
        self.accents.pop(word, None)
        self.homographs.pop(word, None)

        if word in self.homographs_unresolvable:
            if morph in self.homographs_unresolvable[word][MORPHS]:
                if not pos in self.homographs_unresolvable[word][MORPHS][morph]:
                    self.homographs_unresolvable[word][MORPHS][morph].add(pos)
                    self.homographs_unresolvable[word][POS_SET].add(pos)
                    self.changed = True
                    print('new unresolvable homograph pos', word[:pos + 1] + '́' + word[pos + 1:], self.homographs_unresolvable[word][MORPHS][morph])
                else:
                    print('unresolvable homograph exists', word[:pos + 1] + '́' + word[pos + 1:], self.homographs_unresolvable[word][POS_SET])
            else:
                self.homographs_unresolvable[word][POS_SET].add(pos)
                self.homographs_unresolvable[word][MORPHS][morph] = set([pos])

                self.changed = True
                print('new unresolvable', word[:pos + 1] + '́' + word[pos + 1:], morph)
        else:
            self.homographs_unresolvable[word] = (set(), {})
            self.homographs_unresolvable[word][POS_SET].add(pos)
            self.homographs_unresolvable[word][MORPHS][morph] = set([pos])

            self.changed = True
            print('new unresolvable', word[:pos + 1] + '́' + word[pos + 1:], morph)

    def clean_homographs(self):
        for k in list(self.homographs):
            if len(self.homographs[k][POS_SET]) == 1:
                data = self.homographs.pop(k)
                if count_vovels(k) > 1:
                    self.add_accent(k, list(data[0])[0])

    def move_to_unresolvable(self, word):
        if word in self.homographs:
            h = self.homographs.pop(word)
            self.homographs_unresolvable[word] = (h[POS_SET], {})
            for morph in h[MORPHS]:
                self.homographs_unresolvable[word][MORPHS][morph] = set([h[MORPHS][morph]])

            print('homograph moved to unresolvable', word)

bad_words_h = ['автозаводска', 'автозаводско', 'автозаводски']
skip_words = ['асессоров', 'поатласнее', 'поатласней', 'багрящая', 'багрящее', 'багрящие', 'багрящего']
not_found_words_h = []
prefixes = ['авто', 'агит', 'по']

if __name__ == "__main__":
    dictionary = AccentDictionary()
    dictionary.load()

    morpher = pymorphy2.MorphAnalyzer()

    skip = True

    for word in dictionary.homographs_old:
        if skip:
            if word == 'багрящего':
                skip = False
            else:
                continue

        if word in skip_words:
            continue
        # word = 'стоит'
        print(word)
        variants = parse_wikt_ru(word)
        prefix = None

        if len(variants) == 0:
            if not(word in dictionary.homographs or word in dictionary.homographs_unresolvable or word in bad_words_h or word in not_found_words_h):
                parse = morpher.parse(word)[0]
                normal_word = parse.normal_form
                print('normal_form', normal_word, word)
                variants = parse_wikt_ru(normal_word)

                fl = False

                for variant in variants:
                    for word_var in variant[0]:
                        if word_var.replace('́', '') == word:
                            fl = True
                            break
                    if fl: break

                if not fl and parse.tag.POS == 'PRTF':
                    # no variants for prtf in 'прич ru'
                    print('Not found, continue', word)
                    continue

                if not fl:
                    match = re.match(r'|'.join(prefixes), word)
                    variants = []

                    if match:
                        prefix = match.group()
                        word = word[match.end():match.endpos]
                        print('приставка', prefix, word)
                        variants = parse_wikt_ru(word)

                        if len(variants) == 0:
                            parse = morpher.parse(word)
                            normal_word = parse[0].normal_form
                            print('normal_form', normal_word, word)
                            variants = parse_wikt_ru(normal_word)

                            fl = False

                            for variant in variants:
                                for word_var in variant[0]:
                                    if word_var.replace('́', '') == word:
                                        fl = True
                                        break

                            if not fl:
                                print('Not found', word)
                                raise Exception()
                    else:
                        print('Not found', word)
                        raise Exception()


            else:
                print('Not found, word in dict', word)

        if prefix is not None:
            for variant in variants:
                variant[1] = prefix + variant[1]
                for i, word_var in enumerate(variant[0]):
                    variant[0][i] = prefix + word_var

        for variant in variants:
            for word_var in variant[0]:
                if 'ё' in word_var: continue

                morph = Morph()
                morph.set_base(variant[1])
                morph.fill_tags_from_variant(variant)

                word_t = word_var.replace('́', '')
                if '́' in word_var:
                    pos_t = word_var.index('́') - 1
                else:
                    raise Exception()

                dictionary.add_homograph(word_t, morph, pos_t)
                pass

    # dictionary.save()

