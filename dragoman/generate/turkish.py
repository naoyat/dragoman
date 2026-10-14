#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からトルコ語の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)
#   語順: 主語 - 受け手 (与格) - 目的語 (対格) - 後置詞句 - 動詞 (SOV)。主語の代名詞は書かない (動詞の人称の語尾で分かる)
#   接尾辞は母音調和で形が変わる: 2通り (a / e: -da / -de) と4通り (ı / i / u / ü: -ı / -i / -u / -ü)。
#     無声子音の後ろは d → t (kitapta)。多音節の語の末尾の p・ç・t・k は母音の前で b・c・d・ğ (kitap → kitabı)
#   格: 対格 -(y)ı、与格 -(y)a、位格 -da、奪格 -dan、属格 -(n)ın、具格 -(y)la。所有 3人称 -(s)ı (属格の名詞と組む)
#   動詞: 過去 -dı、現在 (進行) -(ı)yor、未来 -(y)acak、否定 -ma (過去 gelmedi・現在 gelmiyor・未来 gelmeyecek)、
#     受動 -ıl / -n、人称 -m・-n・-・-k・-nız・-lar。繋辞 -(y)dı (過去)・değil (否定)
#   関係節: 主語の空所 -(y)an (gülü gören kız)、目的語の空所 -dık + 所有 (kızın gördüğü gül)
#
import dataclasses

from . import transfer, english
from .frame import NP

BACK, FRONT = 'aıou', 'eiöü'
VOWELS = BACK + FRONT + 'âîû'
VOICELESS = 'çfhkpsşt'
PRONOUNS = {('ego', 'sg'): 'ben', ('ego', 'pl'): 'biz', ('tū', 'sg'): 'sen', ('tū', 'pl'): 'siz', ('is', 'sg'): 'o',
            ('is', 'pl'): 'onlar', ('hic', 'sg'): 'bu', ('ille', 'sg'): 'o', ('quis', 'sg'): 'kim', ('quid', 'sg'): 'ne',
            ('sē', 'sg'): 'kendi', ('sē', 'pl'): 'kendileri'}
# 代名詞の格の形
PRONOUN_CASES = {
    'ben': {'Acc': 'beni', 'Dat': 'bana', 'Loc': 'bende', 'Abl': 'benden', 'Gen': 'benim', 'Ins': 'benimle'},
    'sen': {'Acc': 'seni', 'Dat': 'sana', 'Loc': 'sende', 'Abl': 'senden', 'Gen': 'senin', 'Ins': 'seninle'},
    'o': {'Acc': 'onu', 'Dat': 'ona', 'Loc': 'onda', 'Abl': 'ondan', 'Gen': 'onun', 'Ins': 'onunla'},
    'bu': {'Acc': 'bunu', 'Dat': 'buna', 'Loc': 'bunda', 'Abl': 'bundan', 'Gen': 'bunun', 'Ins': 'bununla'},
    'biz': {'Gen': 'bizim'}, 'siz': {'Gen': 'sizin'},
}
DETERMINERS = {'hic': 'bu', 'hīc': 'bu', 'iste': 'şu', 'ille': 'o', 'is': 'o', 'omnis': 'bütün', 'alius': 'başka',
               'tōtus': 'bütün', 'multus': 'çok'}
POSSESSIVES = {'meus': 'benim', 'tuus': 'senin', 'suus': 'kendi', 'noster': 'bizim', 'vester': 'sizin'}
NUMERALS = {'ūnus': 'bir', 'duo': 'iki', 'trēs': 'üç', 'quattuor': 'dört', 'quīnque': 'beş', 'decem': 'on',
            'centum': 'yüz', 'mīlle': 'bin'}
