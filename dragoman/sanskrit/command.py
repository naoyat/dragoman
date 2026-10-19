#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# サンスクリットのコマンドの設定 (core/cli.py)
#
import sys

from dragoman.core.cli import Command
from dragoman.core import options
from . import analyzer, buddhist, compound, dictionary, morphology, script

USAGE = '''
  echo "रामो वनं गच्छति ।" | python3 dragoman.py --lang=sa
  echo "rāmo vanaṃ gacchati" | python3 dragoman.py --lang=sa      (IAST でも)
'''
OPTIONS = options.LANGUAGE['sa']   # 定義は core/options.py に (解析器を読まずに集められるように)


def header(analysis, options):
    original = ' '.join(analysis.surfaces)
    return '%s  (%s)' % (original, script.devanagari(script.to_slp1(original)))


def _has_letter(w):
    return any(c.isalpha() for c in w)


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 語ごとに発音から (sanskrit/katakana.py)"""
    from .katakana import katakana as kana
    return [kana(w, **kana_options) for w in analysis.surfaces if _has_letter(w)]


def handle_option(option, arg, options):
    if option == '--compound-labels':
        if arg not in compound.LABEL_STYLES:
            sys.exit('--compound-labels: %s のどれか' % '|'.join(compound.LABEL_STYLES))
        compound.set_label_style(arg)
        return True
    if option in ('--buddhist', '--no-buddhist'):
        buddhist.set_forced(option == '--buddhist')
        return True
    if option in ('-v', '--voice'):
        options.speech, options.voice = True, arg
        return True
    return False


def available():
    if dictionary.available() and morphology.available():
        return None
    return 'no Sanskrit data (vidyut data and python3 tools/build_sanskrit_dic.py)'


COMMAND = Command(lang='sa', name='サンスクリット', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=header, descendant_langs=('pi', 'hi', 'en', 'ja'), fallback_langs=('bn', 'mr'),
                  options=OPTIONS,
                  handle_option=handle_option, katakana=katakana)
