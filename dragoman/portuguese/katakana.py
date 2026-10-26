#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ポルトガル語の語をカタカナで書く: espeak-ng の発音 (IPA) を、どの言語にも共通の規則 (core/kana.py) で。
# 発音はブラジル (既定。pt='br'、--kana-pt=br: espeak-ng の pt-br) か ポルトガル (pt='pt'、--kana-pt=pt: espeak-ng の pt)
#
#   ブラジル: obrigado → オブリガドゥ、cidade → スィダジ、noite → ノイチ、Rio → ヒウ、coração → コラサウン、mãe → マイン、
#            muito → ムイントゥ、Brasil → ブラズィウ、também → タンベイン、gente → ジェンチ
#   ポルトガル: cidade → スィダド、noite → ノイト、Rio → リウ、Lisboa → リジュボア、vocês → ヴォセシュ
#
#   - 鼻母音は「ン」(bem → ベイン)。鼻音の二重母音は「ン」を最後に1つ (coração の ɐ̃ʊ̃ → アウン、mãe の ɐ̃j̃ → アイン)、
#     鼻音の子音の前の鼻母音は母音だけ (também → タンベイン)
#   - ブラジルの t・d + i は「チ」「ジ」(espeak-ng の tʃ・dʒ)、語頭・rr の r [x~h] はハ行 (carro → カホ)、語末の l [w] は「ウ」
#   - ポルトガルの弱い e [ɨ] は母音を書かない (noite → ノイト)、語末・子音の前の s [ʃ] は「シュ」
#   - 長さは書かない (ポルトガル語の母音に長短の区別は無い)
#
import functools
import shutil
import subprocess
import unicodedata

from dragoman.core.kana import kana, split_ipa

VOICES = {'br': 'pt-br', 'pt': 'pt'}
NASAL = '̃'
VOWEL_LETTERS = 'aɐæeɛəiɪoɔuʊɨyɯ'
NASAL_CONSONANTS = ('m', 'n', 'ŋ', 'ɲ')


def available():
    return shutil.which('espeak-ng') is not None


@functools.lru_cache(maxsize=20000)
def ipa(word, pt='br'):
    out = subprocess.run(['espeak-ng', '-v', VOICES.get(pt, 'pt-br'), '-q', '--ipa', word], capture_output=True,
                         text=True).stdout
    return out.strip()


def _base(p):
    return unicodedata.normalize('NFD', p or '')[:1]


def _is_vowel(p):
    return bool(p) and _base(p) in VOWEL_LETTERS


def _nasal(p):
    return NASAL in unicodedata.normalize('NFD', p or '')


def _oral(p):
    return unicodedata.normalize('NFC', unicodedata.normalize('NFD', p).replace(NASAL, ''))


def phonemes(word, pt='br'):
    """espeak-ng の IPA → 共通の規則の音素の列 (ポルトガル語の読み替え)"""
    phs = [p for p in split_ipa(ipa(word, pt)) if p not in ('ˈ', 'ˌ', ' ')]
    out = []
    for k, p in enumerate(phs):
        prev = out[-1] if out else ''
        nxt = phs[k + 1] if k + 1 < len(phs) else ''
        base = _base(p)
        if base == 'y':
            p = 'i' + p[1:]                       # espeak-ng のブラジルの [i] (cidade の -de → dʒy)
            base = 'i'
        if base == 'ə' and prev in ('ɾ', 'r', 'l') and nxt and not _is_vowel(nxt):
            continue                              # r・l と子音の間に espeak-ng が入れる ə (verdade → vˌeɾədˈadʒy)
        if base == 'ɨ':
            continue                              # ポルトガルの弱い e は書かない (noite → ノイト)
        if base == 'ɹ':
            p = 'r'
        if base == 'ɪ' and prev == 'e' and nxt in ('ŋ', 'm', 'n') and k + 2 < len(phs) and not _is_vowel(phs[k + 2]):
            continue                              # 子音の前の em・en の eɪŋ は鼻母音 [ẽ] (gente → ジェンチ。語末の bem → ベイン)
        if base == 'ʎ':
            out += ['l', 'j']                     # lh [ʎ] → リャ行 (filho → フィリョ)
            continue
        if base == 'w' and prev and not _is_vowel(prev) and prev not in ('k', 'ɡ', 'g') and _is_vowel(nxt):
            p = 'u'                               # 子音の後ろの w は母音 (muito → ムイント)。k・g の後ろは「クァ」のまま
        if _is_vowel(p) and _nasal(p):
            # 鼻母音: 後ろが鼻母音・鼻音の半母音なら「ン」は最後の1つ、鼻音の子音の前なら母音だけ、ほかは母音 + ン
            if nxt and (_is_vowel(nxt) and _nasal(nxt) or _base(nxt) in 'yjw' and (_nasal(nxt) or k + 2 >= len(phs))) or \
                    _base(nxt) in NASAL_CONSONANTS:
                out.append(_oral(p))
                continue
            out += [_oral(p), 'ŋ']
            continue
        out.append(p)
    # 鼻音の二重母音の最後の半母音 (mãe の y・coração の ʊ̃) の後ろに「ン」
    fixed = []
    for k, p in enumerate(out):
        fixed.append(p)
        if k > 0 and _base(out[k - 1]) in VOWEL_LETTERS and _base(p) in 'jiuʊ' and k + 1 == len(out) and \
                any(_nasal(x) for x in phs[-2:]) and 'ŋ' not in out[-2:]:
            fixed.append('ŋ')
    return fixed


# 1語だけで espeak-ng に渡すと文字の名前の読みになる機能語 (冠詞 o「オ」でなく弱い [u]、接続詞 e「エ」でなく [i])
UNSTRESSED = {'o': ['u'], 'e': ['i']}


def katakana(word, pt='br', long='phonemic', **options):
    """語 → カタカナ (pt: 'br' ブラジル / 'pt' ポルトガル)"""
    if not available():
        return word
    lower = word.lower()
    phs = UNSTRESSED[lower] if lower in UNSTRESSED else phonemes(word, pt if pt in VOICES else 'br')
    return kana(phs, long=long, **options)


def sentence(text, **options):
    from dragoman.core.kana import text_words
    return [katakana(w, **options) for w in text_words(text)]
