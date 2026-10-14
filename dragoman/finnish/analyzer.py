#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フィンランド語の文の解析
#
# spaCy (fi_core_news_sm) の品詞・原形・格・依存関係で語の項目を作り (finnish/morphology.py)、否定動詞・助動詞を
# 本動詞にまとめてから、並列・係り先・格の枠・日本語訳は共通の解析器 (core/analyzer.py) をフィンランド語の設定
# (FINNISH) で使う:
#   - 15の格: 主格「が」、属格「の」(名詞の前から掛かる)、分格・目的語の属格「を」、内格 -ssa「〜の中で」、出格 -sta
#     「〜の中から」、入格 -Vn「〜の中へ」、所格 -lla「〜で」、離格 -lta「〜から」、向格 -lle「〜に」、様格 -na
#     「〜として」、変格 -ksi「〜に (なる)」…。目的語 (依存関係の obj) の属格・分格・主格は対格に読み替える
#   - 否定動詞 ei (人称で変わる: en, et, ei, emme …) + 本動詞は否定、olla + 過去分詞は完了 (Olen lukenut「私は読んだ」)、
#     voida・täytyä・haluta + 不定詞「〜できる・〜ねばならない・〜したい」
#   - 所格 + olla は所有 (Minulla on kaksi kissaa「私には猫が2匹いる」)、olla の補語は繋辞の文
#   - 所有の接尾辞 (siskoni「私の姉妹」) は「私の」、関係代名詞 joka は共通の解析器の関係節
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '-': 'comma', '(': 'comma', ')': 'comma', '"': None,
               '”': None, '“': None, '»': None, '«': None}
TOKEN = re.compile(r"[A-Za-zÅÄÖåäöÀ-ÿŠšŽž]+(?:[-:'][A-Za-zÅÄÖåäöÀ-ÿŠšŽž]+)*|\d+(?:[.,]\d+)*|[.!?…,;:—–\-()\"”“»«]")
MODALS = {'voida': 'ことができる', 'täytyä': 'なければならない', 'pitää': 'なければならない', 'haluta': 'たい',
          'saada': 'てもよい', 'alkaa': '始める', 'osata': 'ことができる'}
GENDER = 'c'


def _root_items(lemma):
    return []


FINNISH = language.Language(
    name='fi',
    and_words=('ja', 'sekä'),
    or_words=('tai', 'vai'),
    copulas=frozenset({'olla'}),
    negations=frozenset({'ei', 'en', 'et', 'emme', 'ette', 'eivät', '(ei)'}),
    case_particles=dict(morphology.CASE_JA),
    absolute_case=None,
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_precedes_head=True,
    objects_follow_verb=True,
    possessor_cases=('Ade',),
)


def tokens(text):
    return TOKEN.findall(text)


