#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からモンゴル語 (ハルハ方言・キリル文字) の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)
#   語順: 主語 - 受け手 (与位格) - 目的語 (対格) - 後置詞句 - 動詞 (SOV)。動詞は人称で変わらない
#   接尾辞は母音調和で4通り (男性 а・о、女性 э・ө): 奪格 -аас / -ээс / -оос / -өөс、造格 -аар …、共同格 -тай / -тэй / -той
#   格: 属格 -ын / -ийн / -ы / -н、対格 -ыг / -ийг / -г、与位格 -д / -т、奪格、造格、共同格
#   動詞: 現在・未来 -на / -нэ / -но / -нө、過去 -сан / -сэн / -сон / -сөн、否定 -гүй (過去 -сангүй・現在 -хгүй)、
#     命令は語幹。繋辞は書かない (過去は байсан、否定は биш)
#   関係節: 分詞 (過去 -сан・現在 -дог / -даг・未来 -х) を名詞の前に (Батын бичсэн захиа)
#
import dataclasses

from . import transfer, english
from .frame import NP

BACK = 'аоуяёюы'
VOWELS = 'аэиоуөүяеёюы'
LONG_ENDINGS = ('аа', 'ээ', 'оо', 'өө', 'уу', 'үү', 'ай', 'эй', 'ой', 'уй', 'үй', 'ий', 'иа', 'ио')
PRONOUNS = {('ego', 'sg'): 'би', ('ego', 'pl'): 'бид', ('tū', 'sg'): 'чи', ('tū', 'pl'): 'та нар', ('is', 'sg'): 'тэр',
            ('is', 'pl'): 'тэд', ('hic', 'sg'): 'энэ', ('ille', 'sg'): 'тэр', ('quis', 'sg'): 'хэн', ('quid', 'sg'): 'юу',
            ('sē', 'sg'): 'өөрөө', ('sē', 'pl'): 'өөрсдөө'}
PRONOUN_CASES = {
    'би': {'Gen': 'миний', 'Acc': 'намайг', 'Dat': 'надад', 'Abl': 'надаас', 'Ins': 'надаар', 'Com': 'надтай'},
    'чи': {'Gen': 'чиний', 'Acc': 'чамайг', 'Dat': 'чамд', 'Abl': 'чамаас', 'Ins': 'чамаар', 'Com': 'чамтай'},
    'тэр': {'Gen': 'түүний', 'Acc': 'түүнийг', 'Dat': 'түүнд', 'Abl': 'түүнээс', 'Ins': 'түүгээр', 'Com': 'түүнтэй'},
    'бид': {'Gen': 'бидний', 'Acc': 'биднийг', 'Dat': 'бидэнд', 'Abl': 'биднээс', 'Com': 'бидэнтэй'},
    'тэд': {'Gen': 'тэдний', 'Acc': 'тэднийг', 'Dat': 'тэдэнд', 'Abl': 'тэднээс', 'Com': 'тэдэнтэй'},
    'энэ': {'Gen': 'үүний', 'Acc': 'үүнийг', 'Dat': 'үүнд', 'Abl': 'үүнээс', 'Com': 'үүнтэй'},
}
DETERMINERS = {'hic': 'энэ', 'hīc': 'энэ', 'iste': 'тэр', 'ille': 'тэр', 'is': 'тэр', 'omnis': 'бүх', 'alius': 'өөр',
               'tōtus': 'бүх', 'multus': 'олон'}
POSSESSIVES = {'meus': 'миний', 'tuus': 'чиний', 'suus': 'өөрийн', 'noster': 'манай', 'vester': 'та нарын'}
NUMERALS = {'ūnus': 'нэг', 'duo': 'хоёр', 'trēs': 'гурван', 'quattuor': 'дөрвөн', 'quīnque': 'таван', 'decem': 'арван'}
# ラテン語の前置詞 + 格 → (格, 後置詞)
POSTPOSITIONS = {('in', 'Abl'): ('Dat', ''), ('in', 'Acc'): ('Dir', ''), ('ad', 'Acc'): ('Dir', ''),
                 ('ex', 'Abl'): ('Abl', ''), ('ē', 'Abl'): ('Abl', ''), ('ab', 'Abl'): ('Abl', ''), ('ā', 'Abl'): ('Abl', ''),
                 ('cum', 'Abl'): ('Com', ''), ('dē', 'Abl'): ('Gen', 'тухай'), ('sine', 'Abl'): ('Nom', 'гүй'),
                 ('propter', 'Acc'): ('Gen', 'учир'), ('post', 'Acc'): ('Gen', 'дараа'), ('ante', 'Acc'): ('Gen', 'өмнө'),
                 ('sub', 'Abl'): ('Gen', 'доор'), ('super', 'Acc'): ('Gen', 'дээр'), ('prō', 'Abl'): ('Gen', 'төлөө'),
                 ('apud', 'Acc'): ('Gen', 'дэргэд'), ('inter', 'Acc'): ('Gen', 'дунд'), ('per', 'Acc'): ('Ins', '')}
