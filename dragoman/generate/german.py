#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からドイツ語の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)。名詞の性と、名詞・動詞の語形は辞書
#     (de/wiktionary.sqlite の語形の表。Wiktionary の変化表) から
#   名詞句: 定冠詞 (性・数・格: der / die / das / den / dem / des) + 形容詞 (弱変化の語尾 -e / -en) + 名詞 (複数・与格複数の -n、
#     属格単数の -(e)s)。固有名詞・代名詞は冠詞なし
#   語順: 主文は動詞が2番目 (主語 - 定動詞 - 与格 - 対格 - 前置詞句 - nicht - 過去分詞・不定詞・分離の前つづり)。
#     関係節は関係代名詞 (der / die / das …) で始めて動詞を最後に
#   時制: 現在、過去 (完了・未完了は過去形 sah)、過去完了 (hatte / war + 過去分詞)、未来 (werden + 不定詞)、
#     受動 (werden + 過去分詞)。否定 nicht
#
import dataclasses
import functools
import os
import sqlite3

from dragoman.core import paths
from . import transfer, english
from .frame import NP

ARTICLES = {  # (格, 性 / 複数) → 定冠詞
    ('Nom', 'm'): 'der', ('Nom', 'f'): 'die', ('Nom', 'n'): 'das', ('Nom', 'p'): 'die',
    ('Acc', 'm'): 'den', ('Acc', 'f'): 'die', ('Acc', 'n'): 'das', ('Acc', 'p'): 'die',
    ('Dat', 'm'): 'dem', ('Dat', 'f'): 'der', ('Dat', 'n'): 'dem', ('Dat', 'p'): 'den',
    ('Gen', 'm'): 'des', ('Gen', 'f'): 'der', ('Gen', 'n'): 'des', ('Gen', 'p'): 'der'}
RELATIVES = {**ARTICLES, ('Dat', 'p'): 'denen', ('Gen', 'm'): 'dessen', ('Gen', 'n'): 'dessen',
             ('Gen', 'f'): 'deren', ('Gen', 'p'): 'deren'}
DEMONSTRATIVE_ENDINGS = {('Nom', 'm'): 'er', ('Nom', 'f'): 'e', ('Nom', 'n'): 'es', ('Nom', 'p'): 'e',
                         ('Acc', 'm'): 'en', ('Acc', 'f'): 'e', ('Acc', 'n'): 'es', ('Acc', 'p'): 'e',
                         ('Dat', 'm'): 'em', ('Dat', 'f'): 'er', ('Dat', 'n'): 'em', ('Dat', 'p'): 'en',
                         ('Gen', 'm'): 'es', ('Gen', 'f'): 'er', ('Gen', 'n'): 'es', ('Gen', 'p'): 'er'}
POSSESSIVE_ENDINGS = {('Nom', 'm'): '', ('Nom', 'f'): 'e', ('Nom', 'n'): '', ('Nom', 'p'): 'e',
                      ('Acc', 'm'): 'en', ('Acc', 'f'): 'e', ('Acc', 'n'): '', ('Acc', 'p'): 'e',
                      ('Dat', 'm'): 'em', ('Dat', 'f'): 'er', ('Dat', 'n'): 'em', ('Dat', 'p'): 'en',
                      ('Gen', 'm'): 'es', ('Gen', 'f'): 'er', ('Gen', 'n'): 'es', ('Gen', 'p'): 'er'}
