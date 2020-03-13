import pickle
from os import path
from typing import Dict, List, Set, Tuple

from utilities import count_vovels

POS_SET = 0
MORPHS = 1

class Morph:
    POS = ('NOUN', 'ADJ')
    TAGS = ('Animacy', 'Case', 'Gender', 'Number')

    def __init__(self, morph: str):
        self.pos: str = None
        self.base: str = None
        self.tags: Dict[str, str] = None

        splits = morph.split()
        tags = None

        if len(splits) == 1:
            self.pos = splits[0]
        if len(splits) == 2:
            if '=' in splits[1]:
                self.pos = splits[0]
                tags = splits[1]
            else:
                self.base = splits[0]
                self.pos = splits[1]
        else:
            self.base = splits[0]
            self.pos = splits[1]
            tags = splits[2]

        if tags is not None:
            self.tags = {}
            for tag in tags.split('|'):
                name, value = tag.split('=')
                self.tags[name] = value

    def __eq__(self, another):
        return isinstance(another, Morph) and self.pos == another.pos and self.base == another.base and self.tags == another.tags

    def __hash__(self):
        return hash(self.pos) + hash(self.base) + hash(frozenset(self.tags.items()))

    def __str__(self):
        return self.base if self.base is not None else '' + ' ' + self.pos + ' ' + '|'.join(['='.join(x) for x in self.tags.items()])

class AccentDictionary:

    def __init__(self):
        self.accents: Dict[str, int] = {} # Word form : accent position
        self.homographs_old: Dict[str, Tuple[Set[int], Dict[str, int]]] = {} # Word form: [Set[accent positions], {morphological tag: position}]
        self.homographs: Dict[str, Tuple[Set[int], Dict[Morph, int]]] = {}
        self.homographs_unresolvable: Set[str] = set() # Words
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
                self.homographs_unresolvable = set(pickle.load(f))

        self.start_size = (len(self.accents), len(self.homographs), len(self.homographs_unresolvable))
        print(*self.start_size)

    def save(self):
        with open(r'accents.pickle', 'wb') as f:
            pickle.dump(self.accents, f)
        with open(r'homographs.pickle', 'wb') as f:
            pickle.dump(self.homographs, f)
        with open(r'homographs2.pickle', 'wb') as f:
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

    def add_homograph(self, word: str, pms: List[Tuple[int, Morph]]):
        if count_vovels(word) < 2: return
        self.accents.pop(word, None)

        if word in self.homographs_unresolvable:
            print('Word is unresolvable:', word, pms)
            return

        if word in self.homographs:
            for pos, morph in pms:
                self.add_to_homograph(word, morph, pos)

        else:
            self.new_homograph(word, pms)

    def new_homograph(self, word, pms):
        self.homographs[word] = [set(), {}]

        for pos, morph in pms:
            self.add_to_homograph(word, morph, pos)

    def add_to_homograph(self, word, morph, pos):
        if morph is not None:
            if morph in self.homographs[word][MORPHS]:
                if self.homographs[word][MORPHS][morph] != pos:
                    self.add_homograph_unresolvable(word)
                else:
                    print('homograph exists', self.homographs[word])
            else:
                self.homographs[word][POS_SET].add(pos)
                self.homographs[word][MORPHS][morph] = pos

                self.changed = True
                print('new homograph', word, pos, morph)
        else:
            raise RuntimeError('No morph')

    def add_homograph_unresolvable(self, word):
        if count_vovels(word) < 2: return
        self.accents.pop(word, None)
        self.homographs.pop(word, None)

        if word not in self.homographs_unresolvable:
            self.homographs_unresolvable.append(word)
            self.changed = True
            print('new unresolvable homograph', word)

if __name__ == "__main__":
    dictionary = AccentDictionary()
    dictionary.load()

    for word, homograph in dictionary.homographs_old.items():
        for m, p in homograph[MORPHS].items():
            if '(1)' in m or '(2)' in m or '(2)' in m or '(3)' in m or '(4)' in m:
                raise Exception()

            morph = Morph(m)
            print(word, morph, m)



            dictionary.add_homograph(word, [(p, morph)])
            pass

    pass