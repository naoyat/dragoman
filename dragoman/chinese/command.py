#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語 (普通話) のコマンドの設定 (core/cli.py)
#
import re

from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py zh -e "我昨天买了一本书。"
  語に切り分け (spaCy の pkuseg と CC-CEDICT の見出し)、spaCy (zh_core_web_sm) の品詞・依存関係で語の項目を作り、
  量詞・的・アスペクト (了・过・着)・把・被・方位詞をまとめて、格の枠から日本語に訳す。簡体字も繁体字も読む。
  辞書は tools/build_chinese_dic.py (CC-CEDICT)、pip で zh_core_web_sm・spacy-pkuseg・opencc
'''
NOTES = '  見出しの行に拼音 (声調記号付き) を添える。音読は macOS の say の Tingting (普通話)、無ければ espeak-ng (cmn)'


def original(analysis):
    return ''.join(analysis.original if getattr(analysis, 'original', None) else analysis.surfaces)


def pinyin_text(words):
    """語の列 → 声調記号付きの拼音 (語ごとに空白で: wǒ zuótiān mǎi le)"""
    try:
        from pypinyin import lazy_pinyin, Style
    except ImportError:
        return ''
    out = []
    for w in words:
        if re.search('[㐀-鿿]', w):
            out.append(''.join(lazy_pinyin(w, style=Style.TONE)))
        elif out and re.fullmatch(r'[。，、；：？！…]', w):
            out[-1] += {'。': '.', '，': ',', '、': ',', '；': ';', '：': ':', '？': '?', '！': '!', '…': '…'}[w]
    return ' '.join(out)


def header(analysis, options):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    return '%s  (%s)' % (original(analysis), pinyin_text(words))


def romanized(word):
    try:
        from pypinyin import lazy_pinyin, Style
        return ''.join(lazy_pinyin(word, style=Style.TONE))
    except ImportError:
        return word


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('relative'):
        out.append('連体修飾節: %s (名詞に掛ける)' % item.attrib('relative'))
    return out


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 語ごとに拼音から (chinese/katakana.py)"""
    from .katakana import katakana as word_kana
    words = getattr(analysis, 'original', None) or analysis.surfaces
    return [word_kana(w) for w in words if re.search('[㐀-鿿]', w)]


def available():
    if not morphology.available():
        return ('no Chinese model or data (pip install zh_core_web_sm spacy-pkuseg opencc; '
                'python3 tools/build_chinese_dic.py)')
    return None


COMMAND = Command(lang='zh', name='中国語 (普通話)', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=header, speech_text=lambda a, o: original(a), romanize=romanized, explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='zh', katakana=katakana, notes=NOTES)