PRONOUNS = {  # (ラテン語の代名詞, 数) → {格: 形}
    ('ego', 'sg'): {'Nom': 'ich', 'Acc': 'mich', 'Dat': 'mir', 'Gen': 'meiner'},
    ('tū', 'sg'): {'Nom': 'du', 'Acc': 'dich', 'Dat': 'dir', 'Gen': 'deiner'},
    ('ego', 'pl'): {'Nom': 'wir', 'Acc': 'uns', 'Dat': 'uns', 'Gen': 'unser'},
    ('tū', 'pl'): {'Nom': 'ihr', 'Acc': 'euch', 'Dat': 'euch', 'Gen': 'euer'},
    ('is', 'pl'): {'Nom': 'sie', 'Acc': 'sie', 'Dat': 'ihnen', 'Gen': 'ihrer'},
    ('sē', 'sg'): {'Nom': 'sich', 'Acc': 'sich', 'Dat': 'sich', 'Gen': 'seiner'},
    ('quis', 'sg'): {'Nom': 'wer', 'Acc': 'wen', 'Dat': 'wem', 'Gen': 'wessen'},
    ('quid', 'sg'): {'Nom': 'was', 'Acc': 'was', 'Dat': 'was', 'Gen': 'wessen'}}
THIRD = {'m': {'Nom': 'er', 'Acc': 'ihn', 'Dat': 'ihm', 'Gen': 'seiner'},
         'f': {'Nom': 'sie', 'Acc': 'sie', 'Dat': 'ihr', 'Gen': 'ihrer'},
         'n': {'Nom': 'es', 'Acc': 'es', 'Dat': 'ihm', 'Gen': 'seiner'}}
DEMONSTRATIVES = {'hic': 'dies', 'hīc': 'dies', 'iste': 'dies', 'ille': 'jen', 'is': 'dies'}
POSSESSIVES = {'meus': 'mein', 'tuus': 'dein', 'suus': 'sein', 'noster': 'unser', 'vester': 'euer'}
NUMERALS = {'ūnus': 'ein', 'duo': 'zwei', 'trēs': 'drei', 'quattuor': 'vier', 'quīnque': 'fünf', 'decem': 'zehn',
            'centum': 'hundert', 'mīlle': 'tausend'}
QUANTIFIERS = {'omnis': 'all', 'multus': 'viel', 'tōtus': 'ganz', 'alius': 'ander'}
PREPOSITIONS = {('in', 'Abl'): ('in', 'Dat'), ('in', 'Acc'): ('in', 'Acc'), ('ad', 'Acc'): ('zu', 'Dat'),
                ('ex', 'Abl'): ('aus', 'Dat'), ('ē', 'Abl'): ('aus', 'Dat'), ('ab', 'Abl'): ('von', 'Dat'),
                ('ā', 'Abl'): ('von', 'Dat'), ('cum', 'Abl'): ('mit', 'Dat'), ('dē', 'Abl'): ('über', 'Acc'),
                ('sine', 'Abl'): ('ohne', 'Acc'), ('per', 'Acc'): ('durch', 'Acc'), ('propter', 'Acc'): ('wegen', 'Gen'),
                ('ob', 'Acc'): ('wegen', 'Gen'), ('post', 'Acc'): ('nach', 'Dat'), ('ante', 'Acc'): ('vor', 'Dat'),
                ('sub', 'Abl'): ('unter', 'Dat'), ('super', 'Acc'): ('über', 'Dat'), ('prō', 'Abl'): ('für', 'Acc'),
                ('apud', 'Acc'): ('bei', 'Dat'), ('contrā', 'Acc'): ('gegen', 'Acc'), ('inter', 'Acc'): ('zwischen', 'Dat'),
                ('prope', 'Acc'): ('bei', 'Dat')}
CONTRACTIONS = {('in', 'dem'): 'im', ('in', 'das'): 'ins', ('zu', 'dem'): 'zum', ('zu', 'der'): 'zur',
                ('von', 'dem'): 'vom', ('bei', 'dem'): 'beim', ('an', 'dem'): 'am'}
CONNECTIVES = {'et': 'und', 'que': 'und', 'atque': 'und', 'ac': 'und', 'sed': 'aber', 'at': 'aber', 'autem': 'aber',
               'enim': 'denn', 'nam': 'denn', 'igitur': 'also', 'itaque': 'deshalb', 'tamen': 'trotzdem', 'tum': 'dann',
               'deinde': 'dann', 'aut': 'oder', 'vel': 'oder'}
