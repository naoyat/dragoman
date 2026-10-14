#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からフィンランド語の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)。名詞・形容詞・動詞の語形は辞書
#     (fi/wiktionary.sqlite の語形の表。Wiktionary の変化表) から
#   語順: 主語 - 動詞 - 目的語 - 場所の句 (SVO)。1・2人称の主語の代名詞は書かない (動詞の人称の語尾で分かる)
#   格: 目的語は全体なら属格 (単数: luki kirjan)・主格 (複数)、否定の文と感情・継続の動詞 (rakastaa・odottaa) は分格。
#     受け手は向格 -lle、場所は内格 -ssa、方向は入格、起点は出格 -sta、手段は所格 -lla。前置詞は場所の格か後置詞
#     (kanssa「〜と一緒に」・jälkeen「〜の後で」…。属格の後ろ)
#   動詞: 現在・過去・完了 (olla + 過去分詞)・否定 (否定動詞 ei + 本動詞)・受動 (非人称の受動 luetaan) は語形の表から
#   形容詞は名詞と同じ格・数 (kaunis ruusu・kaunista ruusua)。繋辞 olla の補語は主格 (複数の主語なら分格の複数)
#
import dataclasses
import functools
import os
import sqlite3

from dragoman.core import paths
from . import transfer, english
from .frame import NP

CASE_TAGS = {'Nom': 'nominative', 'Gen': 'genitive', 'Par': 'partitive', 'Ine': 'inessive', 'Ela': 'elative',
             'Ill': 'illative', 'Ade': 'adessive', 'Abl': 'ablative', 'All': 'allative', 'Ess': 'essive',
             'Tra': 'translative', 'Abe': 'abessive', 'Com': 'comitative'}
PRONOUNS = {('ego', 'sg'): 'minä', ('ego', 'pl'): 'me', ('tū', 'sg'): 'sinä', ('tū', 'pl'): 'te', ('is', 'sg'): 'hän',
            ('is', 'pl'): 'he', ('hic', 'sg'): 'tämä', ('ille', 'sg'): 'tuo', ('quis', 'sg'): 'kuka', ('quid', 'sg'): 'mikä',
            ('sē', 'sg'): 'itse'}
PRONOUN_CASES = {
    'minä': {'Acc': 'minut', 'Gen': 'minun', 'Par': 'minua', 'All': 'minulle', 'Ade': 'minulla', 'Abl': 'minulta', 'Ine': 'minussa', 'Ela': 'minusta', 'Ill': 'minuun'},
    'sinä': {'Acc': 'sinut', 'Gen': 'sinun', 'Par': 'sinua', 'All': 'sinulle', 'Ade': 'sinulla', 'Abl': 'sinulta', 'Ine': 'sinussa', 'Ela': 'sinusta', 'Ill': 'sinuun'},
    'hän': {'Acc': 'hänet', 'Gen': 'hänen', 'Par': 'häntä', 'All': 'hänelle', 'Ade': 'hänellä', 'Abl': 'häneltä', 'Ine': 'hänessä', 'Ela': 'hänestä', 'Ill': 'häneen'},
    'me': {'Acc': 'meidät', 'Gen': 'meidän', 'Par': 'meitä', 'All': 'meille', 'Ade': 'meillä', 'Abl': 'meiltä'},
    'te': {'Acc': 'teidät', 'Gen': 'teidän', 'Par': 'teitä', 'All': 'teille', 'Ade': 'teillä', 'Abl': 'teiltä'},
    'he': {'Acc': 'heidät', 'Gen': 'heidän', 'Par': 'heitä', 'All': 'heille', 'Ade': 'heillä', 'Abl': 'heiltä'},
    'tämä': {'Acc': 'tämän', 'Gen': 'tämän', 'Par': 'tätä', 'All': 'tälle', 'Ine': 'tässä'},
}
RELATIVE = {'Nom': 'joka', 'Acc': 'jonka', 'Gen': 'jonka', 'Par': 'jota', 'All': 'jolle', 'Ine': 'jossa', 'Ade': 'jolla'}
RELATIVE_PL = {'Nom': 'jotka', 'Acc': 'jotka', 'Gen': 'joiden', 'Par': 'joita', 'All': 'joille', 'Ine': 'joissa'}
DETERMINERS = {'hic': 'tämä', 'hīc': 'tämä', 'iste': 'se', 'ille': 'tuo', 'is': 'se', 'omnis': 'kaikki', 'alius': 'toinen',
               'tōtus': 'koko', 'multus': 'moni'}
