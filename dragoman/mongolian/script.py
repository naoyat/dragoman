#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語のラテン文字の転写 → キリル文字 (入力用)。Wiktionary の転写 (öčigdör・sajn・javax・unšix) と、
# 文法書の例文の転写 (UD Mongolian-GDUD: öcigdör・oxin-d・bai-na。ハイフンは形態素の境) を受け付ける
#
#   from_latin('Xüü öcigdör oxin-d nom ög-sön.') → 'Хүү өчигдөр охинд ном өгсөн.'
#
import re
import unicodedata

# 二字の綴り (先に)
DIGRAPHS = [('shch', 'щ'), ('sh', 'ш'), ('ch', 'ч'), ('kh', 'х'), ('ts', 'ц'), ('zh', 'ж'), ('yo', 'ё'), ('yu', 'ю'),
            ('ya', 'я'), ('ye', 'е'), ('jo', 'ё'), ('ju', 'ю'), ('ja', 'я'), ('je', 'е'), ('ai', 'ай'), ('ei', 'эй'),
            ('oi', 'ой'), ('ui', 'уй'), ('üi', 'үй'), ('ii', 'ий'), ('aj', 'ай'), ('ej', 'эй'), ('oj', 'ой'), ('uj', 'уй'),
            ('üj', 'үй'), ('ij', 'ий')]
LETTERS = {'a': 'а', 'b': 'б', 'v': 'в', 'w': 'в', 'g': 'г', 'ɢ': 'г', 'ɣ': 'г', 'd': 'д', 'e': 'э', 'ə': 'э',
           'ž': 'ж', 'ʒ': 'з', 'z': 'з', 'i': 'и', 'j': 'ж', 'k': 'к', 'l': 'л', 'ɮ': 'л', 'm': 'м', 'n': 'н', 'ŋ': 'н',
           'o': 'о', 'ɔ': 'о', 'ö': 'ө', 'ø': 'ө', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'ʊ': 'у', 'ü': 'ү',
           'f': 'ф', 'x': 'х', 'h': 'х', 'c': 'ч', 'č': 'ч', 'š': 'ш', 'y': 'ы', 'ï': 'ы', "'": 'ь', 'ʰ': ''}
LATIN_WORD = re.compile(r"[A-Za-zÀ-ɏɐ-ʯʰ'=-]+(?:\.[A-Za-zÀ-ɏɐ-ʯʰ'=-]+)*")   # 語の中の . (bic.üül) は形態素の境


def has_cyrillic(text):
    return any('Ѐ' <= c <= 'ӿ' for c in text)


def _word(word):
    word = word.replace('-', '').replace('=', '').replace('.', '')
    upper = word[:1].isupper()
    low = unicodedata.normalize('NFC', word.lower())
    out, i = '', 0
    while i < len(low):
        matched = False
        for latin, cyr in DIGRAPHS:
            if low.startswith(latin, i):
                # j / y + 母音は я / ё / ю / е (母音の後ろでも: soyoo → соёо)。母音の前でない j / y は下で й
                out += cyr
                i += len(latin)
                matched = True
                break
        if not matched:
            c = low[i]
            if c in 'jy' and i > 0 and low[i - 1] in 'aeiouüöɔəʊ':
                out += 'й'
            elif c == 'j' and i + 1 < len(low) and low[i + 1] in 'aeouü':
                out += 'ж'
            else:
                out += LETTERS.get(c, c)
            i += 1
    return out[:1].upper() + out[1:] if upper else out


def from_latin(text):
    """ラテン文字の転写の文 → キリル文字 (キリル文字を含めばそのまま)"""
    if has_cyrillic(text) or not re.search('[A-Za-z]', text):
        return text
    return LATIN_WORD.sub(lambda m: _word(m.group(0)) if re.search('[A-Za-z]', m.group(0)) else m.group(0), text)
