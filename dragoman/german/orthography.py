#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古い綴り (19世紀・1901年の正書法統一より前、1996年の改革より前) を今の綴りに直す。グリム童話 (1857年版) などを読むため
#
#   roth → rot、Thür → Tür、Athem → Atem (th → t)      todt → tot、tödten → töten (dt → t)
#   gieng → ging、fieng → fing (ie → i)                   erschrack → erschrak (ck → k)
#   daß → dass、wußte → wusste (短い母音の後ろの ß → ss)   Waare → Ware (aa → a)、seyn → sein (ey → ei)
#   hätt → hätte、wär → wäre、wills → will es (語末の e の脱落・es の縮約)
#
# 規則は辞書 (語形の表・見出し) に無い語にだけ当て、直した形が辞書にあるときだけ採る (Theater・Thron はそのまま)。
# 縮小形 (-lein・-chen) は元の名詞を探す (Spieglein → Spiegel、Töchterlein → Tochter、Stühlchen → Stuhl)
#
import functools
import itertools
import re

from . import dictionary

# 直す規則 (古い綴り, 今の綴り)。組み合わせても試す (übermüthig → übermütig は th → t だけ)。
# 強い規則 (th・dt・aa・ey) は今の綴りに出ない並びなので、辞書に形がある語にも当てる (roth の項目は地名 Roth・
# 変化表の異綴り)。弱い規則 (ie・ck・ß・c) は今の綴りにもある並び (die・rief・saß・großen) なので、辞書に無い語にだけ
STRONG_RULES = [('th', 't'), ('Th', 'T'), ('dt', 't'), ('aa', 'a'), ('ey', 'ei')]
WEAK_RULES = [('ie', 'i'), ('ck', 'k'), ('ß', 'ss')]   # ie → i は小文字の語だけ (固有名詞 Amiens はそのまま)
# 語ごとの表: 縮約・語末の e の脱落
WORDS = {'hätt': 'hätte', 'wär': 'wäre', 'könnt': 'könnte', 'möcht': 'möchte', 'sollt': 'sollte', 'würd': 'würde',
         'hab': 'habe', 'Stund': 'Stunde', 'Gemüs': 'Gemüse', 'Gemüschen': 'Gemüse', 'gieng': 'ging',
         'giengen': 'gingen', 'fieng': 'fing', 'fiengen': 'fingen', 'hieng': 'hing', 'Hernach': 'hernach',
         'mutterseelig': 'mutterseelenallein'}
SPLITS = {'wills': ['will', 'es'], 'wars': ['war', 'es'], 'gibts': ['gibt', 'es'], 'giebts': ['gibt', 'es'],
          'ists': ['ist', 'es'], 'hats': ['hat', 'es'], 'kanns': ['kann', 'es'], 'gehts': ['geht', 'es'],
          'keins': ['keines']}
OLD_LINK = re.compile(r'^(?:formerly standard|obsolete|archaic|dated|superseded|pre-1996|pre-reform|old) '
                      r'(?:spelling|form)s? of ([^\s,;:()]+)', re.I)
UMLAUT_BACK = [('äu', 'au'), ('ä', 'a'), ('ö', 'o'), ('ü', 'u')]


@functools.lru_cache(maxsize=100000)
def known(word):
    return bool(dictionary.forms(word)) or bool(dictionary.lemmas(word))


@functools.lru_cache(maxsize=100000)
def modern(word):
    """古い綴りの語 → 今の綴り (直せなければそのまま)"""
    if word in WORDS:
        return WORDS[word]
    if len(word) < 3 or not re.search('[A-Za-zÄÖÜäöüß]', word):
        return word
    rows = [r for r in dictionary.lemmas(word) if r['word'] == word]   # 表記の合う見出し (roth は地名の Roth でない)
    links = [OLD_LINK.match(r['en'] or '') for r in rows]
    if rows and all(links):
        return links[0].group(1)   # 語義が「Formerly standard spelling of dass」だけの項目 (daß → dass)
    if rows:
        return word   # 語義のある見出し (Theater) はそのまま
    if word.isupper():
        return word   # 略語 (CRS)
    rules = STRONG_RULES + ([] if known(word) else [(a, b) for a, b in WEAK_RULES if a != 'ie' or word.islower()])
    applicable = [(a, b) for a, b in rules if a in word]
    for n in range(1, min(3, len(applicable)) + 1):
        for combo in itertools.combinations(applicable, n):
            candidate = word
            for a, b in combo:
                candidate = candidate.replace(a, b)
            if candidate != word and known(candidate):
                return candidate
    return word


def tokens(surfaces):
    """語の列の綴りを直す (縮約は2語に)。返り値: (直した語の列, 元の語の位置のリスト)"""
    out, origin = [], []
    for k, w in enumerate(surfaces):
        if w.lower() in SPLITS:
            parts = SPLITS[w.lower()]
            out += [parts[0][:1].upper() + parts[0][1:] if w[:1].isupper() else parts[0]] + parts[1:]
            origin += [k] * len(parts)
            continue
        out.append(modern(w))
        origin.append(k)
    return out, origin


@functools.lru_cache(maxsize=50000)
def diminutive_base(word):
    """縮小形 (-lein・-chen・-elein・-elchen) → 元の名詞 (辞書の見出し)。違えば None"""
    if not word[:1].isupper():
        return None
    for suffix in ('elein', 'elchen', 'lein', 'chen'):
        if not word.endswith(suffix) or len(word) - len(suffix) < 2:
            continue
        stem = word[:-len(suffix)]
        backs = []
        for a, b in UMLAUT_BACK:
            if a in stem:
                backs.append(stem[::-1].replace(a[::-1], b[::-1], 1)[::-1])   # 最後のウムラウトを戻す (Töchter → Tochter)
                break
        candidates = [c + end for c in backs + [stem] for end in ('', 'el', 'e', 'en')]
        for c in candidates:
            if c != word and dictionary.lemmas(c, ('noun',)):
                return c
    return None
