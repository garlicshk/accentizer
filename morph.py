from typing import Dict

class Morph:
    opencorpora_tags = None
    universaldependencies_tags = None

    def __init__(self):
        self.base: str = None

    def __eq__(self, another):
        return isinstance(another, Morph) and self.base == another.base and self.opencorpora_tags == another.opencorpora_tags and self.universaldependencies_tags == another.universaldependencies_tags

    def __hash__(self):
        return hash(self.base) + hash(self.opencorpora_tags) + hash(self.universaldependencies_tags)

    def __str__(self):
        return (self.base if self.base is not None else '') + ' ' + str(self.opencorpora_tags)

    def __repr__(self):
        return (self.base if self.base is not None else '') + ' ' + str(self.opencorpora_tags)

    def set_base(self, base):
        assert base is not None
        assert len(base) > 0
        self.base = base

    def fill_tags_from_variant(self, variant):
        self.opencorpora_tags = OpencorporaTags()
        self.opencorpora_tags.from_variant(variant[2])

        self.universaldependencies_tags = UniversaldependenciesTags()
        self.universaldependencies_tags.from_variant(variant[3])

    def fill_tags_from_string(self, str):
        splits = morph.split()
        tags = None

        if len(splits) == 1:
            self.set_pos(splits[0])
        if len(splits) == 2:
            if '=' in splits[1]:
                self.set_pos(splits[0])
                tags = splits[1]
            else:
                self.set_base(splits[0])
                self.set_pos(splits[1])
        else:
            self.set_pos(splits[0])
            self.set_pos(splits[1])
            tags = splits[2]

        if tags is not None:
            self.tags = {}
            for tag in tags.split('|'):
                name, value = tag.split('=')
                self.set_tags({name: value})

class BaseTags:
    POS = ()
    TAGS = ()
    CASE = ()
    GENDER = ()
    ANIMACY = ()
    NUMBER = ()
    DEGREE = ()
    TENSE = ()
    PERSON = ()

    def __init__(self):
        self.pos: str = None
        self.tags: Dict[str, str] = {}

    def from_variant(self, variant):
        self.set_pos(variant['pos'])
        self.set_tags(variant['tag'])

    def __eq__(self, another):
        return isinstance(another, BaseTags) and self.pos == another.pos and self.tags == another.tags

    def __hash__(self):
        return hash(self.pos) + hash(frozenset(self.tags.items()))

    def __str__(self):
        return self.pos + ' ' + '|'.join(['='.join(x) for x in self.tags.items()])

    def set_pos(self, pos):
        assert pos in self.POS
        self.pos = pos

    def set_tags(self, tags):
        for name, val in tags.items():
            assert name in self.TAGS

            if name == 'Case':
                assert val in self.CASE
                self.tags[name] = val

            if name == 'Gender':
                assert val in self.GENDER
                self.tags[name] = val

            if name == 'Animacy':
                assert val in self.ANIMACY
                self.tags[name] = val

            if name == 'Number':
                assert val in self.NUMBER
                self.tags[name] = val

            if name == 'Degree':
                assert val in self.DEGREE
                self.tags[name] = val

            if name == 'Tense':
                assert val in self.TENSE
                self.tags[name] = val

            if name == 'Person':
                assert val in self.PERSON
                self.tags[name] = val

class UniversaldependenciesTags(BaseTags):
    POS = ('NOUN', 'ADJ', 'VERB', 'PRON', 'DET')
    TAGS = ('Animacy', 'Case', 'Gender', 'Number', 'Degree', 'Variant', 'Tense', 'Person')
    CASE = ('Nom', 'Gen', 'Dat', 'Acc', 'Ins', 'Loc')
    GENDER = ('Fem', 'Masc', 'Neut')
    ANIMACY = ('Inan', 'Anim')
    NUMBER = ('Sing', 'Plur')
    DEGREE = ('Pos', 'Cmp', 'Sup')
    VARIANT = ('Short')
    TENSE = ('Past', 'Pres', 'Fut')
    PERSON = ('1', '2', '3')

    def set_tags(self, tags):
        super().set_tags(tags)

        for name, val in tags.items():
            assert name in self.TAGS

            if name == 'Variant':
                assert val in self.VARIANT
                self.tags[name] = val


class OpencorporaTags(BaseTags):
    POS = ('NOUN', 'ADJF', 'ADJS', 'VERB')
    POS_G = ('Apro', 'Qual')
    TAGS = ('Animacy', 'Case', 'Gender', 'Number', 'Tense', 'Person')
    CASE = ('nomn', 'gent', 'gen2', 'datv', 'accs', 'ablt', 'loct', 'loc2')
    GENDER = ('femn', 'masc', 'neut')
    ANIMACY = ('inan', 'anim')
    NUMBER = ('sing', 'plur')
    DEGREE = ()
    TENSE = ('pres', 'fast', 'futr')
    PERSON = ('1per', '2per', '3per')

    def __init__(self):
        BaseTags.__init__(self)
        self.pos_grammeme = None

    def from_variant(self, variant):
        super().from_variant(variant)
        if 'pos-grammeme' in variant:
            assert variant['pos-grammeme'] in self.POS_G
            self.pos_grammeme = variant['pos-grammeme']

    def __str__(self):
        return (self.pos if self.pos_grammeme is None else self.pos + ',' + self.pos_grammeme)\
               + ' ' + '|'.join(['='.join(x) for x in self.tags.items()])


