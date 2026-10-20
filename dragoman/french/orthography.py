#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 17世紀 (古典期) のフランス語の綴りを今の綴りに直す (アカデミー・フランセーズの創設 1635年のころ: デカルト・コルネイユ・
# モリエール・ラシーヌの刊本の綴り)
#
#   estoit → était、avoit → avait (-oit → -ait)      teste → tête、escrire → écrire、maistre → maître (子音の前の s)
#   luy → lui、cecy → ceci、j'ay → j'ai (y → i)      bontez → bontés (-ez → -és)、enfans → enfants (-ns → -nts)
#   sçavoir → savoir (sç → s)、foible → faible (oi → ai)、auoir → avoir・vn → un (u と v)、iamais → jamais (i と j)
#   長い s (ſ) → s
#
# 規則で作った綴りの候補のうち、辞書 (見出し・語形の表) にあるものを採る (変える所の少ないものから)。古い綴りの印
# (ſ・-oit・luy・estoit …) のある文 (old_style) では、今の綴りにもある語 (teste「試す」) も古い綴りとして直す
# (今の綴りにもよくある並び oi・-ns の規則は除く: soit・moi・François はそのまま)
#
import functools
import re

from . import dictionary

# 語ごとの表 (規則で作れない形・よく出る語)
WORDS = {'luy': 'lui', 'celuy': 'celui', 'cecy': 'ceci', 'icy': 'ici', 'ainsy': 'ainsi', 'aussy': 'aussi',
         'moy': 'moi', 'toy': 'toi', 'soy': 'soi', 'roy': 'roi', 'loy': 'loi', 'foy': 'foi', 'quoy': 'quoi',
         'pourquoy': 'pourquoi', 'vn': 'un', 'vne': 'une', 'vns': 'uns', 'vnes': 'unes', 'ie': 'je', "i'": "j'",
         'ay': 'ai', 'sçay': 'sais', 'sçais': 'sais', 'sçait': 'sait', 'sçavoir': 'savoir', 'sçavons': 'savons',
         'sçavez': 'savez', 'sçavent': 'savent', 'sçeu': 'su', 'iamais': 'jamais', 'iour': 'jour', 'iours': 'jours',
         'tousiours': 'toujours', 'tousjours': 'toujours', 'desja': 'déjà', 'desia': 'déjà', 'apres': 'après',
         'tres': 'très', 'aupres': 'auprès', 'pres': 'près', 'plustost': 'plutôt', 'aussi-tost': 'aussitôt',
         'aussitost': 'aussitôt', 'tost': 'tôt', 'mesme': 'même', 'mesmes': 'mêmes', 'nostre': 'notre',
         'vostre': 'votre', 'nostres': 'nôtres', 'vostres': 'vôtres', 'cognoistre': 'connaître',
         'connoistre': 'connaître', 'paroistre': 'paraître', 'estre': 'être', 'avecque': 'avec', 'avecques': 'avec',
         'encor': 'encore', 'iusques': 'jusque', 'jusques': 'jusque', 'dés': 'dès', 'a-t-il': 'a-t-il'}
CONSONANT = 'bcdfghjklmnpqrstvwxz'
# 規則: (古い綴りの正規表現, 今の綴りの候補)。強い規則は今の綴りに出ない並び
RULES = [
    (r'ſ', ('s',)),
    (r'sç', ('s',)),
    (r'(?<=[aeiou])u(?=[aeiou])', ('v',)),             # auoir → avoir、deuoir → devoir
    (r'^v(?=[%s])' % CONSONANT, ('u',)),               # vn → un
    (r'^i(?=[aeiou])', ('j',)),                        # iamais → jamais
    (r'oi(?=(?:t|s|ent|ens|ent)$)', ('ai',)),          # estoit → était、avois → avais、avoient → avaient
    (r'oy(?=ent$)', ('ai',)),                          # croyent → croient は下の y → i で
    (r'oi', ('ai',)),                                  # foible → faible、connoissance → connaissance
    (r'(?<=[aeiou])y(?=[%s]|$)' % CONSONANT, ('i',)),  # luy → lui、j'ay → j'ai
    (r'es(?=[%s])' % CONSONANT, ('ê', 'é', 'e')),       # teste → tête、escrire → écrire、estoit → était
    (r'as(?=[%s])' % CONSONANT, ('â', 'a')),           # paste → pâte
    (r'os(?=[%s])' % CONSONANT, ('ô', 'o')),           # hostel → hôtel
    (r'is(?=[%s])' % CONSONANT, ('î', 'i')),           # maistre → maître、isle → île
    (r'us(?=[%s])' % CONSONANT, ('û', 'u')),           # gouster → goûter
    (r'ez$', ('és',)),                                 # bontez → bontés
    (r'(?<=[ae])ns$', ('nts',)),                       # enfans → enfants、parens → parents
    (r'gn(?=[aeiou])', ('n',)),                        # cognoistre → connoistre
]
# ſ は大文字・小文字を区別しない照合で s にも合うので、印の語の表だけ区別しない ((?i:…))
OLD_MARKS = re.compile(r"ſ|sç|\b(?i:luy|moy|toy|soy|cecy|celuy|icy|estoit|avoit|estoient|avoient|mesme|nostre|vostre|"
                       r"estre|vn|vne|iamais|tousjours|tousiours|sçay|faisoit|disoit|pouvoit|vouloit|devoit)\b|"
                       r"\b\w+oient\b|\b[iI]'(?=[aeiouy])")
