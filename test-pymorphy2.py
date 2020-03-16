from pprint import pprint

import pymorphy2

from rnnmorph.predictor import RNNMorphPredictor
predictor = RNNMorphPredictor(language="ru")

# from dict_parser import convert_pymorph_tag

morpher = pymorphy2.MorphAnalyzer()

parse = morpher.parse('стоит')

# parse = [convert_pymorph_tag(x) for x in parse]

pprint(parse)

parse2 = predictor.predict(['стоит', ])

pprint(parse2)
