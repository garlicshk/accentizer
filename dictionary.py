import pickle
from os import path
from pprint import pprint
from typing import Dict, Set, Tuple

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
            print('Word is unresolvable:', word, pos)
            return

        if word in self.homographs:
            print('Word is homograph:', word, pos)
            # self.add_homograph(form, [pos, None], [self.accents[form], None])
            return

        if word in self.accents:
            if self.accents[word] != pos:
                print('Word is homograph:', word, pos)
                # self.add_homograph(form, [pos, None], [self.accents[form], None])
            return

        self.accents[word] = pos
        self.changed = True
        print('new accent', word, pos)

    def add_homograph(self, word: str, morph: Morph, pos: int):
        if count_vovels(word) < 2: return
        self.accents.pop(word, None)

        if word in self.homographs_unresolvable:
            print('Word is unresolvable:', word, pos, morph)
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
                self.add_homograph_unresolvable(word, morph, pos)
            else:
                pprint(['homograph exists', word, self.homographs[word]])
        else:
            self.homographs[word][POS_SET].add(pos)
            self.homographs[word][MORPHS][morph] = pos

            self.changed = True
            print('new homograph', word, pos, morph)

    def add_homograph_unresolvable(self, word, morph, pos):
        assert morph is not None

        if count_vovels(word) < 2: return
        self.accents.pop(word, None)
        self.homographs.pop(word, None)

        if word in self.homographs_unresolvable:
            if morph in self.homographs_unresolvable[word][MORPHS]:
                if not pos in self.homographs_unresolvable[word][MORPHS][morph]:
                    self.homographs_unresolvable[word][MORPHS][morph].add(pos)
                    self.changed = True
                    print('new unresolvable homograph pos', self.homographs_unresolvable[word][MORPHS][morph])
                else:
                    print('unresolvable homograph exists', self.homographs_unresolvable[word])
            else:
                self.homographs_unresolvable[word][POS_SET].add(pos)
                self.homographs_unresolvable[word][MORPHS][morph] = set([pos])

                self.changed = True
                print('new unresolvable', word, pos, morph)
        else:
            self.homographs_unresolvable[word] = (set(), {})
            self.homographs_unresolvable[word][POS_SET].add(pos)
            self.homographs_unresolvable[word][MORPHS][morph] = set([pos])

            self.changed = True
            print('new unresolvable', word, pos, morph)

    def clean_homographs(self):
        for k in list(self.homographs):
            if len(self.homographs[k][POS_SET]) == 1:
                data = self.homographs.pop(k)
                if count_vovels(k) > 1:
                    self.add_accent(k, list(data[0])[0])

if __name__ == "__main__":
    dictionary = AccentDictionary()
    dictionary.load()

    for word in dictionary.homographs_old:
        # word = 'стоит'
        print(word)
        variants = parse_wikt_ru(word)
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