MAX_CANDIDATES = 200


def old_style(text):
    """古い綴りの印のある文か (ſ・sç・luy・estoit・-oient …)"""
    return bool(OLD_MARKS.search(text))


@functools.lru_cache(maxsize=100000)
def known(word):
    """今の綴りとして辞書にある語 (見出しか、語形の表の印の付いた形)"""
    w = word.lower()
    return bool(dictionary.lemmas(w)) or any(tags for _, _, tags in dictionary.forms(w))


WEAK = {r'oi(?=(?:t|s|ent|ens|ent)$)', r'oi', r'(?<=[ae])ns$', r'gn(?=[aeiou])'}   # 今の綴りにもよくある並び (soit・moi)


def _candidates(word, strong_only=False):
    """規則で作った候補 (変えた所の数, 綴り) の列 (少ない順)。strong_only なら今の綴りに出ない並びの規則だけ"""
    found = {word: 0}
    for pattern, replacements in RULES:
        if strong_only and pattern in WEAK:
            continue
        for cand, n in list(found.items()):
            if not re.search(pattern, cand):
                continue
            for r in replacements:
                new = re.sub(pattern, r, cand)
                if new not in found and len(found) < MAX_CANDIDATES:
                    found[new] = n + 1
    return sorted(((n, c) for c, n in found.items() if c != word), key=lambda nc: nc[0])


@functools.lru_cache(maxsize=100000)
def modern(word, old=False):
    """古い綴りの語 → 今の綴り (直せなければそのまま)。old は古い綴りの文 (今の綴りにもある語も直す)"""
    if 'ſ' in word:   # 長い s は先に s に (ſçay → sçay → sais)
        plain = word.replace('ſ', 's')
        return modern(plain, True) if plain != word else plain
    lower = word.lower()
    if lower in WORDS:
        return _same_case(word, WORDS[lower])
    if len(word) < 2 or not re.search('[A-Za-zſ]', word) or word.isupper():
        return word
    if "'" in word:   # エリジオンの付いた語 (l'estat) は後ろを直す
        head, _, tail = word.partition("'")
        return head + "'" + modern(tail, old) if tail else _same_case(word, WORDS.get(lower, word))
    is_known = known(word) and 'ſ' not in word
    if is_known and not old:
        return word
    for _, cand in _candidates(lower):
        if not known(cand):
            continue
        # 辞書にある語は、同じ語の古い形 (語形の表で avoit と avait が同じ見出し・同じ印) か、強い規則だけで作った形
        # (teste → tête) のときだけ直す (soit → sait・François → Français にしない)
        if not is_known or _same_word(lower, cand) or cand in {c for _, c in _strong(lower)}:
            return _same_case(word, cand)
    return word


@functools.lru_cache(maxsize=10000)
def _strong(word):
    return tuple(_candidates(word, strong_only=True))


def _same_word(old, cand):
    """語形の表で、古い形と候補が同じ語の同じ形か (avoit・avait は avoir の半過去3人称単数、estoit の見出し estre は
    être、connoissance の見出しは connaissance)"""
    def norm(lemma):
        return WORDS.get(lemma, lemma)
    old_forms = {(norm(l), p, t) for l, p, t in dictionary.forms(old)}
    if any(l == cand for l, _, _ in old_forms):
        return True
    cand_forms = {(l, p, t) for l, p, t in dictionary.forms(cand)}
    return bool(old_forms & cand_forms)


def _same_case(original, modern_form):
    return modern_form[:1].upper() + modern_form[1:] if original[:1].isupper() else modern_form


def tokens(surfaces):
    """語の列の綴りを直す。返り値: (直した語の列, 古い綴りの文か)"""
    old = old_style(' '.join(surfaces))
    return [modern(w, old) for w in surfaces], old
