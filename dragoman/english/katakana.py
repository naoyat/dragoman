#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語の語をカタカナで書く: 発音辞書 CMUdict (米音。ARPABET と強勢) の発音を、どの言語にも共通の規則 (core/kana.py) で
#
#   about → アバウト、water → ウォーター、car → カー、think → スィンク、music → ミューズィック、nation → ネイション
#
# 辞書に無い語と英音 (accent='gb') は espeak-ng の IPA (en-us・en-gb) を ARPABET に読み替えて同じ規則に。発音に忠実に:
#   - 強勢の無いあいまい母音 [ə] は綴りに近い母音 (about → アバウト、lemon → レモン、nation → ネイション。-le は「ル」: table → テイブル)
#   - 二重母音は2つの母音 (make → メイク、go → ゴウ)、[iː]・[uː]・[ɔː] は長く (see → スィー、law → ロー)
#   - 母音の後ろの r は長音に寄せる: ɑr・ɝ・ɚ は「アー」(car → カー、bird → バード、water → ウォーター)、ほかの母音の後ろは
#     「ア」(here → ヒア、care → ケア、more → モア。子音の前の ɔr は「オー」: horse → ホース)。母音の前の r はラ行
#   - k・g + [æ] は「キャ」「ギャ」(cat → キャット)
#   - 強勢のある短い母音の後ろの p・t・k・tʃ・dʒ・ʃ・b・d・g は「ッ」(語末: cat → キャット、bridge → ブリッジ、big → ビッグ。
#     語中の p・t・k + 母音: happy → ハッピー)
#   - 強勢の無い -er・-or・-ar は「アー」(英音: doctor → ドクター)、-ful は「フル」、the・a は「ザ」「ア」
#   - 語末の [ŋ] は「ング」(sing → スィング)、語末の強勢の無い [i] は長く (happy → ハッピー)
#
import functools
import os
import re
import shutil
import subprocess

from dragoman.core import paths
from dragoman.core.kana import kana, split_ipa, text_words

CMUDICT = paths.data('en/cmudict.dict')
VOWELS = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW', 'OH'}
CONSONANTS = {'B': 'b', 'CH': 'tʃ', 'D': 'd', 'DH': 'ð', 'F': 'f', 'G': 'g', 'HH': 'h', 'JH': 'dʒ', 'K': 'k', 'L': 'l',
              'M': 'm', 'N': 'n', 'NG': 'ŋ', 'P': 'p', 'R': 'r', 'S': 's', 'SH': 'ʃ', 'T': 't', 'TH': 'θ', 'V': 'v',
              'W': 'w', 'Y': 'j', 'Z': 'z', 'ZH': 'ʒ'}
