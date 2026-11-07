#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語のコマンドの設定 (core/cli.py)
#
import re

from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py yue -e "我食咗飯喇。"
  語に切り分け (PyCantonese と CC-Canto・CC-CEDICT の見出し)、広東語の語を普通話の語に置き換えて (佢 → 他、咗 → 了、
  我高過佢 → 我比他高 …)、普通話の解析器 (spaCy の zh_core_web_sm の品詞・依存関係) で日本語に訳す。表示は広東語のまま。
  辞書は tools/build_cantonese_dic.py (CC-Canto) と tools/build_chinese_dic.py (CC-CEDICT)、pip で pycantonese
'''
NOTES = '  見出しの行に粤拼 (Jyutping) を添える。音読は macOS の say の Sinji (香港)、無ければ espeak-ng (yue)'
HAN = '[㐀-鿿豈-﫿]'


def original(analysis):
    return ''.join(analysis.original if getattr(analysis, 'original', None) else analysis.surfaces)


def jyutping_text(words):
    """語の列 → 粤拼 (語ごとに空白で、語の中の音節は続けて: ngo5 sik6 zo2 faan6)"""
    out = []
    for w in words:
        if re.search(HAN, w):
            out.append(morphology.jyutping(w).replace(' ', ''))
        elif out and re.fullmatch(r'[。，、；：？！…]', w):
            out[-1] += {'。': '.', '，': ',', '、': ',', '；': ';', '：': ':', '？': '?', '！': '!', '…': '…'}[w]
    return ' '.join(out)


def header(analysis, options):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    return '%s  (%s)' % (original(analysis), jyutping_text(words))


def romanized(word):
    return morphology.jyutping(word).replace(' ', '') or word


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    key = getattr(word, 'key', None)
    if key and key != word.surface and re.search(HAN, word.surface):
        out.append('普通話: %s' % key)
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('relative'):
        out.append('連体修飾節: %s (名詞に掛ける)' % item.attrib('relative'))
    return out


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 語ごとに粤拼から (cantonese/katakana.py)"""
    from .katakana import katakana as word_kana
    words = getattr(analysis, 'original', None) or analysis.surfaces
    return [word_kana(w) for w in words if re.search(HAN, w)]


def available():
    if not morphology.available():
        return ('no Cantonese data (pip install pycantonese zh_core_web_sm spacy-pkuseg opencc; '
                'python3 tools/build_chinese_dic.py; python3 tools/build_cantonese_dic.py)')
    return None


COMMAND = Command(lang='yue', name='広東語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=header, speech_text=lambda a, o: original(a), romanize=romanized, explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='yue', katakana=katakana, notes=NOTES)
