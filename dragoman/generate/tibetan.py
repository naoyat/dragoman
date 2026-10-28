#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) から古典チベット語の文を作る (Wylie 綴り)
#
#   語: チベット語の辞書 (bo/tibetan.sqlite の words: 英語の訳語) から英語の訳語を仲立ちに (基本の語は PREFERRED)。
#     動詞の時制の語幹は stems の表から (mthong / mthong / mthong / mthong、sbyin / byin …)
#   語順: 主語 - 受け手 + la - 目的語 - 後置の句 - 動詞 + 終止の助詞 (SOV)。目的語のある文の主語は能格 (kyis/gyis/gis/-s)
#   助詞は前の語の終わりの字で形が変わる: 能格 kyis/gyis/gis/-s、属格 kyi/gyi/gi/-'i、終止 go/ngo/do/no/bo/mo/'o/ro/lo/so、
#     名詞化 pa/ba、命令 cig/zhig/shig
#   時制: 現在・未来・過去・命令の語幹、否定は現在・未来 mi、過去・禁止 ma。繋辞 yin (否定 min)、存在 yod (med)
#   名詞句: 名詞 + 形容詞 (bu mo mdzes po)、複数 rnams、属格の名詞は前 (dge rgan gyi dpe cha)、
#     関係節は前に 名詞化 + 属格 (dge rgan gyis bstod pa'i bu)。受動は無いので能動に組み替える
#
import functools
import math
import os
import sqlite3

from . import english
from .frame import NP, Lex
from dragoman.core import paths

PREFERRED = {('girl', 'noun'): 'bu mo', ('boy', 'noun'): 'bu', ('child', 'noun'): 'bu', ('son', 'noun'): 'bu',
             ('daughter', 'noun'): 'bu mo', ('king', 'noun'): 'rgyal po', ('queen', 'noun'): 'rgyal mo',
             ('teacher', 'noun'): 'dge rgan', ('book', 'noun'): 'dpe cha', ('flower', 'noun'): 'me tog',
             ('rose', 'noun'): 'me tog', ('garden', 'noun'): 'skyed tshal', ('city', 'noun'): 'grong khyer',
             ('house', 'noun'): 'khang pa', ('water', 'noun'): 'chu', ('god', 'noun'): 'lha', ('man', 'noun'): 'mi',
             ('person', 'noun'): 'mi', ('woman', 'noun'): 'bud med', ('father', 'noun'): 'pha', ('mother', 'noun'): 'ma',
             ('beautiful', 'adj'): 'mdzes po', ('good', 'adj'): 'bzang po', ('bad', 'adj'): 'ngan pa',
             ('great', 'adj'): 'chen po', ('big', 'adj'): 'chen po', ('large', 'adj'): 'chen po',
             ('small', 'adj'): 'chung ngu', ('see', 'verb'): 'mthong', ('give', 'verb'): 'sbyin',
             ('praise', 'verb'): 'bstod', ('come', 'verb'): "'ong", ('go', 'verb'): "'gro", ('say', 'verb'): 'zer',
             ('sing', 'verb'): 'glu len'}
POSTPOSITIONS = {('in', 'Abl'): 'na', ('in', 'Acc'): 'la', ('ad', 'Acc'): 'la', ('ex', 'Abl'): 'nas',
                 ('ē', 'Abl'): 'nas', ('ab', 'Abl'): 'nas', ('ā', 'Abl'): 'nas', ('cum', 'Abl'): 'dang lhan cig',
                 ('sine', 'Abl'): 'med par', ('post', 'Acc'): 'gi rjes su', ('ante', 'Acc'): 'gi snga rol tu'}
PRONOUNS = {('ego', 'sg'): 'nga', ('ego', 'pl'): 'nga cag', ('tū', 'sg'): 'khyod', ('tū', 'pl'): 'khyed',
            ('is', 'sg'): "de", ('is', 'pl'): 'de dag', ('hic', 'sg'): "'di", ('hic', 'pl'): "'di dag",
            ('ille', 'sg'): 'de', ('ille', 'pl'): 'de dag', ('quis', 'sg'): 'su', ('quid', 'sg'): 'ci'}
