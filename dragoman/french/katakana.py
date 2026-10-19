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
#   - あいまい母音 ə はウ段 (le → ル、je → ジュ、que → ク、de → ドゥ)
#   - 文は文全体を espeak-ng に渡して語ごとに (sentence。y → i、m'aimes → mɛm)。リエゾンの子音は次の語の頭に (Les enfants →
#     レ ザンファン)、il y a は1語「イリヤ」
#   - 子音 + w + a は「ソワ」(oi)、子音 + w + i は「ルイ」(ui)
#   - 音素としての長母音は無いので、長さは実際の発音の長さ (ˑ。既定は long='phonetic'): 強勢のある (最後の音節の) 母音のうち、
#     語末の o・ø・ɑ (Rousseau → ルソー) と、語末の r・z・ʒ・v の前 (Pierre → ピエール)、o・ø・ɑ の後ろの語末の子音の前
#     (Claude → クロード)
#   - 語末の [n]・[m] ははっきり発音されるので「ヌ」「ム」。綴りが -nne なら「ンヌ」(Anne → アンヌ)、ほかは2音節以上なら前の母音を
#     長く (Céline → セリーヌ、Antoine → アントワーヌ。une → ユヌ、femme → ファム)
#   - 短い母音の後ろの語末の p・t・k は「ッ」(Juliette → ジュリエット)
# espeak-ng が無ければ綴りの規則 (core/katakana_names.latin(…, 'fr')) で
#
import functools
import shutil
import subprocess
import unicodedata

from dragoman.core.kana import kana, split_ipa, WORD_BREAK

LENGTHENING = ('ʁ', 'z', 'ʒ', 'v')   # 後ろに来ると強勢のある母音を長くする子音
LIAISON = ('z', 't', 'n', 'p', 'ʁ')    # リエゾンの子音 (次の母音で始まる語の頭に移す)
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
        phs = [_french_vowel(p) for p in phs]
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


def _french_vowel(p):
    """フランス語の母音の書き方: ɛ̃・œ̃ はアン (ヴァンサン)、あいまい母音 ə はウ段 (le → ル、je → ジュ、de → ドゥ)"""
    p = unicodedata.normalize('NFD', p).replace('ɛ\u0303', 'a\u0303').replace('œ\u0303', 'a\u0303')
    if p.startswith('ə'):
        p = 'ɯ' + p[1:]
    return unicodedata.normalize('NFC', p)


SILENT_ENDINGS = {'z': ('s', 'x', 'z'), 't': ('t', 'd'), 'p': ('p',)}   # リエゾンで読む、ふだんは読まない語末の字


def sentence_words(text):
    """文全体を espeak-ng に渡した発音を、語ごとの音素の列に (文の中の読み: y → i、m'aimes → mɛm)。
    リエゾンの子音 (le-z enfants の z、sont arrivés の t) は次の語の頭に、il y a は1語「イリヤ」に"""
    spellings = [w.lower().strip('.,;:!?') for w in text.split() if any(c.isalpha() for c in w)]
    words = [split_ipa(w) for w in ipa(text).split()]
    words = [[p for p in w if p not in ('ˈ', 'ˌ')] for w in words]
    # リエゾンの印 (-): le-z → le と z (z は次の語の頭に)
    out = []
    for w in words:
        joined = ''.join(w)
        if '-' in joined:
            head, _, tail = joined.partition('-')
            out.append(split_ipa(head) + (['-' + tail] if tail else []))
        else:
            out.append(w)
    words = out
    for k in range(len(words) - 1):
        w, nxt = words[k], words[k + 1]
        if w and w[-1].startswith('-'):   # 印の付いたリエゾン
            consonant = w[-1][1:]
            words[k] = w[:-1]
            if consonant:
                words[k + 1] = split_ipa(consonant) + nxt
        elif len(w) > 1 and w[-1] in LIAISON and _is_vowel(w[-2]) and nxt and _is_vowel(nxt[0]) and \
                (_nasal(w[-2]) or _silent(w[-1], spellings[k] if len(spellings) == len(words) else '')):
            # リエゾン (sont arrivés → ソン タリヴェ、avait une → …ヴェ テュヌ)。綴りでも読む語末の子音はそのまま
            # (Antoine et → アントワーヌ エ、petite amie → プティット アミ)
            words[k], words[k + 1] = w[:-1], [w[-1]] + nxt
    # il y a (il i a) → ilja「イリヤ」
    merged = []
    k = 0
    while k < len(words):
        if ''.join(words[k]) == 'il' and k + 2 < len(words) and ''.join(words[k + 1]) == 'i' and \
                words[k + 2] and _is_vowel(words[k + 2][0]):
            merged.append(['i', 'l', 'i', 'j'] + words[k + 2])   # イ・リ・ヤ (「リャ」にしない)
            k += 3
            continue
        merged.append(words[k])
        k += 1
    return [w for w in merged if w]


