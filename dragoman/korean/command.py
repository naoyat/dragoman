#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary, morphology

USAGE = '''
  ./dragoman.py ko -e "소년이 학교에서 책을 읽었다."
  語節を形態素解析器 kiwipiepy で名詞・用言と助詞・語尾に分け、助詞 (이/가・을/를・에게・에서 …) から格を、語尾から
  時制・文の種類・接続を決めて日本語に訳す。辞書は tools/build_korean_dic.py (Wiktionary)、pip install kiwipiepy
'''

CASE_NAMES = {'Nom': '主格', 'Acc': '対格', 'Gen': '属格', 'Dat': '与格', 'Obl': '後置詞の目的語', 'Voc': '呼格'}


def explain(word):
    item = word.items[0] if word.items else None
    if item is None:
        return []
    out = []
    if item.attrib('form'):
        out.append(item.attrib('form'))
    if item.attrib('hanja'):
        out.append('漢字語 %s' % item.attrib('hanja'))
    particles = getattr(word, 'particles', None)
    if particles:
        out.append('助詞: %s' % ' + '.join(particles))
    focus = getattr(word, 'focus', None)
    if focus:
        out.append({'topic': '主題 은/는 →「は」', 'also': '도 →「も」', 'only': '만 →「だけ」'}[focus])
    if getattr(word, 'attributive', None):
        out.append('連体形 -%s (後ろの名詞に掛かる)' % word.attributive)
    if item.attrib('relative'):
        out.append('関係節「%s」が掛かる' % item.attrib('relative'))
    head = getattr(word, 'relative_of', None)
    if head is not None:
        out.append('関係節の語 (%s に掛かる)' % head.surface)
    return out


def original(analysis):
    """元の文"""
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '(“"‘「' else (' ' if text else '') + w
    return text


def available():
    if not morphology.available():
        return 'no Korean analyzer or data (pip install kiwipiepy; python3 tools/build_korean_dic.py)'
    return None


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 標準発音の規則で語ごとに (korean/katakana.py。한국어 → ハングゴ)"""
    from .katakana import sentence
    return sentence(original(analysis), **kana_options)


COMMAND = Command(lang='ko', name='韓国語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=lambda a, o: original(a), explain=explain,
                  descendant_langs=('en', 'ja'), speech_lang='ko', katakana=katakana)
