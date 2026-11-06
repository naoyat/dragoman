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
  echo "𑖌𑖽 𑖦𑖜𑖰 𑖢𑖟𑖿𑖦𑖸 𑖮𑖳𑖽" | python3 dragoman.py --lang=sa      (悉曇文字でも)
'''
OPTIONS = options.LANGUAGE['sa']   # 定義は core/options.py に (解析器を読まずに集められるように)


def _convert(text, f):
    """語ごとに文字を変える (句読点はそのまま。悉曇文字のダンダは । ॥ に)"""
    out = []
    for w in text.split():
        if w in analyzer.PUNCTUATION:
            out.append({'\U000115c2': '।', '\U000115c3': '॥'}.get(w, w))
        else:
            out.append(f(script.to_slp1(w)))
    return ' '.join(out)


def _iast(slp1):
    return script.iast('oM' if slp1 == 'AUM' else slp1)   # ॐ は oṃ


def _siddham(slp1):
    return script.siddham('oM' if slp1 == 'AUM' else slp1)   # ॐ (vidyut は AUM に) は 𑖌𑖽


def header(analysis, options):
    """見出し: 入力のままの語 (連声を解く前の形: rāmaḥ・vanaṃ。解いた形 rāmas・vanam は語の表に) を
    IAST とデーヴァナーガリーで (悉曇文字を表示するなら悉曇文字も)"""
    tokens = ' '.join(getattr(analysis, 'tokens', analysis.surfaces))
    shown = _convert(tokens, script.devanagari)
    if script.siddham_wanted(tokens):   # 悉曇文字も (--siddham か、入力が悉曇文字)
        shown += ' / ' + _convert(tokens, _siddham).replace('।', '\U000115c2').replace('॥', '\U000115c3')
    return '%s  (%s)' % (_convert(tokens, _iast), shown)


def letters(analysis):
    """ノートの文字の図: 入力の語 (悉曇文字も表示するなら、悉曇文字の語も)"""
    from dragoman.core import letters as core_letters
    tokens = getattr(analysis, 'tokens', analysis.surfaces)
    words = core_letters.words_of(' '.join(tokens))
    if script.siddham_wanted(' '.join(tokens)):
        words += [_siddham(script.to_slp1(t)) for t in tokens if t not in analyzer.PUNCTUATION and _has_letter(t)]
    return words, None


def _has_letter(w):
    return any(c.isalpha() for c in w)


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 語ごとに発音から (sanskrit/katakana.py)。--kana-reading=shittan なら日本の悉曇の読み
    (入力のままの語から: 連声を解いた語ではなく)"""
    from . import katakana as kana
    if kana.READING == 'shittan':   # 長母音の「ー」は種字1字だけの行に (hrīḥ → キリーク、真言の中では キリク)
        from .shittan import reading
        words = [w for w in getattr(analysis, 'tokens', analysis.surfaces)
                 if w not in analyzer.PUNCTUATION and _has_letter(w)]
        return [reading(w, alone=len(words) == 1) for w in words]
    return [kana.katakana(w, **kana_options) for w in analysis.surfaces if _has_letter(w)]


def handle_option(option, arg, options):
    if option == '--compound-labels':
        if arg not in compound.LABEL_STYLES:
            sys.exit('--compound-labels: %s のどれか' % '|'.join(compound.LABEL_STYLES))
        compound.set_label_style(arg)
        return True
    if option in ('--buddhist', '--no-buddhist'):
        buddhist.set_forced(option == '--buddhist')
        return True
    if option == '--siddham':
        script.set_siddham(True)
        return True
    if option == '--kana-reading':
        from . import katakana as kana
        if arg not in kana.READINGS:
            sys.exit('--kana-reading: %s のどれか' % '|'.join(kana.READINGS))
        kana.READING = arg
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
                  handle_option=handle_option, katakana=katakana, letters=letters)
