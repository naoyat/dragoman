#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# デーヴァナーガリー (ヒンディー語): ラテン文字への転写 (Wiktionary の転写に近い形: laṛkā, mẽ, paṛhnā)。
# ヒンディー語は子音に含まれる母音 a を、語末と「母音 + 子音 _ 子音 + 母音」の位置で読まない (schwa の脱落):
#   कमरा kamrā (kamarā でない)、लड़का laṛkā、समझना samajhnā、घर ghar
#
#   translit('पढ़ता हूँ') → 'paṛhtā hū̃'    key('पढ़ता') → 'पढ़ता' (ヌクタの合成をそろえる)
#
import re
import unicodedata

VIRAMA, NUKTA, ANUSVARA, CANDRABINDU, VISARGA = '्', '़', 'ं', 'ँ', 'ः'
CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ṅ', 'च': 'c', 'छ': 'ch', 'ज': 'j', 'झ': 'jh', 'ञ': 'ñ',
    'ट': 'ṭ', 'ठ': 'ṭh', 'ड': 'ḍ', 'ढ': 'ḍh', 'ण': 'ṇ', 'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm', 'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'ś',
    'ष': 'ṣ', 'स': 's', 'ह': 'h', 'ळ': 'ḷ',
}
NUKTA_CONSONANTS = {'क': 'q', 'ख': 'x', 'ग': 'ġ', 'ज': 'z', 'फ': 'f', 'ड': 'ṛ', 'ढ': 'ṛh', 'य': 'y', 'र': 'r'}
VOWEL_SIGNS = {'ा': 'ā', 'ि': 'i', 'ी': 'ī', 'ु': 'u', 'ू': 'ū', 'ृ': 'ŕ',
               'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॅ': 'ê', 'ॉ': 'ô'}
VOWELS = {'अ': 'a', 'आ': 'ā', 'इ': 'i', 'ई': 'ī', 'उ': 'u', 'ऊ': 'ū', 'ऋ': 'ŕ', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o',
          'औ': 'au', 'ऑ': 'ô', 'ऍ': 'ê'}
NASAL = {'a': 'ã', 'ā': 'ā̃', 'i': 'ĩ', 'ī': 'ī̃', 'u': 'ũ', 'ū': 'ū̃', 'e': 'ẽ', 'o': 'õ', 'ai': 'a͠i', 'au': 'a͠u'}
# 子音の前の anusvāra は同じ調音位置の鼻音 (हिंदी hindī、संबंध sambandh)
# (h・y の前、長母音 + ṭh・ch の前は母音の鼻音化: सिंह sĩh、संयोग sãyog。Wiktionary の転写の流儀を数えて決めた)
HOMORGANIC = {'k': 'ṅ', 'g': 'ṅ', 'c': 'ñ', 'j': 'ñ', 'ṭ': 'ṇ', 'ḍ': 'ṇ', 'p': 'm', 'b': 'm', 'm': 'm', 'ś': 'ñ',
              'ṣ': 'ñ', 'v': 'm'}
LONG_VOWELS = {'ā', 'ī', 'ū', 'e', 'o', 'ai', 'au'}
DANDA = '।॥'
DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')
DEVANAGARI = re.compile('[ऀ-ॿ]')


def key(text):
    """辞書引きのキー: NFC にそろえ、ヌクタ付きの合成文字 (ड़ U+095C) を基本字 + ヌクタに分ける"""
    text = unicodedata.normalize('NFC', text).translate(DIGITS)
    return unicodedata.normalize('NFD', text).replace('‍', '').replace('‌', '')


def is_devanagari(text):
    return bool(DEVANAGARI.search(text))