POSSESSIVES = {'meus': "nga'i", 'tuus': 'khyod kyi', 'suus': 'rang gi', 'noster': 'nga cag gi', 'vester': 'khyed kyi'}
# 直接の疑問文の疑問の副詞 (動詞の前)
QUESTION_WORDS = {'quandō': 'nam', 'ubi': 'gang na', 'cūr': "ci'i phyir", 'quārē': "ci'i phyir", 'quōmodo': 'ji ltar',
                  'unde': 'gang nas', 'quō': 'gang du'}
CONNECTIVES = {'et': 'yang', 'sed': "'on kyang", 'autem': 'yang', 'ubi': 'na', 'cum': 'na', 'postquam': 'nas',
               'sī': 'na', 'quod': 'phyir', 'quia': 'phyir'}
TENSES = {'present': 'pres', 'imperfect': 'past', 'perfect': 'past', 'past-perfect': 'past', 'future': 'fut',
          'future-perfect': 'fut'}


@functools.lru_cache(maxsize=1)
def _db():
    path = paths.data('bo', 'tibetan.sqlite')
    return sqlite3.connect(path, check_same_thread=False) if os.path.exists(path) else None


def available():
    return _db() is not None


@functools.lru_cache(maxsize=1)
def _index():
    """英語の訳語 → [(順位, 見出し, 品詞)]"""
    index = {}
    for wylie, pos, en, rank in _db().execute('SELECT wylie, pos, en, rank FROM words'):
        for j, gloss in enumerate(g.strip().lower() for g in (en or '').split(',')):
            if gloss:
                index.setdefault(gloss, []).append((j + (rank or 0), wylie, pos))
    return index


def to_tibetan(lex, pos):
    pos = {'participle': 'verb', 'name': 'noun'}.get(pos, pos)
    sources = english.candidates(lex) or [e for e in (lex.en or '').split(',') if e]
    if (lex.lang or 'la') == 'la':   # 手作りの辞書の日本語に和英で合う英語を先に (transfer と同じ)
        from .transfer import _with_japanese
        sources = _with_japanese(list(sources)[:6], [j.strip() for j in (lex.ja or '').split(',') if j.strip()])
    for en in sources[:1]:
        found = PREFERRED.get((en.lower(), pos)) or PREFERRED.get((en.lower().split(' ')[-1], pos))
        if found:
            return found
    best = None
    for i, en in enumerate(s.lower() for s in sources[:5]):
        for j, wylie, p in _index().get(en, []):
            if p == pos and (best is None or 3 * i + j < best[0]):
                best = (3 * i + j, wylie)
    return best[1] if best else None


def stem(lemma, tense):
    """動詞の時制の語幹 (stems の表。無ければ見出しのまま)"""
    row = _db().execute('SELECT form FROM stems WHERE lemma = ? AND tense = ? LIMIT 1', (lemma, tense)).fetchone()
    return row[0] if row else lemma


# ----------------------------------------------------------------------
# 助詞の形 (前の語の終わりの字で)

def _final(word):
    """最後の音節の終わりの字: 'g' 'ng' 'd' 'n' 'b' 'm' "'" 'r' 'l' 's'、母音なら ''"""
    syllable = word.split(' ')[-1]
    if syllable.endswith('ng'):
        return 'ng'
    last = syllable[-1:]
    if last in 'aeiou':
        return ''
    return last