WORDS = {'semper': 'immer', 'saepe': 'oft', 'iam': 'schon', 'nunc': 'jetzt', 'hodiē': 'heute', 'crās': 'morgen',
         'heri': 'gestern', 'ibi': 'dort', 'hīc': 'hier', 'etiam': 'auch', 'quoque': 'auch', 'valdē': 'sehr',
         'magnopere': 'sehr', 'statim': 'sofort', 'mox': 'bald', 'tandem': 'endlich', 'iterum': 'wieder',
         'numquam': 'nie', 'bene': 'gut', 'posteā': 'danach', 'diū': 'lange'}
SEPARABLE = ('zurück', 'weg', 'fern', 'statt', 'teil', 'heim', 'hin', 'her', 'los', 'fest', 'vorbei', 'weiter', 'an', 'auf',
             'aus', 'ein', 'mit', 'nach', 'vor', 'zu', 'ab', 'bei', 'dar', 'um')
SEIN_VERBS = ('gehen', 'kommen', 'fahren', 'laufen', 'fliegen', 'sterben', 'werden', 'bleiben', 'sein', 'fallen',
              'reisen', 'wachsen', 'ankommen', 'aufstehen', 'einschlafen', 'schwimmen', 'steigen', 'fliehen')
PERSON_TAGS = {(1, 'sg'): ('first-person', 'singular'), (2, 'sg'): ('second-person', 'singular'),
               (3, 'sg'): ('third-person', 'singular'), (1, 'pl'): ('first-person', 'plural'),
               (2, 'pl'): ('second-person', 'plural'), (3, 'pl'): ('third-person', 'plural')}
AUX = {'haben': {(1, 'sg'): 'habe', (2, 'sg'): 'hast', (3, 'sg'): 'hat', (1, 'pl'): 'haben', (2, 'pl'): 'habt', (3, 'pl'): 'haben'},
       'haben_past': {(1, 'sg'): 'hatte', (2, 'sg'): 'hattest', (3, 'sg'): 'hatte', (1, 'pl'): 'hatten', (2, 'pl'): 'hattet', (3, 'pl'): 'hatten'},
       'sein': {(1, 'sg'): 'bin', (2, 'sg'): 'bist', (3, 'sg'): 'ist', (1, 'pl'): 'sind', (2, 'pl'): 'seid', (3, 'pl'): 'sind'},
       'sein_past': {(1, 'sg'): 'war', (2, 'sg'): 'warst', (3, 'sg'): 'war', (1, 'pl'): 'waren', (2, 'pl'): 'wart', (3, 'pl'): 'waren'},
       'werden': {(1, 'sg'): 'werde', (2, 'sg'): 'wirst', (3, 'sg'): 'wird', (1, 'pl'): 'werden', (2, 'pl'): 'werdet', (3, 'pl'): 'werden'},
       'werden_past': {(1, 'sg'): 'wurde', (2, 'sg'): 'wurdest', (3, 'sg'): 'wurde', (1, 'pl'): 'wurden', (2, 'pl'): 'wurdet', (3, 'pl'): 'wurden'}}


@functools.lru_cache(maxsize=1)
def _db():
    path = paths.data('de', 'wiktionary.sqlite')
    if not os.path.exists(path):
        return None
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute('CREATE INDEX IF NOT EXISTS forms_lemma ON forms (lemma, pos)')
    return db


@functools.lru_cache(maxsize=50000)
def _forms(lemma, pos):
    db = _db()
    if db is None:
        return ()
    return tuple((form, frozenset(tags.split(','))) for form, tags in
                 db.execute('SELECT form, tags FROM forms WHERE lemma = ? AND pos = ?', (lemma, pos)))


def find_form(lemma, pos, wanted, avoid=()):
    """語形の表から、印 wanted をすべて持つ (avoid を持たない) 形。無ければ None"""
    wanted, avoid = set(wanted), set(avoid)
    for form, tags in _forms(lemma, pos):
        if wanted <= tags and not tags & avoid and ' ' not in form:
            return form
    return None


