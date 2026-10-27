#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からフランス語の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)。名詞の性と、名詞・形容詞・動詞の語形は
#     辞書 (fr/wiktionary.sqlite の語形の表。Wiktionary の変化表) から。無ければ規則 (複数 -s、女性 -e)
#   名詞句: 定冠詞 (le / la / l' / les。固有名詞は冠詞なし) + 前に置く形容詞 (beau・petit・grand …) + 名詞 +
#     後ろに置く形容詞 (性・数の一致) + de + 属格の名詞句。前置詞と冠詞の縮約 (à le → au、de les → des)
#   語順: 主語 - (ne) - 接語の代名詞 (me・le・lui …) - 動詞 (- pas) - 過去分詞 - 目的語 - à + 受け手 - 前置詞句。
#     関係節は qui (主語の空所)・que (目的語の空所)
#   時制: 現在、複合過去 (avoir / être + 過去分詞。完了)、半過去 (未完了)、大過去 (avait + 過去分詞)、単純未来、
#     受動 (être + 過去分詞)。否定 ne … pas。存在の文は il y a
#
import dataclasses
import functools
import os
import re
import sqlite3

from dragoman.core import paths
from . import transfer, english
from .frame import NP

VOWEL_START = re.compile(r'^[aeiouyhàâéèêëîïôûœæ]', re.I)
# 有音の h (le héros・la honte) は母音扱いしない
ASPIRATED_H = ('héros', 'honte', 'haut', 'hache', 'haine', 'hall', 'hasard', 'hibou', 'homard', 'huit', 'hurler')
PRONOUNS = {  # (ラテン語の代名詞, 数) → {Nom: 主語, Acc: 直接目的の接語, Dat: 間接目的の接語, Str: 強勢形}
    ('ego', 'sg'): {'Nom': 'je', 'Acc': 'me', 'Dat': 'me', 'Str': 'moi'},
    ('tū', 'sg'): {'Nom': 'tu', 'Acc': 'te', 'Dat': 'te', 'Str': 'toi'},
    ('ego', 'pl'): {'Nom': 'nous', 'Acc': 'nous', 'Dat': 'nous', 'Str': 'nous'},
    ('tū', 'pl'): {'Nom': 'vous', 'Acc': 'vous', 'Dat': 'vous', 'Str': 'vous'},
    ('sē', 'sg'): {'Nom': 'il', 'Acc': 'se', 'Dat': 'se', 'Str': 'soi'},
    ('quis', 'sg'): {'Nom': 'qui', 'Acc': 'qui', 'Dat': 'qui', 'Str': 'qui'},
    ('quid', 'sg'): {'Nom': 'que', 'Acc': 'que', 'Dat': 'quoi', 'Str': 'quoi'}}
THIRD = {('m', 'sg'): {'Nom': 'il', 'Acc': 'le', 'Dat': 'lui', 'Str': 'lui'},
         ('f', 'sg'): {'Nom': 'elle', 'Acc': 'la', 'Dat': 'lui', 'Str': 'elle'},
         ('m', 'pl'): {'Nom': 'ils', 'Acc': 'les', 'Dat': 'leur', 'Str': 'eux'},
         ('f', 'pl'): {'Nom': 'elles', 'Acc': 'les', 'Dat': 'leur', 'Str': 'elles'}}
DEMONSTRATIVES = {'hic', 'hīc', 'iste', 'ille', 'is'}
POSSESSIVES = {'meus': ('mon', 'ma', 'mes'), 'tuus': ('ton', 'ta', 'tes'), 'suus': ('son', 'sa', 'ses'),
               'noster': ('notre', 'notre', 'nos'), 'vester': ('votre', 'votre', 'vos')}
NUMERALS = {'ūnus': 'un', 'duo': 'deux', 'trēs': 'trois', 'quattuor': 'quatre', 'quīnque': 'cinq', 'sex': 'six',
            'septem': 'sept', 'octō': 'huit', 'novem': 'neuf', 'decem': 'dix', 'centum': 'cent', 'mīlle': 'mille'}
QUANTIFIERS = {'omnis': ('tout', 'toute', 'tous', 'toutes'), 'tōtus': ('tout', 'toute', 'tous', 'toutes')}
# 名詞の前に置く形容詞 (BANGS: 美・年齢・数・善悪・大きさ)
BEFORE_NOUN = {'beau', 'bon', 'grand', 'petit', 'jeune', 'vieux', 'nouveau', 'joli', 'mauvais', 'long', 'gros',
               'haut', 'premier', 'dernier', 'autre', 'meilleur', 'même', 'seul', 'cher', 'pauvre', 'vrai', 'faux'}
IRREGULAR_ADJECTIVES = {'beau': ('belle', 'beaux', 'belles'), 'nouveau': ('nouvelle', 'nouveaux', 'nouvelles'),
                        'vieux': ('vieille', 'vieux', 'vieilles'), 'bon': ('bonne', 'bons', 'bonnes'),
                        'blanc': ('blanche', 'blancs', 'blanches'), 'long': ('longue', 'longs', 'longues'),
                        'gros': ('grosse', 'gros', 'grosses'), 'heureux': ('heureuse', 'heureux', 'heureuses')}