def sentences(text):
    current = []
    for token in tokens(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def _item(word):
    return word.items[0] if isinstance(word, Word) and word.items else None


def _pos(word):
    item = _item(word)
    return item.pos if item is not None else None


def _cngs(case, number):
    return [(case, number, GENDER)]


def _case_of(token, feats):
    case = morphology.CASES.get(feats.get('Case'), 'Nom')
    if token.dep_ in ('obj',) and case in ('Gen', 'Par', 'Nom', 'Acc'):
        return 'Acc'   # 目的語の属格 (kirjan)・分格 (kissaa)・主格 → 対格
    if token.dep_.startswith('nsubj') and case == 'Par':
        return 'Nom'   # 分格の主語 (存在の文の kissaa)
    return case


def item_of(token):
    feats = morphology.morph(token)
    text, lemma, pos = token.text, token.lemma_, token.pos_
    lower = text.lower()
    if pos == 'PUNCT':
        return None
    number = morphology.NUMBERS.get(feats.get('Number'), 'sg')
    if pos in ('NOUN', 'PROPN', 'NUM', 'X') or pos == 'PRON' and feats.get('PronType') != 'Rel':
        case = _case_of(token, feats)
        if pos == 'PRON':
            ja, person, pnumber = morphology.PRONOUNS.get(lemma.lower(), (lemma, 3, number))
            if token.dep_ == 'det' and lemma.lower() in morphology.DETERMINERS:
                return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': morphology.DETERMINERS[lemma.lower()],
                        'gloss_lang': 'ja', '_': [(c, n, GENDER) for c in morphology.CASES for n in ('sg', 'pl')],
                        'demonstrative': True, 'compact': True}
            return {'surface': text, 'pos': 'pronoun', 'base': lemma, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                    'number': pnumber, '_': _cngs(case, pnumber), 'compact': True, 'main': True}
        ja, gloss_lang, row = morphology.gloss(lemma, 'name' if pos == 'PROPN' else 'noun')
        if ja is None:
            ja, gloss_lang = (lemma, 'en') if pos == 'PROPN' else (lemma, 'ja')
        possessor = morphology.POSSESSORS.get((feats.get('Person[psor]'), feats.get('Number[psor]')))
        if possessor and gloss_lang == 'ja':
            ja = ','.join(possessor + j for j in ja.split(',')[:2])
        if pos == 'NUM':
            if ja and gloss_lang == 'ja' and len(ja) <= 2:
                ja += 'つの'   # 数詞は「二つの」(名詞に掛ける)
            return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja, 'gloss_lang': gloss_lang,
                    '_': [(c, n, GENDER) for c in morphology.CASES for n in ('sg', 'pl')], 'main': True}
        data = {'surface': text, 'pos': 'noun', 'base': lemma, 'lemma': lemma, 'ja': ja, 'gloss_lang': gloss_lang,
                '_': _cngs(case, number), 'main': True, 'case_name': morphology.CASE_NAMES.get(feats.get('Case'))}
        if pos == 'PROPN':
            data['proper'] = True
        if possessor:   # 所有の接尾辞 (siskoni「私の姉妹」。文の枠では所有形容詞に)
            data['possessive'] = 'P%s%s' % (feats.get('Person[psor]'), 'sg' if feats.get('Number[psor]') == 'Sing' else 'pl')
        return data
    if pos == 'PRON':   # 関係代名詞 joka
        return {'surface': text, 'pos': 'pronoun', 'base': lemma, 'ja': '〜するところの', 'gloss_lang': 'ja',
                'desc': '関係代名詞', '_': [(c, number, g) for c in (_case_of(token, feats),) for g in (GENDER,)],
                'compact': True}
    if pos == 'ADJ':
        ja, gloss_lang, row = morphology.gloss(lemma, 'adj')
        case = morphology.CASES.get(feats.get('Case'), 'Nom')
        return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en',
                '_': [(case, number, GENDER), (case, 'pl' if number == 'sg' else 'sg', GENDER)], 'main': True}
    if pos == 'DET':
        ja = morphology.DETERMINERS.get(lemma.lower(), lemma)
        return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja, 'gloss_lang': 'ja',
                '_': [(c, n, GENDER) for c in morphology.CASES for n in ('sg', 'pl')], 'demonstrative': True}
    if pos in ('VERB', 'AUX'):
        return _verb_data(token, feats)
    if pos == 'ADP':
        return {'surface': text, 'pos': 'preposition', 'base': lemma,
                'ja': morphology.ADPOSITIONS.get(lemma.lower(), '〜' + lemma), 'gloss_lang': 'ja', 'dominates': 'Gen'}
    if pos in ('CCONJ', 'SCONJ'):
        return {'surface': text, 'pos': 'conj', 'base': lemma, 'ja': morphology.CONJUNCTIONS.get(lower, lemma),
                'gloss_lang': 'ja'}
    ja, gloss_lang, row = morphology.gloss(lower if lower in morphology.GLOSSES else lemma, 'adv')
    return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en'}