def particle(word, kind):
    """能格 (erg)・属格 (gen)・終止 (fin)・疑問 (q)・名詞化 (nom)・命令 (imp) の助詞を付けた形"""
    f = _final(word)
    vowel = f in ('', "'")
    base = word[:-1] if f == "'" else word   # 語末の ' (a-chung) は付く助詞に置き換わる (dga' → dga's)
    if kind == 'erg':
        return base + 's' if vowel else word + ' ' + {'g': 'gis', 'ng': 'gis', 'd': 'kyis', 'b': 'kyis',
                                                      's': 'kyis'}.get(f, 'gyis')
    if kind == 'gen':
        return base + "'i" if vowel else word + ' ' + {'g': 'gi', 'ng': 'gi', 'd': 'kyi', 'b': 'kyi',
                                                       's': 'kyi'}.get(f, 'gyi')
    if kind == 'fin':
        return word + "'o" if f == '' else word + ' ' + (f + 'o' if f != "'" else "'o")
    if kind == 'q':   # 疑問の助詞 (終止の助詞と同じく前の字で: 'ong ngam・yod dam・bzo'am)
        return word + "'am" if f == '' else word + ' ' + (f + 'am' if f != "'" else "'am")
    if kind == 'nom':
        return word + ' ' + ('ba' if f in ('', 'ng', "'", 'r', 'l') else 'pa')
    if kind == 'imp':
        return word + ' ' + ('cig' if f in ('g', 'd', 'b') else 'shig' if f == 's' else 'zhig')
    return word


# ----------------------------------------------------------------------

def noun_phrase(np):
    if np.members:
        return ' dang '.join(noun_phrase(m) for m in np.members)
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun':
        return PRONOUNS.get((head.lemma, np.number), 'de')
    if head.proper:   # ラテン文字の名前は [ ] に入れてチベット文字に変換しない
        return '[%s]' % english.word(head)
    word = to_tibetan(head, 'noun') or '[%s]' % english.word(head)
    # 所有形容詞は属格の代名詞を前に (nga'i dpe cha「私の本」、suus は rang gi「自分の」)
    before = [POSSESSIVES[m.lemma] for m in np.modifiers if isinstance(m, Lex) and m.lemma in POSSESSIVES]
    before += [particle(noun_phrase(g), 'gen') for g in np.genitives]
    before += [particle(realize(r, gap=r.gap, final=False), 'gen') for r in np.relatives]
    after = []
    for m in np.modifiers:
        if isinstance(m, NP):
            after.append(' dang '.join(to_tibetan(x.head, 'adj') or '?' for x in m.members))
        elif m.pos == 'pronoun' and m.lemma in ('hic', 'ille', 'is'):
            after.append("'di" if m.lemma == 'hic' else 'de')
        elif isinstance(m, Lex) and m.lemma in POSSESSIVES:
            continue
        else:
            after.append(to_tibetan(m, 'adj') or '[%s]' % english.word(m))
    if np.number == 'pl' and head.pos != 'pronoun':
        after.append('rnams')
    return ' '.join(before + [word] + after)


def verb_word(clause):
    lemma = to_tibetan(clause.verb, 'verb')
    if lemma is None:
        return '[%s]' % english.word(clause.verb)
    parts = lemma.split(' ')
    head, main = ' '.join(parts[:-1]), parts[-1]   # glu len「歌を取る」: 前の語はそのまま
    if clause.mood == 'imperative':
        if clause.negated:
            form = 'ma ' + stem(main, 'pres')
        else:
            form = particle(stem(main, 'imp'), 'imp')
    else:
        tense = TENSES.get(clause.tense, 'pres')
        form = stem(main, tense)
        if clause.negated:
            form = ('ma ' if tense == 'past' else 'mi ') + form
    return (head + ' ' + form).strip()


def _sentence_end(verb, question, clause):
    """文末の助詞: 平叙は終止の助詞 (ngo・do …)、諾否の疑問は疑問の助詞 (ngam・dam …。「または」と同じ語で選択を問う)、
    疑問詞のある文は動詞で終える (su 'ong /「誰が来るか」)"""
    if question and clause.question_word:
        return verb
    return particle(verb, 'q' if question else 'fin')


