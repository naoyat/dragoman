#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py de -e "Der Mann liest das Buch."
  spaCy (de_core_news_sm) で品詞・格・性・数を付け、助動詞・話法の助動詞と本動詞 (枠構造)・分離動詞の前つづりを
  まとめ、格の枠から日本語に訳す。辞書は tools/build_german_dic.py (Wiktionary)、
  pip install spacy && python3 -m spacy download de_core_news_sm
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('old_spelling'):
        out.append('古い綴り %s → %s' % (item.attrib('old_spelling'), word.surface))
    if item.attrib('separable'):
        out.append('分離動詞 (前つづり %s)' % item.attrib('separable'))
    return out


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '(„"»‚' else (' ' if text else '') + w
    return text


def available():
    if not morphology.available():
        return 'no German model or data (python3 -m spacy download de_core_news_sm; python3 tools/build_german_dic.py)'
    return None


COMMAND = Command(lang='de', name='ドイツ語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='de')
