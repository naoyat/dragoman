#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology


USAGE = '''
  ./dragoman.py mn -e "Хүү өчигдөр охинд ном өгсөн."
  語を辞書 (Wiktionary) と規則で語幹と接尾辞 (格・再帰所有・時制・否定・副動詞・分詞) に分け、格の接尾辞から格の枠を
  決めて日本語に訳す。語順のままの訳 (≒) も添える。ラテン文字の転写 (Xüü öcigdör oxin-d …) も読む。
  辞書は tools/build_mongolian_dic.py
'''


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    rec = getattr(word, 'record', None)
    if rec is not None and rec.get('kind') == 'noun' and rec.get('case') not in (None, 'Nom'):
        out.append('格: %s' % rec['case'])
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('script'):
        out.append('モンゴル文字 %s' % item.attrib('script'))
    if item.attrib('relative'):
        out.append('関係節「%s」が掛かる' % item.attrib('relative'))
    return out


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '("“«' else (' ' if text else '') + w
    return text


def available():
    return None if dictionary.available() else 'no Mongolian data (python3 tools/build_mongolian_dic.py)'


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 綴りの発音から語ごとに (mongolian/katakana.py)"""
    from .katakana import sentence
    from .script import from_latin, has_cyrillic
    text = original(analysis)
    return sentence(text if has_cyrillic(text) else from_latin(text), **kana_options)   # ラテン文字の転写はキリル文字に


COMMAND = Command(lang='mn', name='モンゴル語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='mn', katakana=katakana)