CONNECTIVES = {'et': 'бас', 'que': 'бас', 'atque': 'бас', 'sed': 'гэвч', 'at': 'гэвч', 'autem': 'харин', 'enim': 'учир нь',
               'nam': 'учир нь', 'igitur': 'тиймээс', 'itaque': 'тиймээс', 'tamen': 'гэсэн ч', 'tum': 'тэгээд',
               'deinde': 'дараа нь', 'aut': 'эсвэл', 'vel': 'эсвэл'}
WORDS = {'semper': 'үргэлж', 'saepe': 'байнга', 'iam': 'аль хэдийн', 'nunc': 'одоо', 'hodiē': 'өнөөдөр',
         'crās': 'маргааш', 'heri': 'өчигдөр', 'ibi': 'тэнд', 'hīc': 'энд', 'etiam': 'бас', 'quoque': 'бас',
         'valdē': 'маш', 'magnopere': 'маш', 'statim': 'даруй', 'mox': 'удахгүй', 'iterum': 'дахин', 'bene': 'сайн',
         'numquam': 'хэзээ ч', 'posteā': 'дараа нь'}


# ----------------------------------------------------------------------
# 母音調和

def harmony(word):
    """母音調和の組: 'а' (男性)・'о' (男性で о のみ)・'э' (女性)・'ө' (女性で ө)"""
    vowels = [c for c in word.lower() if c in 'аэоөуүяеёю']
    if not vowels:
        return 'э'
    first = vowels[0]
    if any(v in 'аяуюё' for v in vowels) or first == 'а':
        return 'о' if first == 'о' and not any(v in 'аяу' for v in vowels) else 'а'
    if first == 'о':
        return 'о'
    if first == 'ө':
        return 'ө'
    return 'э'


def _ends_vowel(word):
    return word[-1:].lower() in VOWELS


def _long_end(word):
    return word.lower().endswith(LONG_ENDINGS)


def case_form(word, case):
    """名詞 + 格の接尾辞"""
    if case in ('Nom', '', None):
        return word
    h = harmony(word)
    long_v = h + h   # аа・ээ・оо・өө
    low = word.lower()
    if case == 'Gen':
        if _long_end(word):
            return word + 'гийн'
        if low.endswith('н'):
            return word + ('ы' if h in 'ао' else 'ий')
        if _ends_vowel(word):
            return word + 'гийн' if low.endswith(('и', 'ы')) else word + 'ны' if h in 'ао' else word + 'ний'
        return word + ('ийн' if h in 'эө' or low.endswith(('ж', 'ч', 'ш', 'г', 'ь', 'к')) else 'ын')
    if case == 'Acc':
        if _ends_vowel(word) or low.endswith('й'):
            return word + 'г'
        return word + ('ийг' if h in 'эө' or low.endswith(('ж', 'ч', 'ш', 'г', 'ь', 'к')) else 'ыг')
    if case == 'Dat':
        if low.endswith(('ж', 'ч', 'ш')):
            return word + 'ид'                      # ээжид
        if low.endswith(('т', 'д')):
            return word + h + 'д'                   # хотод
        if low.endswith(('г', 'р', 'с')):
            return word + 'т'                       # гэрт・Улаанбаатарт
        return word + 'д'
    if case in ('Abl', 'Ins'):
        tail = 'с' if case == 'Abl' else 'р'
        if _long_end(word):
            return word + 'г' + long_v + tail
        return word + long_v + tail
    if case == 'Com':
        return word + {'а': 'тай', 'о': 'той', 'э': 'тэй', 'ө': 'тэй'}[h]
    if case == 'Dir':
        return word + (' руу' if h in 'ао' else ' рүү')
    return word