def _verb_data(token, feats):
    lemma = token.lemma_
    ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    tense = {'Pres': 'present', 'Past': 'perfect'}.get(feats.get('Tense'), 'present')
    mood = {'Ind': 'indicative', 'Imp': 'imperative', 'Cnd': 'subjunctive', 'Pot': 'subjunctive'}.get(feats.get('Mood'),
                                                                                                   'indicative')
    if feats.get('VerbForm') in ('Inf', 'Part'):
        mood = 'participle' if feats.get('VerbForm') == 'Part' else 'infinitive'
    person = int(feats['Person']) if feats.get('Person', '').isdigit() else 3
    data = {'surface': token.text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
            'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en', 'voice': 'passive' if feats.get('Voice') == 'Pass' else 'active',
            'mood': mood, 'tense': tense, 'person': person, 'number': morphology.NUMBERS.get(feats.get('Number'), 'sg'),
            'main': True, 'part_past': feats.get('PartForm') == 'Past'}
    if lemma == 'olla':
        data['existential'] = token.dep_ not in ('cop', 'aux')
        if token.dep_ == 'cop:own' or token.dep_ == 'ROOT':
            data['existential'] = True
    if feats.get('Polarity') == 'Neg' and lemma == 'ei':
        data['negation_verb'] = True
    return data


def merge_verbs(words, doc):
    """否定動詞 ei・完了の olla・話法の動詞を本動詞にまとめる (助動詞の位置に置く)"""
    by_i = {w.doc_i: w for w in words}
    removed = set()
    for token in doc:
        word = by_i.get(token.i)
        item = _item(word) if word is not None else None
        if item is None or item.pos != 'verb':
            continue
        head = by_i.get(token.head.i)
        hitem = _item(head) if head is not None else None
        if token.dep_ == 'aux' and hitem is not None and hitem.pos == 'verb' and token.i < token.head.i:
            data = dict(hitem.item)
            data.update(person=item.attrib('person'), number=item.attrib('number'), mood='indicative',
                        surface=word.surface + ' … ' + head.surface)
            data.pop('existential', None)
            if item.attrib('negation_verb'):   # ei tullut「来なかった」・ei tule「来ない」
                data['tense'] = 'perfect' if hitem.attrib('part_past') else 'present'
                data['negated'] = True
                data['form'] = '否定動詞 ei'
            elif item.attrib('lemma') == 'olla' and hitem.attrib('part_past'):   # olen lukenut「私は読んだ」
                data['tense'] = 'pluperfect' if item.attrib('tense') == 'perfect' else 'perfect'
                data['form'] = '完了 (olla + 過去分詞)'
            elif item.attrib('lemma') in MODALS and hitem.attrib('gloss_lang') == 'ja':
                from dragoman.core.japanese import attach_auxiliary
                data['ja'] = attach_auxiliary(hitem.ja.split(',')[0], MODALS[item.attrib('lemma')])
                data['tense'] = item.attrib('tense')
                data['form'] = '%s + 不定詞' % item.attrib('lemma')
            else:
                data['tense'] = item.attrib('tense')
            word.items = [type(hitem)(data)]
            word.surface = data['surface']
            word.token_ixs = (word.token_ix, head.token_ix)
            word.token_ix = head.token_ix
            if data.get('negated'):
                word.negated_verb = True
            removed.add(id(head))
    out = []
    for w in words:
        if id(w) in removed:
            continue
        out.append(w)
        if getattr(w, 'negated_verb', False):
            neg = Word('(ei)', [{'surface': '(ei)', 'pos': 'adv', 'base': 'ei (否定)', 'ja': '〜ない', 'gloss_lang': 'ja'}])
            neg.token_ix = None
            out.insert(len(out) - 1, neg)
    return out


def lookup_all(surfaces):
    doc = morphology.parse(surfaces)
    words = []
    for token in doc:
        data = item_of(token)
        word = Word(token.text, None if data is None else [data])
        word.token_ix = token.i
        word.doc_i = token.i
        words.append(word)
    words = merge_verbs(words, doc)
    for i, word in enumerate(words):
        word.index = i
    return words


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(FINNISH):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
