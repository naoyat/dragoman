#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語のカタカナ読み (--kana): 国語字 (chữ Quốc ngữ) の綴りから、ハノイの発音で音節ごとに
#
#   xin chào → シン チャオ、cảm ơn → カム オン、Hà Nội → ハー ノイ、phở → フォー、Việt Nam → ヴィエット ナム、
#   Nguyễn → グエン、bánh mì → バイン ミー、áo dài → アオ ザイ
#
#   - 頭子音: d・gi・r はハノイの [z] で「ザ」行、v は「ヴ」、ph は「フ」、kh は「カ」行、ch・tr は「チャ」行、
#     x・s は「サ」行、nh は「ニャ」行、ng・ngh は「ガ」行 (語頭の鼻音 [ŋ] は日本語に無いので)、đ は「ダ」行
#   - 末子音: -m「ム」、-n・-ng・-nh「ン」、-p「ップ」、-t「ット」、-c・-ch「ック」。-anh・-ach は「アイン・アイック」
#     (ハノイの発音)、-inh・-ich は「イン・イック」、-ênh・-êch は「エン・エック」
#   - 母音1つで終わる音節は長く「ー」(bà → バー)。声調は書かない
#
import re
import unicodedata

# 声調記号を外す (ă â ê ô ơ ư の字の形はそのまま)
TONES = {'̀', '́', '̃', '̉', '̣'}


def strip_tone(syllable):
    decomposed = unicodedata.normalize('NFD', syllable)
    return unicodedata.normalize('NFC', ''.join(c for c in decomposed if c not in TONES))


INITIALS = (('ngh', 'g'), ('ng', 'g'), ('gh', 'g'), ('gi', 'z'), ('nh', 'ny'), ('ch', 'ch'), ('tr', 'ch'),
            ('ph', 'f'), ('th', 't'), ('kh', 'k'), ('qu', 'kw'), ('b', 'b'), ('c', 'k'), ('d', 'z'), ('đ', 'd'),
            ('g', 'g'), ('h', 'h'), ('k', 'k'), ('l', 'r'), ('m', 'm'), ('n', 'n'), ('p', 'p'), ('r', 'z'),
            ('s', 's'), ('t', 't'), ('v', 'v'), ('x', 's'))
FINALS = (('nh', 'n'), ('ng', 'n'), ('ch', 'k'), ('c', 'k'), ('m', 'm'), ('n', 'n'), ('p', 'p'), ('t', 't'))
# 母音 (声調を外した綴り) → 仮名の母音の列
VOWELS = {'a': 'a', 'ă': 'a', 'â': 'a', 'e': 'e', 'ê': 'e', 'i': 'i', 'y': 'i', 'o': 'o', 'ô': 'o', 'ơ': 'o', 'u': 'u',
          'ư': 'u'}
# 二重母音・三重母音 (長いものから)
CLUSTERS = (('uyê', 'uie'), ('uya', 'uia'), ('ươi', 'uoi'), ('ươu', 'uou'), ('uôi', 'uoi'), ('oai', 'oai'),
            ('oay', 'oai'), ('oeo', 'ueo'), ('iêu', 'ieu'), ('yêu', 'ieu'), ('uây', 'uai'), ('ia', 'ia'), ('iê', 'ie'),
            ('yê', 'ie'), ('ua', 'ua'), ('uô', 'uo'), ('ưa', 'ua'), ('ươ', 'uo'), ('ai', 'ai'), ('ao', 'ao'),
            ('au', 'au'), ('ay', 'ai'), ('âu', 'au'), ('ây', 'ai'), ('eo', 'eo'), ('êu', 'eu'), ('iu', 'iu'),
            ('oi', 'oi'), ('ôi', 'oi'), ('ơi', 'oi'), ('ui', 'ui'), ('ưi', 'ui'), ('ưu', 'uu'), ('oa', 'oa'),
            ('oă', 'oa'), ('oe', 'oe'), ('uê', 'ue'), ('uơ', 'uo'), ('uy', 'ui'), ('uâ', 'ua'))