POSSESSIVES = {'meus': 'minun', 'tuus': 'sinun', 'suus': 'hänen', 'noster': 'meidän', 'vester': 'teidän'}
NUMERALS = {'ūnus': 'yksi', 'duo': 'kaksi', 'trēs': 'kolme', 'quattuor': 'neljä', 'quīnque': 'viisi', 'decem': 'kymmenen'}
# ラテン語の前置詞 + 格 → (格, 後置詞)
PREPOSITIONS = {('in', 'Abl'): ('Ine', ''), ('in', 'Acc'): ('Ill', ''), ('ad', 'Acc'): ('Ill', ''), ('ex', 'Abl'): ('Ela', ''),
                ('ē', 'Abl'): ('Ela', ''), ('ab', 'Abl'): ('Abl', ''), ('ā', 'Abl'): ('Abl', ''), ('cum', 'Abl'): ('Gen', 'kanssa'),
                ('dē', 'Abl'): ('Ela', ''), ('sine', 'Abl'): ('Abe', ''), ('per', 'Acc'): ('Gen', 'kautta'),
                ('propter', 'Acc'): ('Gen', 'takia'), ('ob', 'Acc'): ('Gen', 'takia'), ('post', 'Acc'): ('Gen', 'jälkeen'),
                ('ante', 'Acc'): ('Gen', 'edessä'), ('sub', 'Abl'): ('Gen', 'alla'), ('super', 'Acc'): ('Gen', 'päällä'),
                ('prō', 'Abl'): ('Gen', 'puolesta'), ('apud', 'Acc'): ('Gen', 'luona'), ('inter', 'Acc'): ('Gen', 'välissä'),
                ('contrā', 'Acc'): ('Par', 'vastaan'), ('prope', 'Acc'): ('Gen', 'lähellä')}
CONNECTIVES = {'et': 'ja', 'que': 'ja', 'atque': 'ja', 'ac': 'ja', 'sed': 'mutta', 'at': 'mutta', 'autem': 'mutta',
               'enim': 'sillä', 'nam': 'sillä', 'igitur': 'siksi', 'itaque': 'siksi', 'tamen': 'kuitenkin', 'tum': 'sitten',
               'deinde': 'sitten', 'aut': 'tai', 'vel': 'tai'}
WORDS = {'semper': 'aina', 'saepe': 'usein', 'iam': 'jo', 'nunc': 'nyt', 'hodiē': 'tänään', 'crās': 'huomenna',
         'heri': 'eilen', 'ibi': 'siellä', 'hīc': 'täällä', 'etiam': 'myös', 'quoque': 'myös', 'valdē': 'hyvin',
         'magnopere': 'hyvin', 'statim': 'heti', 'mox': 'pian', 'tandem': 'vihdoin', 'iterum': 'taas', 'numquam': 'ei koskaan',
         'bene': 'hyvin', 'posteā': 'myöhemmin', 'diū': 'kauan'}
PARTITIVE_VERBS = {'rakastaa', 'odottaa', 'auttaa', 'ajatella', 'etsiä', 'kiittää', 'pelätä', 'kuunnella', 'katsoa',
                   'kunnioittaa', 'vihata', 'koskettaa', 'palvella', 'seurata'}
PERSON_TAGS = {(1, 'sg'): ('first-person', 'singular'), (2, 'sg'): ('second-person', 'singular'),
               (3, 'sg'): ('third-person', 'singular'), (1, 'pl'): ('first-person', 'plural'),
               (2, 'pl'): ('second-person', 'plural'), (3, 'pl'): ('third-person', 'plural')}
OLLA = {('present', 1, 'sg'): 'olen', ('present', 2, 'sg'): 'olet', ('present', 3, 'sg'): 'on', ('present', 1, 'pl'): 'olemme',
        ('present', 2, 'pl'): 'olette', ('present', 3, 'pl'): 'ovat', ('past', 1, 'sg'): 'olin', ('past', 2, 'sg'): 'olit',
        ('past', 3, 'sg'): 'oli', ('past', 1, 'pl'): 'olimme', ('past', 2, 'pl'): 'olitte', ('past', 3, 'pl'): 'olivat'}