# ----------------------------------------------------------------------
# 動詞

def stem_of(lemma):
    """動詞の見出し (-х) → 語幹 (өгөх → өг、унших → унш、уух → уу)"""
    stem = lemma[:-1] if lemma.endswith('х') else lemma
    if len(stem) >= 3 and stem[-1] in 'аэоө' and stem[-2] not in VOWELS:
        return stem[:-1]   # 語幹の後ろの短い母音 (өгө → өг、явa → яв)
    if len(stem) >= 3 and stem[-1] == 'и' and stem[-2] in 'жчш':
        return stem[:-1]   # ж・ч・ш の後ろの и (унши → унш)
    return stem


def _joint(stem, ending):
    """語幹と語尾のつなぎの母音: ж・ч・ш の後ろは и (уншина)、子音が2つ続く語幹は母音調和の母音 (хайрлана)"""
    if stem[-1:] in 'жчш':
        return 'и'
    if len(stem) >= 2 and stem[-1] not in VOWELS + 'йь' and stem[-2] not in VOWELS + 'йь' and stem[-1] in 'лмнр' + 'гдвбз':
        return harmony(stem)
    return ''


def conjugate(lemma, tense='present', negated=False, mood='indicative', passive=False):
    stem = stem_of(lemma)
    if passive:
        stem = stem + {'а': 'агд', 'о': 'огд', 'э': 'эгд', 'ө': 'өгд'}[harmony(stem)]   # 受動 -гд (авах → авагдах)
    h = harmony(stem)
    if mood == 'imperative':
        if negated:
            return 'битгий ' + stem
        return stem if not stem.endswith(('ж', 'ч', 'ш')) else stem + 'и'
    if tense in ('perfect', 'past-perfect', 'imperfect'):
        form = stem + ('' if stem[-1:] in 'жчш' else _joint(stem, 'с')) + {'а': 'сан', 'о': 'сон', 'э': 'сэн', 'ө': 'сөн'}[h]
        return form + 'гүй' if negated else form
    if negated:
        return (lemma if not passive else stem + 'х') + 'гүй'   # 未来分詞 + 否定 (үзэхгүй「見ない」)
    return stem + _joint(stem, 'н') + {'а': 'на', 'о': 'но', 'э': 'нэ', 'ө': 'нө'}[h]


def participle(lemma, tense='perfect', negated=False):
    stem = stem_of(lemma)
    h = harmony(stem)
    if tense in ('perfect', 'past-perfect', 'imperfect'):
        form = stem + ('' if stem[-1:] in 'жчш' else _joint(stem, 'с')) + {'а': 'сан', 'о': 'сон', 'э': 'сэн', 'ө': 'сөн'}[h]
    elif tense == 'future':
        form = lemma
    else:
        form = stem + ('и' if stem[-1:] in 'жчш' else _joint(stem, 'д')) + {'а': 'даг', 'о': 'дог', 'э': 'дэг', 'ө': 'дөг'}[h]
    return form + 'гүй' if negated else form


# 従属節の副動詞 (ラテン語の従属節の接続詞 → モンゴル語の動詞の形)
SUBORDINATORS = ('et', 'cum', 'ubi', 'simul', 'postquam', 'dum', 'sī', 'quod', 'quia', 'quoniam', 'quamquam', 'etsī',
                 'priusquam', 'antequam', 'ut', 'dōnec')


