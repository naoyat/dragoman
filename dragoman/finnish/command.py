#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フィンランド語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py fi -e "Poika luki kirjan koulussa."
  spaCy (fi_core_news_sm) で品詞・格 (15格)・依存関係を付け、否定動詞 ei・完了の olla・話法の動詞を本動詞にまとめ、
  格の枠から日本語に訳す。辞書は tools/build_finnish_dic.py (Wiktionary)、python3 -m spacy download fi_core_news_sm
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('case_name'):
        out.append(item.attrib('case_name'))
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('relative'):
        out.append('関係節「%s」が掛かる' % item.attrib('relative'))
    head = getattr(word, 'relative_of', None)
    if head is not None:
        out.append('関係節の語 (%s に掛かる)' % head.surface)
    return out


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '("“«' else (' ' if text else '') + w
    return text


def available():
    if not morphology.available():
        return 'no Finnish model or data (python3 -m spacy download fi_core_news_sm; python3 tools/build_finnish_dic.py)'
    return None


COMMAND = Command(lang='fi', name='フィンランド語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='fi')
