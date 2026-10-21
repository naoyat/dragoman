#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ロシア語の語をカタカナで書く: 強勢記号を付けた綴り (morphology.stressed: Москва́) から発音を作り、どの言語にも共通の規則
# (core/kana.py) で
#
#   Москва́ → マスクヴァー、молоко́ → マラコー、Пу́тин → プーチン、Татья́на → タチヤーナ、Достое́вский → ダスタイェーフスキー
#
# 発音どおりに (綴りには寄せない):
#   - 強勢の無い о・а は「ア」、е・я は「イ」(語末の я は「ア」): Москва́ → マスクヴァー、тебя́ → チビャー
#   - 強勢のある母音は開音節 (語末か、次の母音までの子音が1つか、子音 + r・l・n・m・v・j) なら長く (ˑ。既定 long='phonetic'): Ната́ша → ナターシャ、Ива́н → イヴァン
#   - 軟子音: т・д は「チ」「ジ」の行 (Пу́тин → プーチン、дя́дя → ジャージャ)、ほかは子音 + j (ня → ニャ、всё → フスョー)、
#     e・и の前はそのまま (си・зи は「シ」「ジ」: сы の「スィ」と分ける)。
#     ь の後ろに母音の続かない軟子音は「イ段」(мать → マチ、Игорь → イーガリ)、ь + 母音は「イ」+ j (Татья́на → タチヤーナ)
#   - 語末と無声子音の前の有声子音は無声に (Че́хов → チェーハフ、во́дка → ヴォートカ)、有声子音 (в を除く) の前の無声子音は有声に
#     (вокза́л → ヴァグザール)
#   - сч・зч は щ (сча́стья → シャスチヤ)、ы はウ段 + ィ (кры́лья → クルィリヤ)、-ого・-его の г は [v] (сего́дня → シヴォードニャ。
#     мно́го・стро́го などは г のまま)、-тся・-ться は「ッツァ」、語末の -ий・-ый は「イー」
# 強勢が分からない語 (辞書に無い語) は、母音が1つならそれに、2つ以上なら弱める・長くするをしない
#
import unicodedata

from dragoman.core.kana import kana
from . import script

HARD_VOWELS = {'а': 'a', 'о': 'o', 'у': 'u', 'ы': 'ɨ', 'э': 'e'}
SOFT_VOWELS = {'я': 'a', 'ё': 'o', 'ю': 'u', 'е': 'e', 'и': 'i'}
CONSONANTS = {'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ж': 'ʒ', 'з': 'z', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
              'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'tʃ', 'ш': 'ʃ', 'щ': 'ʃ',
              'й': 'j'}
ALWAYS_HARD = ('ж', 'ш', 'ц')
VOICELESS = {'b': 'p', 'v': 'f', 'g': 'k', 'd': 't', 'z': 's', 'ʒ': 'ʃ'}
VOICED = {v: k for k, v in VOICELESS.items()}
# 綴りどおりに読まない語・つづり (強勢記号を除いた形で)
SPELLING = (('сч', 'щ'), ('зч', 'щ'), ('вств', 'ств'), ('лнц', 'нц'), ('рдц', 'рц'), ('стн', 'сн'), ('здн', 'зн'))
G_WORDS = ('много', 'немного', 'строго', 'дорого', 'недорого', 'убого', 'полого', 'отлого', 'нестрого')   # -ого の г を読む語
WORDS = {'что': 'што', 'чтобы': 'штобы', 'конечно': 'конешно', 'скучно': 'скушно', 'его': 'ево', 'сегодня': 'севодня'}


def _segments(word):
    """綴り → [(音, 種類, 綴りの添字)]。種類は 'V' (母音)・'C' (子音)・'Cs' (軟子音)・'j'"""
    out = []
    for k, c in enumerate(word):
        prev = word[k - 1] if k else ''
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c in HARD_VOWELS:
            hard = HARD_VOWELS[c]
            out.append(('i' if hard == 'ɨ' and prev in ALWAYS_HARD else hard, 'V', k))
        elif c in SOFT_VOWELS:
            if prev in CONSONANTS and prev != 'й':
                if prev in ALWAYS_HARD and c == 'и':
                    out.append(('i', 'V', k))     # жи・ши・ци は「ジ」「シ」「ツィ」
                else:
                    out.append((SOFT_VOWELS[c], 'V', k))
            else:
                if prev == 'ь' and out and out[-1][1] != 'V':
                    out.append(('i', 'V', None))   # ь + 母音は「イ」+ j (Татьяна → タチヤナ)
                if c != 'и' or prev in ('ь', 'ъ'):
                    out.append(('j', 'j', None))
                out.append((SOFT_VOWELS[c], 'V', k))
        elif c in CONSONANTS:
            soft = c not in ALWAYS_HARD and (nxt == 'ь' or nxt in SOFT_VOWELS)
            out.append((CONSONANTS[c], 'Cs' if soft and c not in ('ч', 'щ', 'й') else 'C', k))
        elif c == 'ь' and out and out[-1][1] in ('C', 'Cs') and not (nxt in SOFT_VOWELS or nxt in HARD_VOWELS):
            if out[-1][0] not in ('ʃ', 'ʒ', 'tʃ', 'j'):
                out.append(('i', 'V', None))       # 母音の続かない ь は「イ段」(мать → マチ)
    return out


