#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ウルドゥー語の語をカタカナで書く: ウルドゥー文字の語をヒンディー語の語形に引き当て (短母音を書かないので)、その転写から
# ヒンディー語と同じ規則で (hindi/katakana.py)。引き当てられない語は空
#
#   کتاب → キターブ、آدمی → アードミー、ہے → ヘー
#
from dragoman.hindi import katakana as hindi_katakana


def word_katakana(word, **options):
    from dragoman.hindi import script as hindi_script
    from . import dictionary
    candidates = dictionary.candidates(word)
    return hindi_katakana.katakana(hindi_script.translit(candidates[0]), **options) if candidates else ''