def _silent(consonant, spelling):
    """綴りの語末の字がふだんは読まない字か (avait の t、les の s)"""
    return spelling.endswith(SILENT_ENDINGS.get(consonant, ()))


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
    """語末の [n]・[m] は「ヌ」「ム」(綴りが -nne なら「ンヌ」、ほかは2音節以上なら前の母音を長く: une → ユヌ、femme → ファム)"""
    if len(phs) < 2 or phs[-1] not in ('n', 'm') or not _is_vowel(phs[-2]) or _nasal(phs[-2]):
        return phs
    if spelling.endswith(('nne', 'nnes')):
        return phs[:-1] + [phs[-1], phs[-1], 'u']
    if sum(1 for p in phs if _is_vowel(p)) < 2:
        return phs + ['u']
    vowel = phs[-2] if ('ˑ' in phs[-2] or 'ː' in phs[-2]) else phs[-2] + 'ˑ'
    return phs[:-2] + [vowel, phs[-1], 'u']


def sentence(text, long='phonetic', **options):
    """文のカタカナ読み (語ごとの列): 文全体の発音から (Il y a un chat → イリヤ アン シャ)"""
    if not available():
        from dragoman.core.katakana_names import latin
        return [latin(w, 'fr') for w in text.split()]
    options.setdefault('final_sokuon', True)
    spellings = _merge_il_y([w for w in text.split() if any(c.isalpha() for c in w)])
    words = sentence_words(text)
    out = []
    for n, w in enumerate(words):
        fixed = []
        for k, p in enumerate(w):   # 子音 + w + 母音: oi は「オワ」、ui は「ウイ」
            p = _french_vowel(p)
            nxt = w[k + 1] if k + 1 < len(w) else ''
            prev = fixed[-1] if fixed else ''
            if p == 'w' and prev and not _is_vowel(prev) and _is_vowel(nxt):
                fixed += ['o', 'w'] if nxt[:1] in ('a', 'ɑ') else ['u']
                continue
            fixed.append(p)
        spelling = spellings[n].lower().strip('.,;:!?') if len(spellings) == len(words) else ''
        out.append(kana(_final_nasal(_lengthen(fixed), spelling), long=long, **options))
    return out


def _merge_il_y(spellings):
    """綴りの語の列も il y a を1語に (発音の語の列と数を揃えて、語末の -nne・-mme を綴りで見る)"""
    out = []
    k = 0
    while k < len(spellings):
        if spellings[k].lower() == 'il' and k + 2 < len(spellings) and spellings[k + 1].lower() == 'y':
            out.append(' '.join(spellings[k:k + 3]))
            k += 3
            continue
        out.append(spellings[k])
        k += 1
    return out


def katakana(word, long='phonetic', **options):
    if not available():
        from dragoman.core.katakana_names import latin
        return latin(word, 'fr')
    options.setdefault('final_sokuon', True)
    return kana(phonemes(word), long=long, **options)