# ラテン語の前置詞 + 格 → (格の接尾辞, 後置詞)
POSTPOSITIONS = {('in', 'Abl'): ('Loc', ''), ('in', 'Acc'): ('Dat', ''), ('ad', 'Acc'): ('Dat', ''),
                 ('ex', 'Abl'): ('Abl', ''), ('ē', 'Abl'): ('Abl', ''), ('ab', 'Abl'): ('Abl', ''), ('ā', 'Abl'): ('Abl', ''),
                 ('cum', 'Abl'): ('Ins', ''), ('dē', 'Abl'): ('Nom', 'hakkında'), ('sine', 'Abl'): ('Nom', 'olmadan'),
                 ('per', 'Acc'): ('Nom', 'boyunca'), ('propter', 'Acc'): ('Nom', 'yüzünden'), ('ob', 'Acc'): ('Nom', 'yüzünden'),
                 ('post', 'Acc'): ('Abl', 'sonra'), ('ante', 'Acc'): ('Abl', 'önce'), ('sub', 'Abl'): ('Gen', 'altında'),
                 ('super', 'Acc'): ('Gen', 'üstünde'), ('prō', 'Abl'): ('Nom', 'için'), ('apud', 'Acc'): ('Gen', 'yanında'),
                 ('contrā', 'Acc'): ('Dat', 'karşı'), ('inter', 'Acc'): ('Gen', 'arasında')}
CONNECTIVES = {'et': 've', 'que': 've', 'atque': 've', 'ac': 've', 'sed': 'ama', 'at': 'ama', 'autem': 'ise',
               'enim': 'çünkü', 'nam': 'çünkü', 'igitur': 'bu yüzden', 'itaque': 'bu yüzden', 'tamen': 'yine de',
               'tum': 'o zaman', 'deinde': 'sonra', 'aut': 'veya', 'vel': 'veya'}
WORDS = {'semper': 'her zaman', 'saepe': 'sık sık', 'iam': 'artık', 'nunc': 'şimdi', 'hodiē': 'bugün', 'crās': 'yarın',
         'heri': 'dün', 'ibi': 'orada', 'hīc': 'burada', 'etiam': 'de', 'quoque': 'de', 'valdē': 'çok', 'magnopere': 'çok',
         'statim': 'hemen', 'mox': 'yakında', 'tandem': 'sonunda', 'iterum': 'yine', 'numquam': 'asla', 'bene': 'iyi',
         'posteā': 'sonra', 'diū': 'uzun süre'}
PERSON_SUFFIXES = {  # (人称, 数) → 過去 -dı の後ろ / 進行 -yor の後ろ / 未来 -acak の後ろ
    (1, 'sg'): ('m', 'um', 'ım'), (2, 'sg'): ('n', 'sun', 'sın'), (3, 'sg'): ('', '', ''),
    (1, 'pl'): ('k', 'uz', 'ız'), (2, 'pl'): ('nız', 'sunuz', 'sınız'), (3, 'pl'): ('lar', 'lar', 'lar')}
IRREGULAR_STEMS = {'gitmek': 'gid', 'etmek': 'ed', 'tatmak': 'tad', 'gütmek': 'güd', 'demek': 'di', 'yemek': 'yi'}


# ----------------------------------------------------------------------
# 母音調和

def _last_vowel(word):
    for c in reversed(word.lower()):
        if c in VOWELS:
            return {'â': 'a', 'î': 'i', 'û': 'u'}.get(c, c)
    return 'e'


def two(word, back, front):
    """2通りの母音 (a / e)"""
    return back if _last_vowel(word) in BACK else front


def four(word):
    """4通りの母音 (ı / i / u / ü)"""
    return {'a': 'ı', 'ı': 'ı', 'o': 'u', 'u': 'u', 'e': 'i', 'i': 'i', 'ö': 'ü', 'ü': 'ü'}[_last_vowel(word)]


def _ends_vowel(word):
    return word[-1:].lower() in VOWELS


def _d(word):
    """d / t (無声子音の後ろは t)"""
    return 't' if word[-1:].lower() in VOICELESS else 'd'


