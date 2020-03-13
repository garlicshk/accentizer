russian_vowels = {'а', 'о', 'у', 'э', 'ы', 'и', 'я', 'ё', 'ю', 'е', 'А', 'О', 'У', 'Э', 'Ы', 'И', 'Я', 'Ё', 'Ю', 'Е'}

def count_vovels(word):
    vowels_counter = 0
    for c in word:
        if c in russian_vowels:
            vowels_counter += 1
    return vowels_counter


def get_first_vovel_pos(word):
    for i, c in enumerate(word):
        if c in russian_vowels:
            return i + 1