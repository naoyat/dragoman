#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary

USAGE = '''
  ./dragoman.py ang -e "Se cyning lufode þone ealdormann."
  語ごとに Wiktionary の変化表のすべての読み (格・数・性、法・時制・人称・数) を並べ、冠詞 (sē) を名詞に掛け、
  助動詞と本動詞をまとめてから、格の枠で日本語に訳す。綴りは長音符・点が無くてもよく、ð と þ は同じに読む。
  辞書は tools/build_oldenglish_dic.py (Wiktionary)
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('guessed'):
        out.append('辞書に無い語: %s と推定' % item.attrib('guessed'))
    if item.attrib('variant'):
        out.append('綴りの揺れ: %s として引いた' % item.attrib('variant'))
    return out


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '("“' else (' ' if text else '') + w
    return text


def speech_text(analysis, options):
    """音読: 解析で選んだ読みの辞書の綴り (長音符付き) を音素の列に (oldenglish/phonology.py)"""
    from . import phonology
    return phonology.espeak_words(analyzer.spelled(analysis))


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 解析で選んだ読みの辞書の綴り (長音符付き) の発音から (oldenglish/phonology.katakana)"""
    from .phonology import katakana as kana
    return [kana(s, lemma, **kana_options) for s, lemma in analyzer.spelled(analysis) if any(c.isalpha() for c in s)]


def available():
    return None if dictionary.available() else 'no Old English dictionary (python3 tools/build_oldenglish_dic.py)'


COMMAND = Command(lang='ang', name='古英語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=speech_text, explain=explain,
                  descendant_langs=('en',), katakana=katakana)