NEGATIVE = {(1, 'sg'): 'en', (2, 'sg'): 'et', (3, 'sg'): 'ei', (1, 'pl'): 'emme', (2, 'pl'): 'ette', (3, 'pl'): 'eivät'}


@functools.lru_cache(maxsize=1)
def _db():
    path = paths.data('fi', 'wiktionary.sqlite')
    if not os.path.exists(path):
        return None
    db = sqlite3.connect(path, check_same_thread=False)
    has_forms = db.execute("SELECT 1 FROM sqlite_master WHERE name = 'forms'").fetchone()
    return db if has_forms else None


@functools.lru_cache(maxsize=50000)
def _forms(lemma, pos):
    db = _db()
    if db is None:
        return ()
    return tuple((form, frozenset(tags.split(','))) for form, tags in
                 db.execute('SELECT form, tags FROM forms WHERE lemma = ? AND pos = ?', (lemma, pos)))


def find_form(lemma, pos, wanted, avoid=(), spaced=False):
    wanted, avoid = set(wanted), set(avoid)
    for form, tags in _forms(lemma, pos):
        if wanted <= tags and not tags & avoid and (spaced or ' ' not in form):
            return form
    return None


def case_form(word, case, number='sg', pos='noun'):
    """名詞・形容詞の格の形 (語形の表から。無ければ見出しのまま)"""
    if case == 'Acc':   # 全体の目的語: 単数は属格の形、複数は主格の形
        case = 'Gen' if number == 'sg' else 'Nom'
    if case == 'Nom' and number == 'sg':
        return word
    number_tag = 'singular' if number == 'sg' else 'plural'
    form = find_form(word, pos, (CASE_TAGS.get(case, 'nominative'), number_tag), avoid=('accusative',)) or \
        find_form(word, pos, (CASE_TAGS.get(case, 'nominative'), number_tag))
    if form is None and pos == 'adj':
        form = find_form(word, 'noun', (CASE_TAGS.get(case, 'nominative'), number_tag))
    if form is None and number == 'sg' and word[:1].isupper() and word.isalpha():
        form = name_case(word, case)
    return form or word


# 辞書に無い名前の単数の格語尾 (Liisa → Liisaa・Liisan、Matti → Mattia・Matin、Gretel → Greteliä)。
# 閉じた音節の格では重子音を短くする (子音階程交替の量の交替だけ)
NAME_ENDINGS = {'Gen': ('n', True), 'Par': ('a', False), 'Ine': ('ssa', True), 'Ela': ('sta', True), 'Ill': ('+n', False),
                'Ade': ('lla', True), 'Abl': ('lta', True), 'All': ('lle', True), 'Ess': ('na', False), 'Tra': ('ksi', True)}


def name_case(word, case):
    if case not in NAME_ENDINGS:
        return None
    ending, weak = NAME_ENDINGS[case]
    if word[-1:] not in 'aeiouyäö':
        word += 'i'   # 子音で終わる名前 (Gretel → Gretelin・Greteliä)
    back = any(c in BACK_VOWELS for c in word.lower())
    if weak and len(word) > 3 and word[-3] == word[-2] and word[-2] in 'kpt':
        word = word[:-2] + word[-1]   # Matti → Matin
    if ending == '+n':
        return word + word[-1] + 'n'   # Liisa → Liisaan
    if ending == 'a' and len(word) > 2 and word[-1] == word[-2]:
        ending = 'ta'
    return word + (ending if back else ending.replace('a', 'ä'))


POSSESSOR_PERSONS = {'meus': (1, 'sg'), 'tuus': (2, 'sg'), 'suus': (3, 'sg'), 'noster': (1, 'pl'), 'vester': (2, 'pl')}
POSSESSIVE_SUFFIXES = {(1, 'sg'): 'ni', (2, 'sg'): 'si', (1, 'pl'): 'mme', (2, 'pl'): 'nne'}
BACK_VOWELS = 'aou'


