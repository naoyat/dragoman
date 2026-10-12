#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# アイヌ語の表記: 照合用の形 (現代の標準的なローマ字表記に寄せる) とカタカナ
#
# 知里幸惠『アイヌ神謡集』(1923) などの古いローマ字表記を、現代の表記 (中川裕・田村すず子などの辞典で使うもの) に寄せる:
#   sh → s (shirokanipe → sirokanipe、sapash → sapas)、ch → c (chikap → cikap)
#   母音の後ろの i / u (二重母音の後半) → y / w (kamui → kamuy、yaieyukar → yayeyukar、pauchi → pawci)
#   人称の接辞の = は照合では除く (ku=kor → kukor) ので、分けて書いても続けて書いてもよい
#
import re
import unicodedata

VOWELS = 'aeiou'
ACCENTS = {'́', '̀', '̂', '̄'}  # アクセント記号 (á) は照合では除く


def key(word):
    """照合用の形 (小文字、アクセント・= ・‘’ を除き、古い表記を現代の表記に)"""
    w = unicodedata.normalize('NFD', word.lower())
    w = ''.join(c for c in w if c not in ACCENTS)
    w = unicodedata.normalize('NFC', w)
    w = w.replace('=', '').replace('’', "'").replace('‘', "'").strip(".,;:!?“”\"()'")
    w = w.replace('sh', 's').replace('ch', 'c')
    w = re.sub(r'(?<=[aeiou])i', 'y', w)   # kamui → kamuy、yaieyukar → yayeyukar (母音の後ろの i)
    w = re.sub(r'(?<=[aeiou])u', 'w', w)   # pauci → pawci、kamuiutar → kamuywtar (母音の後ろの u)
    w = re.sub(r'(?<=n)g', 'k', w)          # 知里の表記の ng = nk (ingaras → inkaras)
    return w


def is_ainu_latin(text):
    return bool(re.search('[a-z]', text.lower()))


try:
    from ainu_utils import to_kana as _to_kana
except ImportError:  # ainu-utils (MIT) が無ければカタカナは出さない
    _to_kana = None


def kana(text):
    """ローマ字 → カタカナ (ainu-utils があれば)"""
    if _to_kana is None:
        return ''
    try:
        return _to_kana(key(text))
    except Exception:
        return ''


# カタカナ → ローマ字 (入力のカタカナを読むため。ainu-utils はローマ字 → カタカナだけ)
#   音節末の子音は小書きの文字: ㇰ k、ㇱ・ㇲ s、ㇳ t、ㇴ・ン n、ㇵ〜ㇹ h、ㇷ゚ p、ㇺ m、ㇻ〜ㇿ r。ッ は t (マッカチ → matkaci)
#   母音の後ろのイ・ウは y・w (アイヌ → aynu、カムイ → kamuy)。濁音は清音と区別しない (アイヌ語に有声・無声の対立が無い)
KANA_DIGRAPHS = {'トゥ': 'tu', 'チャ': 'ca', 'チュ': 'cu', 'チェ': 'ce', 'チョ': 'co', 'ウェ': 'we', 'ウィ': 'wi',
                 'ウォ': 'wo', 'イェ': 'ye', 'シャ': 'sa', 'シュ': 'su', 'シェ': 'se', 'ショ': 'so', 'ツァ': 'ca',
                 'ㇷ゚': 'p'}
KANA = dict(zip('アイウエオ', 'aeiou'.replace('e', 'i', 0)))
KANA.update({'ア': 'a', 'イ': 'i', 'ウ': 'u', 'エ': 'e', 'オ': 'o'})
for _row, _c in (('カキクケコ', 'k'), ('ガギグゲゴ', 'k'), ('サシスセソ', 's'), ('ザジズゼゾ', 's'), ('タチツテト', 't'),
                 ('ダヂヅデド', 't'), ('ナニヌネノ', 'n'), ('ハヒフヘホ', 'h'), ('バビブベボ', 'p'), ('パピプペポ', 'p'),
                 ('マミムメモ', 'm'), ('ラリルレロ', 'r')):
    for _k, _v in zip(_row, 'aiueo'):
        KANA[_k] = _c + _v
KANA.update({'シ': 'si', 'ジ': 'si', 'チ': 'ci', 'ヂ': 'ci', 'ツ': 'tu', 'ヅ': 'tu', 'ヤ': 'ya', 'ユ': 'yu', 'ヨ': 'yo',
             'ワ': 'wa', 'ヰ': 'wi', 'ヱ': 'we', 'ヲ': 'wo', 'ン': 'n', 'ッ': 't',
             'ㇰ': 'k', 'ㇱ': 's', 'ㇲ': 's', 'ㇳ': 't', 'ㇴ': 'n', 'ㇵ': 'h', 'ㇶ': 'h', 'ㇷ': 'h', 'ㇸ': 'h', 'ㇹ': 'h',
             'ㇺ': 'm', 'ㇻ': 'r', 'ㇼ': 'r', 'ㇽ': 'r', 'ㇾ': 'r', 'ㇿ': 'r', 'ㇷ゚': 'p', 'ー': ''})
KATAKANA = re.compile('[\u30a0-\u30ff\u31f0-\u31ff]')


def has_kana(text):
    return bool(KATAKANA.search(text))


def from_kana(text):
    """カタカナ → ローマ字 (照合用の形に寄せる: 母音の後ろの i・u は y・w)。カタカナ以外はそのまま"""
    text = unicodedata.normalize('NFC', text).replace('ㇷ\u309a', 'ㇷ゚')
    out = ''
    i = 0
    while i < len(text):
        two = text[i:i + 2]
        if two in KANA_DIGRAPHS:
            out += KANA_DIGRAPHS[two]
            i += 2
            continue
        c = text[i]
        out += KANA.get(c, '' if c in ('・', '　') and False else (' ' if c == '　' else c))
        i += 1
    out = re.sub(r'(?<=[aeiou])i(?![aeiou])', 'y', out)   # アイヌ → aynu、カムイ → kamuy
    out = re.sub(r'(?<=[aeiou])u(?![aeiou])', 'w', out)
    return out.replace('。', '.').replace('、', ',').replace('？', '?').replace('！', '!')

