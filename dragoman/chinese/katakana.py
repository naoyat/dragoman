#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語 (普通話) の語をカタカナで書く: 語の拼音 (CC-CEDICT。無ければ pypinyin) の音節ごとに、声母 (初めの子音) の行と
# 韻母 (残り) の段で。声調は書かない
#
#   你好 → ニハオ (長さは書かない)、九 (jiǔ) → ジョウ、对 (duì) → ドゥェイ、北京 → ベイジン、
#   中国 → ジョングオ、谢谢 → シエシエ、的 → ダ、日本 → リベン、月亮 → ユエリャン、女儿 → ニュアル
#
#   - 無気音 b・d・g・j・zh・z はバ・ダ・ガ・ジャ・ジャ・ザ行、有気音 p・t・k・q・ch・c はパ・タ・カ・チャ・チャ・ツァ行
#     (日本語の耳には無気音が濁って聞こえる)。x・sh はシャ行、s はサ行、r はラ行、h はハ行、f はファ行
#   - 省いて書く韻母は元の形で: iu = iou「ヨウ」(九 → ジョウ)、ui = uei「ウェイ」(对 → ドゥェイ)、un = uen「ウン」
#   - j・q・x・y の後ろの u は ü「ユ」(去 → チュ、学 → シュエ)。zi・ci・si の i は「ウ」(ズ・ツ・ス)、zhi・chi・shi・ri の i は
#     「イ」(ジ・チ・シ・リ)
#   - e は「ウ」(哥 → グ、喝 → フ)、軽声の e は「ア」(的 → ダ、了 → ラ)。eng は「オン」(风 → フォン)、ong は「オン」
#   - 儿化 (哪儿 nǎr) の r は「ル」
#
import re

from dragoman.core.kana import ROWS

INITIALS = ('zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's',
            'y', 'w')
# 声母 → 共通の規則の行 (core/kana.ROWS)
ROW = {'b': 'b', 'p': 'p', 'm': 'm', 'f': 'f', 'd': 'd', 't': 't', 'n': 'n', 'l': 'r', 'g': 'g', 'k': 'k', 'h': 'h',
       'j': 'ʒ', 'q': 'tʃ', 'x': 'ʃ', 'zh': 'ʒ', 'ch': 'tʃ', 'sh': 'ʃ', 'r': 'r', 'z': 'z', 'c': 'ts', 's': 's', '': ''}
# 韻母 → 段の列 (母音の並び。'N' は「ン」、'ʏ' は「ユ」の段、'ɰ' は「ウ」を小書きにしない)
FINALS = {
    'a': 'a', 'o': 'o', 'e': 'u', 'ai': 'ai', 'ei': 'ei', 'ao': 'ao', 'ou': 'ou', 'an': 'aN', 'en': 'eN', 'ang': 'aN',
    'eng': 'oN', 'ong': 'oN', 'er': 'ar',
    'i': 'i', 'ia': 'ja', 'ie': 'ie', 'iao': 'jao', 'iu': 'jou', 'iou': 'jou', 'ian': 'ieN', 'in': 'iN', 'iang': 'jaN',
    'ing': 'iN', 'iong': 'joN',
    'u': 'u', 'ua': 'wa', 'uo': 'wo', 'uai': 'wai', 'ui': 'wei', 'uei': 'wei', 'uan': 'waN', 'un': 'uN', 'uen': 'uN',
    'uang': 'waN', 'ueng': 'woN',
    'ü': 'ʏ', 'üe': 'ʏe', 'üan': 'ʏeN', 'ün': 'ʏN', 'v': 'ʏ', 've': 'ʏe', 'van': 'ʏeN', 'vn': 'ʏN',
}
SMALL = {'a': 'ァ', 'i': 'ィ', 'u': 'ゥ', 'e': 'ェ', 'o': 'ォ'}
YOON = {'a': 'ャ', 'u': 'ュ', 'o': 'ョ', 'e': 'ェ'}


def split(syllable):
    """拼音の音節 (数字の声調付き: jiu3) → (声母, 韻母, 声調)"""
    s = syllable.lower().replace('u:', 'ü')
    tone = int(s[-1]) if s[-1:].isdigit() else 5
    s = s.rstrip('012345')
    initial = next((i for i in INITIALS if s.startswith(i) and len(s) > len(i)), '')
    final = s[len(initial):]
    if initial in ('j', 'q', 'x', 'y') and final.startswith('u'):
        final = 'ü' + final[1:]   # ju・qu・xu・yu の u は ü
    if initial == 'y':
        initial, final = '', ('i' + final if not final.startswith(('i', 'ü')) else final)   # ya → ia、yi → i
    if initial == 'w':
        initial, final = '', ('u' + final if final != 'u' else 'u')   # wa → ua、wu → u
    if initial == '' and final in ('ia', 'io'):
        pass
    return initial, final, tone