def possessive(word, case, number, person, owner_number):
    """所有の接尾辞 (kirja → kirjani・kirjasi・kirjansa、talossa → talossani・talossaan)"""
    if case in ('Nom', 'Acc', 'Gen'):
        base = case_form(word, 'Gen', number)
        base = base[:-1] if base.endswith('n') else base   # 属格の -n を外した語幹 (talon → talo、talojen → taloje)
        if number == 'pl' and case == 'Nom':
            base = case_form(word, 'Gen', 'sg')[:-1]
    else:
        base = case_form(word, case, number)
    back = any(v in base for v in BACK_VOWELS) and not any(v in base[-3:] for v in 'äöy')
    if base.endswith('n') and case == 'Ill':
        base = base[:-1]   # 入格の -n は落ちる (taloon → talooni・taloonsa)
        if (person, owner_number) not in POSSESSIVE_SUFFIXES:
            return base + ('nsa' if any(v in base for v in BACK_VOWELS) else 'nsä')
    if (person, owner_number) in POSSESSIVE_SUFFIXES:
        return base + POSSESSIVE_SUFFIXES[(person, owner_number)]
    if base[-1:] in 'aeiouyäö' and case not in ('Nom', 'Acc', 'Gen'):
        return base + base[-1] + 'n'   # 3人称: 母音で終わる格は母音を延ばして -n (talossaan)
    return base + ('nsa' if back else 'nsä')


# ----------------------------------------------------------------------
# 語

def available():
    return transfer.available('fi') and _db() is not None


def to_finnish(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'fi':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'fi')
        if found:
            return found[0]
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', lex.lemma) if not unicodedata.combining(c))
    target = transfer.best(lex, 'fi', pos)
    return target.lemma if target else None


