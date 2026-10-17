#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の綴り: 辞書を引く鍵と、ʻokina (声門閉鎖音 ʻ) の書き方の揺れ
#
# 今の綴りは ʻokina (ʻ U+02BB) と kahakō (長音符 ā ē ī ō ū) を書く (paʻu「煤」・pau「終わり」、kāu「あなたの」・kau「置く」)。
# 19世紀の新聞・聖書などは両方を書かないので、鍵は ʻokina と長音符を除いた小文字 (kaʻu → kau)。ʻokina の代わりの
# ' ‘ ` ’ も ʻ に揃える (normalize)
#
import unicodedata

OKINA = 'ʻ'
OKINA_VARIANTS = "'‘`’ʼ"


def normalize(text):
    """ʻokina の代わりの字 (' ‘ ` ’) を ʻ に、NFC に"""
    text = unicodedata.normalize('NFC', text)
    return ''.join(OKINA if c in OKINA_VARIANTS else c for c in text)


def key(text):
    """照合用の鍵: ʻokina と長音符を除いて小文字に (Kaʻū → kau)"""
    text = normalize(text).replace(OKINA, '')
    nfd = unicodedata.normalize('NFD', text)
    return unicodedata.normalize('NFC', ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')).lower()


def marked(text):
    """ʻokina か長音符を書いた綴りか"""
    t = normalize(text)
    return OKINA in t or unicodedata.normalize('NFD', t) != t


def is_hawaiian(text):
    """ハワイ語らしい綴り: ʻokina か、ハワイ語の字 (a e i o u h k l m n p w) だけの語が多い"""
    import re
    t = normalize(text)
    if OKINA in t and re.search('[āēīōū]', t.lower()):
        return True
    words = re.findall(r"[A-Za-zĀĒĪŌŪāēīōūʻ]+", t)
    return bool(words) and all(re.fullmatch('[aeiouāēīōūhklmnpwʻ]+', w.lower()) for w in words) and \
        sum(1 for w in words if OKINA in w) >= 1