# 母音で始まる接尾辞の前で語幹の母音が落ちる名詞 (şehir → şehri、oğul → oğlu)
VOWEL_DROP = {'şehir': 'şehr', 'ağız': 'ağz', 'oğul': 'oğl', 'burun': 'burn', 'alın': 'aln', 'gönül': 'gönl',
              'isim': 'ism', 'resim': 'resm', 'fikir': 'fikr', 'akıl': 'akl', 'vakit': 'vakt', 'şekil': 'şekl',
              'ömür': 'ömr', 'nehir': 'nehr', 'sabır': 'sabr', 'beyin': 'beyn', 'boyun': 'boyn', 'karın': 'karn',
              'kayın': 'kayn', 'emir': 'emr', 'şükür': 'şükr', 'hüküm': 'hükm', 'kısım': 'kısm', 'zihin': 'zihn'}


def _soften(word, proper=False):
    """母音の前の子音の有声化 (多音節の語: kitap → kitab、çocuk → çocuğ、ağaç → ağac)"""
    if word in VOWEL_DROP and not proper:
        return VOWEL_DROP[word]
    if proper or len([c for c in word if c in VOWELS]) < 2:
        return word
    return word[:-1] + {'p': 'b', 'ç': 'c', 't': 'd', 'k': 'ğ'}.get(word[-1], word[-1])


def case_form(word, case, possessed=False, proper=False):
    """名詞 + 格の接尾辞 (所有の接尾辞の後ろは n を挟む: kızı + a → kızına)"""
    if case in ('Nom', '', None):
        return word
    sep = "'" if proper else ''
    vowel_end = _ends_vowel(word)
    buffer_n = 'n' if possessed else ''
    if case == 'Acc':
        return word + sep + (buffer_n or ('y' if vowel_end else '')) + four(word) if vowel_end or possessed else \
            _soften(word, proper) + sep + four(word)
    if case == 'Dat':
        if possessed:
            return word + 'n' + two(word, 'a', 'e')
        return (word + sep + 'y' if vowel_end else _soften(word, proper) + sep) + two(word, 'a', 'e')
    if case == 'Loc':
        return word + sep + buffer_n + (_d(word) if not possessed else 'd') + two(word, 'a', 'e')
    if case == 'Abl':
        return word + sep + buffer_n + (_d(word) if not possessed else 'd') + two(word, 'an', 'en')
    if case == 'Gen':
        if vowel_end:
            return word + sep + 'n' + four(word) + 'n'
        return _soften(word, proper) + sep + four(word) + 'n'
    if case == 'Ins':
        return word + sep + ('y' if vowel_end else '') + two(word, 'la', 'le')
    return word


POSSESSOR_PERSONS = {'meus': (1, 'sg'), 'tuus': (2, 'sg'), 'suus': (3, 'sg'), 'noster': (1, 'pl'), 'vester': (2, 'pl')}


def possessive(word, person, number):
    """所有の接尾辞 (kitap → kitabım・kitabın・kitabı・kitabımız・kitabınız・kitapları)"""
    if (person, number) == (3, 'sg'):
        return possessive3(word)
    if (person, number) == (3, 'pl'):
        return word + two(word, 'ları', 'leri')
    base = word if _ends_vowel(word) else _soften(word) + four(word)
    v = four(base)
    return base + {(1, 'sg'): 'm', (2, 'sg'): 'n', (1, 'pl'): 'm' + v + 'z', (2, 'pl'): 'n' + v + 'z'}[(person, number)]


def possessive3(word):
    """所有の3人称 -(s)ı (kız → kızı、çiftçi → çiftçisi、kitap → kitabı)"""
    if _ends_vowel(word):
        return word + 's' + four(word)
    return _soften(word) + four(word)


def plural(word):
    return word + two(word, 'lar', 'ler')


# ----------------------------------------------------------------------
# 動詞

def stem_of(infinitive):
    """不定詞 → 語幹 (görmek → gör、okumak → oku)"""
    if infinitive.endswith(('mak', 'mek')):
        return infinitive[:-3]
    return infinitive


def _vowel_stem(infinitive):
    """母音の前の語幹 (gitmek → gid、demek → di)"""
    head, _, last = infinitive.rpartition(' ')
    if last in IRREGULAR_STEMS:   # 複合動詞 (dans etmek → dans ed)
        return (head + ' ' if head else '') + IRREGULAR_STEMS[last]
    return stem_of(infinitive)


