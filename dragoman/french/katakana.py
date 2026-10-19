#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語の語 (主に固有名詞) をカタカナで書く: espeak-ng のフランス語の発音 (IPA) を、どの言語にも共通の規則
# (core/kana.py) で
#
#   Emmanuel → エマニュエル、François → フランソワ、Juliette → ジュリエット、Pierre → ピエール、Hugues → ユグ
#
# 綴りの規則でなく発音から書くので、読まない字・鼻母音・語末の子音は espeak-ng に任せる:
#   - 鼻母音は「ン」(ɛ̃・œ̃ も今のフランス語の音 [æ̃] に近いのでアン: Vincent → ヴァンサン)。鼻母音は長くしない (Jean → ジャン)
#   - 子音 + w + a は「ソワ」(oi)、子音 + w + i は「ルイ」(ui)
#   - 音素としての長母音は無いので、長さは実際の発音の長さ (ˑ。既定は long='phonetic'): 強勢のある (最後の音節の) 母音のうち、
#     語末の o・ø・ɑ (Rousseau → ルソー) と、語末の r・z・ʒ・v の前 (Pierre → ピエール)、o・ø・ɑ の後ろの語末の子音の前
#     (Claude → クロード)
#   - 語末の [n]・[m] ははっきり発音されるので「ヌ」「ム」。綴りが -nne・-mme なら「ンヌ」「ンム」(Anne → アンヌ)、ほかは前の母音を
#     長く (Céline → セリーヌ、Antoine → アントワーヌ)
#   - 短い母音の後ろの語末の p・t・k は「ッ」(Juliette → ジュリエット)
# espeak-ng が無ければ綴りの規則 (core/katakana_names.latin(…, 'fr')) で
#
import functools
import shutil
import subprocess
import unicodedata

from dragoman.core.kana import kana, split_ipa, WORD_BREAK

LENGTHENING = ('ʁ', 'z', 'ʒ', 'v')   # 後ろに来ると強勢のある母音を長くする子音
LONG_VOWELS = ('o', 'ø', 'ɑ')       # 閉音節でも長い母音


def available():
    return shutil.which('espeak-ng') is not None


@functools.lru_cache(maxsize=20000)
def ipa(word):
    out = subprocess.run(['espeak-ng', '-v', 'fr', '-q', '--ipa', word], capture_output=True, text=True).stdout
    return out.strip()


def _is_vowel(p):
    return bool(p) and unicodedata.normalize('NFD', p)[0] in 'aɑæeɛəøœiɪoɔuʊyʏ'


def _nasal(p):
    return '̃' in unicodedata.normalize('NFD', p or '')


def phonemes(word):
    """IPA → 共通の規則の音素の列 (フランス語の読み替えと、実際の長さの印 ˑ)"""
    spellings = word.split()
    words = ipa(word).split()
    out = []
    for n, w in enumerate(words):
        spelling = spellings[n].lower() if len(spellings) == len(words) else ''
        phs = [p for p in split_ipa(w) if p not in ('ˈ', 'ˌ')]
        phs = [unicodedata.normalize('NFC', unicodedata.normalize('NFD', p).replace('ɛ̃', 'ã')
                                     .replace('œ̃', 'ã')) for p in phs]   # ɛ̃・œ̃ はアン
        fixed = []
        for k, p in enumerate(phs):   # 子音 + w + 母音: oi は「オワ」、ui は「ウイ」
            nxt = phs[k + 1] if k + 1 < len(phs) else ''
            prev = fixed[-1] if fixed else ''
            if p == 'w' and prev and not _is_vowel(prev) and _is_vowel(nxt):
                if nxt[:1] in ('a', 'ɑ'):
                    fixed += ['o', 'w']
                else:
                    fixed.append('u')
                continue
            fixed.append(p)
        out += _final_nasal(_lengthen(fixed), spelling)
        out.append(WORD_BREAK)
    return out[:-1]


def _lengthen(phs):
    """強勢のある (最後の音節の) 母音の実際の長さ (ˑ)"""
    vowels = [k for k, p in enumerate(phs) if _is_vowel(p)]
    if not vowels:
        return phs
    k = vowels[-1]
    if _nasal(phs[k]) or 'ː' in phs[k]:
        return phs
    rest = phs[k + 1:]
    base = unicodedata.normalize('NFD', phs[k])[0]
    if (not rest and base in LONG_VOWELS) or (len(rest) == 1 and (rest[0] in LENGTHENING or base in LONG_VOWELS)):
        return phs[:k] + [phs[k] + 'ˑ'] + phs[k + 1:]
    return phs


def _final_nasal(phs, spelling):
    """語末の [n]・[m] は「ヌ」「ム」(綴りが -nne・-mme なら「ンヌ」、ほかは前の母音を長く)"""
    if len(phs) < 2 or phs[-1] not in ('n', 'm') or not _is_vowel(phs[-2]) or _nasal(phs[-2]):
        return phs
    if spelling.endswith(('nne', 'mme', 'nnes', 'mmes')):
        return phs[:-1] + [phs[-1], phs[-1], 'u']
    vowel = phs[-2] if ('ˑ' in phs[-2] or 'ː' in phs[-2]) else phs[-2] + 'ˑ'
    return phs[:-2] + [vowel, phs[-1], 'u']


def katakana(word, long='phonetic', **options):
    if not available():
        from dragoman.core.katakana_names import latin
        return latin(word, 'fr')
    options.setdefault('final_sokuon', True)
    return kana(phonemes(word), long=long, **options)