def converb(lemma, key, negated=False, tense='perfect'):
    """従属節の動詞の形: ирэхэд・ирсний дараа・ирэх үед・ирвэл・ирсэн учраас・ирэхээс өмнө・ирэхийн тулд・иртэл"""
    if negated:
        return lemma + 'гүй ' + converb('байх', key, tense=tense)   # ирэхгүй байхад
    stem = stem_of(lemma)
    h = harmony(stem)
    long_ = h * 2
    if key == 'et':   # 続く動作 -аад (ирээд・уншаад・суугаад)
        return stem + ('г' if _long_end(stem) else '') + long_ + 'д'
    if key in ('cum', 'ubi', 'simul'):
        return lemma + h + 'д'
    if key == 'postquam':
        past = participle(lemma, 'perfect')
        return past[:-2] + ('ны' if h in 'ао' else 'ний') + ' дараа'
    if key == 'dum':
        return lemma + ' үед'   # 主語が違ってもよい (Хүү унтах үед, охин уншина)
    if key == 'sī':
        return stem + ('б' if stem.endswith('в') else 'в') + h + 'л'   # уншвал・явбал
    past = tense in ('perfect', 'past-perfect', 'imperfect')
    if key in ('quod', 'quia', 'quoniam'):
        return participle(lemma, 'perfect' if past else 'present') + ' учраас'   # дуулсан / дуулдаг учраас
    if key in ('quamquam', 'etsī'):
        return participle(lemma, 'perfect' if past else 'present') + ' ч гэсэн'
    if key in ('priusquam', 'antequam'):
        return lemma + long_ + 'с өмнө'
    if key == 'ut':
        return lemma + ('ын' if h in 'ао' else 'ийн') + ' тулд'
    if key == 'dōnec':
        cluster = len(stem) >= 2 and stem[-1] not in VOWELS + 'йь' and stem[-2] not in VOWELS + 'йь'
        return stem + ('и' if stem[-1:] in 'жчш' else h if cluster else '') + 'т' + h + 'л'   # уншитал・унтатал
    return None


# ----------------------------------------------------------------------
# 語

def available():
    return transfer.available('mn')


def to_mongolian(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'mn':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'mn')
        if found:
            return found[0]
        return cyrillic_name(lex.lemma)
    target = transfer.best(lex, 'mn', pos)
    return target.lemma if target else None


CYRILLIC = {'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'э', 'f': 'ф', 'g': 'г', 'h': 'х', 'i': 'и', 'j': 'й', 'k': 'к',
            'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'v': 'в',
            'w': 'в', 'x': 'кс', 'y': 'и', 'z': 'з'}


def cyrillic_name(lemma):
    """ラテン語の名前をキリル文字に (語尾はそのまま: Mārcus → Маркус)"""
    import unicodedata
    plain = ''.join(c for c in unicodedata.normalize('NFD', lemma) if not unicodedata.combining(c))
    plain = plain.replace('ae', 'e').replace('ph', 'f').replace('th', 't').replace('qu', 'кв').replace('ch', 'х')
    out = ''.join(CYRILLIC.get(c.lower(), c) for c in plain)
    return out[:1].upper() + out[1:]