SHORT = {'AE', 'AH', 'EH', 'IH', 'UH', 'AA', 'OH'}      # 後ろの子音を「ッ」にする短い母音 (強勢のあるもの)
FINAL_GEMINATE = {'P', 'T', 'K', 'CH', 'JH', 'SH', 'B', 'D', 'G'}
MEDIAL_GEMINATE = {'P', 'T', 'K', 'CH', 'SH'}
SCHWA_LETTERS = {'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'a', 'y': 'i'}
# espeak-ng の IPA → ARPABET (長いものから)
IPA_ARPABET = [('eɪ', 'EY'), ('aɪ', 'AY'), ('aʊ', 'AW'), ('ɔɪ', 'OY'), ('oʊ', 'OW'), ('əʊ', 'OW'), ('ɪə', 'IY R'), ('iə', 'IY R'),
               ('eə', 'EH R'), ('ʊə', 'UH R'), ('iː', 'IY'), ('uː', 'UW'), ('ɑː', 'AA'), ('ɔː', 'AO'), ('ɜː', 'ER'),
               ('tʃ', 'CH'), ('dʒ', 'JH'), ('n̩', 'AH N'), ('l̩', 'AH L'),
               ('i', 'IY'), ('ɪ', 'IH'), ('ᵻ', 'IH'), ('ɛ', 'EH'), ('e', 'EH'), ('æ', 'AE'), ('a', 'AE'), ('ɑ', 'AA'),
               ('ɒ', 'OH'), ('ɔ', 'AO'), ('o', 'OW'), ('ʊ', 'UH'), ('u', 'UW'), ('ʌ', 'AH'), ('ə', 'AH'), ('ɐ', 'AH'),
               ('ɚ', 'ER'), ('ɝ', 'ER'), ('ɹ', 'R'), ('r', 'R'), ('ɾ', 'T'), ('ʔ', 'T'), ('ʃ', 'SH'), ('ʒ', 'ZH'),
               ('θ', 'TH'), ('ð', 'DH'), ('ŋ', 'NG'), ('j', 'Y'), ('w', 'W'), ('h', 'HH'), ('ɡ', 'G'), ('ɫ', 'L')]


@functools.lru_cache(maxsize=1)
def _cmudict():
    table = {}
    if not os.path.exists(CMUDICT):
        return table
    with open(CMUDICT, encoding='utf-8') as f:
        for line in f:
            parts = line.split('#')[0].split()
            if len(parts) < 2 or '(' in parts[0]:   # word(2) などの別の発音は _variants で
                continue
            table.setdefault(parts[0], parts[1:])
    return table


@functools.lru_cache(maxsize=1)
def _variants():
    """同じ綴りの別の発音 (CMUdict の word(2)): 語 → [発音1, 発音2, …]。同綴り異音語の表 (HOMOGRAPHS) の語だけ"""
    table = {}
    if not os.path.exists(CMUDICT):
        return table
    with open(CMUDICT, encoding='utf-8') as f:
        for line in f:
            parts = line.split('#')[0].split()
            if len(parts) < 2:
                continue
            word = parts[0].split('(')[0]
            if word in HOMOGRAPHS:
                table.setdefault(word, []).append(parts[1:])
    return table


# 品詞で発音の変わる語 (同綴り異音語): 語 → {品詞: CMUdict の何番目の発音 (0 から)}。品詞は spaCy の Penn の印から
# VERB (原形・現在形・-ing)・PAST (過去形・過去分詞)・NOUN・ADJ・ADV。表に無い品詞は最初の発音
HOMOGRAPHS = {
    'read': {'VERB': 1, 'NOUN': 1, 'PAST': 0}, 'live': {'VERB': 1, 'ADJ': 0, 'ADV': 0},
    'lives': {'VERB': 0, 'NOUN': 1}, 'lead': {'VERB': 1, 'NOUN': 1, 'PAST': 1}, 'close': {'VERB': 1, 'ADJ': 0, 'ADV': 0},
    'use': {'NOUN': 0, 'VERB': 1}, 'record': {'VERB': 0, 'NOUN': 1, 'ADJ': 1}, 'present': {'NOUN': 0, 'ADJ': 0, 'VERB': 1},
    'object': {'NOUN': 0, 'VERB': 1}, 'project': {'NOUN': 0, 'VERB': 1}, 'subject': {'NOUN': 1, 'ADJ': 1, 'VERB': 0},
    'content': {'NOUN': 0, 'ADJ': 1}, 'contract': {'NOUN': 0, 'VERB': 1}, 'conduct': {'NOUN': 0, 'VERB': 1},
    'desert': {'NOUN': 0, 'VERB': 1}, 'excuse': {'NOUN': 0, 'VERB': 1}, 'minute': {'NOUN': 0, 'ADJ': 1},
    'permit': {'VERB': 0, 'NOUN': 1}, 'produce': {'VERB': 0, 'NOUN': 1}, 'refuse': {'VERB': 0, 'NOUN': 1},
    'tear': {'VERB': 0, 'NOUN': 1}, 'wind': {'NOUN': 1, 'VERB': 0}, 'wound': {'PAST': 0, 'NOUN': 1, 'VERB': 1},
    'increase': {'VERB': 0, 'NOUN': 1}, 'decrease': {'VERB': 0, 'NOUN': 1},
}
# 口語の綴り (歌詞などに出るもの): CMUdict に無いか、CMUdict の発音が誤っているもの
COLLOQUIAL = {'tryna': 'T R AY1 N AH0', 'outta': 'AW1 T AH0', 'imma': 'AY1 M AH0', "i'ma": 'AY1 M AH0',
              'finna': 'F IH1 N AH0', 'whatcha': 'W AH1 CH AH0'}
PENN = {'VB': 'VERB', 'VBP': 'VERB', 'VBZ': 'VERB', 'VBG': 'VERB', 'VBD': 'PAST', 'VBN': 'PAST', 'NN': 'NOUN',
        'NNS': 'NOUN', 'NNP': 'NOUN', 'JJ': 'ADJ', 'JJR': 'ADJ', 'JJS': 'ADJ', 'RB': 'ADV'}


def available():
    return os.path.exists(CMUDICT) or shutil.which('espeak-ng') is not None


@functools.lru_cache(maxsize=20000)
def _espeak(word, accent):
    if shutil.which('espeak-ng') is None:
        return ''
    voice = 'en-gb' if accent == 'gb' else 'en-us'
    return subprocess.run(['espeak-ng', '-v', voice, '-q', '--ipa', word], capture_output=True, text=True).stdout.strip()


def _from_ipa(ipa):
    """espeak-ng の IPA → ARPABET (強勢 ˈ・ˌ は次の母音に 1・2、ほかの母音は 0)"""
    text = ipa.replace(' ', '')
    out = []
    stress = '0'
    k = 0
    while k < len(text):
        if text[k] in 'ˈˌ':
            stress = '1' if text[k] == 'ˈ' else '2'
            k += 1
            continue
        if text[k] in 'ː.-':
            k += 1
            continue
        for ipa_, arpa in IPA_ARPABET:
            if text.startswith(ipa_, k):
                for a in arpa.split():
                    if a in VOWELS:
                        out.append(a + stress)
                        stress = '0'
                    else:
                        out.append(a)
                k += len(ipa_)
                break
        else:
            ch = text[k].upper()
            if ch in CONSONANTS:
                out.append(ch)
            k += 1
    return out


def arpabet(word, accent='us', tag=None):
    """語 → ARPABET の列 (米音は CMUdict、無ければ espeak-ng。英音は espeak-ng)。tag (Penn の品詞の印) があれば
    同綴り異音語の発音を選ぶ (read: VBD → R EH1 D、VBP → R IY1 D)"""
    key = word.lower().strip("'").replace('’', "'")
    if key in COLLOQUIAL:
        return COLLOQUIAL[key].split()
    if accent != 'gb' and tag and key in HOMOGRAPHS:
        variants = _variants().get(key, [])
        n = HOMOGRAPHS[key].get(PENN.get(tag, ''), 0)
        if n < len(variants):
            return list(variants[n])
    if accent != 'gb':
        if key.endswith('in') and word.endswith(("'", '’')):
            # g を落とした -in' は -ing の発音の ŋ を n に (lovin' → ラヴィン。CMUdict の名前の Lovin より先に)
            full = _cmudict().get(key + 'g')
            if full and full[-1] == 'NG':
                return list(full[:-1]) + ['N']
        entry = _cmudict().get(key)
        if entry:
            return list(entry)
    return _from_ipa(_espeak(word, accent))


def _schwa_vowels(word, arpa):
    """強勢の無い AH (あいまい母音) ごとに綴りの母音字 (数が合わなければ a)"""
    spelling = word.lower()
    groups = [(m.group(), m.start()) for m in re.finditer(r'[aeiouy]+', spelling) if not (m.start() == 0 and m.group() == 'y')]
    vowels = [p for p in arpa if p[:-1] in VOWELS or p in VOWELS]
    if len(groups) == len(vowels) + 1 and spelling.endswith('e') and groups[-1][0] == 'e':
        groups = groups[:-1]                      # 読まない語末の e (make)
    while len(groups) > len(vowels):
        silent = [k for k, (g, s) in enumerate(groups) if g == 'e' and k > 0]
        if not silent:
            break
        del groups[silent[0]]                     # 語中の読まない e (careful → care + ful)
    if len(groups) != len(vowels):
        return {}
    out = {}
    n = 0
    for k, p in enumerate(arpa):
        if p[:-1] in VOWELS:
            group, start = groups[n]
            if p == 'AH0':
                end = start + len(group)
                follow = spelling[end:end + 2]
                if spelling in ('the', 'a', 'an'):
                    out[k] = 'a'                  # the → ザ、a → ア
                elif re.search(r'[^aeiou]le$', spelling) and n == len(groups) - 1:
                    out[k] = ''                   # -le は母音を書かない (table → テイブル、little → リトル)
                elif follow[:1] == 'r' and (len(follow) < 2 or follow[1] not in 'aeiouy'):
                    out[k] = 'aː'                 # 英音の -er・-or・-ar (water → ウォーター)
                elif group == 'e' and end == len(spelling) and spelling[start - 1:start] == 'r':
                    out[k] = 'a'                  # 英音の -re (fire → ファイア、here → ヒア)
                elif group[-1] == 'u' and follow[:1] == 'l':
                    out[k] = 'u'                  # -ful は「フル」(beautiful → ビューティフル)
                else:
                    out[k] = SCHWA_LETTERS.get(group[-1], 'a')
            n += 1
    return out


def phonemes(word, accent='us', tag=None):
    """語 → 共通の規則の音素の列"""
    arpa = arpabet(word, accent, tag)
    if word.lower().replace('’', "'").endswith("n't") and arpa[-3:] == ['AH0', 'N', 'T']:
        arpa = arpa[:-3] + ['N', 'T']   # -n't の n は音節になる (wasn't [wʌzn̩t] → ワズント、weren't → ワーント)
    schwas = _schwa_vowels(word, arpa)
    out = []
    n = len(arpa)
    skip = False
    for k, p in enumerate(arpa):
        if skip:
            skip = False
            continue
        base, stress = (p[:-1], p[-1]) if p[-1:].isdigit() else (p, '')
        nxt = arpa[k + 1] if k + 1 < n else ''
        nxt_base = nxt[:-1] if nxt[-1:].isdigit() else nxt
        after = arpa[k + 2] if k + 2 < n else ''
        prev = arpa[k - 1] if k else ''
        if base in VOWELS:
            r_coda = nxt_base == 'R' and not (after[:-1] in VOWELS)
            if base == 'AA':
                out.append('aː' if r_coda or (not nxt and stress == '1') else 'a')
            elif base == 'OH':
                out.append('o')
            elif base == 'AE':
                if out and out[-1] in ('k', 'g'):
                    out.append('j')               # cat → キャット
                out.append('a')
            elif base == 'AH':
                vowel = schwas.get(k, 'a') if stress == '0' else 'a'
                if vowel:
                    out.append(vowel)
            elif base == 'ER' and nxt_base in VOWELS:
                out += ['a', 'r']                 # r の後ろに母音: every → エヴァリー、different → ディファレント
            elif base == 'ER':
                out.append('a' if prev[:-1] in VOWELS and stress == '0' else 'aː')   # fire → ファイア
            elif base == 'AO':
                out.append('o' if r_coda and not after or nxt_base == 'NG' else 'oː')   # song → ソング
            elif base == 'IY':
                out.append('i' if r_coda or (stress == '0' and nxt) else 'iː')
            elif base == 'UW':
                out.append('u' if r_coda else 'uː' if stress != '0' or not nxt else 'u')
            elif base == 'EY':
                out += ['e', 'i'] if not r_coda else ['e']
            elif base == 'OW':
                out += ['o', 'u'] if not r_coda else ['o']
            elif base == 'AY':
                out += ['a', 'i']
            elif base == 'AW':
                out += ['a', 'u']
            elif base == 'OY':
                out += ['o', 'i']
            elif base == 'EH':
                out.append('e')
            elif base == 'IH':
                out.append('i')
            elif base == 'UH':
                out.append('u')
            if r_coda:                            # 母音の後ろの r: 長音か「ア」
                if base not in ('AA', 'ER') and not (base == 'AO' and after):
                    out.append('a')
            continue
        if base == 'R':
            prev_base = prev[:-1] if prev[-1:].isdigit() else prev
            if prev_base in VOWELS and not (nxt_base in VOWELS):
                continue                          # 母音の後ろの r は書かない (長音・「ア」にした)
            if prev_base == 'ER':
                continue
            out.append('r')
            continue
        ph = CONSONANTS.get(base)
        if ph is None:
            continue
        if base in ('T', 'D') and nxt_base in ('S', 'Z') and k + 2 == n:
            ph = 'ts' if base == 'T' else 'dz'   # 語末の -ts・-ds は「ツ」「ズ」(cats → キャッツ、sits → スィッツ)
            skip = True
        prev_base, prev_stress = (prev[:-1], prev[-1]) if prev[-1:].isdigit() else (prev, '')
        short_before = prev_base in SHORT and prev_stress == '1'
        final = not nxt or nxt_base in ('S', 'Z') and k + 2 == n   # 語末 (複数・3単現の -s の前も: books → ブックス)
        if (short_before and ((final and base in FINAL_GEMINATE) or (nxt_base in VOWELS and base in MEDIAL_GEMINATE))) or \
                (prev_base in ('IH', 'EH', 'AH') and not nxt and base in ('P', 'T', 'K', 'SH', 'CH', 'JH')):
            # 「ッ」(cat → キャット、happy → ハッピー。強勢の無い ɪ・ɛ + 語末の p・t・k も: music → ミューズィック)
            out.append(ph)                        # 「ッ」(cat → キャット、happy → ハッピー)
        out.append(ph)
        if base == 'NG' and not (nxt_base in VOWELS) and nxt_base not in ('K', 'G'):
            out.append('g')                       # 語末の ŋ は「ング」
    # 語末の強勢の無い [i] は長く (happy → ハッピー)
    if arpa and arpa[-1] == 'IY0' and out and out[-1] == 'i':
        out[-1] = 'iː'
    return out


def katakana(word, accent='us', long='phonemic', tag=None, **options):
    return kana(phonemes(word, accent, tag), long=long, **options)


def tags(words):
    """同綴り異音語のある語の列だけ spaCy で品詞を付ける (必要なときだけ解析: 無ければ [None, …])"""
    if not any(w.lower().strip("'") in HOMOGRAPHS for w in words):
        return [None] * len(words)
    try:
        from .morphology import parse
        return [t.tag_ for t in parse(words)]
    except Exception:   # spaCy の英語モデルが無い
        return [None] * len(words)


def ruby_words(words, liaison='next', **options):
    """ルビ用: 語の列 → (語ごとのカタカナ, つながり)。品詞で発音の変わる語があれば文の品詞を付けて (I read → リード、
    I have read → レッド、Where do you live? → リヴ)"""
    return [katakana(w, tag=t, **options) for w, t in zip(words, tags(words))], [False] * max(0, len(words) - 1)


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列)"""
    return ruby_words(text_words(text), **options)[0]
