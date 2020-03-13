from pprint import pprint

import pymorphy2

# from dict_parser import convert_pymorph_tag

morpher = pymorphy2.MorphAnalyzer()

parse = morpher.parse('прыгать')

# parse = [convert_pymorph_tag(x) for x in parse]

pprint(parse)