def word(lex, pos=None):
    found = to_finnish(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


def noun_phrase(np, case='Nom'):
    if np.members:
        parts = [noun_phrase(m, case) for m in np.members]
        conj = ' tai ' if np.conj in ('aut', 'vel') else ' ja '
        return ', '.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
    head = np.head
    if head is None:
        return ''
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.pos == 'pronoun':
        pron = PRONOUNS.get((head.lemma, number)) or PRONOUNS.get((head.lemma, 'sg')) or word(head)
        if case in ('Nom',):
            return pron
        return PRONOUN_CASES.get(pron, {}).get(case) or case_form(pron, case, number, 'pronoun')
    proper = head.proper
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    before = []
    for g in np.genitives:
        before.append(noun_phrase(g, 'Gen'))
    for m in np.modifiers:
        if isinstance(m, NP):
            before.append(' ja '.join(_modifier(x.head, case, number) for x in m.members))
            continue
        before.append(_modifier(m, case, number))
    counted = case == 'Nom' and any(isinstance(m, type(head)) and (m.lemma in NUMERALS and m.lemma != 'ūnus' or
                                                                   m.lemma in NUMERALS.values() and m.lemma != 'yksi')
                                    for m in np.modifiers)
    if counted:   # 数詞の後ろの名詞は分格の単数 (kaksi kissaa)
        head_form = case_form(noun, 'Par', 'sg')
    else:
        head_form = noun if proper and case == 'Nom' else case_form(noun, case, number,
                                                                     'adj' if head.pos in ('adj', 'participle') else 'noun')
    owners = [m for m in np.modifiers if not isinstance(m, NP) and m.lemma in POSSESSOR_PERSONS and m.lang in ('', 'la')]
    if owners and not proper:   # 所有の接尾辞 (minun kirjani。3人称の再帰 suus は接尾辞だけ: kirjansa)
        person, owner_number = POSSESSOR_PERSONS[owners[0].lemma]
        head_form = possessive(noun, case, number, person, owner_number)
        if owners[0].lemma == 'suus':
            before = [b for b in before if b != POSSESSIVES['suus']]
    text = ' '.join(x for x in before + [head_form] if x)
    for r in np.relatives:
        text += ', ' + relative_clause(r, number) + ','
    return text


def _modifier(lex, case, number):
    if lex.lemma in DETERMINERS and lex.lang in ('', 'la'):
        det = DETERMINERS[lex.lemma]
        return PRONOUN_CASES.get(det, {}).get(case) or case_form(det, case, number, 'pronoun')
    if lex.lemma in POSSESSIVES and lex.lang in ('', 'la'):
        return POSSESSIVES[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    adj = word(lex, 'adj')
    if not adj or adj.startswith('['):
        return adj
    return case_form(adj, case, number, 'adj')


def relative_clause(r, number):
    case = {'subject': 'Nom', 'object': 'Acc', 'recipient': 'All', 'possessor': 'Gen'}.get(r.gap or 'subject', 'Nom')
    pronoun = (RELATIVE_PL if number == 'pl' else RELATIVE).get(case, 'joka')
    return ' '.join([pronoun] + realize(r, gap=r.gap or 'subject'))


def prepositional(np, passive=False):
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        return ''   # 非人称の受動は動作主を書かない
    case, post = PREPOSITIONS.get((np.prep.lemma, np.case), ('Ine', '')) if np.prep is not None else ('Ine', '')
    text = noun_phrase(inner, case)
    return (text + ' ' + post).strip() if text else ''


# ----------------------------------------------------------------------
# 動詞

def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            subject.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[subject.head.lemma], subject.number or 'sg'
    if subject is not None:
        return 3, 'pl' if subject.members or subject.number == 'pl' else 'sg'
    return clause.person, clause.number


def verb_form(clause, person, number):
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return lemma
    tense = 'past' if clause.tense in ('perfect', 'imperfect') else 'present'
    if clause.mood == 'imperative':
        form = find_form(lemma, 'verb', ('imperative', 'second-person', 'singular' if number == 'sg' else 'plural'))
        return ('älä ' + (form or lemma)) if clause.negated else (form or lemma)
    if clause.voice == 'passive':
        tags = ('indicative', 'passive', tense) + (('negative',) if clause.negated else ())
        form = find_form(lemma, 'verb', tags, avoid=() if clause.negated else ('negative',), spaced=True)
        return form or lemma
    if clause.tense == 'past-perfect':
        tags = ('indicative',) + PERSON_TAGS[(person, number)]
        form = find_form(lemma, 'verb', tags + (('negative',) if clause.negated else ()),
                         avoid=('present', 'past', 'perfect') + (() if clause.negated else ('negative',)), spaced=True)
        if form:
            return form
    if clause.tense == 'future':   # 未来の形は無い: 現在形で
        tense = 'present'
    tags = ('indicative', tense) + PERSON_TAGS[(person, number)] + (('negative',) if clause.negated else ())
    form = find_form(lemma, 'verb', tags, avoid=() if clause.negated else ('negative',), spaced=clause.negated)
    if form is None and clause.negated:
        return NEGATIVE[(person, number)] + ' ' + lemma
    return form or lemma


def _object_case(clause, obj):
    lemma = word(clause.verb, 'verb')
    if clause.negated or lemma in PARTITIVE_VERBS:
        return 'Par'
    return 'Acc'


def _copula(clause, complement, person, number):
    tense = 'past' if clause.tense in ('perfect', 'imperfect', 'past-perfect') else 'present'
    verb = OLLA[(tense, person, number)]
    if clause.negated:
        verb = NEGATIVE[(person, number)] + (' ole' if tense == 'present' else (' ollut' if number == 'sg' else ' olleet'))
    if complement is None:
        return verb, ''
    adjective = complement.head is not None and complement.head.pos in ('adj', 'participle') or \
        complement.members and all(m.head is not None and m.head.pos in ('adj', 'participle') for m in complement.members)
    case = 'Par' if number == 'pl' and adjective else 'Nom'   # Ruusut ovat kauniita (複数の主語の形容詞は分格の複数)
    return verb, noun_phrase(dataclasses.replace(complement, number=number if adjective else complement.number), case)


def realize(clause, gap=None):
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    person, number = _person(clause)
    subject = (clause.role('subject') or [None])[0]
    head = []
    if subject is not None and gap != 'subject' and not (subject.head is not None and subject.head.pos == 'pronoun'
                                                         and subject.head.lemma in ('ego', 'tū') and gap is None):
        head.append(noun_phrase(subject, 'Nom'))
    rest = [word(adv, 'adv') for adv in clause.adverbs if adv.lemma != 'nōn']
    if clause.copula:
        complements = clause.role('complement')
        owners = clause.role('recipient')
        if owners and not complements:   # 所有: 所格 + olla + 主語 (Minulla on kaksi kissaa「私には猫が2匹いる」)
            tense = 'past' if clause.tense in ('perfect', 'imperfect', 'past-perfect') else 'present'
            verb = 'ei ' + ('ole' if tense == 'present' else 'ollut') if clause.negated else OLLA[(tense, 3, 'sg')]
            owned = noun_phrase(subject, 'Par' if clause.negated else 'Nom') if subject is not None else ''
            return [w for w in [noun_phrase(owners[0], 'Ade'), verb] + rest + [owned] if w]
        verb, comp = _copula(clause, complements[0] if complements else None, person, number)
        places = [prepositional(np) for role, np in clause.args if role == 'prep']
        return [w for w in head + [verb] + rest + [comp] + places if w]
    verb = verb_form(clause, person, number)
    for np in clause.role('recipient'):
        rest.append(noun_phrase(np, 'All'))
    obj = (clause.role('object') or [None])[0]
    if obj is not None and gap != 'object':
        rest.insert(0, noun_phrase(obj, _object_case(clause, obj)))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            rest.append(prepositional(np, clause.voice == 'passive'))
        elif np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
            rest.append(WORDS[np.head.lemma])
        else:
            case = {'means': 'All' if np.animate else 'Ade', 'possessor': 'Gen', 'source': 'Ela'}.get(role, 'Ine')
            rest.append(noun_phrase(np, case))
    return [w for w in head + [verb] + rest if w]


def vocative(np):
    return noun_phrase(np)


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import split_address
    parts = []
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        words = [', '.join(vocative(np) for np in group) + ',' for group in groups]
        for key in rest.connectives:
            if key in CONNECTIVES and k > 0:
                words.append(CONNECTIVES[key])
        words += realize(rest)
        parts.append(' '.join(w for w in words if w))
    text = ', '.join(parts).replace(' ,', ',').replace(',,', ',').rstrip(',')
    return text[:1].upper() + text[1:] + '.'


# ----------------------------------------------------------------------
# 比較の表

CASE_HOW = {'Nom': '主格', 'Acc': '属格 (全体の目的語)', 'Par': '分格 (否定・継続の目的語)', 'Gen': '属格 -n',
            'All': '向格 -lle', 'Ade': '所格 -lla', 'Ine': '内格 -ssa', 'Ela': '出格 -sta', 'Ill': '入格',
            'Abl': '離格 -lta', 'Abe': '欠格 -tta'}
PRO_DROP_HOW = '1・2人称は書かない (動詞の人称の語尾で分かる)'
PREDICATE_HOW = '人称・数・時制の語尾 (luen・luki)、否定は否定動詞 ei (人称で変わる) + 本動詞、受動は非人称の受動 (luetaan)'
COPULA_HOW = 'olla + 補語 (複数の主語の形容詞は分格の複数)'
ADDRESS_HOW = '主格'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return '', '書かない (非人称の受動は動作主を書かない)'
        case, post = PREPOSITIONS.get((np.prep.lemma, np.case), ('Ine', ''))
        return prepositional(np, passive), CASE_HOW.get(case, case) + (' + 後置詞 %s' % post if post else '')
    if role == 'object':
        case = _object_case(clause, np)
        return noun_phrase(np, case), CASE_HOW[case] if not (case == 'Acc' and np.number == 'pl') else '主格の複数 (全体の目的語)'
    case = {'subject': 'Nom', 'recipient': 'All', 'means': 'All' if np.animate else 'Ade', 'possessor': 'Gen',
            'address': 'Nom', 'source': 'Ela'}.get(role, 'Ine')
    return noun_phrase(np, case), CASE_HOW.get(case, case) if role != 'address' else ADDRESS_HOW


def compare_predicate(clause, reduced):
    person, number = _person(clause)
    if clause.copula:
        complements = clause.role('complement')
        verb, comp = _copula(clause, complements[0] if complements else None, person, number)
        return ' '.join(x for x in (verb, comp) if x), COPULA_HOW
    return verb_form(clause, person, number), PREDICATE_HOW