def _syllables(word):
    """[(子音 (無ければ None), 母音 (None は内在の a、'' は virāma), 鼻音化)]"""
    out = []
    chars = list(key(word))
    i = 0
    while i < len(chars):
        c = chars[i]
        if c in CONSONANTS:
            cons = CONSONANTS[c]
            if i + 1 < len(chars) and chars[i + 1] == NUKTA:
                cons = NUKTA_CONSONANTS.get(c, cons)
                i += 1
            vowel = None
            if i + 1 < len(chars) and chars[i + 1] in VOWEL_SIGNS:
                vowel = VOWEL_SIGNS[chars[i + 1]]
                i += 1
            elif i + 1 < len(chars) and chars[i + 1] == VIRAMA:
                vowel = ''
                i += 1
            out.append([cons, vowel, False])
        elif c in VOWELS:
            out.append([None, VOWELS[c], False])
        elif c in (ANUSVARA, CANDRABINDU) and out:
            out[-1][2] = 'anusvara' if c == ANUSVARA else 'candrabindu'
        elif c == VISARGA and out:
            out.append(['ḥ', '', False])
        else:
            out.append([c, '', False])  # 句読点・数字など
        i += 1
    return out


def _schwa_deletion(sylls):
    """内在の a (vowel None) を読むかどうか: 語末は読まない。右から見て「母音 + 子音 _ 子音 + 母音」の a は読まない"""
    n = len(sylls)
    keep = [s[1] is not None for s in sylls]  # True: 書かれた母音 (または virāma)
    vowels = [s[1] if s[1] is not None else 'a' for s in sylls]
    # 語末の a (-ya / -ra / -śva などの子音連続の後ろは読む: विश्व viśva、प्रिय priya。बुद्ध buddh は読まない)
    if n > 1 and sylls[-1][1] is None and sylls[-1][0] is not None and not sylls[-1][2] and not (
            sylls[-2][1] == '' and (sylls[-1][0] in ('y', 'r') or sylls[-1][0] == 'v' and sylls[-2][0] in ('ś', 's', 't', 'd'))
            or sylls[-1][0] == 'y' and sylls[-2][1] in ('i', 'ī')):  # -iya (प्रिय priya)
        vowels[-1] = ''
    # 語中: i 番目の a は、前の音節に母音があり (i-1 の a は残る)、後ろの子音に母音が続けば落とす
    for i in range(n - 2, 0, -1):
        if sylls[i][1] is not None or sylls[i][0] is None or sylls[i][2]:
            continue
        prev_has_vowel = vowels[i - 1] != ''
        nxt = sylls[i + 1]
        next_has_vowel = nxt[0] is not None and vowels[i + 1] != ''
        if prev_has_vowel and next_has_vowel and i >= 1 and (i - 1 > 0 or sylls[i - 1][0] is None or True):
            vowels[i] = ''
            # 連続して落とさない (कमरा は kamrā、कमरों は kamrõ)
            if i - 1 >= 1 and sylls[i - 1][1] is None:
                pass
    del keep
    return vowels


def translit_word(word):
    sylls = _syllables(word)
    if not sylls:
        return word
    vowels = _schwa_deletion(sylls)
    out = []
    for k, ((cons, written, nasal), vowel) in enumerate(zip(sylls, vowels)):
        if cons is not None:
            out.append(cons)
        if nasal:
            nxt = sylls[k + 1][0] if k + 1 < len(sylls) else None
            if nasal == 'anusvara' and nxt and nxt[0] not in 'ḥhy' and vowel not in ('', None) and \
                    nxt[0].isalpha() and not (vowel in LONG_VOWELS and nxt in ('ṭh', 'ch')):
                out.append(vowel + HOMORGANIC.get(nxt[0], 'n'))  # संस्कृत sanskŕt、अहिंसा ahinsā、अंश añś
                continue
            out.append(NASAL.get(vowel or 'a', (vowel or 'a') + '̃'))
            continue
        out.append(vowel)
    return ''.join(out)


def translit(text):
    """文・語のラテン文字への転写 (ダンダ । は .)"""
    text = re.sub('[।॥]', '.', text)
    return ' '.join(re.sub('[\u0900-\u0963\u0966-\u097f]+', lambda m: translit_word(m.group(0)), w)
                    for w in text.split())


