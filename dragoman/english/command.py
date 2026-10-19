#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py en -e "The boy reads a book."
  ./dragoman.py en --kana-only -e "I don't know what you're talking about."
  spaCy (en_core_web_sm) で品詞・係り受けを付け、助動詞と本動詞をまとめ、格の枠から日本語に訳す。訳語は英和の表
  ($DRAGOMAN_DATA/en-ja.sqlite。tools/build_en_ja.py)。カタカナ読みは CMUdict ($DRAGOMAN_DATA/en/cmudict.dict) と espeak-ng。
  pip install spacy && python3 -m spacy download en_core_web_sm
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    return [item.attrib('form')] if item.attrib('form') else []


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        attach = w in analyzer.PUNCTUATION and w not in '("“' or w.lower() in ("n't", "'s", "'re", "'m", "'ll", "'ve", "'d")
        text += w if attach else (' ' if text else '') + w
    return text


def available():
    if not morphology.available():
        return 'no English model or data (python3 -m spacy download en_core_web_sm; python3 tools/build_en_ja.py)'
    return None


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): CMUdict (米音) か espeak-ng (英音) の発音から語ごとに (english/katakana.sentence)"""
    from .katakana import sentence
    return sentence(original(analysis), **kana_options)


COMMAND = Command(lang='en', name='英語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('ja',), speech_lang='en', katakana=katakana)
