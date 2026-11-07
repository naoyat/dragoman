#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# パーリ語のコマンドの設定 (core/cli.py)
#
import sys

from dragoman.core.cli import Command
from dragoman.core import options
from . import analyzer, dictionary, script

USAGE = '''
  echo "Manopubbaṅgamā dhammā, manoseṭṭhā manomayā." | ./dragoman.py pi
  echo "නමෝ තස්ස භගවතෝ" | ./dragoman.py pi              (シンハラ文字・タイ文字・ビルマ文字・デーヴァナーガリーでも)
  ./dragoman.py pi --kana --script=thai samples/dhammapada.pi.txt
'''
OPTIONS = options.LANGUAGE['pi']


def _letters(w):
    return w not in analyzer.PUNCTUATION and any(c.isalpha() for c in w)


def _join(words):
    """語を空白で (句読点の前には空けない)"""
    out = ''
    for w in words:
        out += w if not out or (w in analyzer.PUNCTUATION and w not in '।॥') else ' ' + w
    return out


def header(analysis, options):
    """見出し: 入力の語 (ローマ字。連声を分ける前の形) と、入力の文字か --script の文字"""
    tokens = getattr(analysis, 'tokens', analysis.surfaces)
    shown = script.SHOWN or getattr(analysis, 'script', None)
    if not shown:
        return _join(tokens)
    return '%s  (%s)' % (_join(tokens), _join(script.convert(w, shown) if _letters(w) else w for w in tokens))


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 入力の語ごとに発音から (pali/katakana.py)"""
    from . import katakana as kana
    return [kana.katakana(w, **kana_options) for w in getattr(analysis, 'tokens', analysis.surfaces) if _letters(w)]


def speech_text(analysis, options):
    return _join(getattr(analysis, 'tokens', analysis.surfaces))


def handle_option(option, arg, options):
    if option == '--script':
        if arg not in script.SCRIPTS:
            sys.exit('--script: %s のどれか' % '|'.join(script.SCRIPTS))
        script.SHOWN = script.SCRIPTS[arg]
        return True
    return False


def available():
    if dictionary.available():
        return None
    return 'no Pali data ($DRAGOMAN_DATA/pi/dpd.db from Digital Pāḷi Dictionary and python3 tools/build_pali_dic.py)'


COMMAND = Command(lang='pi', name='パーリ語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=header, descendant_langs=('en', 'ja'), options=OPTIONS,
                  handle_option=handle_option, katakana=katakana, speech_text=speech_text)