PREPOSITIONS = {('in', 'Abl'): 'dans', ('in', 'Acc'): 'dans', ('ad', 'Acc'): 'à', ('ex', 'Abl'): 'de',
                ('ē', 'Abl'): 'de', ('ab', 'Abl'): 'de', ('ā', 'Abl'): 'de', ('cum', 'Abl'): 'avec',
                ('dē', 'Abl'): 'sur', ('sine', 'Abl'): 'sans', ('per', 'Acc'): 'par', ('propter', 'Acc'): 'à cause de',
                ('ob', 'Acc'): 'à cause de', ('post', 'Acc'): 'après', ('ante', 'Acc'): 'devant', ('sub', 'Abl'): 'sous',
                ('sub', 'Acc'): 'sous', ('super', 'Acc'): 'sur', ('prō', 'Abl'): 'pour', ('apud', 'Acc'): 'chez',
                ('contrā', 'Acc'): 'contre', ('inter', 'Acc'): 'entre', ('prope', 'Acc'): 'près de',
                ('trāns', 'Acc'): 'au-delà de', ('circum', 'Acc'): 'autour de'}
CONNECTIVES = {'et': 'et', 'que': 'et', 'atque': 'et', 'ac': 'et', 'sed': 'mais', 'at': 'mais', 'autem': 'mais',
               'enim': 'car', 'nam': 'car', 'igitur': 'donc', 'itaque': 'donc', 'tamen': 'pourtant', 'tum': 'alors',
               'deinde': 'ensuite', 'aut': 'ou', 'vel': 'ou'}
SUBORDINATORS = {'cum': 'quand', 'ubi': 'quand', 'sī': 'si', 'quod': 'parce que', 'quia': 'parce que',
                 'quoniam': 'puisque', 'dum': 'pendant que', 'postquam': 'après que', 'ut': 'pour que',
                 'quamquam': 'bien que', 'etsī': 'bien que', 'priusquam': 'avant que', 'antequam': 'avant que',
                 'dōnec': "jusqu'à ce que", 'simul': 'dès que', 'nisi': 'si … ne … pas', 'quīn': 'sans que'}
# 後ろの動詞を接続法にする接続詞 (sans que personne ne s'en aperçoive、bien qu'il pleuve)
SUBJUNCTIVE_AFTER = {'quīn', 'quamquam', 'etsī', 'priusquam', 'antequam', 'ut', 'nē', 'dōnec'}
# 否定の代名詞 (ne … personne・ne … rien は pas を付けない)
NEGATIVE_PRONOUNS = {'nēmō', 'nihil', 'nūllus'}
WORDS = {'nēmō': 'personne', 'nihil': 'rien', 'nūllus': 'personne', 'semper': 'toujours', 'saepe': 'souvent', 'iam': 'déjà', 'nunc': 'maintenant', 'hodiē': "aujourd'hui",
         'crās': 'demain', 'heri': 'hier', 'ibi': 'là', 'hīc': 'ici', 'etiam': 'aussi', 'quoque': 'aussi',
         'valdē': 'très', 'magnopere': 'beaucoup', 'statim': 'immédiatement', 'mox': 'bientôt', 'tandem': 'enfin',
         'iterum': 'de nouveau', 'numquam': 'jamais', 'bene': 'bien', 'male': 'mal', 'posteā': 'ensuite', 'diū': 'longtemps'}
PERSON_TAGS = {(1, 'sg'): ('first-person', 'singular'), (2, 'sg'): ('second-person', 'singular'),
               (3, 'sg'): ('singular', 'third-person'), (1, 'pl'): ('first-person', 'plural'),
               (2, 'pl'): ('plural', 'second-person'), (3, 'pl'): ('plural', 'third-person')}
AVOIR = {('present', 1, 'sg'): 'ai', ('present', 2, 'sg'): 'as', ('present', 3, 'sg'): 'a', ('present', 1, 'pl'): 'avons',
         ('present', 2, 'pl'): 'avez', ('present', 3, 'pl'): 'ont', ('imperfect', 1, 'sg'): 'avais',
         ('imperfect', 2, 'sg'): 'avais', ('imperfect', 3, 'sg'): 'avait', ('imperfect', 1, 'pl'): 'avions',
         ('imperfect', 2, 'pl'): 'aviez', ('imperfect', 3, 'pl'): 'avaient'}
ETRE = {('present', 1, 'sg'): 'suis', ('present', 2, 'sg'): 'es', ('present', 3, 'sg'): 'est', ('present', 1, 'pl'): 'sommes',
        ('present', 2, 'pl'): 'êtes', ('present', 3, 'pl'): 'sont', ('imperfect', 1, 'sg'): 'étais',
        ('imperfect', 2, 'sg'): 'étais', ('imperfect', 3, 'sg'): 'était', ('imperfect', 1, 'pl'): 'étions',
        ('imperfect', 2, 'pl'): 'étiez', ('imperfect', 3, 'pl'): 'étaient', ('future', 1, 'sg'): 'serai',
        ('future', 2, 'sg'): 'seras', ('future', 3, 'sg'): 'sera', ('future', 1, 'pl'): 'serons',
        ('future', 2, 'pl'): 'serez', ('future', 3, 'pl'): 'seront'}
# de + 名詞を目的語にした動詞 (解析の french/morphology.DE_OBJECT_VERBS と同じ)。フランス語に戻すとき de を付ける
DE_OBJECT_VERBS = {'se apercevoir', 'se méfier', 'se souvenir', 'se moquer', 'se servir', 'se occuper', 'profiter',
                   'douter', 'se rendre compte', 'avoir besoin'}
