#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  echo "Tôi đã đọc quyển sách mà anh cho tôi." | ./dragoman.py vi
  ./dragoman.py vi --kana samples/vietnamese.txt
  語に切り分け (Stanza と Wiktionary の見出し)、Stanza (UD Vietnamese-VTB) の品詞・依存関係で語の項目を作り、
  量詞・所有 (của)・相の副詞 (đã・đang・sẽ)・否定・助動詞・受動 (bị・được)・文末の疑問の助詞をまとめて、
  格の枠から日本語に訳す。辞書は tools/build_vietnamese_dic.py (Wiktionary・Unihan)、pip で stanza
'''
NOTES = '  音読は macOS の say の Linh (ハノイの発音)、無ければ espeak-ng (vi)。カタカナ読みもハノイの発音から'


def original(analysis):
    """元の文 (語の切り分けの前の音節のまま)"""
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        if w in analyzer.PUNCTUATION and w not in '(“"‘':
            text += w
        else:
            text += (' ' if text and not text.endswith(('(', '“', '‘')) else '') + w
    return text


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('han'):
        out.append('漢越語: %s' % item.attrib('han'))
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('measure'):
        out.append('量詞: %s' % item.attrib('measure'))
    if item.attrib('relative'):
        out.append('関係節: %s (名詞に掛ける)' % item.attrib('relative'))
    if item.attrib('possessor'):
        out.append('所有者 (名詞の後ろ)')
    return out


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 語ごとに綴りから (vietnamese/katakana.py。ハノイの発音)"""
    from .katakana import katakana as word_kana
    words = getattr(analysis, 'original', None) or analysis.surfaces
    return [word_kana(w) for w in words if w not in analyzer.PUNCTUATION and any(c.isalpha() for c in w)]


def available():
    if not morphology.available():
        return ('no Vietnamese model or data (pip install stanza; Stanza vi models in $DRAGOMAN_DATA/vi/stanza; '
                'python3 tools/build_vietnamese_dic.py)')
    return None


COMMAND = Command(lang='vi', name='ベトナム語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='vi', katakana=katakana, notes=NOTES)