def passive_stem(stem):
    """受動の語幹: 母音で終われば -n (oku → okun)、l で終われば -ın (bil → bilin)、ほかは -ıl (gör → görül)"""
    if _ends_vowel(stem):
        return stem + 'n'
    if stem.endswith('l'):
        return stem + four(stem) + 'n'
    return stem + four(stem) + 'l'


def conjugate(infinitive, tense='present', person=3, number='sg', negated=False, passive=False, mood='indicative'):
    stem = stem_of(infinitive)
    vstem = _vowel_stem(infinitive)
    if passive:
        stem = vstem = passive_stem(stem if _ends_vowel(stem) else vstem)   # gitmek → gidiliyor
    if mood == 'imperative':
        if negated:
            return stem + two(stem, 'ma', 'me')
        return stem if number == 'sg' else vstem + (four(stem) if not _ends_vowel(stem) else 'y' + four(stem)) + 'n'
    person_suffix = PERSON_SUFFIXES.get((person, number), PERSON_SUFFIXES[(3, 'sg')])
    if tense in ('perfect', 'past-perfect', 'imperfect'):
        base = stem + two(stem, 'ma', 'me') if negated else stem
        past = base + _d(base) + four(base)
        suffix = person_suffix[0]
        if suffix in ('nız',):
            suffix = 'n' + four(past) + 'z'
        elif suffix == 'lar':
            suffix = two(past, 'lar', 'ler')
        return past + suffix
    if tense in ('future', 'future-perfect'):
        base = stem + two(stem, 'ma', 'me') if negated else vstem
        future = base + ('y' if _ends_vowel(base) else '') + two(base, 'acak', 'ecek')
        suffix = person_suffix[2]
        if not suffix:
            return future
        if suffix == 'lar':
            return future + two(future, 'lar', 'ler')
        harmonized = suffix.replace('ı', four(future))
        return future[:-1] + 'ğ' + harmonized if harmonized[0] in VOWELS else future + harmonized
    # 現在 (進行 -iyor): a / e で終わる語幹はその母音を落として4通りの母音 (bekle → bekliyor、ara → arıyor)、
    # ı / i / u / ü で終わる語幹はそのまま (oku → okuyor)、子音で終わる語幹は4通りの母音を足す (gel → geliyor)
    if negated:
        base = stem + 'm' + four(stem)            # gelmiyor・okumuyor
    elif vstem[-1:] in 'ae':
        base = vstem[:-1] + four(vstem[:-1])
    elif _ends_vowel(vstem):
        base = vstem
    else:
        base = vstem + four(vstem)
    progressive = base + 'yor'
    suffix = person_suffix[1]
    if suffix == 'lar':
        return progressive + 'lar'
    return progressive + suffix


def participle(infinitive, gap, tense='present', negated=False, possessor=None):
    """関係節の分詞: 主語の空所 -(y)an (gören)、それ以外 -dık + 所有 (gördüğü・gördüğüm)。未来は -acak / -acağı"""
    stem = stem_of(infinitive)
    vstem = _vowel_stem(infinitive)
    base = stem + two(stem, 'ma', 'me') if negated else vstem
    dik_base = stem + two(stem, 'ma', 'me') if negated else stem   # -dık は子音で始まるので元の語幹 (gittiği・yediği)
    if gap == 'subject':
        if tense in ('future',):
            return base + ('y' if _ends_vowel(base) else '') + two(base, 'acak', 'ecek')
        return base + ('y' if _ends_vowel(base) else '') + two(base, 'an', 'en')
    owner = {('ego', 'sg'): 'm', ('tū', 'sg'): 'n', ('ego', 'pl'): 'miz', ('tū', 'pl'): 'niz'}.get(possessor, '')
    if tense in ('future',):
        stem_part = base + ('y' if _ends_vowel(base) else '') + two(base, 'acağ', 'eceğ')
    else:
        stem_part = dik_base + _d(dik_base) + four(dik_base) + 'ğ'
    v = four(stem_part)
    if owner == 'm':
        return stem_part + v + 'm'
    if owner == 'n':
        return stem_part + v + 'n'
    if owner in ('miz', 'niz'):
        return stem_part + v + owner[0] + v + 'z'
    return stem_part + v


