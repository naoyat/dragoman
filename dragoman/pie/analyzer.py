#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 印欧祖語 (シュライヒャーの表記) の文の解析
#
# 手作りの辞書 (lexicon.py) で語を引き、動詞の前に離して書いた加音 ā を動詞に含め、後置の ka「と」を前に移してから、
# 共通の解析器を印欧祖語の設定 (PIE) で使う。定動詞の選び方・形容詞と名詞の一致はサンスクリットと同じ
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from dragoman.sanskrit.analyzer import choose_agreeing_nouns, choose_verbs
from . import dictionary
from .lexicon import AUGMENT

PUNCTUATION = {'.': 'period', ',': 'comma', ';': 'comma', ':': 'period', '?': 'question', '!': 'period'}   # 引用の前の : で文を分ける
TOKEN = re.compile(r"[A-Za-zĀāĪīŪū]+(?:-[A-Za-zĀāĪīŪū]+)*|[.,;:?!]")

PIE = language.Language(
    name='ine',
    and_words=('ka',),
    copulas=frozenset({'as'}),
    negations=frozenset({'na'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Ins': 'で', 'Dat': 'に', 'Abl': 'から', 'Gen': 'の', 'Loc': 'で',
                    'Voc': 'よ'},
    absolute_case='Loc',
    pronoun_subject=True,
    possessor_cases=('Dat', 'Gen'),
    lookup=dictionary.verb_items,
    dictionary=dictionary,
)

POSTPOSITIVE = ('ka',)


def tokens(text):
    """語と句読点 (引用符は捨てる。vividvant-svas のハイフンの語は1語のまま: 辞書引きで分ける)"""
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


def lookup_all(surfaces):
    words = []
    augment = False
    pieces = [(ix, part) for ix, surface in enumerate(surfaces) for part in surface.split('-') if part]
    surfaces = [part for _, part in pieces]
    for ix, surface in enumerate(surfaces):
        if surface.lower() == AUGMENT and ix + 1 < len(surfaces) and any(
                i['pos'] == 'verb' for i in dictionary.lookup(surfaces[ix + 1])):
            augment = True   # 次の動詞の加音
            continue
        if surface in PUNCTUATION:
            word = Word(surface, None)
        else:
            items = dictionary.lookup(surface)
            if augment:
                for item in items:
                    item['augment'] = True
            word = Word(surface, items)
        augment = False
        word.token_ix = pieces[ix][0]
        words.append(word)
    choose_verbs(words)
    choose_agreeing_nouns(words)
    # 後置の ka (A B ka) は前の語の手前に移して、ラテン語の et と同じ形 (A et B) にする
    for i in range(1, len(words)):
        if words[i].surface.lower() in POSTPOSITIVE and words[i].items and words[i].items[0].pos == 'conj':
            words[i - 1], words[i] = words[i], words[i - 1]
    for i, word in enumerate(words):
        word.index = i
    return words


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(PIE):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.tokens = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
