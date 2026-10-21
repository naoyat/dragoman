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
#     レ ザンファン)、il y a は1語「イリヤ」、il・elle + 母音で始まる語も1語 (il est → イレ、elle est → エレ)
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


ENCHAINEMENT = ('il', 'ɛl')   # 母音で始まる次の語と続けて1語に読む代名詞 (il est → イレ、elle est → エレ)


def _sentence_groups(text):
    """(語の音素の列, 頭に続けた語の音素の数) の列。文全体を espeak-ng に渡した発音を、語ごとの音素の列に (文の中の読み: y → i、m'aimes → mɛm)。
    リエゾンの子音 (le-z enfants の z、sont arrivés の t) は次の語の頭に、il y a は1語「イリヤ」に、
    il・elle + 母音で始まる語も1語に (il est → イレ、elle aime → エレム)"""
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
        elif len(w) > 1 and w[-1] in LIAISON and nxt and _is_vowel(nxt[0]) and \
                ((_is_vowel(w[-2]) and _nasal(w[-2])) or _silent(w[-1], spellings[k] if len(spellings) == len(words) else '')):
            # リエゾン (sont arrivés → ソン タリヴェ、avait une → …ヴェ テュヌ、ils ont → イル ゾン)。綴りでも読む語末の子音は
            # そのまま (Antoine et → アントワーヌ エ、petite amie → プティット アミ)
            words[k], words[k + 1] = w[:-1], [w[-1]] + nxt
    # il y a (il i a) → ilja「イリヤ」
    merged = []
    k = 0
    while k < len(words):
        if ''.join(words[k]) == 'il' and k + 2 < len(words) and ''.join(words[k + 1]) == 'i' and \
                words[k + 2] and _is_vowel(words[k + 2][0]):
            merged.append((['i', 'l', 'i', 'j'] + words[k + 2], 4))   # イ・リ・ヤ (「リャ」にしない)
            k += 3
            continue
        if ''.join(words[k]) in ENCHAINEMENT and k + 1 < len(words) and words[k + 1] and _is_vowel(words[k + 1][0]):
            merged.append((words[k] + words[k + 1], len(words[k])))   # il est → イレ、elle a → エラ
            k += 2
            continue
        merged.append((words[k], 0))
        k += 1
    return [(w, head) for w, head in merged if w]


def sentence_words(text):
    """文の発音を語ごとの音素の列に (_sentence_groups の語の列だけ)"""
    return [w for w, _ in _sentence_groups(text)]


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
    groups = _sentence_groups(text)
    out = []
    for n, (w, head) in enumerate(groups):
        fixed = []
        for k, p in enumerate(w):   # 子音 + w + 母音: oi は「オワ」、ui は「ウイ」
            p = _french_vowel(p)
            nxt = w[k + 1] if k + 1 < len(w) else ''
            prev = fixed[-1] if fixed else ''
            if p == 'w' and prev and not _is_vowel(prev) and _is_vowel(nxt):
                fixed += ['o', 'w'] if nxt[:1] in ('a', 'ɑ') else ['u']
                continue
            fixed.append(p)
        spelling = spellings[n].lower().strip('.,;:!?') if len(spellings) == len(groups) else ''
        # 長さと語末の n・m は続けた語の後ろの語だけで見る (elle aime → エレム)
        out.append(kana(fixed[:head] + _final_nasal(_lengthen(fixed[head:]), spelling.split()[-1] if spelling else ''),
                        long=long, **options))
    return out


def _merge_il_y(spellings):
    """綴りの語の列も il y a・il est・elle est を1語に (発音の語の列と数を揃えて、語末の -nne・-mme を綴りで見る)"""
    out = []
    k = 0
    while k < len(spellings):
        if spellings[k].lower() == 'il' and k + 2 < len(spellings) and spellings[k + 1].lower() == 'y':
            out.append(' '.join(spellings[k:k + 3]))
            k += 3
            continue
        if spellings[k].lower() in ('il', 'elle') and k + 1 < len(spellings) and \
                unicodedata.normalize('NFD', spellings[k + 1].lower())[:1] in tuple('aeiouyh'):
            out.append(' '.join(spellings[k:k + 2]))
            k += 2
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


