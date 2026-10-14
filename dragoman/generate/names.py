#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 固有名詞の置き換え: ラテン語などの名前 → 英語の名前 (Wiktionary の訳語。Iēsus → Jesus) → 各言語の名前
# (Иисус・Ἰησοῦς・يَسُوع・יֵשׁוּעַ)。表は tools/build_name_index.py で作る ($DRAGOMAN_DATA/<lang>/names.tsv)
#
import difflib
import functools
import os
import re
import unicodedata

from dragoman.core import paths

# 英語の名前らしい語句 (大文字で始まる語の並び。説明文 "Roman statesman and orator" は除く)
NAME = re.compile(r"[A-Z][\w'’-]*(?: (?:of |the |de )?[A-Z][\w'’-]*){0,3}")

# 表の選び方では決まらないもの (キリスト教の文脈の名前: アラビア語の عِيسَى はクルアーンの形)
# ヘブライ語の יֵשׁוּ は現代語の形 (聖書の形は יֵשׁוּעַ)
# ロシア語の Иешуа は Иисус と同じ語義で並ぶ
OVERRIDES = {('ar', 'Jesus'): ('يَسُوع', 'm'), ('he', 'Jesus'): ('יֵשׁוּעַ', 'm'), ('ru', 'Jesus'): ('Иисус', 'm')}


def is_name(text):
    return bool(text) and bool(NAME.fullmatch(text))


@functools.lru_cache(maxsize=None)
def _index(lang):
    path = paths.data(lang, 'names.tsv')
    index = {}
    if not os.path.exists(path):
        return index
    with open(path, encoding='utf-8') as f:
        for line in f:
            fields = line.rstrip('\n').split('\t')
            if len(fields) < 4:
                continue
            word, keys, gender, senses = fields[0], fields[1].split(','), fields[2], int(fields[3] or 0)
            for k, key in enumerate(keys):
                index.setdefault(key, []).append((word, gender, senses, k))
    return index


def available(lang):
    return bool(_index(lang))


def _plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c)).lower()


def lookup(english, lang, original=''):
    """英語の名前 → (言語 lang の名前, 性)。無ければ None。
    候補が複数なら英語の名前が語義の先頭にあるもの (Иисус「Jesus, Joshua」。Иешуа「Yeshua, Jesus」より)、
    元の綴り (original) に近いもの (インドネシア語の Jesus: Isa より Yesus)、語義の多いものを先に"""
    if (lang, english) in OVERRIDES:
        return OVERRIDES[(lang, english)]
    hits = _index(lang).get(english)
    if not hits:
        return None
    similar = lambda word: difflib.SequenceMatcher(None, _plain(word), _plain(original or english)).ratio()
    word, gender, _, _ = min(hits, key=lambda h: (h[3], -similar(h[0]), -h[2]))
    return word, gender


MN_LATIN = dict(zip('абвгдеёжзийклмноөпрстуүфхцчшщъыьэюя',
                    ['a', 'b', 'v', 'g', 'd', 'ye', 'yo', 'zh', 'z', 'i', 'i', 'k', 'l', 'm', 'n', 'o', 'ö', 'p', 'r', 's',
                     't', 'u', 'ü', 'f', 'kh', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya']))


def latin_spelling(lex):
    """ほかの言語の固有名詞のラテン文字の綴り (민수 → Minsu、Дорж → Dorzh)。ラテン文字の言語はそのまま"""
    lemma = lex.lemma
    if lex.lang == 'ko':
        from dragoman.korean.script import romanize
        lemma = romanize(lemma)
    elif lex.lang == 'mn':   # 英語式の綴り (Дорж → Dorzh、Цэцэг → Tsetseg、Улаанбаатар → Ulaanbaatar)
        lemma = ''.join(MN_LATIN.get(c, c) for c in lemma.lower())
    elif lex.lang == 'ru':
        from dragoman.russian.script import translit
        lemma = translit(lemma)
    elif lex.lang == 'grc':
        from dragoman.greek.romanize import romanize_word
        lemma = romanize_word(lemma)
    return lemma[:1].upper() + lemma[1:]


def localized(lex, lang):
    """固有名詞の語 (Lex) → (言語 lang の名前, 性)。英語の名前が分からないか表に無ければ None"""
    if lex.origin and lex.origin[0] == lang:
        return lex.origin[1], ''   # 元の言語に戻す (Minsu → 민수)
    if lex.origin and lex.origin[0] in ('mn', 'ru') and lang in ('mn', 'ru'):
        return lex.origin[1], ''   # キリル文字の名前はロシア語・モンゴル語でもそのまま (Дорж・Иван)
    from . import english
    name = english.word(lex)
    if not is_name(name):
        return None
    return lookup(name, lang, english._flat(lex.lemma))