def word(lex, pos=None):
    found = to_mongolian(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


def noun_phrase(np, case='Nom'):
    if np.members:
        parts = [noun_phrase(m) for m in np.members]
        conj = ' эсвэл ' if np.conj in ('aut', 'vel') else ' ба '
        return conj.join(parts[:-1] + [noun_phrase(np.members[-1], case)])
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun':
        key = (head.lemma, 'pl' if np.number == 'pl' else 'sg')
        pron = PRONOUNS.get(key) or PRONOUNS.get((head.lemma, 'sg')) or word(head)
        return PRONOUN_CASES.get(pron, {}).get(case) or case_form(pron, case)
    before = [noun_phrase(g, 'Gen') for g in np.genitives]
    before += [relative_clause(r) for r in np.relatives]
    for m in np.modifiers:
        if isinstance(m, NP):
            before.append(' '.join(_modifier(x.head) for x in m.members))
            continue
        before.append(_modifier(m))
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    counted = any(not isinstance(m, NP) and m.lemma in NUMERALS and m.lemma != 'ūnus' for m in np.modifiers)
    if np.number == 'pl' and np.animate and not counted:   # 数詞の後ろは複数の語尾を付けない (хоёр муур)
        noun += 'ууд' if harmony(noun) in 'ао' else 'үүд'
    return ' '.join(x for x in before + [case_form(noun, case)] if x)


def _modifier(lex):
    for table in (DETERMINERS, POSSESSIVES, NUMERALS):
        if lex.lemma in table and lex.lang in ('', 'la'):
            return table[lex.lemma]
    return word(lex, 'adj') or '[%s]' % english.word(lex)


def relative_clause(r):
    return ' '.join(realize(r, gap=r.gap or 'subject'))


def prepositional(np, passive=False):
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        text = noun_phrase(inner, 'Ins')
        return text
    case, post = POSTPOSITIONS.get((np.prep.lemma, np.case), ('Dat', '')) if np.prep is not None else ('Dat', '')
    text = noun_phrase(inner, case)
    if not text:
        return ''
    return text + (' ' + post if post else '')


def verb_form(clause, gap=None):
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return lemma
    if gap is not None:
        return participle(lemma, clause.tense, clause.negated)
    return conjugate(lemma, clause.tense, clause.negated, clause.mood, clause.voice == 'passive')


def _copula(complement, clause):
    text = noun_phrase(complement)
    past = clause.tense in ('perfect', 'past-perfect', 'imperfect')
    if clause.negated:
        return text + (' биш байсан' if past else ' биш')
    return text + (' байсан' if past else '')


def realize(clause, gap=None, subordinate=False):
    """節の語の列。subordinate なら従属節: 動詞を副動詞に (Гэртээ ирэхэд・Бороо орвол)"""
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    if subordinate and gap is None and not clause.copula and clause.subordinator in SUBORDINATORS:
        out = realize(dataclasses.replace(clause, subordinator=''))
        lemma = word(clause.verb, 'verb')
        if out and lemma and not lemma.startswith('[') and clause.voice != 'passive':
            form = converb(lemma, clause.subordinator, clause.negated, clause.tense)
            if form:
                return out[:-1] + [form]
        return out
    subject = (clause.role('subject') or [None])[0]
    out = []
    if subject is not None and gap != 'subject':
        out.append(noun_phrase(subject, 'Gen' if gap is not None else 'Nom'))   # 関係節の主語は属格 (Батын бичсэн)
    for adv in clause.adverbs:
        if adv.lemma not in ('nōn',):
            out.append(word(adv, 'adv'))
    if clause.copula:
        for role, np in clause.args:
            if role == 'prep':
                out.append(prepositional(np))
        complements = clause.role('complement')
        if complements:
            out.append(_copula(complements[0], clause) if gap is None else noun_phrase(complements[0]))
        else:
            out.append('байсан' if clause.tense in ('perfect', 'imperfect') else 'байна')
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
        case = {'means': 'Dat' if np.animate else 'Ins', 'possessor': 'Gen', 'source': 'Abl'}.get(role, 'Dat')
        out.append(noun_phrase(np, case))
    out.append(verb_form(clause, gap))
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
        if chain:   # 同じ主語の続く動作は -аад で次の節に (Гэрт ирээд хоол идсэн)
            rest = dataclasses.replace(rest, subordinator='et')
        words += realize(rest, subordinate=k + 1 < len(clauses))
        text = ' '.join(w for w in words if w)
        parts.append(text + (' ' if chain else ', ') if k + 1 < len(clauses) else text)
        chained = chain
    text = ''.join(parts)
    return text[:1].upper() + text[1:] + '.'


# ----------------------------------------------------------------------
# 比較の表

CASE_HOW = {'Nom': '主格 (印なし)', 'Acc': '対格 -ыг / -ийг / -г', 'Dat': '与位格 -д / -т', 'Abl': '奪格 -аас (母音調和)',
            'Gen': '属格 -ын / -ийн', 'Ins': '造格 -аар (母音調和)', 'Com': '共同格 -тай', 'Dir': '方向格 руу / рүү'}
PRO_DROP_HOW = '書かない (動詞は人称で変わらないので文脈で)'
PREDICATE_HOW = '語幹 + 時制の語尾 (現在 -на・過去 -сан。母音調和で4通り)、否定 -гүй、受動 -гд'
COPULA_HOW = '繋辞を書かない (名詞文。過去は байсан、否定は биш)'
ADDRESS_HOW = '主格 (印なし)'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, '造格 (受動の動作主)'
        case, post = POSTPOSITIONS.get((np.prep.lemma, np.case), ('Dat', ''))
        return text, CASE_HOW.get(case, case) + (' + 後置詞 %s' % post if post else '')
    if role == 'subject':
        return noun_phrase(np), '主格 (印なし)'
    case = {'object': 'Acc', 'recipient': 'Dat', 'means': 'Dat' if np.animate else 'Ins', 'possessor': 'Gen',
            'address': 'Nom', 'source': 'Abl'}.get(role, 'Dat')
    return noun_phrase(np, case), CASE_HOW.get(case, case) if role != 'address' else ADDRESS_HOW


def compare_predicate(clause, reduced):
    if clause.copula:
        complements = clause.role('complement')
        if complements:
            return _copula(complements[0], clause), COPULA_HOW
        return realize(reduced)[-1], COPULA_HOW
    return verb_form(clause), PREDICATE_HOW
