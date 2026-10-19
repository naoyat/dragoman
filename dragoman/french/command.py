#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py fr -e "Le garçon lit un livre à l'école."
  spaCy (fr_core_news_sm) で品詞・性・数・人称・時制を付け、助動詞 (avoir / être)・話法の助動詞と本動詞をまとめ、
  格の枠から日本語に訳す。名詞の格は文の中の役割から。辞書は tools/build_french_dic.py (Wiktionary)、
  pip install spacy && python3 -m spacy download fr_core_news_sm
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('clitic'):
        out.append('接語の代名詞 (動詞の前)')
    if item.attrib('reform'):   # 1990年の綴りの改革 (rectifications orthographiques)
        kind, other = item.attrib('reform')
        out.append('1990年の新しい綴りでは %s' % other if kind == 'new' else '1990年の新しい綴り (従来の綴りは %s)' % other)
    return out


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        if w in analyzer.PUNCTUATION and w not in '(«"“' or text.endswith("'"):
            text += (' ' if w in ':;!?»' and text else '') + w
        else:
            text += (' ' if text else '') + w
    return text


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 元の文の語ごとに espeak-ng の発音から (french/katakana.py。l'allocution は1語で)"""
    from .katakana import katakana as kana
    words = getattr(analysis, 'original', None) or analysis.surfaces
    return [kana(w, **kana_options) for w in words if any(c.isalpha() for c in w)]


def available():
    if not morphology.available():
        return 'no French model or data (python3 -m spacy download fr_core_news_sm; python3 tools/build_french_dic.py)'
    return None


COMMAND = Command(lang='fr', name='フランス語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='fr', katakana=katakana)