@functools.lru_cache(maxsize=50000)
def gender(noun):
    db = _db()
    if db is None:
        return 'n'
    row = db.execute("SELECT gender FROM lemmas WHERE word = ? AND pos IN ('noun', 'name') AND gender != '' LIMIT 1",
                     (noun,)).fetchone()
    return row[0] if row and row[0] in ('m', 'f', 'n') else 'n'


# ----------------------------------------------------------------------
# 名詞句

def noun_form(noun, case, number):
    if number == 'pl':
        form = find_form(noun, 'noun', ('plural', {'Nom': 'nominative', 'Acc': 'accusative', 'Dat': 'dative',
                                                    'Gen': 'genitive'}[case]))
        form = form or find_form(noun, 'noun', ('plural',))
        if form is None:
            return noun
        form = noun[0] + form[1:] if noun[:1].isupper() else form
        if case == 'Dat' and not form.endswith(('n', 's')):
            form += 'n'
        return form
    tag = {'Nom': 'nominative', 'Acc': 'accusative', 'Dat': 'dative', 'Gen': 'genitive'}[case]
    forms = [f for f, tags in _forms(noun, 'noun') if {tag, 'singular'} <= tags and ' ' not in f]
    if not forms:
        return noun
    weak = [f for f in (noun.lower() + 'n', noun.lower() + 'en') if f in forms]
    genitives = [f for f, tags in _forms(noun, 'noun') if {'genitive', 'singular'} <= tags]
    if weak and case in ('Acc', 'Dat') and \
            any(g in (noun.lower() + e for e in ('n', 'en', 'ns', 'ens')) for g in genitives):
        # 弱変化の男性名詞 (den Bauern・dem Menschen。口語の den Mensch は選ばない)、属格 -(e)ns の名詞 (dem Namen・
        # dem Herzen。Herz の対格は表に Herz だけなので Herz のまま)
        return noun[0] + weak[0][1:]
    if noun.lower() in forms and case != 'Gen':
        return noun   # 見出しと同じ形があれば (Buch の与格は Buche より Buch)
    form = forms[0]
    return noun[0] + form[1:]   # 弱変化 (den Bauern)・属格 (des Buches)


def adjective_form(adj, case, key, article=True):
    """形容詞の語尾 (定冠詞の後ろの弱変化: 主格単数・女性中性の対格単数 -e、ほか -en。冠詞なしは強変化)"""
    if not article:
        return adj + {'Nom': {'m': 'er', 'f': 'e', 'n': 'es', 'p': 'e'}, 'Acc': {'m': 'en', 'f': 'e', 'n': 'es', 'p': 'e'},
                      'Dat': {'m': 'em', 'f': 'er', 'n': 'em', 'p': 'en'},
                      'Gen': {'m': 'en', 'f': 'er', 'n': 'en', 'p': 'er'}}[case][key]
    if case == 'Nom' and key != 'p' or case == 'Acc' and key in ('f', 'n'):
        return _stem_adjective(adj) + 'e'
    return _stem_adjective(adj) + 'en'


def _stem_adjective(adj):
    if adj.endswith('e'):
        return adj[:-1]
    if adj.endswith(('el', 'er')) and adj in ('dunkel', 'teuer', 'sauber', 'edel', 'eitel'):
        return adj[:-2] + adj[-1]
    return {'hoch': 'hoh'}.get(adj, adj)


def available():
    return transfer.available('de')


def to_german(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'de':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'de')
        return found[0] if found else _latin_name(lex.lemma)
    target = transfer.best(lex, 'de', pos)
    return target.lemma if target else None


def _latin_name(lemma):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', lemma) if not unicodedata.combining(c))


