#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からポルトガル語 (ブラジル) の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)。名詞の性と、名詞・形容詞・動詞の語形は
#     辞書 (pt/wiktionary.sqlite の語形の表。Wiktionary の変化表) から。無ければ規則 (複数 -s・-ões・-is、女性 -a)
#   名詞句: 定冠詞 (o / a / os / as。固有名詞は冠詞なし) + 前に置く形容詞 (bom・grande・outro …) + 名詞 +
#     後ろに置く形容詞 (性・数の一致) + de + 属格の名詞句。前置詞と冠詞の縮約 (de o → do、em a → na、a o → ao、
#     por o → pelo)、前置詞と代名詞 (de ele → dele、em ela → nela、com mim → comigo)
#   語順: 主語 - (não) - 接語の代名詞 (me・te・o・a・lhe …。ブラジルの話し言葉と同じく動詞の前) - 動詞 - 目的語 -
#     a + 受け手 - 前置詞句。主語の代名詞は書く (ブラジルの話し言葉)。2人称単数は você (動詞は3人称)
#   時制: 現在、完了は完全過去 (viu)、未完了過去 (via)、過去完了 tinha + 過去分詞、単純未来 (verá)、
#     受動 ser + 過去分詞 (主語の性・数に一致)。否定 não。存在の文は há、場所の繋辞は estar
#   関係節は que (主語・目的語の空所)・a quem (受け手)・de quem (所有者)。補文は que (望む・命じる・感情は接続法)
#
import dataclasses
import functools
import os
import sqlite3

from dragoman.core import paths
from . import transfer, english
from .frame import NP, Lex, Clause

PRONOUNS = {  # (ラテン語の代名詞, 数) → {Nom: 主語, Acc: 直接目的の接語, Dat: 間接目的の接語, Str: 前置詞の後ろ}
    ('ego', 'sg'): {'Nom': 'eu', 'Acc': 'me', 'Dat': 'me', 'Str': 'mim'},
    ('tū', 'sg'): {'Nom': 'você', 'Acc': 'te', 'Dat': 'te', 'Str': 'você'},
    ('ego', 'pl'): {'Nom': 'nós', 'Acc': 'nos', 'Dat': 'nos', 'Str': 'nós'},
    ('tū', 'pl'): {'Nom': 'vocês', 'Acc': 'vocês', 'Dat': 'vocês', 'Str': 'vocês'},
    ('sē', 'sg'): {'Nom': 'ele', 'Acc': 'se', 'Dat': 'se', 'Str': 'si'},
    ('sē', 'pl'): {'Nom': 'eles', 'Acc': 'se', 'Dat': 'se', 'Str': 'si'},
    ('quis', 'sg'): {'Nom': 'quem', 'Acc': 'quem', 'Dat': 'quem', 'Str': 'quem'},
    ('quid', 'sg'): {'Nom': 'o que', 'Acc': 'o que', 'Dat': 'o que', 'Str': 'o que'}}
THIRD = {('m', 'sg'): {'Nom': 'ele', 'Acc': 'o', 'Dat': 'lhe', 'Str': 'ele'},
         ('f', 'sg'): {'Nom': 'ela', 'Acc': 'a', 'Dat': 'lhe', 'Str': 'ela'},
         ('m', 'pl'): {'Nom': 'eles', 'Acc': 'os', 'Dat': 'lhes', 'Str': 'eles'},
         ('f', 'pl'): {'Nom': 'elas', 'Acc': 'as', 'Dat': 'lhes', 'Str': 'elas'}}
# 動詞の人称・数 (você・vocês は3人称)
VERB_PERSON = {('tū', 'sg'): (3, 'sg'), ('tū', 'pl'): (3, 'pl'), ('ego', 'sg'): (1, 'sg'), ('ego', 'pl'): (1, 'pl')}
DEMONSTRATIVES = {'hic': ('este', 'esta', 'estes', 'estas'), 'hīc': ('este', 'esta', 'estes', 'estas'),
                  'iste': ('esse', 'essa', 'esses', 'essas'), 'ille': ('aquele', 'aquela', 'aqueles', 'aquelas'),
                  'is': ('esse', 'essa', 'esses', 'essas')}
POSSESSIVES = {'meus': 'meu', 'tuus': 'seu', 'suus': 'seu', 'noster': 'nosso', 'vester': 'seu'}
NUMERALS = {'ūnus': ('um', 'uma'), 'duo': ('dois', 'duas'), 'trēs': 'três', 'quattuor': 'quatro', 'quīnque': 'cinco',
            'sex': 'seis', 'septem': 'sete', 'octō': 'oito', 'novem': 'nove', 'decem': 'dez', 'centum': 'cem',
            'mīlle': 'mil'}
QUANTIFIERS = {'omnis': ('todo', 'toda', 'todos', 'todas'), 'tōtus': ('todo', 'toda', 'todos', 'todas'),
               'multus': ('muito', 'muita', 'muitos', 'muitas'), 'paucī': ('pouco', 'pouca', 'poucos', 'poucas')}
# 名詞の前に置く形容詞
BEFORE_NOUN = {'bom', 'mau', 'outro', 'mesmo', 'primeiro', 'último', 'próprio', 'único', 'belo', 'velho', 'novo',
               'grande', 'pequeno', 'certo', 'cada', 'vários', 'segundo', 'terceiro'}