def translit_known(word, lemma, lemma_roman):
    """辞書にある語の転写: 見出し語なら Wiktionary の転写、変化形なら、見出し語で規則の転写と Wiktionary の転写が
    違う所 (a の有無・鼻音) を同じ位置に写す (लड़कों: laṛkā の直しを laṛkõ にも)"""
    import difflib
    rule = translit_word(word)
    if not lemma_roman:
        return rule
    lemma_roman = unicodedata.normalize('NFC', lemma_roman)
    if key(word) == key(lemma):
        return lemma_roman
    lemma_rule = unicodedata.normalize('NFC', translit_word(lemma))
    rule = unicodedata.normalize('NFC', rule)
    if lemma_rule == lemma_roman:
        return rule
    common = 0
    while common < min(len(rule), len(lemma_rule)) and rule[common] == lemma_rule[common]:
        common += 1
    out = []
    last = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, lemma_rule, lemma_roman).get_opcodes():
        if op == 'equal' or i2 > common or (op == 'insert' and i1 >= common):
            continue
        out.append(rule[last:i1] + lemma_roman[j1:j2])
        last = i2
    return ''.join(out) + rule[last:]


# ----------------------------------------------------------------------
# ラテン文字 → デーヴァナーガリー (入力用)。IAST と ISO 15919 (ē ō・ṁ・m̐・r̥・ṛ = ड़・ṛh = ढ़) と Wiktionary 式の
# 転写 (mẽ・hū̃・laṛkā・q x ġ z f のヌクタ)。内在の a は書いても (laṛakā) 書かなくても (laṛkā) よい。
#
#   子音の連続は結合文字 (प्यार pyār) か、内在の a の脱落 (कमरा kamrā・बोलना bolnā) か一意に決まらない。
#   子音の前の鼻音 (hindī) も anusvāra (हिंदी) か結合文字 (हिन्दी) か。候補を作って辞書にある綴りを選ぶ

LATIN_CONSONANTS = {
    'kh': 'ख', 'gh': 'घ', 'ch': 'छ', 'jh': 'झ', 'ṭh': 'ठ', 'ḍh': 'ढ', 'th': 'थ', 'dh': 'ध', 'ph': 'फ', 'bh': 'भ',
    'ṛh': 'ढ़', 'k': 'क', 'g': 'ग', 'ṅ': 'ङ', 'c': 'च', 'j': 'ज', 'ñ': 'ञ', 'ṭ': 'ट', 'ḍ': 'ड', 'ṇ': 'ण',
    't': 'त', 'd': 'द', 'n': 'न', 'p': 'प', 'b': 'ब', 'm': 'म', 'y': 'य', 'ẏ': 'य़', 'r': 'र', 'l': 'ल', 'ḷ': 'ळ',
    'v': 'व', 'w': 'व', 'ś': 'श', 'ṣ': 'ष', 's': 'स', 'h': 'ह', 'q': 'क़', 'x': 'ख़', 'ġ': 'ग़', 'z': 'ज़',
    'f': 'फ़', 'ṛ': 'ड़',
}
LATIN_VOWELS = {'ai': ('ऐ', 'ै'), 'au': ('औ', 'ौ'), 'a': ('अ', ''), 'ā': ('आ', 'ा'), 'i': ('इ', 'ि'),
                'ī': ('ई', 'ी'), 'u': ('उ', 'ु'), 'ū': ('ऊ', 'ू'), 'e': ('ए', 'े'), 'ē': ('ए', 'े'),
                'o': ('ओ', 'ो'), 'ō': ('ओ', 'ो'), 'r̥': ('ऋ', 'ृ'), 'ŕ': ('ऋ', 'ृ'), 'ê': ('ऍ', 'ॅ'),
                'ô': ('ऑ', 'ॉ'), 'æ': ('ऍ', 'ॅ'), 'ŏ': ('ऑ', 'ॉ')}
