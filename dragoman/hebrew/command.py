#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 聖書ヘブライ語 (と聖書アラム語) のコマンドの設定 (core/cli.py)
#
import sys

from dragoman.core.cli import Command
from dragoman.core import options
from . import analyzer, dictionary, explain, script

USAGE = '''
  echo "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ׃" | python3 dragoman.py --lang=he
  母音記号 (ニクード) 付きの本文を入れる (朗唱記号はあってもよい)。聖書アラム語の部分もそのまま読める
'''
OPTIONS = options.LANGUAGE['he']   # 定義は core/options.py に (解析器を読まずに集められるように)


def original_text(analysis):
    return ' '.join(script.pointed(s) for s in getattr(analysis, 'tokens', analysis.surfaces)
                    if s not in analyzer.PUNCTUATION and not s.startswith('('))


def header(analysis, options):
    original = original_text(analysis)
    return '%s  (%s)' % (script.isolate(original), ' '.join(script.translit(w) for w in original.split()))


def handle_option(option, arg, options):
    if option == '--binyan':
        options.extra['binyan'] = arg
        return True
    if option == '--divine-name':
        if arg not in script.DIVINE_NAME_MODES:
            sys.exit('--divine-name: %s のどれか' % '|'.join(script.DIVINE_NAME_MODES))
        options.extra['divine_name'] = arg
        return True
    return False


def texts_hook(options):
    if 'binyan' in options.extra:
        from . import binyan
        print('\n'.join(binyan.table(options.extra['binyan'])))
        return True
    return False


def speech_setup(options, speech):
    speech.divine_name = options.extra.get('divine_name', 'adonai')


def available():
    return None if dictionary.available() else 'no Hebrew data (python3 tools/build_hebrew_dic.py)'


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 聖書の時代の再建音で語ごとに (hebrew/katakana.py。既定は古い時代、--kana-hebrew=tiberian で
    ティベリア式。神の名は朗読の読み アドーナーイ)"""
    from .katakana import sentence
    return sentence(original_text(analysis), **kana_options)


COMMAND = Command(lang='he', name='聖書ヘブライ語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=header, speech_text=lambda a, o: original_text(a), romanize=script.translit,
                  explain=explain.notes, descendant_langs=('en', 'ja', 'el', 'la', 'ar'),
                  options=OPTIONS, handle_option=handle_option,
                  texts_hook=texts_hook, speech_setup=speech_setup, katakana=katakana)
