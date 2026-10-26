#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ポルトガル語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from dragoman.core import options as option_defs
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py pt -e "O menino leu o livro da professora."
  spaCy (pt_core_news_sm) で品詞・性・数・人称・時制・依存関係を付け、助動詞 (ter / ser / estar / ir)・話法の動詞と
  本動詞をまとめ、格の枠から日本語に訳す。ブラジルとポルトガルの両方を読む。辞書は tools/build_portuguese_dic.py
  (Wiktionary)、pip で pt_core_news_sm
'''
OPTIONS = option_defs.LANGUAGE['pt']
NOTES = '  音読は macOS の say (ブラジル Luciana / ポルトガル Joana)、無ければ espeak-ng (pt-br / pt)'
SAY_VOICES = {'br': 'Luciana', 'pt': 'Joana'}
ESPEAK_VOICES = {'br': 'pt-br', 'pt': 'pt'}


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('clitic'):
        out.append('接語の代名詞 (%s)' % ('動詞の後ろ' if item.attrib('enclitic') else '動詞の前'))
    if item.attrib('possessive_pronoun'):
        out.append('de + 代名詞 (所有「〜の」)')
    return out


def original(analysis):
    """元の文 (接語はハイフンで動詞に付ける: deu-me)"""
    text = ''
    for w in getattr(analysis, 'original', None) or analysis.surfaces:
        if w.startswith('-') and len(w) > 1:
            text += w
        elif w in analyzer.PUNCTUATION and w not in '(«"“':
            text += w
        else:
            text += (' ' if text else '') + w
    return text


def variety(options):
    return options.extra.get('variety', 'br')


def handle_option(option, arg, options):
    if option == '--variety':
        if arg not in ('br', 'pt'):
            raise SystemExit('--variety は br か pt')
        options.extra['variety'] = arg
        options.kana_options.setdefault('pt', arg)
        return True
    return False


def speech_setup(options, speech):
    """音読の声: ブラジル (既定) かポルトガル (--variety=pt)"""
    v = variety(options)
    speech.SAY_VOICES['pt'] = SAY_VOICES[v]
    speech.ESPEAK_VOICES['pt'] = ESPEAK_VOICES[v]


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 語ごとに espeak-ng の発音から (portuguese/katakana.py。--kana-pt=pt でポルトガルの発音)"""
    from .katakana import sentence
    return sentence(original(analysis).replace('-', ' '), **kana_options)


def available():
    if not morphology.available():
        return 'no Portuguese model or data (pip install pt_core_news_sm; python3 tools/build_portuguese_dic.py)'
    return None


COMMAND = Command(lang='pt', name='ポルトガル語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='pt', katakana=katakana, options=OPTIONS, notes=NOTES,
                  handle_option=handle_option, speech_setup=speech_setup)
