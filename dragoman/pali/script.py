# -*- coding: utf-8 -*-
#
# パーリ語の文字: ローマ字 (PTS 式の IAST: ṃ・ḷ) と、シンハラ文字・タイ文字・ビルマ文字・デーヴァナーガリーの間の変換
# (vidyut の lipi。ISO 15919 を経て: 子音の ḷ・長い ē ō・ṁ を区別するので)
#
#   to_roman('ධම්මපදං') → dhammapadaṃ、convert('dhamma', 'Thai') → ธมฺม
#
# SuttaCentral (Mahāsaṅgīti) の ṁ も ṃ に揃える
#
import re
import unicodedata

from vidyut import lipi

SCRIPTS = {'sinhala': 'Sinhala', 'thai': 'Thai', 'myanmar': 'Burmese', 'devanagari': 'Devanagari'}
RANGES = {'Sinhala': '඀-෿', 'Thai': '฀-๿', 'Burmese': 'က-႟', 'Devanagari': 'ऀ-ॿ'}
LETTERS = 'A-Za-zĀāĪīŪūṂṃṀṁṄṅÑñṬṭḌḍṆṇḶḷ'
_detect = [(name, re.compile('[%s]' % r)) for name, r in RANGES.items()]
SHOWN = None   # 見出しに添える文字 (--script。None なら入力の文字。ローマ字の入力なら添えない)


def normalize(text):
    """ローマ字の綴りを揃える (NFC、ṁ → ṃ、Velthuis 風の ŋ は ṅ)"""
    text = unicodedata.normalize('NFC', text)
    return text.replace('ṁ', 'ṃ').replace('Ṁ', 'Ṃ').replace('ŋ', 'ṅ')


def script_of(text):
    """文字の種類 (vidyut の Scheme の名前)。ローマ字なら None"""
    for name, pattern in _detect:
        if pattern.search(text):
            return name
    return None


def to_iso(roman):
    """パーリ語のローマ字 → ISO 15919 (e・o は長い ē・ō、ṃ は ṁ)"""
    roman = normalize(roman.lower())
    return roman.replace('ṃ', 'ṁ').replace('e', 'ē').replace('o', 'ō')


def from_iso(iso):
    return iso.replace('ṁ', 'ṃ').replace('ē', 'e').replace('ō', 'o').replace('ṅ', 'ṅ')


def to_roman(text):
    """どの文字のパーリ語もローマ字 (ṃ・ḷ) に"""
    name = script_of(text)
    if name is None:
        return normalize(text)
    if name == 'Burmese':
        text = text.replace('ဿ', 'သ္သ')   # ဿ (ss の合字)
    return from_iso(lipi.transliterate(text, getattr(lipi.Scheme, name), lipi.Scheme.Iso15919))


def convert(roman, name):
    """ローマ字 → name の文字 (Sinhala・Thai・Burmese・Devanagari)"""
    out = lipi.transliterate(to_iso(roman), lipi.Scheme.Iso15919, getattr(lipi.Scheme, name))
    if name == 'Burmese':
        out = out.replace('သ္သ', 'ဿ')
    return out


def to_slp1(roman):
    """ローマ字 → SLP1 (サンスクリットの仕組みに渡すとき。ḷ は子音の L)"""
    return lipi.transliterate(to_iso(roman), lipi.Scheme.Iso15919, lipi.Scheme.Slp1)
