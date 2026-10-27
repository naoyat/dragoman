#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からアイヌ語 (北海道方言) の文を作る
#
#   語: 解析側の手作りの語彙表 (ainu/grammar.py の LEXICON。日本語の訳語) を元の語の日本語の訳語で引き、
#     無ければ Wiktionary (kaikki) の英語の語義で。文法の語 (後置詞・人称の接辞・否定) は ainu/grammar.py の表と同じ
#   語順: 主語 - 目的語 - 後置詞句 - 動詞 (SOV)。格の印は無く、場所 ta・方向 un・起点 orowa・道具 ari・同伴 turano
#   人称は動詞の接辞: ku= (私)・e= (あなた)・ci= (私たち)・eci= (あなたたち)、目的語 en= (私)・un= (私たち)。
#     3人称は無標。自動詞の「私たち」は =as
#   時制の区別は無い (未来・意図は kusu ne)。否定 somo、禁止 iteki、繋辞 ne (aynu ne)、形容詞は状態の動詞
#     (pirka「良い」: 補語なら述語、名詞の前なら連体 pirka matkaci)。関係節も名詞の前 (kamuy nukar aynu)
#   ラテン文字の行とカタカナの行
#
import functools
import re

from . import english
from .frame import NP

POSTPOSITIONS = {('in', 'Abl'): 'ta', ('in', 'Acc'): 'un', ('ad', 'Acc'): 'un', ('ex', 'Abl'): 'orowa',
                 ('ē', 'Abl'): 'orowa', ('ab', 'Abl'): 'orowa', ('ā', 'Abl'): 'orowa', ('cum', 'Abl'): 'turano',
                 ('per', 'Acc'): 'peka', ('sub', 'Abl'): 'corpok', ('super', 'Acc'): 'kurka'}
SUBJECT = {(1, 'sg'): 'ku=', (2, 'sg'): 'e=', (3, 'sg'): '', (1, 'pl'): 'ci=', (2, 'pl'): 'eci=', (3, 'pl'): ''}
OBJECT = {(1, 'sg'): 'en=', (1, 'pl'): 'un=', (2, 'sg'): 'e=', (2, 'pl'): 'eci='}
CONNECTIVES = {'et': 'wa', 'sed': 'korka', 'autem': 'wa', 'ubi': 'hike', 'cum': 'hike', 'postquam': 'wa',
               'sī': 'yakun', 'quod': 'kusu', 'quia': 'kusu', 'ut': 'kuni'}
PRONOUNS = {('ego', 'sg'): 'kani', ('ego', 'pl'): 'ciokay', ('tū', 'sg'): 'eani', ('tū', 'pl'): 'ecioka',
            ('quis', 'sg'): 'nen', ('quid', 'sg'): 'hemanta'}
# 直接の疑問文の疑問の副詞 (動詞の前: Matkaci hunak ta an?)
QUESTION_WORDS = {'quandō': 'hempara', 'ubi': 'hunak ta', 'cūr': 'hemanta kusu', 'quārē': 'hemanta kusu',
                  'quōmodo': 'makanak', 'unde': 'hunak wa', 'quō': 'hunak un'}


def _shown(np):
    """名詞句を書くか (人称の代名詞は動詞の接辞で表すので書かない。疑問代名詞 nen・hemanta は書く)"""
    return np.head is None or np.head.pos != 'pronoun' or np.interrogative


@functools.lru_cache(maxsize=1)
def _by_japanese():
    """日本語の訳語 → [(アイヌ語, 品詞)] (手作りの語彙表)"""
    from dragoman.ainu import grammar
    out = {}
    for word, (ja, pos) in grammar.LEXICON.items():
        if not re.fullmatch(r"[a-z=' ]+", word):
            continue   # カタカナの見出し (カタカナのテキストの照合用) は使わない
        for gloss in (ja or '').split(','):
            out.setdefault(gloss.strip(), []).append((word, pos))
    return out


