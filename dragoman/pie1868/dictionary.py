#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 印欧祖語の辞書引き (手作りの辞書 lexicon.py。データのダウンロードは要らない)
#
from .lexicon import FORMS, LEMMAS


def available():
    return True


def gloss(lemma):
    return LEMMAS[lemma][0] if lemma in LEMMAS else lemma


def _item(surface, reading):
    lemma = reading['lemma']
    item = {'surface': surface, 'base': lemma, 'ja': gloss(lemma), 'gloss_lang': 'ja', 'source': 'lexicon',
            'pos': reading['pos']}
    if 'cng' in reading:
        item['_'] = list(reading['cng'])
    for key in ('tense', 'mood', 'voice', 'person', 'number', 'desc', 'gap_ja'):
        if key in reading:
            item[key] = reading[key]
    if reading['pos'] in ('verb', 'participle'):
        item['pres1sg'] = lemma + ('(存在)' if reading.get('exist') else '')   # 存在の as は繋辞の表 (as) から外す
    return item


def lookup(word):
    """語形 (シュライヒャーの表記。大文字・小文字は問わない) → 解析の項目のリスト"""
    return [_item(word, r) for r in FORMS.get(word.lower(), [])]


def verb_items(lemma):
    """見出し (動詞の語根) の訳語の項目 (分詞の元の動詞の訳語に使う)"""
    if lemma not in LEMMAS:
        return []
    return [{'surface': lemma, 'base': lemma, 'ja': gloss(lemma), 'gloss_lang': 'ja', 'pos': 'verb', 'pres1sg': lemma}]


def modern(lemma):
    """見出しの今の再建形 (*h₂ówis)"""
    return LEMMAS[lemma][1] if lemma in LEMMAS else None


def cognates(lemma):
    return LEMMAS[lemma][2] if lemma in LEMMAS else []


def etymology(lemma):
    """語源 (core/etymology の形): 今の再建形と同源の語"""
    if lemma not in LEMMAS:
        return []
    return [{'ancestors': [('root', 'ine-pro', modern(lemma), '')],
             'cognates': [(code, term) for code, term in cognates(lemma)], 'text': ''}]


def descendants(lemma):
    return []