def word(lex, pos=None):
    found = to_german(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


def noun_phrase(np, case='Nom'):
    if np.members:
        parts = [noun_phrase(m, case) for m in np.members]
        conj = ' oder ' if np.conj in ('aut', 'vel') else ' und '
        return ', '.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
    head = np.head
    if head is None:
        return ''
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.pos == 'pronoun':
        if head.lemma == 'is' and number == 'sg':
            return THIRD.get(np.gender if np.gender in THIRD else 'm')[case]
        forms = PRONOUNS.get((head.lemma, number)) or PRONOUNS.get((head.lemma, 'sg'))
        if forms:
            return forms[case]
        if head.lemma in DEMONSTRATIVES:
            g = np.gender if np.gender in ('m', 'f', 'n') else 'n'
            return DEMONSTRATIVES[head.lemma] + DEMONSTRATIVE_ENDINGS[(case, 'p' if number == 'pl' else g)]
        return word(head)
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    if noun[:1].islower() and head.pos not in ('adj', 'participle'):
        noun = noun[:1].upper() + noun[1:]
    g = gender(noun)
    key = 'p' if number == 'pl' else g
    determiner = None
    adjectives = []
    for m in np.modifiers:
        if isinstance(m, NP):
            adjectives += [x.head for x in m.members]
            continue
        if m.lemma in DEMONSTRATIVES and m.lang in ('', 'la'):
            determiner = DEMONSTRATIVES[m.lemma] + DEMONSTRATIVE_ENDINGS[(case, key)]
        elif m.lemma in POSSESSIVES and m.lang in ('', 'la'):
            determiner = POSSESSIVES[m.lemma] + POSSESSIVE_ENDINGS[(case, key)]
        elif m.lemma in NUMERALS and m.lang in ('', 'la'):
            determiner = NUMERALS[m.lemma]
        else:
            adjectives.append(m)
    article = determiner or ('' if head.proper else ARTICLES[(case, key)])
    adjs = []
    for a in adjectives:
        if a.lemma in QUANTIFIERS and a.lang in ('', 'la'):
            adjs.append(QUANTIFIERS[a.lemma] + DEMONSTRATIVE_ENDINGS[(case, key)])
            continue
        form = word(a, 'adj')
        adjs.append(adjective_form(form, case, key, bool(article)) if form and not form.startswith('[') else form)
    text = ' '.join(x for x in [article] + adjs + [noun_form(noun, case, number)] if x)
    for genitive in np.genitives:
        text += ' ' + noun_phrase(genitive, 'Gen')
    for r in np.relatives:
        text += ', ' + relative_clause(r, g if number == 'sg' else 'p') + ','
    return text


def relative_clause(r, key):
    case = {'subject': 'Nom', 'object': 'Acc', 'recipient': 'Dat', 'possessor': 'Gen'}.get(r.gap or 'subject', 'Nom')
    pronoun = RELATIVES[(case, key)]
    words = realize(r, gap=r.gap or 'subject', subordinate=True)
    return ' '.join([pronoun] + words)


def prepositional(np, passive=False):
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        text = noun_phrase(inner, 'Dat')
        return _contract('von', text) if text else ''
    prep, case = PREPOSITIONS.get((np.prep.lemma, np.case), ('in', 'Dat')) if np.prep is not None else ('in', 'Dat')
    text = noun_phrase(inner, case)
    return _contract(prep, text) if text else ''


def _contract(prep, text):
    article, _, rest = text.partition(' ')
    if (prep, article) in CONTRACTIONS and rest:
        return CONTRACTIONS[(prep, article)] + ' ' + rest
    return prep + ' ' + text


# ----------------------------------------------------------------------
# 動詞

def _split_separable(lemma, form):
    """分離動詞の定形 (anrief → rief + an)。分離しなければ (form, '')"""
    for prefix in SEPARABLE:
        rest = lemma[len(prefix):]
        if lemma.startswith(prefix) and form.startswith(prefix) and len(rest) > 3 and _forms(rest, 'verb'):
            return form[len(prefix):], prefix
    return form, ''


def finite(lemma, tense, person, number, subordinate=False):
    """定形 (現在・過去)。返り値: (定形, 分離の前つづり)"""
    tags = PERSON_TAGS.get((person, number), PERSON_TAGS[(3, 'sg')])
    wanted = ('indicative', 'preterite' if tense == 'past' else 'present') + tags
    form = find_form(lemma, 'verb', wanted, avoid=('dependent', 'subjunctive-i', 'subjunctive-ii'))
    form = form or find_form(lemma, 'verb', wanted, avoid=('subjunctive-i', 'subjunctive-ii'))
    if form is None:
        form = _regular(lemma, tense, person, number)
    if subordinate:
        return form, ''
    return _split_separable(lemma, form)


def _regular(lemma, tense, person, number):
    stem = lemma[:-2] if lemma.endswith('en') else lemma[:-1]
    if tense == 'past':
        return stem + {(1, 'sg'): 'te', (2, 'sg'): 'test', (3, 'sg'): 'te', (1, 'pl'): 'ten', (2, 'pl'): 'tet',
                       (3, 'pl'): 'ten'}[(person, number)]
    return stem + {(1, 'sg'): 'e', (2, 'sg'): 'st', (3, 'sg'): 't', (1, 'pl'): 'en', (2, 'pl'): 't',
                   (3, 'pl'): 'en'}[(person, number)]


def participle_form(lemma):
    return find_form(lemma, 'verb', ('participle', 'past')) or 'ge' + (lemma[:-2] if lemma.endswith('en') else lemma) + 't'


def verb_parts(clause, person, number, subordinate=False):
    """(定形, 文末の語の列)。否定の nicht は呼ぶ側で"""
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return lemma, []
    key = (person, number)
    if clause.voice == 'passive':
        aux = 'werden_past' if clause.tense in ('perfect', 'imperfect', 'past-perfect') else 'werden'
        return AUX[aux][key], [participle_form(lemma)]
    if clause.tense == 'past-perfect':
        aux = 'sein_past' if lemma in SEIN_VERBS else 'haben_past'
        return AUX[aux][key], [participle_form(lemma)]
    if clause.tense in ('future', 'future-perfect'):
        return AUX['werden'][key], [lemma]
    form, particle = finite(lemma, 'past' if clause.tense in ('perfect', 'imperfect') else 'present', person, number,
                            subordinate)
    return form, ([particle] if particle else [])


def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            subject.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[subject.head.lemma], subject.number or 'sg'
    if subject is not None:
        return 3, 'pl' if subject.members or subject.number == 'pl' else 'sg'
    return clause.person, clause.number


def _copula_words(clause, person, number):
    key = (person, number)
    if clause.tense in ('perfect', 'imperfect', 'past-perfect'):
        return AUX['sein_past'][key]
    if clause.tense == 'future':
        return AUX['werden'][key]
    return AUX['sein'][key]


def realize(clause, gap=None, subordinate=False):
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    person, number = _person(clause)
    subject = (clause.role('subject') or [None])[0]
    head_words = []
    if subject is not None and gap != 'subject':
        head_words.append(noun_phrase(subject, 'Nom'))
    elif subject is None and gap is None and clause.mood != 'imperative':
        head_words.append({(1, 'sg'): 'ich', (2, 'sg'): 'du', (3, 'sg'): 'er', (1, 'pl'): 'wir', (2, 'pl'): 'ihr',
                           (3, 'pl'): 'sie'}[(person, number)])
    middle, tail = [], []
    for adv in clause.adverbs:
        if adv.lemma != 'nōn':
            middle.append(word(adv, 'adv'))
    if clause.copula:
        complements = clause.role('complement')
        for role, np in clause.args:
            if role == 'prep':
                middle.append(prepositional(np))
        if complements:
            comp = complements[0]
            text = noun_phrase(comp, 'Nom') if not (comp.head is not None and comp.head.pos in ('adj', 'participle')) \
                else (word(comp.head, 'adj') if not comp.members else ' und '.join(word(m.head, 'adj') for m in comp.members))
            tail.append(text)
        if complements or clause.role('prep'):
            verb = _copula_words(clause, person, number)
        else:   # 存在の文 (Agricola est.「農夫がいる」): es gibt + 対格
            verb = 'gab' if clause.tense in ('perfect', 'imperfect', 'past-perfect') else 'gibt'
            head_words = ['es']
            middle.insert(0, noun_phrase(subject, 'Acc') if subject is not None else '')
        if clause.negated:
            tail.insert(0, 'nicht')
    else:
        for np in clause.role('recipient'):
            middle.append(noun_phrase(np, 'Dat'))
        obj = (clause.role('object') or [None])[0]
        if obj is not None and gap != 'object':
            middle.append(noun_phrase(obj, 'Acc'))
        for role, np in clause.args:
            if role in ('subject', 'object', 'recipient', 'complement', 'address'):
                continue
            if role == 'prep':
                middle.append(prepositional(np, clause.voice == 'passive'))
            elif np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
                middle.append(WORDS[np.head.lemma])
            elif role == 'means' and np.animate:
                middle.append(noun_phrase(np, 'Dat'))
            elif role == 'means':
                middle.append(_contract('mit', noun_phrase(np, 'Dat')))
            elif role == 'possessor':
                middle.append(noun_phrase(np, 'Gen'))
            else:
                middle.append(_contract('in', noun_phrase(np, 'Dat')))
        verb, tail = verb_parts(clause, person, number, subordinate)
        if clause.negated:
            tail = ['nicht'] + tail
    if clause.mood == 'imperative' and not clause.copula:
        lemma = word(clause.verb, 'verb')
        stem = (lemma[:-2] if lemma.endswith('en') else lemma)
        return [w for w in [stem + ('t' if number == 'pl' else '')] + middle + (['nicht'] if clause.negated else []) if w]
    if subordinate:   # 関係節・従属節: 動詞を最後に
        return [w for w in head_words + middle + tail + [verb] if w]
    return [w for w in head_words + [verb] + middle + tail if w]


def vocative(np):
    inner = dataclasses.replace(np)
    text = noun_phrase(inner, 'Nom')
    article = text.split(' ')[0]
    return text[len(article) + 1:] if article in ('der', 'die', 'das') else text


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

CASE_HOW = {'Nom': '主格 (der / die / das)', 'Acc': '対格 (den / die / das)', 'Dat': '与格 (dem / der / dem・複数 -n)',
            'Gen': '属格 (des / der、名詞の -(e)s)'}
PRO_DROP_HOW = '代名詞を補う'
PREDICATE_HOW = '人称・数・時制の語形 (sieht・sah)、完了 haben / sein + 過去分詞、未来・受動 werden。主文は2番目'
COPULA_HOW = 'sein + 補語 (形容詞は語尾なし)'
ADDRESS_HOW = '冠詞なし'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, '前置詞 von + 与格 (受動の動作主)'
        prep, case = PREPOSITIONS.get((np.prep.lemma, np.case), ('in', 'Dat'))
        return text, '%s + %s' % (prep, {'Dat': '与格', 'Acc': '対格', 'Gen': '属格'}[case])
    if role == 'address':
        return vocative(np), ADDRESS_HOW
    case = {'subject': 'Nom', 'object': 'Acc', 'recipient': 'Dat', 'means': 'Dat', 'possessor': 'Gen'}.get(role, 'Dat')
    text = noun_phrase(np, case)
    if role == 'means' and not np.animate:
        return _contract('mit', text), 'mit + 与格'
    if role in ('place', 'source'):
        return _contract('in', text), 'in + 与格'
    return text, CASE_HOW.get(case, case)


def compare_predicate(clause, reduced):
    person, number = _person(clause)
    if clause.copula:
        words = realize(reduced)
        subject = (clause.role('subject') or [None])[0]
        head = noun_phrase(subject, 'Nom') if subject is not None else ''
        text = ' '.join(words)
        return (text[len(head):].strip() if head and text.startswith(head) else text), COPULA_HOW
    verb, tail = verb_parts(clause, person, number)
    return ' '.join(x for x in [verb] + (['nicht'] if clause.negated else []) + tail if x), PREDICATE_HOW