# 副動詞・従属節の形 (ラテン語の従属節の接続詞 → トルコ語の動詞の形)。'dik' は -dık + 所有の語尾 (主語は属格)
SUBORDINATE_FORMS = {'et': 'ıp', 'cum': 'ınca', 'ubi': 'ınca', 'simul': 'ınca', 'postquam': 'dıktan sonra', 'dum': 'ken',
                     'sī': 'sa', 'quod': 'dik için', 'quia': 'dik için', 'quoniam': 'dik için', 'quamquam': 'dik halde',
                     'etsī': 'dik halde', 'priusquam': 'madan önce', 'antequam': 'madan önce', 'ut': 'mak için',
                     'nē': 'mamak için', 'dōnec': 'ana kadar'}
# 語幹 + -ır (超越形) の単音節の動詞 (ほかの単音節の子音で終わる語幹は -ar / -er)
AORIST_IR = {'al', 'bil', 'bul', 'dur', 'gel', 'gör', 'kal', 'ol', 'öl', 'san', 'var', 'ver', 'vur', 'ol', 'sanmak', 'de',
             'ye'}


def aorist(infinitive, negated=False):
    """超越形 (gelir・okur・yapar・gelmez)"""
    stem = stem_of(infinitive)
    if negated:
        return stem + two(stem, 'maz', 'mez')
    vstem = _vowel_stem(infinitive)
    if _ends_vowel(stem):
        return stem + 'r'
    if sum(c in VOWELS for c in stem) == 1 and stem not in AORIST_IR:
        return vstem + two(stem, 'ar', 'er')
    return vstem + four(stem) + 'r'


def converb(infinitive, key, person=3, number='sg', negated=False):
    """従属節の動詞の形 (gelince・geldikten sonra・gelirken・gelirse・geldiği için・gelmeden önce)"""
    form = SUBORDINATE_FORMS[key]
    stem = stem_of(infinitive)
    vstem = _vowel_stem(infinitive)
    neg = stem + two(stem, 'ma', 'me')
    if form == 'ıp':   # 続く動作 (açıp・gelip・okuyup・gidip)
        base = neg if negated else vstem
        return base + ('y' if _ends_vowel(base) else '') + four(base) + 'p'
    if form == 'ınca':
        base = neg if negated else vstem
        y = 'y' if _ends_vowel(base) else ''
        return base + y + four(base) + 'nc' + two(base, 'a', 'e')
    if form == 'ana kadar':
        base = neg if negated else vstem
        return base + ('y' if _ends_vowel(base) else '') + two(base, 'an', 'en') + two(base, 'a', 'e') + ' kadar'
    if form == 'dıktan sonra':
        base = neg if negated else stem
        past = base + _d(base) + four(base) + 'k'
        return past + 't' + two(past, 'an', 'en') + ' sonra'
    if form == 'ken':
        return aorist(infinitive, negated) + 'ken'   # gelirken・okurken
    if form == 'sa':
        base = aorist(infinitive, negated)
        return base + 's' + two(base, 'a', 'e') + {(1, 'sg'): 'm', (2, 'sg'): 'n', (1, 'pl'): 'k',
                                                    (2, 'pl'): 'n' + four(base) + 'z'}.get((person, number), '')
    if form.startswith('dik'):
        possessor = {(1, 'sg'): ('ego', 'sg'), (2, 'sg'): ('tū', 'sg'), (1, 'pl'): ('ego', 'pl'),
                     (2, 'pl'): ('tū', 'pl')}.get((person, number))
        return participle(infinitive, 'object', 'past', negated, possessor) + form[3:]
    if form == 'madan önce':
        return neg + two(stem, 'dan', 'den') + ' önce'
    if form in ('mak için', 'mamak için'):
        return (neg + two(stem, 'mak', 'mek') if negated or form == 'mamak için' else infinitive) + ' için'
    return conjugate(infinitive, 'present', person, number, negated)


# ----------------------------------------------------------------------
# 語

def available():
    return transfer.available('tr')