def _word_ipa(words):
    """語の列 → 語ごとの IPA の音素の列 (文全体を espeak-ng に渡して空白で分ける。リエゾンの印 - の後ろは次の語の頭の
    子音として ('-', 子音) で残す)。語の数が合わなければ語ごとに"""
    import re
    raw = ipa(' '.join(words)).split()
    if len(raw) != len(words):
        raw = [ipa(w).replace(' ', '') for w in words]
    # espeak-ng が別の言語に切り替えた語 ((en)…(fr): d'aujourd'hui) はエリジオンを分けて引き直す
    raw = [_elided_ipa(w) if '(' in r else r for w, r in zip(words, raw)]
    out = []
    for w in raw:
        head, mark, tail = w.partition('-')
        phs = [p for p in split_ipa(head) if p not in ('ˈ', 'ˌ')]
        out.append((phs, split_ipa(tail) if mark and tail else []))
    return out


ELISION_SOUNDS = {"d'": 'd', "l'": 'l', "j'": 'ʒ', "m'": 'm', "t'": 't', "s'": 's', "n'": 'n', "c'": 's', "qu'": 'k'}


def _elided_ipa(word):
    """エリジオンの付いた語の IPA (d'aujourd'hui → d + aujourd'hui の IPA)"""
    import re
    lower = word.lower().replace('’', "'")
    for prefix, sound in ELISION_SOUNDS.items():
        if lower.startswith(prefix) and len(lower) > len(prefix):
            return sound + re.sub(r'\([a-z-]+\)', '', ipa(word[len(prefix):])).replace(' ', '')
    return re.sub(r'\([a-z-]+\)', '', ipa(word)).replace(' ', '')


def ruby_words(words, liaison='next', long='phonetic', **options):
    """ルビ用: 語の列 (句読点を除いた綴り) → (語ごとのカタカナ, 語の間で音がつながったか)。
    リエゾン・アンシェヌマンの子音は liaison='next' なら次の語に (les enfants → レ / ザンファン、il est → イ / レ、
    il y a → イ / リ / ヤ)、'prev' なら前の語に残す (レズ / アンファン)"""
    if not available():
        from dragoman.core.katakana_names import latin
        return [latin(w, 'fr') for w in words], [False] * max(0, len(words) - 1)
    options.setdefault('final_sokuon', True)
    spellings = [w.lower() for w in words]
    pairs = _word_ipa(words)
    phs = [list(p) for p, _ in pairs]
    links = [False] * max(0, len(words) - 1)
    kept = [[] for _ in words]
    for k in range(len(words) - 1):
        marked = pairs[k][1]
        nxt = phs[k + 1]
        moved = []
        if marked:   # 印の付いたリエゾン (le-z enfants)
            moved = marked
        elif len(phs[k]) > 1 and phs[k][-1] in LIAISON and nxt and _is_vowel(nxt[0]) and \
                ((_is_vowel(phs[k][-2]) and _nasal(phs[k][-2])) or _silent(phs[k][-1], spellings[k])):
            moved = [phs[k].pop()]   # リエゾン (sont arrivés)
        elif ''.join(phs[k]) in ENCHAINEMENT and nxt and _is_vowel(nxt[0]):
            moved = [phs[k].pop()]   # アンシェヌマン (il est → イ / レ)
        if ''.join(phs[k] + moved) in ('i', 'li') and spellings[k] == 'y' and nxt and _is_vowel(nxt[0]):
            phs[k + 1] = ['j'] + nxt   # il y a の y + a は「ヤ」(イ / リ / ヤ)
            links[k] = True
        if not moved:
            continue
        links[k] = True
        if liaison == 'prev':
            kept[k] = moved   # 前の語に残す子音 (語の読みを作ってから語末に足す: レズ / アンファン)
        else:
            phs[k + 1] = moved + phs[k + 1]
    out = []
    for w, spelling, extra in zip(phs, spellings, kept):
        fixed = []
        for k, p in enumerate(w):   # 子音 + w + 母音: oi は「オワ」、ui は「ウイ」
            p = _french_vowel(p)
            nxt = w[k + 1] if k + 1 < len(w) else ''
            prev = fixed[-1] if fixed else ''
            if p == 'w' and prev and not _is_vowel(prev) and _is_vowel(nxt):
                fixed += ['o', 'w'] if nxt[:1] in ('a', 'ɑ') else ['u']
                continue
            fixed.append(p)
        text = kana(_final_nasal(_lengthen(fixed), spelling.strip(".,;:!?")), long=long, **options) if fixed else ''
        if extra and not (extra == ['n'] and text.endswith('ン')):   # 鼻母音の後ろの n は「ン」に含まれる (un ami)
            from dragoman.core.kana import CODA, CONSONANTS
            text += ''.join(CODA.get(CONSONANTS.get(p, p), '') for p in extra)
        out.append(text)
    return out, links