def phonemes(word):
    """強勢記号を付けた語 → 共通の規則の音素の列"""
    word = unicodedata.normalize('NFC', word)
    stress = script.stress_index(word)
    plain = script.strip_stress(word).lower()
    plain = WORDS.get(plain, plain)   # 同じ長さの綴りに置き換える (強勢の添字はそのまま)
    for old, new in SPELLING:
        if old in plain:
            k = plain.index(old)
            if stress is not None and stress > k:
                stress -= len(old) - len(new)
            plain = plain.replace(old, new, 1)
    if plain.endswith(('ого', 'его')) and len(plain) > 3 and plain not in G_WORDS:
        plain = plain[:-2] + 'во'
    tsa = plain.endswith(('ться', 'тся'))
    if tsa:
        plain = plain[:-4] if plain.endswith('ться') else plain[:-3]
    vowel_positions = [k for k, c in enumerate(plain) if c in HARD_VOWELS or c in SOFT_VOWELS]
    if plain in UNSTRESSED:
        stress = -1                          # 強勢の無い語 (не → ニ、на → ナ)
    elif stress is None and len(vowel_positions) == 1:
        stress = vowel_positions[0]
    segs = _segments(plain)
    if tsa:
        segs += [('ts', 'C', None), ('ts', 'C', None), ('a', 'V', None)]
    # 語末の -ий・-ый (強勢の無いもの) は「イー」
    if len(segs) >= 2 and segs[-1][0] == 'j' and segs[-2][1] == 'V' and segs[-2][0] in ('i', 'ɨ') and \
            segs[-2][2] != stress and not tsa:
        segs = segs[:-2] + [(segs[-2][0] + 'ː', 'V', segs[-2][2])]
    # 有声・無声の同化 (右から): 語末は無声、無声子音の前は無声、有声子音 (в を除く) の前は有声
    out = list(segs)
    following = 'voiceless'   # 語末
    for k in range(len(out) - 1, -1, -1):
        ph, kind, idx = out[k]
        if kind not in ('C', 'Cs'):
            following = None
            continue
        if following == 'voiceless':
            ph = VOICELESS.get(ph, ph)
        elif following == 'voiced':
            ph = VOICED.get(ph, ph)
        out[k] = (ph, kind, idx)
        if ph in VOICED or ph in ('x', 'ts', 'tʃ'):
            following = 'voiceless'
        elif ph in VOICELESS and ph != 'v':
            following = 'voiced'
        else:
            following = None   # в・鳴音は同化させない
    # 母音の弱まりと強勢の長さ
    vowels = {}
    for k, (ph, kind, idx) in enumerate(out):
        if kind != 'V':
            continue
        if stress is not None and idx is not None and idx != stress and 'ː' not in ph:
            letter = plain[idx]
            if letter in ('о', 'а'):
                ph = 'a'
            elif letter in ('е', 'я'):
                ph = 'a' if letter == 'я' and idx == len(plain) - 1 else 'i'
        elif idx is not None and idx == stress and _open(out[k + 1:]):
            ph += 'ˑ'                              # 開音節の強勢のある母音
        vowels[k] = ph
    out = [(vowels.get(k, ph), kind, idx) for k, (ph, kind, idx) in enumerate(out)]
    # 軟子音
    result = []
    for k, (ph, kind, idx) in enumerate(out):
        nxt = out[k + 1] if k + 1 < len(out) else None
        if kind == 'Cs':
            if ph in ('t', 'd'):
                result.append('tʃ' if ph == 't' else 'dʒ')   # Путин → プーチン
                continue
            if ph in ('s', 'z') and nxt is not None and nxt[1] == 'V' and nxt[0][:1] == 'i':
                ph = 'ɕ' if ph == 's' else 'ʑ'     # си・зи は「シ」「ジ」(сы の「スィ」と分ける)
            if result and result[-1] == {'ɕ': 's', 'ʑ': 'z'}.get(ph):
                result[-1] = ph                     # сси → ッシ (Росси́я → ラッシーヤ)
            result.append(ph)
            if nxt is not None and nxt[1] == 'V' and nxt[0][:1] in ('a', 'o', 'u'):
                result.append('j')                  # ня → ニャ
            continue
        result.append(ph)
    return result


SONORANTS = ('r', 'l', 'n', 'm', 'v', 'j')
UNSTRESSED = ('и', 'а', 'о', 'у', 'но', 'не', 'ни', 'на', 'за', 'по', 'до', 'из', 'от', 'об', 'со', 'во', 'ко', 'же',
              'ли', 'бы')   # 強勢の無い1音節の語 (接続詞・前置詞・小辞)


def _open(rest):
    """強勢のある母音の音節が開いているか: 語末か、次の母音までの子音が1つか、子音 + 流音・鼻音など (Ната́ша・Москва́。
    во́дка・А́нна・Ива́н は閉じる)。ь の「イ」(мать) は母音に数えない"""
    consonants = []
    for ph, kind, idx in rest:
        if kind == 'V':
            if idx is None:
                return False
            break
        consonants.append(ph)
    else:
        return not consonants
    if len(consonants) <= 1:
        return True
    return len(consonants) == 2 and consonants[1] in SONORANTS and consonants[0] != consonants[1]


def sentence(words, **options):
    """文のカタカナ読み (強勢記号を付けた語の列 → 語ごとの列)。母音の無い前置詞 (в・к・с) は次の語に続ける
    (в Москве́ → ヴマスクヴェー、с дру́гом →ズドルーガム)"""
    out = []
    prefix = ''
    for w in words:
        if not any(c.isalpha() for c in w):
            continue
        plain = script.strip_stress(w).lower()
        if plain in ('в', 'к', 'с'):
            prefix += w
            continue
        out.append(katakana(prefix + w, **options))
        prefix = ''
    if prefix:
        out.append(katakana(prefix, **options))
    return out


def katakana(word, long='phonetic', **options):
    """強勢記号を付けた語 (Москва́) → カタカナ"""
    if script.strip_stress(word).lower() == 'б':
        return 'ブ'   # бы を縮めた助詞 б は前の語に続けて読む (語末の無声化をしない: сколько б → スコリカ ブ)
    return kana(phonemes(word), long=long, **options)