def to_turkish(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'tr':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'tr')
        return found[0] if found else _latin_name(lex.lemma)
    target = transfer.best(lex, 'tr', pos)
    return target.lemma if target else None


def _latin_name(lemma):
    """ラテン語の名前をトルコ語の綴りに (マクロンを外し、c → k、v → v。語尾はそのまま: Mārcus → Markus)"""
    import unicodedata
    plain = ''.join(c for c in unicodedata.normalize('NFD', lemma) if not unicodedata.combining(c))
    return plain.replace('ae', 'e').replace('c', 'k').replace('C', 'K').replace('qu', 'kv').replace('ph', 'f') \
        .replace('th', 't').replace('y', 'i')


def word(lex, pos=None):
    found = to_turkish(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


def noun_phrase(np, case='Nom'):
    if np.members:
        parts = [noun_phrase(m, 'Nom') for m in np.members]
        conj = ' veya ' if np.conj in ('aut', 'vel') else ' ve '
        joined = ', '.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
        last = noun_phrase(np.members[-1], case)
        return joined[:len(joined) - len(parts[-1])] + last
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun':
        key = (head.lemma, 'pl' if np.number == 'pl' else 'sg')
        pron = PRONOUNS.get(key) or PRONOUNS.get((head.lemma, 'sg')) or word(head)
        return PRONOUN_CASES.get(pron, {}).get(case) or case_form(pron, case)
    before = []
    for r in np.relatives:
        before.append(relative_clause(r))
    for m in np.modifiers:
        if isinstance(m, NP):
            before.append(' ve '.join(_modifier(x.head) for x in m.members))
            continue
        before.append(_modifier(m))
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    counted = any(not isinstance(m, NP) and m.lemma in NUMERALS and m.lemma != 'ūnus' for m in np.modifiers)
    if np.number == 'pl' and not counted:   # 数詞の後ろは単数 (iki kedi)
        noun = plural(noun)
    possessed = False
    owners = [m for m in np.modifiers if not isinstance(m, NP) and m.lemma in POSSESSOR_PERSONS and m.lang in ('', 'la')]
    if owners:   # 所有の接尾辞 (benim kitabım・annem。属格の代名詞は前に残す)
        person, owner_number = POSSESSOR_PERSONS[owners[0].lemma]
        noun = possessive(noun, person, owner_number)
        possessed = person == 3
        if owners[0].lemma == 'suus':
            before = [b for b in before if b != POSSESSIVES['suus']]   # 3人称の所有は接尾辞だけ (kitabı)
    if np.genitives:   # 属格 + 所有の3人称 (çiftçinin kızı)
        before.insert(0, ' '.join(noun_phrase(g, 'Gen') for g in np.genitives))
        noun = possessive3(noun)
        possessed = True
    return ' '.join(x for x in before + [case_form(noun, case, possessed, head.proper)] if x)


def _modifier(lex):
    for table in (DETERMINERS, POSSESSIVES, NUMERALS):
        if lex.lemma in table and lex.lang in ('', 'la'):
            return table[lex.lemma]
    return word(lex, 'adj') or '[%s]' % english.word(lex)


def relative_clause(r):
    return ' '.join(realize(r, gap=r.gap or 'subject'))


def prepositional(np, passive=False):
    inner_np = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        text = noun_phrase(inner_np)
        return text + ' tarafından' if text else ''
    case, post = POSTPOSITIONS.get((np.prep.lemma, np.case), ('Loc', '')) if np.prep is not None else ('Loc', '')
    text = noun_phrase(inner_np, case)
    if not text:
        return ''
    if post in ('altında', 'üstünde', 'yanında', 'arasında'):
        return text + ' ' + post
    return text + (' ' + post if post else '')


def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            subject.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[subject.head.lemma], subject.number or 'sg'
    if subject is not None:
        return 3, 'pl' if (subject.members or subject.number == 'pl') and subject.animate else 'sg'
    return clause.person, clause.number


def verb_form(clause, gap=None, possessor=None):
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return lemma
    if gap is not None:
        tense = 'future' if clause.tense == 'future' else 'present' if gap == 'subject' else 'past'
        return participle(lemma, gap, tense, clause.negated, possessor)
    person, number = _person(clause)
    return conjugate(lemma, clause.tense, person, number, clause.negated, clause.voice == 'passive', clause.mood)


def _copula(complement, clause, subject_person=(3, 'sg')):
    text = noun_phrase(complement)
    past = clause.tense in ('perfect', 'past-perfect', 'imperfect')
    person, number = subject_person
    if clause.negated:
        neg = 'değil'
        if past:
            neg += 'di' + {(1, 'sg'): 'm', (2, 'sg'): 'n', (1, 'pl'): 'k', (2, 'pl'): 'niz'}.get((person, number), '')
        else:
            neg += {(1, 'sg'): 'im', (2, 'sg'): 'sin', (1, 'pl'): 'iz', (2, 'pl'): 'siniz'}.get((person, number), '')
        return text + ' ' + neg
    if past:
        y = 'y' if _ends_vowel(text) else ''
        d = 'd' if y else _d(text)
        return text + y + d + four(text) + {(1, 'sg'): 'm', (2, 'sg'): 'n', (1, 'pl'): 'k',
                                            (2, 'pl'): 'n' + four(text) + 'z'}.get((person, number), '')
    suffix = {(1, 'sg'): 'y' + four(text) + 'm' if _ends_vowel(text) else four(text) + 'm',
              (2, 'sg'): 's' + four(text) + 'n', (1, 'pl'): ('y' if _ends_vowel(text) else '') + four(text) + 'z',
              (2, 'pl'): 's' + four(text) + 'n' + four(text) + 'z'}.get((person, number), '')
    return text + suffix


def realize(clause, gap=None, subordinate=False):
    """節の語の列。subordinate なら従属節: 動詞を副動詞などの形に (Eve gelince・geldiği için)"""
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    if subordinate and clause.subordinator in SUBORDINATE_FORMS and not clause.copula and gap is None:
        out = realize(dataclasses.replace(clause, subordinator=''))
        lemma = word(clause.verb, 'verb')
        if not out or not lemma or lemma.startswith('['):
            return out
        person, number = _person(clause)
        form = converb(lemma, clause.subordinator, person, number, clause.negated)
        subject = (clause.role('subject') or [None])[0]
        if SUBORDINATE_FORMS[clause.subordinator].startswith('dik') and subject is not None and \
                subject.head is not None and subject.head.pos != 'pronoun' and out[0] == noun_phrase(subject):
            out[0] = noun_phrase(subject, 'Gen')   # -dık の主語は属格 (Ali'nin geldiği için)
        return out[:-1] + [form]
    subject = (clause.role('subject') or [None])[0]
    out = []
    pronoun_subject = subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
        subject.head.lemma in ('ego', 'tū', 'is') and gap is None
    possessor = None
    if subject is not None and gap not in (None, 'subject'):
        # 目的語などの空所の関係節: 主語は属格 (kızın gördüğü)。代名詞の主語は所有の語尾 (gördüğüm)
        if subject.head is not None and subject.head.pos == 'pronoun' and subject.head.lemma in ('ego', 'tū'):
            possessor = (subject.head.lemma, subject.number or 'sg')
        else:
            out.append(noun_phrase(subject, 'Gen'))
    elif subject is not None and gap != 'subject' and not pronoun_subject:
        out.append(noun_phrase(subject))
    for adv in clause.adverbs:
        if adv.lemma not in ('nōn',):
            out.append(word(adv, 'adv'))
    if clause.copula:
        for role, np in clause.args:
            if role == 'prep':
                out.append(prepositional(np))
        complements = clause.role('complement')
        if complements:
            if gap is not None:
                out.append(noun_phrase(complements[0]) + ' olan')
            else:
                out.append(_copula(complements[0], clause, _person(clause)))
        else:
            owners = clause.role('recipient')
            if owners and subject is not None and owners[0].head is not None and owners[0].head.pos == 'pronoun':
                # 所有: 持ち主の属格 + 所有の接尾辞の付いた名詞 + var (Benim iki kedim var「私には猫が2匹いる」)
                owner = {'ego': 'meus', 'tū': 'tuus', 'is': 'suus'}.get(owners[0].head.lemma, 'suus')
                owner = 'noster' if owner == 'meus' and owners[0].number == 'pl' else \
                    'vester' if owner == 'tuus' and owners[0].number == 'pl' else owner
                from .frame import Lex
                owned = dataclasses.replace(subject, modifiers=[Lex(owner, 'adj')] + list(subject.modifiers))
                out = [noun_phrase(owned)]   # 属格の代名詞は所有の修飾語から (benim)
            out.append(('yoktu' if clause.negated else 'vardı') if clause.tense in ('perfect', 'imperfect')
                       else ('yok' if clause.negated else 'var'))
        return [w for w in out if w]
    for np in clause.role('recipient'):
        out.append(noun_phrase(np, 'Dat'))
    obj = (clause.role('object') or [None])[0]
    if obj is not None and gap != 'object':
        out.append(noun_phrase(obj, 'Acc'))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            out.append(prepositional(np, clause.voice == 'passive'))
            continue
        if np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
            out.append(WORDS[np.head.lemma])
            continue
        case = {'means': 'Dat' if np.animate else 'Ins', 'possessor': 'Gen', 'source': 'Abl'}.get(role, 'Loc')
        out.append(noun_phrase(np, case))
    out.append(verb_form(clause, gap, possessor))
    return [w for w in out if w]


def vocative(np):
    return noun_phrase(np)


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import split_address, chains_with_next
    parts = []
    chained = False
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        words = [', '.join(vocative(np) for np in group) + ',' for group in groups]
        for key in rest.connectives:
            if key in CONNECTIVES and k > 0 and not chained:
                words.append(CONNECTIVES[key])
        chain = chains_with_next(clauses, k)
        if chain:   # 同じ主語の続く動作は -ıp で次の節に (Kapıyı açıp içeri girdi)
            rest = dataclasses.replace(rest, subordinator='et')
        words += realize(rest, subordinate=k + 1 < len(clauses))
        text = ' '.join(w for w in words if w)
        parts.append(text + (' ' if chain else ', ') if k + 1 < len(clauses) else text)
        chained = chain
    text = ''.join(parts)
    return text[:1].upper() + text[1:] + '.'


# ----------------------------------------------------------------------
# 比較の表

CASE_HOW = {'Nom': '主格 (印なし)', 'Acc': '対格 -(y)ı (定の目的語)', 'Dat': '与格 -(y)a', 'Loc': '位格 -da',
            'Abl': '奪格 -dan', 'Gen': '属格 -(n)ın', 'Ins': '具格 -(y)la'}
PRO_DROP_HOW = '書かない (動詞の人称の語尾 -m・-n・-k … で分かる)'
PREDICATE_HOW = '語幹 + 否定 -ma + 時制 (-dı・-iyor・-acak) + 人称の語尾。受動 -ıl / -n (母音調和で形が変わる)'
COPULA_HOW = '補語 + 人称の語尾 (過去 -(y)dı、否定 değil)。動詞の無い文'
ADDRESS_HOW = '主格 (印なし)'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, '後置詞 tarafından (受動の動作主)'
        case, post = POSTPOSITIONS.get((np.prep.lemma, np.case), ('Loc', ''))
        return text, CASE_HOW.get(case, case) + (' + 後置詞 %s' % post if post else '')
    if role == 'subject':
        return noun_phrase(np), '主格 (印なし。動詞の前)'
    case = {'object': 'Acc', 'recipient': 'Dat', 'means': 'Dat' if np.animate else 'Ins', 'possessor': 'Gen',
            'address': 'Nom', 'source': 'Abl'}.get(role, 'Loc')
    return noun_phrase(np, case), CASE_HOW.get(case, case) if role != 'address' else ADDRESS_HOW


def compare_predicate(clause, reduced):
    if clause.copula:
        complements = clause.role('complement')
        if complements:
            return _copula(complements[0], clause, _person(clause)), COPULA_HOW
        return realize(reduced)[-1], COPULA_HOW
    return verb_form(clause), PREDICATE_HOW
