#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# タガログ語の語をカタカナで書く: 綴りがほぼそのまま発音なので、綴り → 音素 → 共通の規則 (core/kana.py)
#
#   salamat → サラマト、kumusta → クムスタ、mahal → マハル、ngayon → ンガヨン、mga → マンガ、ng → ナン、Pilipinas → ピリピナス
#
#   - ng [ŋ] は母音の前で「ンガ」(ngayon → ンガヨン)。小辞 ng は [naŋ]「ナン」、mga は [maˈŋa]「マンガ」
#   - 綴りに書かない声門閉鎖音 (bata [ˈbataʔ]「子供」) は書かない (綴りから分からない)
#   - スペイン語からの語の c・f・j・ñ・q・v・x・z は近い音 (ñ → ニャ行、j → ハ行)、ts はツァ行
#   - 英語からの語 (タガログ語の辞書に無いか「英語から」の名前だけで、英語の発音辞書にある語) は英語の読み
#     (english/katakana.py): mag-enjoy → マグエンジョイ、joy → ジョイ (Jose → ホセ はスペイン語から)
#
from dragoman.core.kana import kana, text_words

VOWELS = {'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u'}
DIGRAPHS = {'ng': 'ŋ', 'ts': 'ts', 'ch': 'tʃ', 'sh': 'ʃ', 'ny': 'ɲ'}
CONSONANTS = {'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'h', 'k': 'k', 'l': 'l', 'm': 'm',
              'n': 'n', 'ñ': 'ɲ', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's', 't': 't', 'v': 'b', 'w': 'w', 'x': 'ks',
              'y': 'j', 'z': 's'}
WORDS = {'ng': ['n', 'a', 'ŋ'], 'mga': ['m', 'a', 'ŋ', 'a']}   # 綴りと読みの違う小辞
# 英語の発音辞書にもあるが、タガログ語の接頭辞・縮約形 (ung = yung) など
NATIVE = {'mag', 'nag', 'pag', 'mang', 'nang', 'um', 'ung', 'ila', 'ana', 'aki', 'mero', 'kin', 'banko', 'bonet', 'resto'}


def phonemes(word):
    word = word.lower()
    if word in WORDS:
        return list(WORDS[word])
    if '-' in word:   # 重ねた語・接頭辞 (araw-araw、mag-aral) は部分ごとに
        return [ph for k, part in enumerate(word.split('-')) for ph in ([' '] if k else []) + phonemes(part)]
    out = []
    k = 0
    while k < len(word):
        two = word[k:k + 2]
        if two in DIGRAPHS:
            out.append(DIGRAPHS[two])
            k += 2
            continue
        c = word[k]
        if c in VOWELS:
            out.append(VOWELS[c])
        elif c in CONSONANTS:
            ph = CONSONANTS[c]
            out += ['k', 's'] if ph == 'ks' else [ph]
        k += 1
    return out


def _english(word):
    """英語からの語か: タガログ語の辞書に無いか「英語から」の名前だけで、英語の発音辞書 (CMUdict) にある"""
    from dragoman.english import katakana as english
    if not word.isalpha() or word.lower() in WORDS or word.lower() in NATIVE or word.lower() not in english._cmudict():
        return False
    try:
        from dragoman.tagalog import dictionary
        rows = list(dictionary.lemmas(word)) + (list(dictionary.lemmas(word.lower())) if word != word.lower() else [])
    except Exception:
        return False
    return all(r['pos'] == 'name' and 'from English' in (r['en'] or '') for r in rows)


def katakana(word, long='phonemic', **options):
    if '-' in word:   # mag-enjoy: 接頭辞 (前の部分) はタガログ語、語根 (最後の部分) が英語ならそこだけ英語の読み
        parts = word.split('-')
        if parts[-1] and _english(parts[-1]):
            from dragoman.english import katakana as english
            return kana(phonemes('-'.join(parts[:-1])), long=long, **options) + english.katakana(parts[-1])
        return kana(phonemes(word), long=long, **options)
    if _english(word):
        from dragoman.english import katakana as english
        return english.katakana(word)
    return kana(phonemes(word), long=long, **options)


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列)"""
    return [katakana(w, **options) for w in text_words(text)]
