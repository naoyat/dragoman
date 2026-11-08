#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 印欧祖語 (シュライヒャーの表記) のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from dragoman.core.languages import lang_name
from . import analyzer, dictionary

USAGE = '''
  ./dragoman.py ine samples/schleicher.txt          (シュライヒャーの寓話 1868)
  echo "Avis akvāsas ka." | ./dragoman.py ine
'''


def _letters(w):
    return w not in analyzer.PUNCTUATION and any(c.isalpha() for c in w)


def _join(words):
    out = ''
    for w in words:
        out += w if not out or w in analyzer.PUNCTUATION else ' ' + w
    return out


def header(analysis, options):
    return _join(getattr(analysis, 'tokens', analysis.surfaces))


def explain(word):
    """今の再建形と、ラテン語・ギリシア語・サンスクリットの同源の語"""
    item = word.items[0] if word.items else None
    if item is None:
        return []
    lemma = item.attrib('base')
    out = []
    if item.attrib('augment'):
        out.append('加音 ā (過去の印) 付き')
    modern = dictionary.modern(lemma)
    if modern:
        cognates = ', '.join('%s %s' % (lang_name(code), term) for code, term in dictionary.cognates(lemma))
        out.append('今の再建: %s%s' % (modern, ('  同源: ' + cognates) if cognates else ''))
    return out


def katakana(analysis, kana_options):
    from . import katakana as kana
    return [kana.katakana(w, **kana_options) for w in getattr(analysis, 'tokens', analysis.surfaces) if _letters(w)]


def speech_text(analysis, options):
    return _join(getattr(analysis, 'tokens', analysis.surfaces))


def available():
    return None


COMMAND = Command(lang='ine', name='印欧祖語 (シュライヒャーの表記)', analyzer=analyzer, dictionary=dictionary,
                  available=available, usage=USAGE, header=header, explain=explain, descendant_langs=('en', 'ja'),
                  katakana=katakana, speech_text=speech_text)