@functools.lru_cache(maxsize=1)
def _by_english():
    """英語の語義 → [(語義の中の順位, アイヌ語 (ラテン文字の見出し), 品詞)] (Wiktionary。照合用の鍵でなく見出しの綴り)"""
    import json
    import os
    from dragoman.ainu import morphology
    from dragoman.core.wiktionary_import import english_glosses
    out = {}
    path = os.path.join(morphology.DATA, 'kaikki.org-dictionary-Ainu.jsonl')
    if not os.path.exists(path):
        return out
    with open(path, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get('word', '')
            if not re.fullmatch(r"[a-z=' ]+", word):
                continue
            for j, gloss in enumerate(g.strip().lower() for g in (english_glosses(entry) or '').split(',')):
                gloss = gloss[3:] if gloss.startswith('be ') else gloss   # be good → good (状態の動詞)
                if gloss:
                    out.setdefault(gloss, []).append((j, word, entry.get('pos')))
    return out


def available():
    from dragoman.ainu import morphology
    return morphology.available()


def to_ainu(lex, pos):
    """語 → アイヌ語の語 (見つからなければ None)。形容詞は状態の動詞 (verb) でも引く"""
    pos = {'participle': 'verb', 'name': 'noun'}.get(pos, pos)
    allowed = {'adj': ('verb', 'adj'), 'verb': ('verb',), 'noun': ('noun',)}.get(pos, (pos,))
    from .japanese import gloss as ja_gloss
    first = ja_gloss(lex).split(',')[0].strip() if lex.ja else ''
    for word, p in _by_japanese().get(first, []) + _by_japanese().get(first.rstrip('い') + 'い', []):
        if p in allowed or pos == 'adj':
            return word
    best = None
    sources = english.candidates(lex) or []
    if (lex.lang or 'la') == 'la':   # 手作りの辞書の日本語に和英で合う英語を先に (transfer と同じ)
        from .transfer import _with_japanese
        sources = _with_japanese(list(sources)[:6], [j.strip() for j in (lex.ja or '').split(',') if j.strip()])
    for i, en in enumerate(s.lower() for s in sources[:5]):
        for j, word, p in _by_english().get(en, []):
            if p in allowed and (best is None or (i, j) < best[0]):
                best = ((i, j), word)
    return best[1] if best else None


def _person(np, clause):
    if np is not None and np.head is not None and np.head.pos == 'pronoun' and np.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[np.head.lemma], 'pl' if np.number == 'pl' else 'sg'
    if np is not None:
        return 3, 'pl' if np.number == 'pl' or np.members else 'sg'
    return clause.person, clause.number


def _plural_verb(word, number):
    """複数の主語の自動詞の複数形 (単複の表: ek → arki など)"""
    if number != 'pl':
        return word
    from dragoman.ainu import morphology
    for row in morphology._tsv('verb_plurals.tsv'):
        if row.get('sg') == word and row.get('pl'):
            return row['pl']
    return word


def noun_phrase(np):
    if np.members:
        out = []
        for k, m in enumerate(np.members):
            if k:
                out.append('newa')   # 「と」
            out += noun_phrase(m)
        return out
    head = np.head
    if head is None:
        return []
    if head.pos == 'pronoun':
        word = PRONOUNS.get((head.lemma, np.number))
        return [word] if word else []
    if head.proper:
        return [english.word(head)]
    word = to_ainu(head, 'noun') or '[%s]' % english.word(head)
    out = []
    for g in np.genitives:   # 所有: 持ち主 + kor + 名詞 (「〜の持つ」)
        out += noun_phrase(g) + ['kor']
    for r in np.relatives:   # 関係節は名詞の前 (kamuy nukar aynu)
        out += realize(r, gap=r.gap)
    for m in np.modifiers:   # 形容詞 (状態の動詞) も名詞の前 (pirka matkaci)
        if isinstance(m, NP):
            out += [w for k, x in enumerate(m.members) for w in (['wa'] if k else []) + [to_ainu(x.head, 'adj') or '?']]
        elif m.pos != 'pronoun':
            out.append(to_ainu(m, 'adj') or '[%s]' % english.word(m))
    return out + [word]


def verb_words(clause, subject, obj):
    person, number = _person(subject, clause)
    verb = to_ainu(clause.verb, 'verb')
    if verb is None:
        return ['[%s]' % english.word(clause.verb)]
    transitive = obj is not None
    if not transitive:
        verb = _plural_verb(verb, number)
    prefix = ''
    if clause.voice == 'passive':
        prefix = 'a='   # 第4人称 (不定の人) が主語の形で受動を表す: a=nukar「見られる」
    elif clause.mood != 'imperative':
        if not transitive and (person, number) == (1, 'pl'):
            verb += '=as'
        else:
            prefix = SUBJECT[(person, number)]
    if transitive and obj.head is not None and obj.head.pos == 'pronoun' and obj.head.lemma in ('ego', 'tū'):
        prefix += OBJECT[({'ego': 1, 'tū': 2}[obj.head.lemma], 'pl' if obj.number == 'pl' else 'sg')]
    words = []
    if clause.negated:
        words.append('iteki' if clause.mood == 'imperative' else 'somo')
    words.append(prefix + verb)
    if clause.mood == 'imperative' and number == 'pl':
        words.append('yan')
    if clause.tense in ('future', 'future-perfect'):
        words += ['kusu', 'ne']
    return words


def realize(clause, gap=None):
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    subject = (clause.role('subject') or [None])[0]
    obj = (clause.role('object') or [None])[0]
    out = []
    if subject is not None and gap != 'subject' and _shown(subject):
        out += noun_phrase(subject)
    wh = QUESTION_WORDS.get(clause.question_word, '').split() if clause.question and gap is None and \
        not any(np.interrogative for _, np in clause.args) else []
    if clause.copula:
        complements = clause.role('complement')
        from .frame import adjective_members
        for np in complements:
            members = adjective_members(np) or ([np] if np.head is not None and np.head.pos in ('adj', 'participle')
                                                and not np.members else None)
            if members:   # 形容詞は状態の動詞として述語に (pirka)
                words = [to_ainu(m.head, 'adj') or '[%s]' % english.word(m.head) for m in members]
                out += [w for k, x in enumerate(words) for w in (['wa'] if k else []) + [x]]
                if clause.negated:
                    out.insert(len(out) - 1, 'somo')
                return out
            out += noun_phrase(np)
        if clause.negated:
            out.append('somo')
        out += wh + ['ne' if complements else 'an']
        for role, np in clause.args:
            if role == 'prep':
                out[-1:-1] = noun_phrase(np) + [POSTPOSITIONS.get((np.prep.lemma, np.case), 'ta')]
        return out
    for np in clause.role('recipient'):   # 与える相手は目的語の前 (kore「与える」は二つの目的語を取る)
        out += noun_phrase(np)
    if obj is not None and gap != 'object' and _shown(obj):
        out += noun_phrase(obj)
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            if clause.voice == 'passive' and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
                continue   # a= の受動は動作主を書かない
            out += noun_phrase(np) + [POSTPOSITIONS.get((np.prep.lemma, np.case), 'ta')]
        elif role == 'means' and np.animate:   # 与格と奪格の同形: 人なら受け手 (印なし。目的語の前に)
            out[len(out) - len(noun_phrase(obj)) if obj is not None and gap != 'object' else len(out):0] = noun_phrase(np)
        elif role == 'means':
            out += noun_phrase(np) + ['ari']
        else:
            out += noun_phrase(np) + ['ta']
    return out + wh + verb_words(clause, subject, obj)


def sentence(clauses):
    """ラテン文字 (とカタカナの行)"""
    if not clauses:
        return ''
    from .frame import split_address
    from dragoman.ainu import script
    words = []
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        for group in groups:
            for np in group:
                words += noun_phrase(np) + [',']
        keys = rest.connectives + ([rest.subordinator] if rest.subordinator else [])
        words += realize(rest) + [CONNECTIVES[key] for key in keys if key in CONNECTIVES]
        if k + 1 < len(clauses):
            words.append(',')
    text = ' '.join(words).replace(' ,', ',')
    text = text[:1].upper() + text[1:] + '.'
    kana = ' '.join(w if w.startswith('[') else script.kana(w)
                    for w in re.findall(r'\[+[^\]]*\]+\S*|\S+', text))   # [英語] (空白を含んでも) は仮名にしない
    return '%s\n            %s' % (text, kana)
