#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語の語をカタカナで書く: espeak-ng のドイツ語の発音 (IPA) を、どの言語にも共通の規則 (core/kana.py) で
#
#   Heinrich → ハインリヒ、Müller → ミュラー、Mozart → モーツァルト、Bach → バッハ、Zürich → ツューリヒ
#
# 音素としての長さがあるので、既定は long='phonemic' (ː だけ「ー」)。日本語の耳に合わせる所だけ手を入れる:
#   - 語末などの -er の [ɐ] は「アー」(Müller → ミュラー、Schubert → シューバート)。母音の後ろの [ɐ] (母音になった r) は「ル」
#     (Hamburg → ハンブルク)
#   - 二重母音 eu・äu [ɔø] は「オイ」(Freud → フロイト)
#   - 母音の続かない ç は「ヒ」(Heinrich → ハインリヒ)、x は前の母音の段 (Bach → バッハ、Koch → コッホ、Buch → ブーフ)
#   - 短い母音の後ろの閉鎖音・摩擦音 + 母音は「ッ」(Mutter → ムッター、Wasser → ヴァッサー)。語末の閉鎖音も (mit → ミット)
#   - 語末の [ŋ] は「ング」(Wolfgang → ヴォルフガング)、pf は「プフ」、tsch は「チュ」(Deutschland → ドイチュラント)
# espeak-ng が無ければ綴りの規則 (core/katakana_names.latin(…, 'de')) で
#
import functools
import shutil
import subprocess
import unicodedata

from dragoman.core.kana import kana, split_ipa

SHORT_VOWELS = ('a', 'ɛ', 'ɪ', 'ɔ', 'ʊ', 'ʏ', 'œ')   # 後ろの子音を「ッ」にする短い母音 (ə は除く)
GEMINATING = ('p', 't', 'k', 'f', 's', 'ʃ', 'ts', 'tʃ')
X_VOWELS = {'a': 'a', 'ɑ': 'a', 'o': 'o', 'ɔ': 'o', 'u': 'u', 'ʊ': 'u'}


def available():
    return shutil.which('espeak-ng') is not None


@functools.lru_cache(maxsize=20000)
def ipa(word):
    out = subprocess.run(['espeak-ng', '-v', 'de', '-q', '--ipa', word], capture_output=True, text=True).stdout
    return out.strip()


def _base(p):
    return unicodedata.normalize('NFD', p or '')[:1]


def _is_vowel(p):
    return bool(p) and _base(p) in 'aɑɐɜeɛəøœiɪoɔuʊyʏ'


def phonemes(word):
    """IPA → 共通の規則の音素の列 (ドイツ語の読み替え)"""
    phs = [p for p in split_ipa(ipa(word)) if p not in ('ˈ', 'ˌ', ' ')]
    out = []
    for k, p in enumerate(phs):
        prev = out[-1] if out else ''
        nxt = phs[k + 1] if k + 1 < len(phs) else ''
        if p.startswith('ɜ'):
            out.append('aː')                    # -er の [ɐ] (espeak-ng の ɜ) は「アー」
        elif p.startswith('ɐ'):
            out.append('r' if _is_vowel(prev) else 'aː')   # 母音の後ろは r (Hamburg)、ほかは -er と同じ
        elif p.startswith('ø') and prev.startswith('ɔ'):
            out.append('i')                     # ɔø (eu・äu) → オイ
        elif p == 'ts' and nxt == 'ʃ':
            out.append('tʃ')                    # tsch [tʃ] (espeak-ng の ts ʃ: Nietzsche → ニーチェ)
        elif p == 'ʃ' and k and phs[k - 1] == 'ts':
            if not _is_vowel(nxt):
                out.append('ʊ')                 # 母音の続かない tsch は「チュ」(Deutschland → ドイチュラント)
            continue
        elif p == 'tʃ' and not _is_vowel(nxt):
            out += ['tʃ', 'ʊ']                  # 母音の続かない tsch は「チュ」
        elif p == 'pf':
            out += ['p', 'f']
        elif p == 'ç' and not _is_vowel(nxt):
            out += ['ç', 'i']                   # 音節末の ç は「ヒ」
        elif p == 'x' and not _is_vowel(nxt) and _base(prev) in X_VOWELS:
            if 'ː' not in prev:
                out.append('x')                 # 短い母音の後ろは「ッ」(Bach → バッハ)
            out += ['x', X_VOWELS[_base(prev)]]
        elif p == 'ŋ' and not _is_vowel(nxt) and nxt not in ('k', 'ɡ', 'g'):
            out += ['ŋ', 'ɡ']                   # 語末の ŋ は「ング」
        elif p in GEMINATING and _base(prev) in SHORT_VOWELS and 'ː' not in prev and _is_vowel(nxt) and \
                not nxt.startswith('ɐ'):
            out += [p, p]                       # 短い母音の後ろの子音 + 母音は「ッ」(Mutter → ムッター)
        else:
            out.append(p)
    return out


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列)。ドイツ語は語をまたいだ音の変化が少ないので語ごとに"""
    words = [w.strip('.,;:!?()«»„“”"\'') for w in text.split()]
    return [katakana(w, **options) for w in words if any(c.isalpha() for c in w)]


def katakana(word, long='phonemic', **options):
    if not available():
        from dragoman.core.katakana_names import latin
        return latin(word, 'de')
    options.setdefault('final_sokuon', True)
    return kana(phonemes(word), long=long, **options)
