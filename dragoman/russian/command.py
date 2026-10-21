#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ロシア語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology, script

USAGE = '''
  echo "Мальчик читает книгу." | python3 dragoman.py --lang=ru
'''
NOTES = '  見出しの行には強勢記号を付けた文と転写を添える。音読は macOS の say のロシア語音声 Milena (無ければ espeak-ng)'


def stressed_text(surfaces):
    """強勢記号を付けた文 (句読点の前の空白を詰める)"""
    out = ''
    for s in surfaces:
        if s.startswith('('):
            continue  # 補った繋辞
        if s in analyzer.PUNCTUATION and s not in ('—', '–', '(', '«', '„', '“'):
            out += s
        else:
            out += (' ' if out else '') + (s if s in analyzer.PUNCTUATION else morphology.stressed(s))
    return out


def explain(word):
    """語の詳細の注記: まとめた構文 (б … ни плёл「譲歩 (疑問詞 + бы … ни + 動詞「〜しても」)」、бы пошёл「条件法」)"""
    item = word.items[0] if word.items else None
    return [item.attrib('form')] if item is not None and item.attrib('form') else []


def _surfaces(analysis):
    """元の文の語の列 (解析で落とした語 б・ни も)"""
    return getattr(analysis, 'original', None) or analysis.surfaces


def header(analysis, options):
    stressed = stressed_text(_surfaces(analysis))
    return '%s  (%s)' % (stressed, script.translit(stressed))


def romanized(word):
    """強勢付きの転写 (Девочка → Dévočka)"""
    return script.translit(morphology.stressed(word))


def available():
    if dictionary.available() and morphology.available():
        return None
    return 'no Russian data (pip install pymorphy3 pymorphy3-dicts-ru, and python3 tools/build_russian_dic.py)'


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 強勢記号を付けた語の発音から語ごとに (russian/katakana.py)"""
    from .katakana import sentence
    return sentence([morphology.stressed(s) for s in _surfaces(analysis) if not s.startswith('(')], **kana_options)


COMMAND = Command(lang='ru', name='ロシア語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=header, speech_text=lambda a, o: stressed_text(_surfaces(a)), explain=explain, romanize=romanized,
                  descendant_langs=('en', 'ja', 'fr', 'de'), fallback_langs=('uk', 'be'), notes=NOTES,
                  katakana=katakana)