# 複合過去で être を取る動詞 (移動・変化)
ETRE_VERBS = {'aller', 'venir', 'arriver', 'partir', 'entrer', 'sortir', 'naître', 'mourir', 'monter', 'descendre',
              'tomber', 'rester', 'retourner', 'devenir', 'revenir', 'rentrer', 'parvenir'}


@functools.lru_cache(maxsize=1)
def _db():
    path = paths.data('fr', 'wiktionary.sqlite')
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
    """語形の表から、印 wanted をすべて持つ (avoid を持たない) 形。無ければ None"""
    wanted, avoid = set(wanted), set(avoid)
    found = [form for form, tags in _forms(lemma, pos) if wanted <= tags and not tags & avoid]
    if not found:
        return None
    # 1990年の新綴り (plait・connait) より従来の綴り (plaît・connaît): アクセント記号の多いほう
    return max(found, key=lambda f: sum(c in 'îûâêô' for c in f))


@functools.lru_cache(maxsize=50000)
def gender(noun):
    db = _db()
    if db is None:
        return 'm'
    # 辞書の最初の項目 (Wiktionary で先に載る主な語義: livre「本」(男性) を livre「ポンド」(女性) より)
    row = db.execute("SELECT gender FROM lemmas WHERE key = ? AND pos IN ('noun', 'name') AND gender IN ('m', 'f') "
                     "ORDER BY pos = 'name', rowid LIMIT 1", (noun.lower(),)).fetchone()
    if row:
        return row[0]
    # 見出しの無い女性形 (professeure: professeur の語形の行に feminine)
    tags = [set(t.split(',')) for (t,) in db.execute("SELECT tags FROM forms WHERE form = ? AND pos = 'noun'",
                                                    (noun.lower(),))]
    return 'f' if tags and all('feminine' in t for t in tags) else 'm'


def _vowel(word):
    return bool(VOWEL_START.match(word)) and not word.lower().startswith(ASPIRATED_H)


def elide(word, following):
    """エリジオン (le → l'、de → d'、que → qu'、ne → n'、je → j'、me → m')"""
    if following and _vowel(following) and word in ('le', 'la', 'de', 'que', 'ne', 'je', 'me', 'te', 'se', 'ce'):
        return word[:-1] + "'"
    return word


def join(words):
    """語をつなぐ (エリジオンの ' の後ろは空けない)"""
    out = ''
    for w in words:
        if not w:
            continue
        out += w if out.endswith("'") or not out else ' ' + w
    return out


def _elided(words):
    """語の列のエリジオンを当てる"""
    out = list(words)
    for k in range(len(out) - 1):
        nxt = next((w for w in out[k + 1:] if w), '')
        out[k] = elide(out[k], nxt.split(' ')[0]) if out[k] else out[k]
    return out


# ----------------------------------------------------------------------
# 名詞句

def plural(noun):
    form = find_form(noun, 'noun', ('plural',))
    if form:
        return form
    if noun.endswith(('s', 'x', 'z')):
        return noun
    if noun.endswith(('eau', 'au', 'eu')):
        return noun + 'x'
    if noun.endswith('al'):
        return noun[:-2] + 'aux'
    return noun + 's'


def adjective_form(adj, g, number):
    """形容詞の性・数の一致 (辞書の語形の表、無ければ -e・-s)"""
    if g == 'm' and number == 'sg':
        return adj
    if adj in IRREGULAR_ADJECTIVES:
        f, mp, fp = IRREGULAR_ADJECTIVES[adj]
        return {('f', 'sg'): f, ('m', 'pl'): mp, ('f', 'pl'): fp}[(g, number)]
    tags = (('feminine',) if g == 'f' else ('masculine',)) + (('plural',) if number == 'pl' else ('singular',))
    form = find_form(adj, 'adj', tags)
    if form is None and g == 'f' and number == 'pl':
        form = find_form(adj, 'adj', ('feminine', 'plural'))
    if form:
        return form
    base = adj if g == 'm' or adj.endswith('e') else adj + 'e'
    if number == 'pl' and not base.endswith(('s', 'x')):
        base += 's'
    return base


def available():
    return transfer.available('fr')


def to_french(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'fr':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'fr')
        return found[0] if found else _latin_name(lex.lemma)
    target = transfer.best(lex, 'fr', pos)
    return target.lemma if target else None


def _latin_name(lemma):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', lemma) if not unicodedata.combining(c))


