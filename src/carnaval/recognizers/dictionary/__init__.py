# Copyright 2026 Patrice AUBERT
# SPDX-License-Identifier: Apache-2.0
"""Recognizers a base de dictionnaires bundled (cities, firstnames).

Les dictionnaires sont stockes dans `assets/dictionaries/<category>/<lang>.txt`,
un toponyme/prenom par ligne. Voir `scripts/build_dictionaries.py` pour
les regenerer depuis les sources upstream (GeoNames, INSEE...).
"""

from carnaval.recognizers.dictionary.automotive_oem import recognize_automotive_oem
from carnaval.recognizers.dictionary.cities import recognize_cities
from carnaval.recognizers.dictionary.firstnames import recognize_firstnames
from carnaval.recognizers.dictionary.surnames import recognize_initial_surname

__all__ = [
    "recognize_automotive_oem",
    "recognize_cities",
    "recognize_firstnames",
    "recognize_initial_surname",
]