PREPOSITIONS = {('in', 'Abl'): 'em', ('in', 'Acc'): 'para', ('ad', 'Acc'): 'para', ('ex', 'Abl'): 'de',
                ('ē', 'Abl'): 'de', ('ab', 'Abl'): 'de', ('ā', 'Abl'): 'de', ('cum', 'Abl'): 'com',
                ('dē', 'Abl'): 'sobre', ('sine', 'Abl'): 'sem', ('per', 'Acc'): 'por', ('propter', 'Acc'): 'por causa de',
                ('ob', 'Acc'): 'por causa de', ('post', 'Acc'): 'depois de', ('ante', 'Acc'): 'diante de',
                ('sub', 'Abl'): 'sob', ('sub', 'Acc'): 'sob', ('super', 'Acc'): 'sobre', ('prō', 'Abl'): 'por',
                ('apud', 'Acc'): 'na casa de', ('contrā', 'Acc'): 'contra', ('inter', 'Acc'): 'entre',
                ('prope', 'Acc'): 'perto de', ('trāns', 'Acc'): 'além de', ('circum', 'Acc'): 'em volta de'}
CONTRACTIONS = {('de', 'o'): 'do', ('de', 'a'): 'da', ('de', 'os'): 'dos', ('de', 'as'): 'das',
                ('em', 'o'): 'no', ('em', 'a'): 'na', ('em', 'os'): 'nos', ('em', 'as'): 'nas',
                ('a', 'o'): 'ao', ('a', 'a'): 'à', ('a', 'os'): 'aos', ('a', 'as'): 'às',
                ('por', 'o'): 'pelo', ('por', 'a'): 'pela', ('por', 'os'): 'pelos', ('por', 'as'): 'pelas',
                ('de', 'ele'): 'dele', ('de', 'ela'): 'dela', ('de', 'eles'): 'deles', ('de', 'elas'): 'delas',
                ('em', 'ele'): 'nele', ('em', 'ela'): 'nela', ('em', 'eles'): 'neles', ('em', 'elas'): 'nelas',
                ('de', 'este'): 'deste', ('de', 'esta'): 'desta', ('em', 'este'): 'neste', ('em', 'esta'): 'nesta',
                ('de', 'esse'): 'desse', ('de', 'essa'): 'dessa', ('em', 'esse'): 'nesse', ('em', 'essa'): 'nessa',
                ('de', 'aquele'): 'daquele', ('de', 'aquela'): 'daquela', ('em', 'aquele'): 'naquele',
                ('em', 'aquela'): 'naquela', ('a', 'aquele'): 'àquele', ('a', 'aquela'): 'àquela'}
WITH_PRONOUNS = {'mim': 'comigo', 'nós': 'conosco'}
CONNECTIVES = {'et': 'e', 'que': 'e', 'atque': 'e', 'ac': 'e', 'sed': 'mas', 'at': 'mas', 'autem': 'mas',
               'enim': 'pois', 'nam': 'pois', 'igitur': 'portanto', 'itaque': 'por isso', 'tamen': 'porém',
               'tum': 'então', 'deinde': 'depois', 'aut': 'ou', 'vel': 'ou'}
SUBORDINATORS = {'cum': 'quando', 'ubi': 'quando', 'sī': 'se', 'quod': 'porque', 'quia': 'porque',
                 'quoniam': 'já que', 'dum': 'enquanto', 'postquam': 'depois que', 'ut': 'para que',
                 'quamquam': 'embora', 'etsī': 'embora', 'priusquam': 'antes que', 'antequam': 'antes que',
                 'dōnec': 'até que', 'simul': 'assim que', 'nisi': 'a menos que', 'quīn': 'sem que'}
# 後ろの動詞を接続法にする接続詞 (para que ele venha、embora chova)
SUBJUNCTIVE_AFTER = {'quīn', 'quamquam', 'etsī', 'priusquam', 'antequam', 'ut', 'nē', 'dōnec', 'nisi'}
# 否定の代名詞 (ninguém・nada。動詞の後ろなら não も付ける: não vi ninguém)
NEGATIVE_PRONOUNS = {'nēmō': 'ninguém', 'nihil': 'nada', 'nūllus': 'ninguém'}
WORDS = {'semper': 'sempre', 'saepe': 'frequentemente', 'iam': 'já', 'nunc': 'agora', 'hodiē': 'hoje',
         'crās': 'amanhã', 'heri': 'ontem', 'ibi': 'lá', 'hīc': 'aqui', 'etiam': 'também', 'quoque': 'também',
         'valdē': 'muito', 'magnopere': 'muito', 'statim': 'imediatamente', 'mox': 'logo', 'tandem': 'finalmente',
         'iterum': 'de novo', 'numquam': 'nunca', 'bene': 'bem', 'male': 'mal', 'posteā': 'depois', 'diū': 'muito tempo',
         'sīc': 'assim', 'ita': 'assim', 'tam': 'tão', 'sōlum': 'só', 'paene': 'quase'}
PERSON_TAGS = {(1, 'sg'): ('first-person', 'singular'), (2, 'sg'): ('second-person', 'singular'),
               (3, 'sg'): ('singular', 'third-person'), (1, 'pl'): ('first-person', 'plural'),
               (2, 'pl'): ('plural', 'second-person'), (3, 'pl'): ('plural', 'third-person')}
SER = {('present', 1, 'sg'): 'sou', ('present', 3, 'sg'): 'é', ('present', 1, 'pl'): 'somos', ('present', 3, 'pl'): 'são',
       ('imperfect', 1, 'sg'): 'era', ('imperfect', 3, 'sg'): 'era', ('imperfect', 1, 'pl'): 'éramos',
       ('imperfect', 3, 'pl'): 'eram', ('preterite', 1, 'sg'): 'fui', ('preterite', 3, 'sg'): 'foi',
       ('preterite', 1, 'pl'): 'fomos', ('preterite', 3, 'pl'): 'foram', ('future', 1, 'sg'): 'serei',
       ('future', 3, 'sg'): 'será', ('future', 1, 'pl'): 'seremos', ('future', 3, 'pl'): 'serão',
       ('subjunctive', 1, 'sg'): 'seja', ('subjunctive', 3, 'sg'): 'seja', ('subjunctive', 1, 'pl'): 'sejamos',
       ('subjunctive', 3, 'pl'): 'sejam'}
