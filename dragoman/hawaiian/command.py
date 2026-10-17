#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary

USAGE = '''
  ./dragoman.py haw -e "Ua hele ke kanaka i ke kula."
  語順 (動詞 - 主語 - 目的語) と小辞 (ua・e … ana・ke … nei、i / iā、ʻo、o / a …) から語の役割を決め、格の枠で日本語に訳す。
  ʻokina・長音符の無い綴り (19世紀の本文) も読む。辞書は tools/build_hawaiian_dic.py (Wiktionary)
'''


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '("“' else (' ' if text else '') + w
    return text


def speech_text(analysis, options):
    """音読: 解析で選んだ読みの綴りを音素の列に (ʻokina を [ʔ] に。hawaiian/phonology.py)"""
    from . import phonology
    return phonology.espeak_words(analyzer.spelled(analysis))


def available():
    return None if dictionary.available() else 'no Hawaiian dictionary (python3 tools/build_hawaiian_dic.py)'


COMMAND = Command(lang='haw', name='ハワイ語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=speech_text,
                  descendant_langs=('en',), speech_lang='haw')
