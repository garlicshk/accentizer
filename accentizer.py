from dictionary import AccentDictionary
from utilities import count_vovels, get_first_vovel_pos


class Accentizer:
    single_vovel_accent = False



    dictionary = AccentDictionary()

    def __init__(self):
        self.dictionary.load()

    def get_accent(self, word, words, sentence):
        # check if already accentized
        if 'ё' in word or '́' in word or 'Ё' in word: return -1

        vovels_count = count_vovels(word)

        if vovels_count == 0: return -1
        if vovels_count == 1:
            return get_first_vovel_pos(word) if self.single_vovel_accent else -1

        # look in accent dictionary
        if word in self.dictionary.accents:
            return self.dictionary.accents[word]


