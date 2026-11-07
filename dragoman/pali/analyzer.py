#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# パーリ語の文の解析
#
# 辞書引き (Digital Pāḷi Dictionary の語形の表。引けなければ DPD の分解 sammantīdha → sammanti + idha) と、
# 後置の並列 (A B ca → ca を前に) だけをここで行い、並列・係り先・格の枠・日本語訳は共通の解析器を
# パーリ語の設定 (PALI) で使う。定動詞の選び方・形容詞と名詞の一致はサンスクリットと同じ (sanskrit/analyzer.py)
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from dragoman.sanskrit.analyzer import choose_agreeing_nouns, choose_verbs
from . import dictionary, script

PUNCTUATION = {'.': 'period', '।': 'period', '॥': 'period', '။': 'period', ',': 'comma', ';': 'comma',
               '၊': 'comma', ':': 'comma', '?': 'question', '!': 'period'}
TOKEN = re.compile(r"[%s'’]+|[඀-෴ก-๎က-၉၌-႟ऀ-ॣ०-ॿ]+|"
                   r"[.,;:?!।॥၊။]" % script.LETTERS)


def _root_items(lemma):
    """動詞の見出し語の訳語 (分詞の元の動詞の訳語に使う)"""
    return dictionary.verb_items(lemma)


# 副詞節の従属接続詞 → (節の後ろに付ける形, 節の動詞の時制) (core/Adverbial.py)
SUBORDINATORS = {'yadā': ('とき', None), 'yadi': ('なら', None), 'sace': ('なら', None), 'ce': ('なら', None),
                 'yasmā': ('ので', None), 'yato': ('ので', None)}

PALI = language.Language(
    name='pi',
    subordinators=SUBORDINATORS,
    and_words=('ca',),
    or_words=('vā',),
    copulas=frozenset({'atthi', 'hoti', 'bhavati'}),
    negations=frozenset({'na', 'mā', 'no'}),
    vocative_particles=frozenset({'bho', 'he', 're', 'are', 'ambho'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Ins': 'で', 'Dat': 'に', 'Abl': 'から', 'Gen': 'の', 'Loc': 'で',
                    'Voc': 'よ'},
    absolute_case='Loc',  # 処格独立
    pronoun_subject=True,
    possessor_cases=('Gen', 'Dat'),
    lookup=_root_items,
)

POSTPOSITIVE = ('ca', 'vā')  # 後置の並列 (A B ca, A ca B ca)


def tokens(text):
    return [script.to_roman(t) if script.script_of(t) else script.normalize(t) for t in TOKEN.findall(text)]


def sentences(text):
    """テキストを文 (. ? ! । ။ で区切る) に分け、各文の語 (ローマ字) の列を返す"""
    current = []
    for token in tokens(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def _words(token):
    """1語 → Word のリスト (連声で融合していれば複数)"""
    if token in PUNCTUATION:
        return [Word(token, None)]
    word = token.lower().replace('’', "'")
    parts = dictionary.deconstruct(word)
    if len(parts) > 1 and parts[0].endswith('ṃ') and all(dictionary.lookup(p) for p in parts):
        return [Word(p, dictionary.lookup(p)) for p in parts]   # 語末の ṃ が m でつながった語 (dukkhamanveti)
    items = dictionary.lookup(word)
    if items and token[:1].islower() and any(not i.get('name') for i in items):
        items = [i for i in items if not i.get('name')]   # 小文字の語は固有名詞に読まない (manomaya「意から成る」)
    if items:
        return [Word(word, items)]
    if word.endswith('n') and dictionary.lookup(word[:-1] + 'ṃ'):   # ti の前の ṃ → n (katan ti)
        return [Word(word[:-1] + 'ṃ', dictionary.lookup(word[:-1] + 'ṃ'))]
    if word.endswith("'"):   # 母音の脱落 (tass' → tassa) は引ける形を探す
        for v in ('a', 'i', 'u', 'ā', 'e', 'o'):
            items = dictionary.lookup(word[:-1] + v)
            if items:
                return [Word(word[:-1] + v, items)]
    if len(parts) > 1:
        words = []
        for k, part in enumerate(parts):
            items = dictionary.lookup(part)
            if not items and k < len(parts) - 1:
                items = dictionary.stem_items(part)   # 複合語の前の要素 (語幹)
            words.append(Word(part, items))
        return words
    return [Word(word, [])]


def lookup_all(surfaces):
    words = []
    for ix, surface in enumerate(surfaces):
        for word in _words(surface):
            word.token_ix = ix  # 元の語の位置 (分解・後置の ca の移動の後も)
            words.append(word)
    choose_verbs(words)
    choose_agreeing_nouns(words)
    # 後置の並列 (A B ca) は ca を前の語の手前に移して、ラテン語と同じ形 (A et B / et A et B) にする
    for i in range(1, len(words)):
        if words[i].surface in POSTPOSITIVE and words[i].items and words[i].items[0].pos == 'conj':
            words[i - 1], words[i] = words[i], words[i - 1]
    for i, word in enumerate(words):
        word.index = i
    return words


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(PALI):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.tokens = list(surfaces)   # 入力の語 (ローマ字に揃えたもの。見出し・カタカナ読みに)
    return analysis


def analyze_text(text):
    shown = script.script_of(text)   # 入力の文字 (シンハラ文字・タイ文字 …。ローマ字なら None)
    for surfaces in sentences(text):
        analysis = analyze_sentence(surfaces)
        analysis.script = shown
        yield analysis