KANA = {
    '': {'a': 'ア', 'i': 'イ', 'u': 'ウ', 'e': 'エ', 'o': 'オ'},
    'k': {'a': 'カ', 'i': 'キ', 'u': 'ク', 'e': 'ケ', 'o': 'コ'},
    'g': {'a': 'ガ', 'i': 'ギ', 'u': 'グ', 'e': 'ゲ', 'o': 'ゴ'},
    's': {'a': 'サ', 'i': 'シ', 'u': 'ス', 'e': 'セ', 'o': 'ソ'},
    'z': {'a': 'ザ', 'i': 'ジ', 'u': 'ズ', 'e': 'ゼ', 'o': 'ゾ'},
    't': {'a': 'タ', 'i': 'ティ', 'u': 'トゥ', 'e': 'テ', 'o': 'ト'},
    'd': {'a': 'ダ', 'i': 'ディ', 'u': 'ドゥ', 'e': 'デ', 'o': 'ド'},
    'n': {'a': 'ナ', 'i': 'ニ', 'u': 'ヌ', 'e': 'ネ', 'o': 'ノ'},
    'ny': {'a': 'ニャ', 'i': 'ニ', 'u': 'ニュ', 'e': 'ニェ', 'o': 'ニョ'},
    'h': {'a': 'ハ', 'i': 'ヒ', 'u': 'フ', 'e': 'ヘ', 'o': 'ホ'},
    'f': {'a': 'ファ', 'i': 'フィ', 'u': 'フ', 'e': 'フェ', 'o': 'フォ'},
    'b': {'a': 'バ', 'i': 'ビ', 'u': 'ブ', 'e': 'ベ', 'o': 'ボ'},
    'p': {'a': 'パ', 'i': 'ピ', 'u': 'プ', 'e': 'ペ', 'o': 'ポ'},
    'v': {'a': 'ヴァ', 'i': 'ヴィ', 'u': 'ヴ', 'e': 'ヴェ', 'o': 'ヴォ'},
    'm': {'a': 'マ', 'i': 'ミ', 'u': 'ム', 'e': 'メ', 'o': 'モ'},
    'r': {'a': 'ラ', 'i': 'リ', 'u': 'ル', 'e': 'レ', 'o': 'ロ'},
    'ch': {'a': 'チャ', 'i': 'チ', 'u': 'チュ', 'e': 'チェ', 'o': 'チョ'},
    'kw': {'a': 'クア', 'i': 'クイ', 'u': 'ク', 'e': 'クエ', 'o': 'クオ'},
}
# 後ろの母音 (二重母音の2つめ以降) の仮名
GLIDES = {'a': 'ア', 'i': 'イ', 'u': 'ウ', 'e': 'エ', 'o': 'オ'}
# 頭子音 + w (o・u で始まる二重母音 oa・oe・uê・uy …: hoa → ホア)
FINAL_KANA = {'m': 'ム', 'n': 'ン', 'p': 'ップ', 't': 'ット', 'k': 'ック'}


def _split(syl):
    """音節 (声調を外した小文字) → (頭子音, 母音の綴り, 末子音)"""
    initial = ''
    for spelling, sound in INITIALS:
        if syl.startswith(spelling) and (len(syl) > len(spelling) or spelling == 'gi'):
            initial, syl = sound, syl[len(spelling):]
            if spelling == 'gi' and (not syl or syl[0] not in 'aăâeêoôơuưy'):
                syl = 'i' + syl   # gì・gìn: gi の i は母音
            break
    final = ''
    for spelling, sound in FINALS:
        if syl.endswith(spelling) and len(syl) > len(spelling):
            final_spelling, final, syl = spelling, sound, syl[:-len(spelling)]
            break
    else:
        final_spelling = ''
    return initial, syl, final, final_spelling


def _vowels(nucleus):
    for spelling, sound in CLUSTERS:
        if nucleus == spelling:
            return sound
    return ''.join(VOWELS.get(c, '') for c in nucleus)


def syllable(syl):
    """1音節 → カタカナ"""
    low = strip_tone(syl.lower())
    if not re.fullmatch('[a-zăâêôơưđ]+', low):
        return syl
    initial, nucleus, final, final_spelling = _split(low)
    vowels = _vowels(nucleus)
    if not vowels:
        return syl
    if final_spelling in ('nh', 'ch') and vowels == 'a':
        vowels = 'ai'   # ハノイの -anh・-ach (bánh → バイン、sách → サイック)
    elif final_spelling in ('nh', 'ch') and vowels == 'e':
        pass            # -ênh・-êch (bệnh → ベン)
    if initial in ('kw',) and vowels[0] in 'aieo':
        head = KANA['k']['u'] + GLIDES[vowels[0]]   # qua → クア
        rest = vowels[1:]
    else:
        head = KANA[initial][vowels[0]]
        rest = vowels[1:]
    out = head + ''.join(GLIDES[v] for v in rest)
    if final:
        out += FINAL_KANA[final]
    elif len(vowels) == 1:
        out += 'ー'     # 母音1つで終わる音節は長く (bà → バー、phở → フォー)
    return out


def katakana(word, **options):
    """語 (音節を空白でつないだもの) → カタカナ (音節ごとに空白で)"""
    return ' '.join(syllable(s) for s in word.split() if s)