ESTAR = {('present', 1, 'sg'): 'estou', ('present', 3, 'sg'): 'está', ('present', 1, 'pl'): 'estamos',
         ('present', 3, 'pl'): 'estão', ('imperfect', 1, 'sg'): 'estava', ('imperfect', 3, 'sg'): 'estava',
         ('imperfect', 1, 'pl'): 'estávamos', ('imperfect', 3, 'pl'): 'estavam', ('preterite', 1, 'sg'): 'estive',
         ('preterite', 3, 'sg'): 'esteve', ('preterite', 1, 'pl'): 'estivemos', ('preterite', 3, 'pl'): 'estiveram',
         ('future', 1, 'sg'): 'estarei', ('future', 3, 'sg'): 'estará', ('future', 1, 'pl'): 'estaremos',
         ('future', 3, 'pl'): 'estarão'}
TER = {('present', 1, 'sg'): 'tenho', ('present', 3, 'sg'): 'tem', ('present', 1, 'pl'): 'temos', ('present', 3, 'pl'): 'têm',
       ('imperfect', 1, 'sg'): 'tinha', ('imperfect', 3, 'sg'): 'tinha', ('imperfect', 1, 'pl'): 'tínhamos',
       ('imperfect', 3, 'pl'): 'tinham', ('future', 1, 'sg'): 'terei', ('future', 3, 'sg'): 'terá',
       ('future', 1, 'pl'): 'teremos', ('future', 3, 'pl'): 'terão'}
# 不定詞を支配する話法の動詞 (ラテン語の見出し) → ポルトガル語の動詞
MODALS = {'possum': 'poder', 'volō': 'querer', 'dēbeō': 'dever', 'oportet': 'precisar', 'faciō': 'fazer',
          'sinō': 'deixar', 'soleō': 'costumar', 'incipiō': 'começar a', 'coepī': 'começar a'}
# 補文を接続法にする動詞 (望む・命じる・感情)
SUBJUNCTIVE_KINDS = ('command', 'emotion')


@functools.lru_cache(maxsize=1)
def _db():
    path = paths.data('pt', 'wiktionary.sqlite')
    if not os.path.exists(path):
        return None
    return sqlite3.connect(path, check_same_thread=False)


@functools.lru_cache(maxsize=50000)
def _forms(lemma, pos):
    db = _db()
    if db is None:
        return ()
    return tuple((form, frozenset(tags.split(','))) for form, tags in
                 db.execute('SELECT form, tags FROM forms WHERE lemma = ? AND pos = ?', (lemma, pos)))


def find_form(lemma, pos, wanted, avoid=()):
    """語形の表から、印 wanted をすべて持つ (avoid を持たない) 形。無ければ None。
    表に何度も (別の印の組でも) 載る形を先に (saber の1人称単数: 標準の sei は2行、方言・俗語の sabo・saibo は1行)"""
    wanted, avoid = set(wanted), set(avoid)
    found = {form for form, tags in _forms(lemma, pos) if wanted <= tags and not tags & avoid and ' ' not in form}
    if not found:
        return None
    rows = {form: sum(1 for f, _ in _forms(lemma, pos) if f == form) for form in found}
    return min(found, key=lambda f: (-rows[f], f))


@functools.lru_cache(maxsize=50000)
def gender(noun):
    if ' ' in noun:
        return gender(noun.split(' ')[0])   # casa de campo は casa の性
    db = _db()
    if db is None:
        return 'f' if noun.endswith(('a', 'ção', 'dade')) else 'm'
    row = db.execute("SELECT gender FROM lemmas WHERE key = ? AND pos IN ('noun', 'name') AND gender IN ('m', 'f') "
                     "ORDER BY pos = 'name', rowid LIMIT 1", (noun.lower(),)).fetchone()
    if row:
        return row[0]
    return 'f' if noun.endswith(('a', 'ção', 'dade', 'gem')) else 'm'


def available():
    return transfer.available('pt')


def to_portuguese(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'pt':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'pt')
        return found[0] if found else _latin_name(lex.lemma)
    target = transfer.best(lex, 'pt', pos)
    return target.lemma if target else None


def _latin_name(lemma):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', lemma) if not unicodedata.combining(c))