UPPER_SIGNS = set('िीेैोौॅॉ')   # 線の上に出る母音記号 (鼻音化は candrabindu でなく anusvāra で書く)
NASALS = set('ṅñṇnm')
LATIN_UNITS = sorted(list(LATIN_CONSONANTS) + list(LATIN_VOWELS) + ['ṁ', 'ṃ', 'm̐', 'ḥ', '~'], key=len, reverse=True)
LATIN_WORD = r"[A-Za-zÀ-ɏḀ-ỿ̀-ͯ~]+"


def _latin_units(word):
    word = unicodedata.normalize('NFC', word.lower()).replace('a͠i', 'ai~').replace('a͠u', 'au~')
    # 鼻音化の母音 (ã ẽ ĩ õ ũ・ā̃ ī̃ ū̃) は母音 + ~ に (m̐ は candrabindu として残す)
    word = unicodedata.normalize('NFD', word)
    word = re.sub('([aeiou][̄]?)̃', r'\1~', word)
    word = unicodedata.normalize('NFC', word.replace('m̐', '\0')).replace('\0', 'm̐')
    units, i = [], 0
    while i < len(word):
        for u in LATIN_UNITS:
            if word.startswith(u, i):
                units.append(u)
                i += len(u)
                break
        else:
            units.append(word[i])
            i += 1
    return units


def _cluster_default_conjunct(units, k):
    """子音 k と次の子音の間の既定: 結合文字 (y・r・v が続く、語頭の連続、s・ś・ṣ が先) なら True"""
    nxt = units[k + 1]
    return nxt in ('y', 'r', 'v', 'w') or k == 0 or units[k] in ('s', 'ś', 'ṣ') and k == 0 or \
        (k > 0 and units[k - 1] in LATIN_CONSONANTS)


def _devanagari_word(word):
    units = _latin_units(word)
    options = []
    k = 0
    after_consonant = False
    while k < len(units):
        u = units[k]
        nxt = units[k + 1] if k + 1 < len(units) else None
        if u == 'ṛ' and after_consonant and nxt not in LATIN_VOWELS:
            u = 'r̥'   # 子音の後ろで母音が続かない ṛ は母音 (IAST の kṛpā → कृपा)
        if u in LATIN_CONSONANTS:
            letter = LATIN_CONSONANTS[u]
            if nxt in LATIN_VOWELS and nxt != 'r̥':
                options.append([letter])   # 母音記号は次の位置で
            elif nxt in LATIN_CONSONANTS:
                conjunct, bare = letter + VIRAMA, letter
                choices = [conjunct, bare] if _cluster_default_conjunct(units, k) else [bare, conjunct]
                if u in NASALS and units[k - 1:k] and units[k - 1] in LATIN_VOWELS:
                    choices = [ANUSVARA] + choices   # hindī → हिंदी / हिन्दी
                options.append(choices)
            else:
                options.append([letter])   # 語末の子音・内在の a の脱落
            after_consonant = True
        elif u in LATIN_VOWELS:
            independent, sign = LATIN_VOWELS[u]
            options.append([sign if after_consonant else independent])
            after_consonant = False
        elif u in ('ṁ', 'ṃ'):
            options.append([ANUSVARA])
            after_consonant = False
        elif u in ('m̐', '~'):
            prev = options[-1][0][-1:] if options else ''
            options.append([ANUSVARA if prev in UPPER_SIGNS else CANDRABINDU])
            after_consonant = False
        elif u == 'ḥ':
            options.append([VISARGA])
            after_consonant = False
        else:
            options.append([u])
            after_consonant = False
        k += 1

    def known(w):
        from . import dictionary
        return bool(dictionary.forms(w) or dictionary.lemmas(w))

    from dragoman.core.reverse import pick
    return unicodedata.normalize('NFC', pick(options, known))


def from_latin(text):
    """ラテン文字で書いたヒンディー語 → デーヴァナーガリー (デーヴァナーガリーを含めばそのまま。文末の . は ।)"""
    if is_devanagari(text) or not re.search('[A-Za-z]', text):
        return text
    text = re.sub(r'\.(?=\s|$)', '।', text)
    return re.sub(LATIN_WORD, lambda m: _devanagari_word(m.group(0)), text)