def realize(clause, gap=None, final=True):
    from .frame import lexical_negation, periphrastic
    from .arabic import to_active
    clause = lexical_negation(periphrastic(clause))
    if clause.voice == 'passive' and not clause.copula:
        clause = to_active(clause)   # 受動は無いので能動に (動作主を能格の主語に)
    subject = (clause.role('subject') or [None])[0]
    obj = (clause.role('object') or [None])[0]
    out = []
    question = clause.question and clause.mood == 'indicative' and gap is None and final
    wh = QUESTION_WORDS.get(clause.question_word, '') if question and \
        not any(np.interrogative for _, np in clause.args) else ''
    if clause.copula:
        if subject is not None and gap != 'subject':
            out.append(noun_phrase(subject))
        complements = clause.role('complement')
        for np in complements:
            if np.head is not None and np.head.pos in ('adj', 'participle') and not np.members:
                out.append(to_tibetan(np.head, 'adj') or '[%s]' % english.word(np.head))
            else:
                out.append(noun_phrase(np))
        for role, np in clause.args:
            if role == 'prep':
                out.append(noun_phrase(np) + ' ' + POSTPOSITIONS.get((np.prep.lemma, np.case), 'na'))
        verb = ('min' if clause.negated else 'yin') if complements else ('med' if clause.negated else 'yod')
        out.append(wh)
        out.append(_sentence_end(verb, question, clause) if final else verb)
        return ' '.join(w for w in out if w)
    if subject is not None and gap != 'subject':
        text = noun_phrase(subject)
        transitive = obj is not None or gap == 'object'   # 関係節の空所が目的語でも他動詞 (dge rgan gyis bstod pa'i bu)
        out.append(particle(text, 'erg') if transitive else text)   # 目的語のある文の主語は能格
    for np in clause.role('recipient'):
        out.append(noun_phrase(np) + ' la')
    if obj is not None and gap != 'object':
        out.append(noun_phrase(obj))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            out.append(noun_phrase(np) + ' ' + POSTPOSITIONS.get((np.prep.lemma, np.case), 'na'))
        elif role == 'means':
            text = noun_phrase(np)
            out.append(text + ' la' if np.animate else particle(text, 'erg'))   # 人なら受け手 la、物なら具格
        else:
            out.append(noun_phrase(np) + ' na')
    verb = verb_word(clause)
    if not final:
        verb = particle(verb, 'nom')   # 関係節・名詞化 (bstod pa)
    elif clause.mood != 'imperative':
        verb = _sentence_end(verb, question, clause)
    out.append(wh)
    out.append(verb)
    return ' '.join(w for w in out if w)


@functools.lru_cache(maxsize=1)
def _converter():
    """Wylie → チベット文字 (pyewts。無ければ None)"""
    try:
        import pyewts
    except ImportError:
        return None
    return pyewts.pyewts()


def tibetan_script(wylie):
    """Wylie → チベット文字。[英語] (訳語の無い語) はそのまま。pyewts が無ければ None"""
    converter = _converter()
    if converter is None:
        return None
    import re
    return ''.join(part if part.startswith('[') else converter.toUnicode(part)
                   for part in re.split(r'(\[[^\]]*\])', wylie))


def sentence(clauses):
    """チベット文字 (と Wylie の行)。pyewts が無ければ Wylie だけ"""
    if not clauses:
        return ''
    from .frame import split_address
    parts = []
    for c in clauses:
        groups, rest = split_address(c)
        keys = rest.connectives + ([rest.subordinator] if rest.subordinator else [])
        words = [noun_phrase(np) for group in groups for np in group] + \
            [CONNECTIVES[key] for key in keys if key in CONNECTIVES] + [realize(rest)]
        parts.append(' '.join(words))
    wylie = ' / '.join(parts) + ' /'   # 節の区切りと文の終わりはシャド (།)
    script = tibetan_script(wylie)
    return '%s\n            %s' % (script, wylie) if script else wylie
