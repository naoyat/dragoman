#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# トルコ語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py tr -e "Çocuk okulda kitap okudu."
  語を形態素解析器 zeyrek で語幹と接尾辞 (格・所有・時制・人称・否定・可能 …) に分け、格の接尾辞から格の枠を決めて
  日本語に訳す。語順のままの訳 (≒) も添える。辞書は tools/build_turkish_dic.py (Wiktionary)、pip install zeyrek
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    rec = getattr(word, 'record', None)
    if rec is not None and rec.get('morphemes'):
        out.append('形態素: %s' % ' + '.join(rec['morphemes']))
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
        return 'no Turkish analyzer or data (pip install zeyrek; python3 tools/build_turkish_dic.py)'
    return None


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 綴りの発音から語ごとに (turkish/katakana.py)"""
    from .katakana import sentence
    return sentence(original(analysis), **kana_options)


COMMAND = Command(lang='tr', name='トルコ語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='tr', katakana=katakana)