def word(lex, pos=None):
    found = to_portuguese(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


# ----------------------------------------------------------------------
# 名詞句

def plural(noun):
    g = gender(noun)
    form = find_form(noun, 'noun', ('plural',), avoid=('feminine',) if g == 'm' else ('masculine',)) if g else None
    form = form or find_form(noun, 'noun', ('plural',), avoid=('feminine', 'diminutive', 'augmentative'))
    if form:
        return form
    if noun.endswith('ão'):
        return noun[:-2] + 'ões'
    if noun.endswith('m'):
        return noun[:-1] + 'ns'
    if noun.endswith(('al', 'el', 'ol', 'ul')):
        return noun[:-1] + 'is'
    if noun.endswith(('r', 'z')):
        return noun + 'es'
    if noun.endswith('s'):
        return noun
    return noun + 's'


def adjective_form(adj, g, number):
    """形容詞の性・数の一致 (辞書の語形の表、無ければ -o → -a、複数 -s)"""
    if g == 'm' and number == 'sg':
        return adj
    tags = (('feminine',) if g == 'f' else ('masculine',)) + (('plural',) if number == 'pl' else ('singular',))
    form = find_form(adj, 'adj', tags, avoid=('superlative', 'diminutive', 'augmentative'))
    if form and not form.endswith(('inho', 'inha', 'inhos', 'inhas', 'ona', 'onas', 'ão', 'ões')):
        return form
    base = adj[:-1] + 'a' if g == 'f' and adj.endswith('o') else adj
    if number == 'pl':
        base = plural(base) if not base.endswith(('o', 'a', 'e')) else base + 's'
    return base


def _pronoun(np, case):
    """代名詞 (case: Nom / Acc / Dat / Str)。人称代名詞でなければ None"""
    head = np.head
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.lemma in ('is', 'ille') and not np.modifiers:
        return THIRD[('f' if np.gender == 'f' else 'm', number)][case]
    if head.lemma == 'sē' and case == 'Nom':
        return THIRD[('f' if np.gender == 'f' else 'm', number)]['Nom']
    forms = PRONOUNS.get((head.lemma, number)) or PRONOUNS.get((head.lemma, 'sg'))
    return forms[case] if forms else None


def gender_of(np):
    if np.head is None or np.members:
        return 'm'
    if np.head.pos == 'pronoun':
        return 'f' if np.gender == 'f' else 'm'
    if np.head.proper:
        return 'f' if np.gender == 'f' else 'm'
    noun = word(np.head, 'noun')
    return gender(noun) if noun and not noun.startswith('[') else 'm'


def _gendered(forms, g, number):
    if isinstance(forms, str):
        return forms
    if len(forms) == 2:
        return forms[1] if g == 'f' else forms[0]
    return {('m', 'sg'): forms[0], ('f', 'sg'): forms[1], ('m', 'pl'): forms[2], ('f', 'pl'): forms[3]}[(g, number)]


def noun_phrase(np, case='Nom', article=True, indefinite=False):
    """名詞句 (case は前置詞の後ろなら 'Str'。代名詞の形を選ぶのに使う。indefinite なら不定冠詞 um・uma・uns・umas)"""
    if np.members:
        parts = [noun_phrase(m, case, article, indefinite) for m in np.members]
        conj = ' ou ' if np.conj in ('aut', 'vel') else ' e '
        return ', '.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
    head = np.head
    if head is None:
        return ''
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.pos == 'pronoun':
        if head.lemma in NEGATIVE_PRONOUNS and head.lang in ('', 'la'):
            return NEGATIVE_PRONOUNS[head.lemma]
        found = _pronoun(np, 'Str' if case in ('Str', 'Acc', 'Dat') else 'Nom')
        if found:
            return found
        if head.lemma in DEMONSTRATIVES:
            if np.gender == 'n':   # 中性の指示代名詞: isto・isso・aquilo (複数は estas coisas)
                neuter = {'hic': 'isto', 'hīc': 'isto', 'ille': 'aquilo'}.get(head.lemma, 'isso')
                return neuter if number == 'sg' else _gendered(DEMONSTRATIVES[head.lemma], 'f', 'pl') + ' coisas'
            return _gendered(DEMONSTRATIVES[head.lemma], 'f' if np.gender == 'f' else 'm', number)
        return word(head)
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    g = gender_of(np)
    determiner, quantifier, possessive = None, None, None
    before, after = [], []
    for m in np.modifiers:
        if isinstance(m, NP):   # 形容詞の並列 (bom e corajoso)
            after.append(' e '.join(adjective_form(word(x.head, 'adj'), g, number) for x in m.members))
            continue
        latin = m.lang in ('', 'la')
        if m.lemma in DEMONSTRATIVES and latin:
            determiner = _gendered(DEMONSTRATIVES[m.lemma], g, number)
        elif m.lemma in POSSESSIVES and latin:
            possessive = adjective_form(POSSESSIVES[m.lemma], g, number)
        elif m.lemma in NUMERALS and latin:
            determiner = _gendered(NUMERALS[m.lemma], g, number)
        elif m.lemma in QUANTIFIERS and latin:
            quantifier = _gendered(QUANTIFIERS[m.lemma], g, number)
        else:
            form = word(m, 'adj')
            if not form:
                continue
            if form.startswith('['):
                after.append(form)
                continue
            (before if form in BEFORE_NOUN else after).append(adjective_form(form, g, number))
    noun_form = plural(noun) if number == 'pl' and not head.proper else noun
    if head.pos in ('adj', 'participle'):
        noun_form = adjective_form(noun, g, number)
    if determiner is None and not head.proper and article and quantifier not in ('muito', 'muita', 'muitos', 'muitas',
                                                                                 'pouco', 'pouca', 'poucos', 'poucas'):
        if indefinite or np.definite is False:   # 元の言語の不定冠詞 (um livro)
            determiner = _gendered(('um', 'uma', 'uns', 'umas'), g, number)
        else:
            determiner = _gendered(('o', 'a', 'os', 'as'), g, number)   # 所有詞の前にも冠詞 (o meu livro)
    words = [quantifier, determiner, possessive] + before + [noun_form] + after
    text = ' '.join(w for w in words if w)
    for genitive in np.genitives:
        text += ' ' + with_preposition('de', noun_phrase(genitive, 'Str'))
    for p in np.participles:   # 名詞に掛かる分詞 (hostem fugientem「逃げる敵」→ o inimigo que foge)
        text += ' ' + _attributive_participle(p, g, number)
    for r in np.relatives:
        text += ' ' + relative_clause(r, g, number)
    return text


def _attributive_participle(p, g, number):
    """名詞に掛かる分詞: 現在は que + 節 (que foge)、過去の受動は過去分詞 (a carta escrita)"""
    lex = _participle_verb(p)
    if lex is None:
        return adjective_form(word(p.verb, 'adj'), g, number)
    lemma = word(lex, 'verb')
    if p.tense != 'present' and p.voice == 'passive' and lemma and not lemma.startswith('['):
        return participle_form(lemma, g, number)
    args = [(r, np) for r, np in p.args if r != 'subject']
    clause = Clause(lex, tense='present' if p.tense == 'present' else 'perfect', number=number, args=args)
    return 'que ' + ' '.join(realize(clause, gap='subject', antecedent=(g, number)))


def with_preposition(prep, text):
    """前置詞 + 名詞句 (de o → do、em a → na、a o → ao、de ele → dele、com mim → comigo)"""
    if not text:
        return ''
    first, _, rest = text.partition(' ')
    if prep == 'com' and text in WITH_PRONOUNS:
        return WITH_PRONOUNS[text]
    if (prep, first) in CONTRACTIONS:
        return CONTRACTIONS[(prep, first)] + (' ' + rest if rest else '')
    return prep + ' ' + text


def relative_clause(r, g, number):
    gap = r.gap or 'subject'
    words = realize(r, gap=gap, antecedent=(g, number))
    pronoun = {'subject': 'que', 'object': 'que', 'recipient': 'a quem', 'possessor': 'de quem'}.get(gap, 'que')
    if gap == 'place' or (gap == 'prep' and r.gap_prep and r.gap_prep[0].lemma == 'in'):
        pronoun = 'onde'
    return ' '.join([pronoun] + words)


def prepositional(np, passive=False):
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        return with_preposition('por', noun_phrase(inner, 'Str'))
    if np.prep is not None and np.prep.lang == 'pt' and np.prep.surface:   # 元のポルトガル語の前置詞 (no → em)
        surface = np.prep.surface.lower()
        base = next((p for (p, a), c in CONTRACTIONS.items() if c == surface), surface)
        return with_preposition(base, noun_phrase(inner, 'Str'))
    prep = PREPOSITIONS.get((np.prep.lemma, np.case), 'em') if np.prep is not None else 'em'
    if prep == 'para' and inner.head is not None and inner.head.proper:
        prep = 'a'   # 町の名前 (a Roma)
    return with_preposition(prep, noun_phrase(inner, 'Str'))


# ----------------------------------------------------------------------
# 動詞

TENSE_TAGS = {'present': ('indicative', 'present'), 'imperfect': ('imperfect', 'indicative'),
              'preterite': ('indicative', 'preterite'), 'future': ('future', 'indicative'),
              'pluperfect': ('indicative', 'pluperfect'), 'subjunctive': ('present', 'subjunctive')}


def finite(lemma, tense, person, number):
    """定形 (現在・未完了過去・完全過去・単純未来・接続法現在)。2人称は3人称の形 (você)"""
    if person == 2:
        person = 3
    for table, verb in ((SER, 'ser'), (ESTAR, 'estar'), (TER, 'ter')):
        if lemma == verb and (tense, person, number) in table:
            return table[(tense, person, number)]
    tags = PERSON_TAGS.get((person, number), PERSON_TAGS[(3, 'sg')])
    form = find_form(lemma, 'verb', TENSE_TAGS[tense] + tags,
                     avoid=('conditional',) if tense == 'subjunctive' else ('subjunctive', 'conditional', 'imperative'))
    return form or _regular(lemma, tense, person, number)


def _regular(lemma, tense, person, number):
    key = (person, number)
    stem, ending = lemma[:-2], lemma[-2:]
    if ending not in ('ar', 'er', 'ir'):
        return lemma
    if tense == 'future':
        return lemma + {(1, 'sg'): 'ei', (3, 'sg'): 'á', (1, 'pl'): 'emos', (3, 'pl'): 'ão'}[key]
    if tense == 'imperfect':
        if ending == 'ar':
            return stem + {(1, 'sg'): 'ava', (3, 'sg'): 'ava', (1, 'pl'): 'ávamos', (3, 'pl'): 'avam'}[key]
        return stem + {(1, 'sg'): 'ia', (3, 'sg'): 'ia', (1, 'pl'): 'íamos', (3, 'pl'): 'iam'}[key]
    if tense == 'preterite':
        if ending == 'ar':
            return stem + {(1, 'sg'): 'ei', (3, 'sg'): 'ou', (1, 'pl'): 'amos', (3, 'pl'): 'aram'}[key]
        v = 'e' if ending == 'er' else 'i'
        return stem + {(1, 'sg'): 'i', (3, 'sg'): v + 'u', (1, 'pl'): v + 'mos', (3, 'pl'): v + 'ram'}[key]
    if tense == 'subjunctive':
        v = 'e' if ending == 'ar' else 'a'
        return stem + {(1, 'sg'): v, (3, 'sg'): v, (1, 'pl'): v + 'mos', (3, 'pl'): v + 'm'}[key]
    v = ending[0] if ending != 'ir' else 'e'
    return stem + {(1, 'sg'): 'o', (3, 'sg'): v, (1, 'pl'): ending[0] + 'mos', (3, 'pl'): v + 'm'}[key]


def participle_form(lemma, g='m', number='sg'):
    form = find_form(lemma, 'verb', ('participle', 'masculine', 'singular')) or find_form(lemma, 'verb', ('participle',))
    if form is None:
        form = lemma[:-2] + ('ado' if lemma.endswith('ar') else 'ido') if lemma.endswith(('ar', 'er', 'ir')) else lemma
    if form.endswith('o'):
        form = form[:-1] + ('a' if g == 'f' else 'o')
    return form + ('s' if number == 'pl' else '')


def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            subject.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[subject.head.lemma], subject.number or 'sg'
    if subject is not None:
        return 3, 'pl' if subject.members or subject.number == 'pl' else 'sg'
    return clause.person or 3, clause.number or 'sg'


def verb_group(clause, person, number, agree=('m', 'sg'), subjunctive=False, infinitive=False):
    """動詞の語の列 (定形と、続く過去分詞)。否定の não・接語の代名詞は呼ぶ側で"""
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return [lemma] if lemma else []
    if lemma.endswith('-se'):
        lemma = lemma[:-3]   # 代名動詞 (levantar-se): 再帰の代名詞は呼ぶ側で
    g, n = agree
    if infinitive:
        return [lemma]
    if clause.voice == 'passive':
        if clause.tense in ('perfect', 'past-perfect'):
            tense = 'imperfect' if clause.tense == 'past-perfect' else 'preterite'
            return [finite('ser', tense, person, number), participle_form(lemma, g, n)]
        tense = {'imperfect': 'imperfect', 'future': 'future'}.get(clause.tense, 'present')
        if subjunctive and tense == 'present':
            tense = 'subjunctive'
        return [finite('ser', tense, person, number), participle_form(lemma, g, n)]
    if clause.tense in ('past-perfect', 'future-perfect'):
        tense = 'imperfect' if clause.tense == 'past-perfect' else 'future'
        return [finite('ter', tense, person, number), participle_form(lemma)]
    tense = {'imperfect': 'imperfect', 'future': 'future', 'perfect': 'preterite'}.get(clause.tense, 'present')
    if subjunctive and tense == 'present':
        tense = 'subjunctive'   # 接続法現在 (para que ele venha)
    return [finite(lemma, tense, person, number)]


def _copula(clause, person, number, location=False):
    tense = {'imperfect': 'imperfect', 'perfect': 'preterite', 'past-perfect': 'imperfect',
             'future': 'future'}.get(clause.tense, 'present')
    return finite('estar' if location else 'ser', tense, person, number)


def _clitic(np, case):
    """目的語・受け手の接語の代名詞 (me・te・o・a・lhe・nos・os・as・lhes)。代名詞でなければ None"""
    if np is None or np.members or np.head is None or np.head.pos != 'pronoun':
        return None
    if np.head.lemma not in ('ego', 'tū', 'is', 'ille', 'sē'):
        return None
    if np.head.lemma == 'tū' and np.number == 'pl':
        return None   # vocês は動詞の後ろ (vi vocês)
    return _pronoun(np, case)


def _enclitic(infinitive, clitic):
    """不定詞 + 3人称の接語 (ler + o → lê-lo、amar + a → amá-la、partir + os → parti-los)"""
    if clitic not in ('o', 'a', 'os', 'as') or not infinitive.endswith(('ar', 'er', 'ir')):
        return None
    stem = infinitive[:-1]
    stem = stem[:-1] + {'a': 'á', 'e': 'ê', 'i': 'i'}[stem[-1]]
    return stem + '-l' + clitic


def _modal(clause, gap, antecedent, subjunctive):
    """話法の動詞 + 不定詞の節 (Eu posso lê-lo、Eu quero ir)。当てはまらなければ None"""
    if clause.copula or len(clause.infinitives) != 1 or clause.verb is None:
        return None
    modal = MODALS.get(clause.verb.lemma) if clause.verb.lang in ('', 'la') else \
        (clause.verb.lemma if clause.verb.lemma in MODALS.values() else None)
    if modal is None:
        return None
    inner = clause.infinitives[0]
    if inner.role('subject') and modal not in ('fazer', 'deixar'):
        return None   # 主語のある補文は que 節 (Eu quero que você venha)
    preposition = None
    if ' ' in modal:
        modal, preposition = modal.split(' ', 1)   # começar a + 不定詞
    person_np = (inner.role('subject') or [None])[0] if modal in ('fazer', 'deixar') else None
    inner_words = realize(dataclasses.replace(inner, mood='indicative', args=[(r, np) for r, np in inner.args
                                                                             if r != 'subject']), gap='subject',
                          infinitive=True)
    outer = dataclasses.replace(clause, verb=Lex(modal, 'verb', lang='pt'), infinitives=[])
    if person_np is not None:
        outer = dataclasses.replace(outer, args=list(outer.args) + [('object', person_np)])
    words = realize(outer, gap, antecedent, subjunctive)
    return words + ([preposition] if preposition else []) + inner_words


# 直接の疑問文の疑問の副詞
QUESTION_WORDS = {'quandō': 'quando', 'ubi': 'onde', 'cūr': 'por que', 'quārē': 'por que', 'quōmodo': 'como',
                  'unde': 'de onde', 'quō': 'aonde', 'quotiēns': 'quantas vezes'}
WHO = {'quis', 'quem', 'cui', 'cūius', 'cuius', 'quibus'}


def direct_question(clause):
    """疑問詞のある直接の疑問文: 疑問詞 + 平叙の語順 (Quando ele vem?・Quem o menino vê?・O que a menina faz?)。
    「どこにいるか」は estar + 主語 (Onde está a menina?)"""
    from .frame import interrogative_np, without_interrogative, where_is
    owner, role, wh = interrogative_np(clause)
    plain = dataclasses.replace(clause, question_word='', question=False)
    if wh is None and where_is(clause) is not None:
        return [QUESTION_WORDS[clause.question_word], _copula(clause, *_person(clause), location=True),
                noun_phrase(where_is(clause), 'Nom')]
    if wh is None:
        return [QUESTION_WORDS.get(clause.question_word, clause.question_word)] + realize(plain)
    if owner is clause and role == 'subject':
        return realize(plain)
    first = 'quem' if clause.question_word in WHO and wh.gender != 'n' else 'o que'
    if role == 'prep':
        first = prepositional(dataclasses.replace(wh, head=dataclasses.replace(wh.head, lemma='quis' if first == 'quem'
                                                                              else 'quid')))
    elif role == 'recipient':
        first = 'a ' + first
    return [first] + realize(without_interrogative(plain))


def realize(clause, gap=None, antecedent=None, subjunctive=False, infinitive=False):
    from .frame import lexical_negation, periphrastic, reflexive_subject
    clause = lexical_negation(periphrastic(clause))
    if clause.question and clause.question_word and clause.mood == 'indicative' and gap is None and not infinitive:
        return direct_question(clause)
    modal = _modal(clause, gap, antecedent, subjunctive)
    if modal is not None:
        return modal
    complements = [inner for inner in clause.infinitives if inner.infinitive_kind in ('saying', 'command', 'emotion') and
                   inner.role('subject')]
    if complements:   # 補文は que 節 (Eu sei que você vem、Eu quero que você venha)
        main = realize(dataclasses.replace(clause, infinitives=[i for i in clause.infinitives if i not in complements]),
                       gap, antecedent, subjunctive, infinitive)
        for inner in complements:
            main += ['que'] + realize(dataclasses.replace(reflexive_subject(inner, clause), mood='indicative',
                                                          infinitive_kind=''),
                                      subjunctive=inner.infinitive_kind in SUBJUNCTIVE_KINDS)
        return main
    person, number = _person(clause)
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            (subject.head.lemma, number) in VERB_PERSON:
        person, number = VERB_PERSON[(subject.head.lemma, number)]
    elif person == 2:
        person = 3   # você・vocês
    words = []
    negative_subject = subject is not None and subject.head is not None and subject.head.lemma in NEGATIVE_PRONOUNS
    if subject is not None and gap != 'subject' and not infinitive:
        found = _pronoun(subject, 'Nom') if subject.head is not None and subject.head.pos == 'pronoun' and \
            not subject.members and subject.head.lemma not in NEGATIVE_PRONOUNS else None
        words.append(found or noun_phrase(subject, 'Nom'))
    elif subject is None and gap is None and clause.mood != 'imperative' and not infinitive:
        pronoun = {(1, 'sg'): 'eu', (1, 'pl'): 'nós'}.get((person, number))
        if pronoun is None and clause.person == 2:
            pronoun = 'você' if number == 'sg' else 'vocês'
        if pronoun is None:
            pronoun = 'ele' if number == 'sg' else 'eles'
        words.append(pronoun)
    agree = antecedent if gap == 'subject' and antecedent else \
        ((gender_of(subject), 'pl' if subject.members or subject.number == 'pl' else 'sg') if subject is not None
         else ('m', number))
    adverbs = [word(a, 'adv') for a in clause.adverbs if a.lemma != 'nōn']
    negation = ['não'] if clause.negated and not negative_subject else []
    if clause.copula:
        complements = clause.role('complement')
        preps = [prepositional(np) for role, np in clause.args if role == 'prep']
        owner = (clause.role('recipient') or [None])[0]
        if not complements and subject is not None and owner is not None and gap is None:
            # 所有の与格 (Mihi est liber「私には本がある」): 所有者 + ter + 名詞 (Eu tenho um livro)
            have = dataclasses.replace(clause, copula=False, verb=Lex('ter', 'verb', lang='pt'),
                                       args=[('subject', owner), ('object', dataclasses.replace(subject, definite=False))] +
                                       [(r, np) for r, np in clause.args if r not in ('subject', 'recipient')])
            return realize(have, gap, antecedent, subjunctive, infinitive)
        if not complements and subject is not None and (not preps or subject.definite is False) and gap is None:
            # 存在の文 (Agricola est「農夫がいる」、不定の主語と場所: Há um livro na mesa): há + 名詞
            verb = {'imperfect': 'havia', 'perfect': 'houve', 'future': 'haverá'}.get(clause.tense, 'há')
            noun = noun_phrase(subject, 'Acc', indefinite=True)
            return negation + [verb, noun] + preps + adverbs
        verb = _copula(clause, person, number, location=not complements and bool(preps))
        tail = []
        if complements:
            comp = complements[0]
            adjectival = all(m.head is not None and m.head.pos in ('adj', 'participle') for m in comp.members) \
                if comp.members else comp.head is not None and comp.head.pos in ('adj', 'participle')
            if adjectival:   # 形容詞の補語は主語に一致 (A estrada é longa e larga)
                g, n = agree
                forms = [adjective_form(word(m.head, 'adj'), g, n) for m in comp.members] if comp.members else \
                    [adjective_form(word(comp.head, 'adj'), g, n)]
                tail.append(' e '.join(f for f in forms if f))
            else:
                tail.append(noun_phrase(comp, 'Nom', article=comp.head is not None and comp.head.pos != 'noun' or
                                        bool(comp.modifiers)))
        return [w for w in words + negation + [verb] + adverbs + tail + preps if w]
    clitics, objects, after_verb = [], [], []
    obj = (clause.role('object') or [None])[0]
    if obj is not None and gap != 'object':
        clitic = _clitic(obj, 'Acc')
        if clitic:
            clitics.append(clitic)
        else:
            objects.append(noun_phrase(obj, 'Acc'))
    for np in clause.role('recipient'):
        clitic = _clitic(np, 'Dat')
        if clitic:
            clitics.insert(0, clitic)
        else:
            objects.append(with_preposition('a', noun_phrase(np, 'Str')))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            objects.append(prepositional(np, clause.voice == 'passive'))
        elif np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
            objects.append(WORDS[np.head.lemma])
        elif role == 'means':   # 受動の動作主 (人) は por、ほかは手段 com
            objects.append(with_preposition('por' if np.animate and clause.voice == 'passive' else 'com',
                                            noun_phrase(np, 'Str')))
        elif role == 'possessor':
            objects.append(with_preposition('de', noun_phrase(np, 'Str')))
        else:
            objects.append(with_preposition('em', noun_phrase(np, 'Str')))
    lemma_pt = word(clause.verb, 'verb')
    if lemma_pt.endswith('-se'):   # 代名動詞の再帰の代名詞 (ele se levanta、eu me chamo)
        clitics.insert(0, {(1, 'sg'): 'me', (1, 'pl'): 'nos'}.get((person, number), 'se'))
    verb = verb_group(clause, person, number, agree, subjunctive, infinitive)
    if infinitive and len(clitics) == 1 and verb:
        enclitic = _enclitic(verb[0], clitics[0])
        if enclitic:   # posso lê-lo
            return [w for w in negation + [enclitic] + adverbs + objects if w]
    if clause.mood == 'imperative':
        form = find_form(lemma_pt, 'verb', ('imperative', 'second-person', 'plural' if number == 'pl' else 'singular'))
        if clause.negated or not form:   # 否定の命令は接続法 (não fale)
            form = finite(lemma_pt, 'subjunctive', 3, number)
        return [w for w in negation + clitics + [form] + objects + adverbs if w]
    negative_object = any(np.head is not None and np.head.lemma in NEGATIVE_PRONOUNS for r, np in clause.args
                          if r != 'subject')
    if negative_object and not negation and not negative_subject:
        negation = ['não']   # não vi ninguém (動詞の後ろの否定の代名詞にも não)
    for inner in clause.infinitives:   # 知覚の動詞 + 主語のある不定詞 (Eu vejo a menina cantar)、主語の無い不定詞
        inner_subject = (inner.role('subject') or [None])[0]
        if inner_subject is not None:
            objects.append(noun_phrase(inner_subject, 'Acc'))
        objects += realize(dataclasses.replace(inner, args=[(r, np) for r, np in inner.args if r != 'subject']),
                           gap='subject', infinitive=True)
    for p in clause.adjuncts:
        if p.kind != 'absolute':
            objects.append(_adverbial_participle(p))
    return [w for w in words + negation + clitics + verb + after_verb + adverbs + objects if w]


def gerund(lemma):
    """現在分詞 (動名詞): colher → colhendo"""
    form = find_form(lemma, 'verb', ('gerund',))
    if form:
        return form
    return lemma[:-1] + 'ndo' if lemma.endswith(('ar', 'er', 'ir')) else lemma


def _participle_verb(p):
    return Lex(p.verb.verb, 'verb', p.verb.verb_ja, lang=p.verb.lang) if p.verb.verb else None


def _adverbial_participle(p):
    """述語的な分詞句: 現在は動名詞 (colhendo as flores)、過去は depois de + 不定詞"""
    lex = _participle_verb(p)
    lemma = word(lex, 'verb') if lex is not None else ''
    if not lemma or lemma.startswith('['):
        return word(p.verb, 'adj')
    passive = p.voice == 'passive' and p.tense != 'present'
    rest = [noun_phrase(np, 'Acc') if r == 'object' else prepositional(np, passive) if r == 'prep' else
            with_preposition('por' if passive else 'com' if r == 'means' else 'a', noun_phrase(np, 'Str'))
            for r, np in p.args if r != 'subject']
    if passive:   # 過去の受動の分詞は主語に一致した過去分詞 (comovida pelas palavras)
        head = participle_form(lemma, 'f' if p.gender == 'f' else 'm', p.number or 'sg')
    else:
        head = gerund(lemma) if p.tense == 'present' else 'depois de ' + lemma
    return ' '.join([head] + rest)


def absolute(p):
    """独立奪格: 現在は enquanto + 節 (enquanto a menina canta)、過去は depois que + 節 (depois que o rei morreu)"""
    lex = _participle_verb(p)
    if lex is None or p.subject is None:
        return ''
    args = [('subject', p.subject)] + [(r, np) for r, np in p.args if r != 'subject']
    if p.tense == 'present':
        return 'enquanto ' + ' '.join(realize(Clause(lex, args=args)))
    voice = 'passive' if p.voice == 'passive' else 'active'
    return 'depois que ' + ' '.join(realize(Clause(lex, tense='perfect', voice=voice, args=args)))


def vocative(np):
    return noun_phrase(np, 'Nom', article=False)


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
        subordinate = rest.subordinator in SUBORDINATORS and \
            (k + 1 < len(clauses) or k > 0 and not rest.after_main or rest.subordinator == 'quīn')   # 主節の後ろの従属節も
        if subordinate:
            words.append(SUBORDINATORS[rest.subordinator])
        words += [absolute(p) + ',' for p in rest.adjuncts if p.kind == 'absolute' and absolute(p)]
        words += realize(rest, subjunctive=subordinate and rest.subordinator in SUBJUNCTIVE_AFTER)
        parts.append(' '.join(w for w in words if w))
    text = ', '.join(parts).replace(' ,', ',').replace(',,', ',').rstrip(',')
    return text[:1].upper() + text[1:] + '.'


# ----------------------------------------------------------------------
# 比較の表

PRO_DROP_HOW = '代名詞を補う (eu・ele …。ブラジルの話し言葉)'
PREDICATE_HOW = '人称・数・時制の語形 (vê・viu・via)、過去完了 tinha + 過去分詞、受動 ser + 過去分詞、否定 não'
COPULA_HOW = 'ser + 補語 (形容詞は主語の性・数に一致)、場所は estar'
ADDRESS_HOW = '冠詞なし'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, '前置詞 por (受動の動作主)'
        return text, '前置詞 %s' % text.split(' ')[0]
    if role == 'address':
        return vocative(np), ADDRESS_HOW
    if role == 'subject':
        return noun_phrase(np, 'Nom'), '動詞の前 (格の印なし)'
    if role == 'object':
        clitic = _clitic(np, 'Acc')
        return (clitic, '動詞の前の接語の代名詞') if clitic else (noun_phrase(np, 'Acc'), '動詞の後ろ (格の印なし)')
    if role == 'recipient':
        clitic = _clitic(np, 'Dat')
        return (clitic, '動詞の前の接語の代名詞 (lhe・lhes)') if clitic else \
            (with_preposition('a', noun_phrase(np, 'Str')), '前置詞 a')
    if role == 'possessor':
        return with_preposition('de', noun_phrase(np, 'Str')), '前置詞 de'
    if role == 'means':
        return with_preposition('com', noun_phrase(np, 'Str')), '前置詞 com'
    return with_preposition('em', noun_phrase(np, 'Str')), '前置詞 em'


def compare_predicate(clause, reduced):
    person, number = _person(clause)
    if person == 2:
        person = 3
    if clause.copula:
        words = realize(reduced)
        subject = (clause.role('subject') or [None])[0]
        head = noun_phrase(subject, 'Nom') if subject is not None else ''
        text = ' '.join(words)
        return (text[len(head):].strip() if head and text.startswith(head) else text), COPULA_HOW
    words = (['não'] if clause.negated else []) + verb_group(clause, person, number)
    return ' '.join(words), PREDICATE_HOW