def _row(initial, vowel):
    return ROWS[ROW[initial]][vowel]


def syllable_kana(syllable):
    if syllable.lower().rstrip('012345') == 'r':
        return 'ル'   # 儿化 (哪儿 → ナル)
    initial, final, tone = split(syllable)
    if final == 'i' and initial in ('z', 'c', 's'):
        return _row(initial, 'u')                     # zi・ci・si → ズ・ツ・ス
    if final == 'i' and initial in ('zh', 'ch', 'sh', 'r'):
        return _row(initial, 'i')                     # zhi・chi・shi・ri → ジ・チ・シ・リ
    if final == 'e' and tone == 5 and initial:
        return _row(initial, 'a')                     # 軽声の e (的 → ダ、了 → ラ)
    if final == 'o' and initial in ('b', 'p', 'm', 'f'):
        final = 'uo'                                  # bo・po・mo・fo は [uo] (ボ → ブオ)
        return _row(initial, 'u') + 'オ'
    if not initial and final in ('uen', 'un'):
        return 'ウェン'                              # wen (文 → ウェン。子音の後ろの un は「ウン」: 春 → チュン)
    seq = FINALS.get(final)
    if seq is None:
        return final
    out = ''
    k = 0
    if seq[0] == 'j':                                  # i + 母音: 子音があれば拗音 (jia → ジャ、liu → リョウ)
        vowel = seq[1]
        out = (_row(initial, 'i')[:-1] if initial and _row(initial, 'i').endswith('ィ') else _row(initial, 'i')) + YOON.get(vowel, vowel) \
            if initial else {'a': 'ヤ', 'o': 'ヨ', 'u': 'ユ', 'e': 'イェ'}[vowel]
        if initial in ('j', 'q', 'x', 'zh', 'ch', 'sh'):
            out = _row(initial, vowel)                # ジャ・チャ・シャの行はそのまま拗音 (jia → ジャ)
        k = 2
    elif seq[0] == 'w':                                # u + 母音 (gua → グア、duo → ドゥオ、dui → ドゥェイ)
        vowel = seq[1]
        if initial:
            out = _row(initial, 'u') + ('ァ' if vowel == 'a' else 'オ' if vowel == 'o' else 'ェ')
            if vowel == 'a' and initial not in ('g', 'k', 'h'):
                out = _row(initial, 'u') + 'ア'   # ズア・チュアン (クァ・グァ・ファ は小書き)。uo は「オ」(グオ・ドゥオ)
        else:
            out = {'a': 'ワ', 'o': 'ウォ', 'e': 'ウェ'}[vowel]
        k = 2
    elif seq[0] == 'ʏ':                                # ü (去 → チュ、学 → シュエ、月 → ユエ)
        if initial:
            out = _row(initial, 'y') if ROW[initial] not in ('ʒ', 'tʃ', 'ʃ') else _row(initial, 'u')
        else:
            out = 'ユ'
        k = 1
    else:
        out = _row(initial, seq[0])
        k = 1
    for c in seq[k:]:
        out += 'ン' if c == 'N' else {'a': 'ア', 'i': 'イ', 'u': 'ウ', 'e': 'エ', 'o': 'オ', 'r': 'ル'}.get(c, c)
    if final == 'er' and not initial:
        out = 'アル'   # 儿・二・耳
    return out


def pinyin_kana(pinyin):
    """拼音 (音節を空白で区切った、数字の声調付き: zhong1 guo2) → カタカナ"""
    return ''.join(syllable_kana(s) for s in pinyin.split() if re.match(r"[a-zA-Zü:]+[0-5]?$", s))


def katakana(word, **options):
    """漢字の語 → カタカナ"""
    from . import morphology
    if not re.search('[㐀-鿿]', word):
        return ''
    return pinyin_kana(morphology.pinyin(word))


def sentence(text, **options):
    from .segment import segment
    return [katakana(w) for w in segment(text) if re.search('[㐀-鿿]', w)]