def word(lex, pos=None):
    found = to_french(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


def _pronoun(np, case):
    """代名詞 (case: Nom / Acc / Dat / Str)。人称代名詞でなければ None"""
    head = np.head
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.lemma in ('is', 'ille') and not np.modifiers:
        return THIRD[('f' if np.gender == 'f' else 'm', number)][case]
    forms = PRONOUNS.get((head.lemma, number)) or PRONOUNS.get((head.lemma, 'sg'))
    return forms[case] if forms else None


def gender_of(np):
    if np.head is None or np.members:
        return 'm'
    if np.head.pos == 'pronoun':
        return 'f' if np.gender == 'f' else 'm'
    noun = word(np.head, 'noun')
    if np.head.proper:
        return 'f' if np.gender == 'f' else 'm'
    return gender(noun) if noun and not noun.startswith('[') else 'm'


def noun_phrase(np, case='Nom', article=True, indefinite=False):
    """名詞句 (case は前置詞の後ろなら 'Str'。代名詞の形を選ぶのに使う。indefinite なら不定冠詞 un・une・des)"""
    if np.members:
        parts = [noun_phrase(m, case, article, indefinite) for m in np.members]
        conj = ' ou ' if np.conj in ('aut', 'vel') else ' et '
        return ', '.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
    if np.gender == 'f' and np.head is not None and np.head.pos == 'noun' and \
            (np.animate or english.female_counterpart(np.head)):
        np = _feminine_noun(np, force=True)   # 女性の人の名詞 (magistra・professora) は女性形
    head = np.head
    if head is None:
        return ''
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.pos == 'pronoun':
        found = _pronoun(np, 'Str' if case in ('Str', 'Acc', 'Dat') else 'Nom')
        if found:
            return found
        if head.lemma in DEMONSTRATIVES:
            return 'celui-ci' if np.gender != 'f' else 'celle-ci'
        return word(head)
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    g = gender_of(np)
    determiner = None
    before, after = [], []
    quantifier = None
    for m in np.modifiers:
        if isinstance(m, NP):
            after += [x.head for x in m.members]
            continue
        if m.lemma in DEMONSTRATIVES and m.lang in ('', 'la'):
            determiner = 'ces' if number == 'pl' else 'cette' if g == 'f' else 'cet' if _vowel(noun) else 'ce'
        elif m.lemma in POSSESSIVES and m.lang in ('', 'la'):
            m_, f_, p_ = POSSESSIVES[m.lemma]
            determiner = p_ if number == 'pl' else (f_ if g == 'f' and not _vowel(noun) else m_)
        elif m.lemma in NUMERALS and m.lang in ('', 'la'):
            determiner = NUMERALS[m.lemma] if m.lemma != 'ūnus' else ('une' if g == 'f' else 'un')
        elif m.lemma in QUANTIFIERS and m.lang in ('', 'la'):
            ms, fs, mp, fp = QUANTIFIERS[m.lemma]
            quantifier = {('m', 'sg'): ms, ('f', 'sg'): fs, ('m', 'pl'): mp, ('f', 'pl'): fp}[(g, number)]
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
    if determiner is None and not head.proper and article:
        if indefinite or np.definite is False:   # 元の言語の不定冠詞 (un livre)
            determiner = 'des' if number == 'pl' else ('une' if g == 'f' else 'un')
        else:
            determiner = 'les' if number == 'pl' else ('la' if g == 'f' else 'le')
    words = [quantifier, determiner] + before + [noun_form] + after
    text = join(_elided([w for w in words if w]))
    for genitive in np.genitives:
        text += ' ' + with_preposition('de', noun_phrase(genitive, 'Str'))
    for r in np.relatives:
        text += ' ' + relative_clause(r, g, number)
    return text


def with_preposition(prep, text):
    """前置詞 + 名詞句 (à le → au、à les → aux、de le → du、de les → des、de + 母音 → d')"""
    if not text:
        return ''
    first, _, rest = text.partition(' ')
    if prep in ('à', 'de') and first in ('le', 'les') and rest:
        return {('à', 'le'): 'au', ('à', 'les'): 'aux', ('de', 'le'): 'du', ('de', 'les'): 'des'}[(prep, first)] + ' ' + rest
    if prep == 'de' and _vowel(text):
        return "d'" + text
    return prep + ' ' + text


def relative_clause(r, g, number):
    gap = r.gap or 'subject'
    words = realize(r, gap=gap, antecedent=(g, number))
    pronoun = {'subject': 'qui', 'object': 'que', 'recipient': 'à qui', 'possessor': 'dont'}.get(gap, 'qui')
    if pronoun == 'que' and words and _vowel(words[0]):
        return "qu'" + join(words)
    return join([pronoun] + words)


def prepositional(np, passive=False):
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        return with_preposition('par', noun_phrase(inner, 'Str'))
    if np.prep is not None and np.prep.lang == 'fr' and np.prep.surface:   # 元のフランス語の前置詞 (à l'école を dans にしない)
        return with_preposition({'au': 'à', 'aux': 'à', 'du': 'de', 'des': 'de', "d'": 'de'}.get(np.prep.surface, np.prep.surface),
                                noun_phrase(inner, 'Str'))
    prep = PREPOSITIONS.get((np.prep.lemma, np.case), 'dans') if np.prep is not None else 'dans'
    if prep == 'dans' and inner.head is not None and inner.head.proper:
        prep = 'à'   # 町の名前は à (à Rome)
    return with_preposition(prep, noun_phrase(inner, 'Str'))


# ----------------------------------------------------------------------
# 動詞

def finite(lemma, tense, person, number):
    """定形 (現在・半過去・単純未来・単純過去)"""
    if lemma == 'être':
        return ETRE.get((tense, person, number)) or ETRE[('present', person, number)]
    if lemma == 'avoir' and (tense, person, number) in AVOIR:
        return AVOIR[(tense, person, number)]
    tags = PERSON_TAGS.get((person, number), PERSON_TAGS[(3, 'sg')])
    tense_tags = {'present': ('indicative', 'present'), 'imperfect': ('imperfect', 'indicative'),
                  'future': ('future', 'indicative'), 'historic': ('historic', 'indicative', 'past'),
                  'subjunctive': ('present', 'subjunctive')}[tense]
    form = find_form(lemma, 'verb', tense_tags + tags, avoid=('conditional',) if tense == 'subjunctive' else
                     ('subjunctive', 'conditional'))
    return form or _regular(lemma, tense, person, number)


def _regular(lemma, tense, person, number):
    key = (person, number)
    if lemma.endswith('er'):
        stem = lemma[:-2]
        if tense == 'imperfect':
            return stem + {(1, 'sg'): 'ais', (2, 'sg'): 'ais', (3, 'sg'): 'ait', (1, 'pl'): 'ions', (2, 'pl'): 'iez',
                           (3, 'pl'): 'aient'}[key]
        if tense == 'future':
            return lemma + {(1, 'sg'): 'ai', (2, 'sg'): 'as', (3, 'sg'): 'a', (1, 'pl'): 'ons', (2, 'pl'): 'ez',
                            (3, 'pl'): 'ont'}[key]
        return stem + {(1, 'sg'): 'e', (2, 'sg'): 'es', (3, 'sg'): 'e', (1, 'pl'): 'ons', (2, 'pl'): 'ez',
                       (3, 'pl'): 'ent'}[key]
    return lemma


def participle_form(lemma, g='m', number='sg'):
    form = find_form(lemma, 'verb', ('participle', 'past'))
    if form is None:
        form = lemma[:-2] + 'é' if lemma.endswith('er') else lemma[:-2] + 'i' if lemma.endswith('ir') else lemma
    return form + ('e' if g == 'f' else '') + ('s' if number == 'pl' and not form.endswith('s') else '')


def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            subject.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[subject.head.lemma], subject.number or 'sg'
    if subject is not None:
        return 3, 'pl' if subject.members or subject.number == 'pl' else 'sg'
    return clause.person or 3, clause.number or 'sg'


def verb_group(clause, person, number, agree=('m', 'sg'), subjunctive=False, infinitive=False):
    """(定形, 定形の後ろの語の列 (過去分詞・不定詞))。否定の ne … pas・接語の代名詞は呼ぶ側で"""
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return lemma, []
    g, n = agree
    if infinitive:   # 話法の動詞の後ろの不定詞の節の動詞は不定詞のまま (je peux lire)
        base = lemma[3:] if lemma.startswith('se ') else lemma
        return (base.split(' ', 1)[1] if base.startswith(('en ', 'y ')) else base), []
    pronominal = lemma.startswith('se ')
    if pronominal:   # 代名動詞 (se lever・se en aller): 動詞の部分で活用し、複合過去は être (再帰の代名詞と en・y は呼ぶ側で)
        lemma = lemma[3:]
        if lemma.startswith(('en ', 'y ')):
            lemma = lemma.split(' ', 1)[1]
    if clause.voice == 'passive':
        tense = 'imperfect' if clause.tense == 'imperfect' else 'future' if clause.tense == 'future' else 'present'
        if clause.tense in ('perfect', 'past-perfect'):   # a été + 過去分詞
            aux = AVOIR[('imperfect' if clause.tense == 'past-perfect' else 'present', person, number)]
            return aux, ['été', participle_form(lemma, g, n)]
        return finite('être', tense, person, number), [participle_form(lemma, g, n)]
    if clause.tense in ('perfect', 'past-perfect', 'future-perfect'):
        tense = 'imperfect' if clause.tense == 'past-perfect' else 'future' if clause.tense == 'future-perfect' else 'present'
        if lemma in ETRE_VERBS or pronominal:
            return finite('être', tense, person, number), [participle_form(lemma, g, n)]
        aux = AVOIR.get((tense, person, number)) or finite('avoir', tense, person, number)
        return aux, [participle_form(lemma)]
    tense = {'imperfect': 'imperfect', 'future': 'future'}.get(clause.tense, 'present')
    if subjunctive and tense == 'present':
        tense = 'subjunctive'   # 接続法現在 (sans qu'il le sache)
    return finite(lemma, tense, person, number), []


def _copula(clause, person, number):
    tense = 'imperfect' if clause.tense in ('imperfect', 'perfect', 'past-perfect') else \
        'future' if clause.tense == 'future' else 'present'
    if clause.tense == 'perfect':
        return AVOIR[('present', person, number)] + ' été'
    return finite('être', tense, person, number)


def _clitic(np, case):
    """目的語・受け手の接語の代名詞 (me・te・le・la・lui・nous・vous・les・leur)。代名詞でなければ None"""
    if np is None or np.members or np.head is None or np.head.pos != 'pronoun':
        return None
    if np.head.lemma not in ('ego', 'tū', 'is', 'ille', 'sē'):
        return None
    return _pronoun(np, case)


def _negate(verb_words, negated):
    """ne + 動詞 + pas (エリジオン n')"""
    if not negated or not verb_words:
        return verb_words
    return ['ne'] + verb_words[:1] + ['pas'] + verb_words[1:]


# 不定詞を支配する話法の動詞 (ラテン語の見出し) → フランス語の動詞
FRENCH_MODALS = {'possum': 'pouvoir', 'volō': 'vouloir', 'dēbeō': 'devoir', 'oportet': 'falloir', 'faciō': 'faire',
                 'sinō': 'laisser'}


def _feminine_noun(np, force=False):
    """人の名詞の女性形 (professeur → professeure。女性の主語の補語)。辞書に女性形が無ければそのまま"""
    from .frame import Lex
    if np.members or np.head is None or np.head.pos != 'noun' or not (np.animate or force) or np.head.proper:
        return np
    lemma = word(np.head, 'noun')
    if gender(lemma) == 'f':
        return np   # もとから女性の名詞 (rainha)
    fem = find_form(lemma, 'noun', ('feminine',), avoid=('plural',))
    if not fem or fem.lower() == lemma.lower():
        return np
    fem = fem
    return dataclasses.replace(np, head=Lex(fem, 'noun', np.head.ja, lang='fr'), gender='f')


def _modal(clause, gap, antecedent, subjunctive):
    """話法の動詞 + 不定詞の節 (Je peux le lire、Il faut partir、Il me fait rire)。当てはまらなければ None"""
    from .frame import Lex
    if clause.copula or len(clause.infinitives) != 1 or clause.verb is None:
        return None
    modal = FRENCH_MODALS.get(clause.verb.lemma) if clause.verb.lang in ('', 'la') else \
        (clause.verb.lemma if clause.verb.lemma in FRENCH_MODALS.values() else None)
    if modal is None:
        return None
    inner = clause.infinitives[0]
    if inner.role('subject') and modal not in ('faire', 'laisser', 'falloir'):
        return None   # 主語のある補文は que 節 (Je veux que tu viennes)
    causative = modal in ('faire', 'laisser')
    person_np = (inner.role('subject') or [None])[0] if causative else None
    inner_words = realize(dataclasses.replace(inner, mood='indicative', args=[(r, np) for r, np in inner.args
                                                                             if r != 'subject']), gap='subject',
                          infinitive=True)
    outer = dataclasses.replace(clause, verb=Lex(modal, 'verb', lang='fr'), infinitives=[])
    if causative and person_np is not None:
        clitic = _clitic(person_np, 'Acc')
        if clitic:   # Il me fait rire (人の接語は faire の前)
            outer = dataclasses.replace(outer, args=list(outer.args) + [('object', person_np)])
        else:        # Il fait rire les enfants
            inner_words = inner_words + [noun_phrase(person_np, 'Acc')]
    if modal == 'falloir' and inner.role('subject'):   # Il faut que je parte (主語のある不定詞の節は que + 接続法)
        tense = {'imperfect': 'imperfect', 'future': 'future'}.get(clause.tense, 'present')   # il fallait que
        return ['il', finite('falloir', tense, 3, 'sg'), 'que'] + \
            realize(dataclasses.replace(inner, mood='indicative'), subjunctive=True)
    if modal == 'falloir':
        outer = dataclasses.replace(outer, args=[(r, np) for r, np in outer.args if r != 'subject'], person=3, number='sg')
    words = realize(outer, gap, antecedent, subjunctive)
    return words + inner_words


# 直接の疑問文の疑問の副詞
QUESTION_WORDS = {'quandō': 'quand', 'ubi': 'où', 'cūr': 'pourquoi', 'quārē': 'pourquoi', 'quōmodo': 'comment',
                  'unde': "d'où", 'quō': 'où', 'quotiēns': 'combien de fois'}
WHO = {'quis', 'quem', 'cui', 'cūius', 'cuius', 'quibus'}


def direct_question(clause):
    """疑問詞のある直接の疑問文: 疑問詞 + est-ce que + 平叙の語順 (Quand est-ce qu'il vient ?・Qu'est-ce que la fille fait ?)。
    「どこにいるか」は倒置 (Où est la fille ?)、疑問代名詞が主語なら語順はそのまま (Qui vient ?)"""
    from .frame import interrogative_np, without_interrogative, where_is
    owner, role, wh = interrogative_np(clause)
    plain = dataclasses.replace(clause, question_word='', question=False)
    if wh is None and where_is(clause) is not None:
        subject = where_is(clause)
        return [QUESTION_WORDS[clause.question_word], _copula(clause, *_person(clause)), noun_phrase(subject, 'Nom')]
    if wh is None:
        first, rest = QUESTION_WORDS.get(clause.question_word, clause.question_word), realize(plain)
    elif owner is clause and role == 'subject':
        return realize(plain)
    else:
        first = 'qui' if clause.question_word in WHO and wh.gender != 'n' else 'que'
        if role == 'prep':
            first = prepositional(dataclasses.replace(wh, head=dataclasses.replace(wh.head, lemma='quis' if first == 'qui'
                                                                                  else 'quid')))
        rest = realize(without_interrogative(plain))
    subject = (clause.role('subject') or [None])[0]
    complex_ = _complex_inverted(rest, subject) if first != 'que' else None
    return [first] + (_inverted(rest) or complex_ or ['est-ce', 'que'] + rest)


def _complex_inverted(words, subject):
    """名詞の主語の複合倒置: 主語 + 動詞-代名詞 (Pourquoi le garçon court-il ?・Quand la fille vient-elle ?)"""
    if subject is None or subject.head is None or subject.head.pos == 'pronoun' or subject.members or \
            not words or words[0] != noun_phrase(subject, 'Nom'):
        return None
    plural = subject.number == 'pl'
    pronoun = ('elles' if plural else 'elle') if gender_of(subject) == 'f' else ('ils' if plural else 'il')
    inverted = _inverted([pronoun] + words[1:])
    return [words[0]] + inverted if inverted else None


SUBJECT_PRONOUNS = {'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles'}


def _inverted(words):
    """代名詞の主語の倒置 (il vient → vient-il、il a → a-t-il)。主語が名詞・je のとき、否定・接語のあるときは None"""
    if len(words) < 2 or words[0] not in SUBJECT_PRONOUNS or ' ' in words[1] or \
            words[1] in ('ne', "n'", 'me', 'te', 'se', 'le', 'la', 'les', 'lui', 'leur', 'y', 'en', 'nous', 'vous') or \
            words[1].endswith("'"):
        return None
    t = '-t' if words[1][-1:] in 'ae' and words[0] in ('il', 'elle', 'on') else ''
    return [words[1] + t + '-' + words[0]] + words[2:]


def realize(clause, gap=None, antecedent=None, subjunctive=False, infinitive=False):
    from .frame import lexical_negation, periphrastic, Lex
    clause = lexical_negation(periphrastic(clause))
    if clause.question and clause.question_word and clause.mood == 'indicative' and gap is None and not infinitive:
        return direct_question(clause)
    modal = _modal(clause, gap, antecedent, subjunctive)
    if modal is not None:
        return modal
    complements = [inner for inner in clause.infinitives if inner.infinitive_kind in ('saying', 'command', 'emotion') and
                   inner.role('subject')]
    from .frame import reflexive_subject
    if complements:   # 補文は que 節 (Je sais que tu viens、Je veux que tu viennes。望む・命じる動詞なら接続法)
        main = realize(dataclasses.replace(clause, infinitives=[i for i in clause.infinitives if i not in complements]),
                       gap, antecedent, subjunctive, infinitive)
        for inner in complements:
            sub = realize(dataclasses.replace(reflexive_subject(inner, clause), mood='indicative', infinitive_kind=''),
                          subjunctive=inner.infinitive_kind in ('command', 'emotion'))   # 望む・命じる・感情は接続法
            main += ["qu'" + sub[0] if sub and _vowel(sub[0]) else 'que'] + (sub[1:] if sub and _vowel(sub[0]) else sub)
        return main
    if clause.experiencer:   # 入れ替えた manquer à を元に (Ego tē dēsīderō の枠 → Tu me manques)
        subject, obj = (clause.role('subject') or [None])[0], (clause.role('object') or [None])[0]
        if subject is not None and obj is not None:
            args = [(r, np) for r, np in clause.args if r not in ('subject', 'object')]
            clause = dataclasses.replace(clause, args=[('subject', dataclasses.replace(obj, case='Nom')),
                                                       ('recipient', dataclasses.replace(subject, case='Dat'))] + args,
                                         experiencer='',
                                         verb=Lex(clause.experiencer, 'verb', lang='fr'), person=None, number=None)
    person, number = _person(clause)
    subject = (clause.role('subject') or [None])[0]
    words = []
    if subject is not None and gap != 'subject':
        found = _pronoun(subject, 'Nom') if subject.head is not None and subject.head.pos == 'pronoun' and \
            not subject.members else None
        words.append(found or noun_phrase(subject, 'Nom'))
    elif subject is None and gap is None and clause.mood != 'imperative':
        words.append({(1, 'sg'): 'je', (2, 'sg'): 'tu', (3, 'sg'): 'il', (1, 'pl'): 'nous', (2, 'pl'): 'vous',
                      (3, 'pl'): 'ils'}[(person, number)])
    agree = antecedent if gap == 'subject' and antecedent else \
        ((gender_of(subject), 'pl' if subject.members or subject.number == 'pl' else 'sg') if subject is not None
         else ('m', number))
    adverbs = [word(a, 'adv') for a in clause.adverbs if a.lemma != 'nōn']
    if clause.copula:
        complements = clause.role('complement')
        preps = [prepositional(np) for role, np in clause.args if role == 'prep']
        if not complements and subject is not None and not preps and gap is None:
            # 存在の文 (Agricola est「農夫がいる」): il y a + 名詞
            verb = {'present': 'a', 'imperfect': 'avait', 'future': 'aura'}.get(
                'imperfect' if clause.tense in ('perfect', 'imperfect', 'past-perfect') else clause.tense, 'a')
            ne = ['n'] if False else []
            noun = noun_phrase(subject, 'Acc', indefinite=True)   # il y a un agriculteur
            if clause.negated:
                return _elided(['il', 'ne', 'y', verb, 'pas', 'de']) + [noun.split(' ', 1)[-1]] + adverbs
            return ['il', 'y', verb, noun] + adverbs
        verb = _copula(clause, person, number)
        verb_words = _elided(_negate(verb.split(' '), clause.negated))
        tail = []
        if complements:
            comp = complements[0]
            adjectival = all(m.head is not None and m.head.pos in ('adj', 'participle') for m in comp.members) \
                if comp.members else comp.head is not None and comp.head.pos in ('adj', 'participle')
            if adjectival:   # 形容詞の補語は主語に一致 (La route est longue et large)
                g, n = agree
                forms = [adjective_form(word(m.head, 'adj'), g, n) for m in comp.members] if comp.members else \
                    [adjective_form(word(comp.head, 'adj'), g, n)]
                tail.append(' et '.join(f for f in forms if f))
            else:
                tail.append(noun_phrase(_feminine_noun(comp) if agree[0] == 'f' else comp, 'Nom'))   # Elle est la professeure
        return [w for w in words + verb_words + adverbs + tail + preps if w]
    clitics, objects = [], []
    obj = (clause.role('object') or [None])[0]
    de_object = clause.verb is not None and clause.verb.lang == 'fr' and clause.verb.lemma in DE_OBJECT_VERBS
    if obj is not None and gap != 'object':
        clitic = _clitic(obj, 'Acc')
        if clitic and de_object:
            clitics.append('en' if obj.head.lemma in ('is', 'ille') else clitic)   # s'en apercevoir
        elif clitic:
            clitics.append(clitic)
        elif de_object:   # s'apercevoir de son erreur (目的語にした de 句を戻す)
            objects.append(with_preposition('de', noun_phrase(obj, 'Acc')))
        else:
            objects.append(noun_phrase(obj, 'Acc'))
    for np in clause.role('recipient'):
        clitic = _clitic(np, 'Dat')
        if clitic:
            clitics.append(clitic)
        else:
            objects.append(with_preposition('à', noun_phrase(np, 'Str')))
    clitics.sort(key=lambda c: c in ('le', 'la', 'les'))   # me le・le lui: 1・2人称と再帰が先、3人称は le・la・les が先
    if any(c in ('lui', 'leur') for c in clitics):
        clitics.sort(key=lambda c: c in ('lui', 'leur'))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            objects.append(prepositional(np, clause.voice == 'passive'))
        elif np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
            objects.append(WORDS[np.head.lemma])
        elif role == 'means':
            objects.append(with_preposition('avec' if not np.animate else 'par', noun_phrase(np, 'Str')))
        elif role == 'possessor':
            objects.append(with_preposition('de', noun_phrase(np, 'Str')))
        else:
            objects.append(with_preposition('dans', noun_phrase(np, 'Str')))
    verb, tail = verb_group(clause, person, number, agree, subjunctive, infinitive)
    lemma_fr = word(clause.verb, 'verb')
    if lemma_fr.startswith('se '):   # 代名動詞の再帰の代名詞 (il se lève・je m'appelle・je m'en vais)
        particle = lemma_fr[3:].split(' ', 1)[0] if lemma_fr[3:].startswith(('en ', 'y ')) else None
        if particle:
            clitics.append(particle)
        clitics.insert(0, {(1, 'sg'): 'me', (2, 'sg'): 'te', (1, 'pl'): 'nous', (2, 'pl'): 'vous'}.get((person, number), 'se'))
    if clause.mood == 'imperative':
        lemma = word(clause.verb, 'verb')
        form = find_form(lemma, 'verb', ('imperative', 'second-person', 'plural' if number == 'pl' else 'singular')) or verb
        out = _elided(_negate([form], clause.negated)) if clause.negated else [form]
        return [w for w in out + objects + adverbs if w]
    verb_words = _elided(clitics + [verb])
    negative_pronoun = any(np.head is not None and np.head.lemma in NEGATIVE_PRONOUNS for _, np in clause.args)
    if clause.negated or negative_pronoun:   # ne … pas (否定の代名詞 personne・rien なら pas を付けない)
        verb_words = _elided(['ne'] + clitics + [verb]) + ([] if negative_pronoun else ['pas'])
    return [w for w in _elided(words + verb_words) + tail + adverbs + objects if w]


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
        subordinate = rest.subordinator in SUBORDINATORS and rest.subordinator != 'nisi' and \
            (k + 1 < len(clauses) or k > 0 and not rest.after_main or rest.subordinator == 'quīn')   # 主節の後ろの従属節も
        if subordinate:
            words.append(SUBORDINATORS[rest.subordinator])
        words += realize(rest, subjunctive=subordinate and rest.subordinator in SUBJUNCTIVE_AFTER)
        parts.append(join(_elided([w for w in words if w])))
    text = ', '.join(parts).replace(' ,', ',').replace(',,', ',').rstrip(',')
    return text[:1].upper() + text[1:] + '.'


# ----------------------------------------------------------------------
# 比較の表

PRO_DROP_HOW = '代名詞を補う (je・il …)'
PREDICATE_HOW = '人称・数・時制の語形 (voit・voyait)、複合過去 avoir / être + 過去分詞、受動 être + 過去分詞、否定 ne … pas'
COPULA_HOW = 'être + 補語 (形容詞は主語の性・数に一致)'
ADDRESS_HOW = '冠詞なし'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, '前置詞 par (受動の動作主)'
        return text, '前置詞 %s' % text.split(' ')[0].split("'")[0]
    if role == 'address':
        return vocative(np), ADDRESS_HOW
    if role == 'subject':
        return noun_phrase(np, 'Nom'), '動詞の前 (格の印なし)'
    if role == 'object':
        clitic = _clitic(np, 'Acc')
        return (clitic, '動詞の前の接語の代名詞') if clitic else (noun_phrase(np, 'Acc'), '動詞の後ろ (格の印なし)')
    if role == 'recipient':
        clitic = _clitic(np, 'Dat')
        return (clitic, '動詞の前の接語の代名詞 (lui・leur)') if clitic else \
            (with_preposition('à', noun_phrase(np, 'Str')), '前置詞 à')
    if role == 'possessor':
        return with_preposition('de', noun_phrase(np, 'Str')), '前置詞 de'
    if role == 'means':
        return with_preposition('avec', noun_phrase(np, 'Str')), '前置詞 avec'
    return with_preposition('dans', noun_phrase(np, 'Str')), '前置詞 dans'


def compare_predicate(clause, reduced):
    person, number = _person(clause)
    if clause.copula:
        words = realize(reduced)
        subject = (clause.role('subject') or [None])[0]
        head = noun_phrase(subject, 'Nom') if subject is not None else ''
        text = join(words)
        return (text[len(head):].strip() if head and text.startswith(head) else text), COPULA_HOW
    verb, tail = verb_group(clause, person, number)
    words = _elided((['ne'] if clause.negated else []) + [verb]) + (['pas'] if clause.negated else []) + tail
    return join(words), PREDICATE_HOW
