#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ラテン語文の解析
#   語の列 → 辞書引き (手作りの辞書 → Wiktionary。2語の形 amātus est、-que) → 品詞タガー (RFTagger) で候補を並べ替え
#   → 共通の解析器 (core/analyzer.py) をラテン語の設定 (latin/profile.py) で
#
# 結果は SentenceAnalysis で返す。表示は core/render.py
#
import os

from dragoman.core import language
from dragoman.core.analyzer import analyze_words, SentenceAnalysis, Clause  # noqa: F401 (ラテン語の解析器からも使えるように)
from dragoman.core.Word import Word
from . import latindic
from . import ldt
from . import profile
from . import rftagger
from . import latin_char as char
from . import textutil


def lookup_all(surfaces_uc):
    def lookup(surface, use_wiktionary=True):
        # 手作りの辞書 (そのまま → 小文字化 → -que を外す) → Wiktionary (同じ順) の順に引く
        sources = [latindic.lookup_abbreviation, latindic.lookup_hand_deponent]   # 個人名の略 (C.) を先に
        if use_wiktionary:
            sources.append(latindic.lookup_wiktionary)
        for source in sources:
            items = source(surface)
            if items: return Word(surface, items)
            if char.isupper(surface[0]):
                items = source(char.tolower(surface))
                if items: return Word(surface, items)
            if surface[-3:] == 'que':
                items = source(surface[:-3])
                if items:
                    return Word(surface, items, {'enclitic':'que'})
        return None

    words = []

    l = len(surfaces_uc)
    i = 0
    while i < l:
        surface = surfaces_uc[i]
        if ord(surface[0]) <= 64: # 辞書引き（記号のみから成る語を除く）
            words.append(Word(surface, None))
            i += 1
            continue
        if i < l-1:
            surface2 = surface + ' ' + surfaces_uc[i+1]
            # 2語の形 (amātus est など) は Wiktionary からは1語目が手作りの辞書に無いときだけ引く
            # (īgnōta erant が「赦されていた」になる、のような取り違えを避ける)
            word2 = lookup(surface2, use_wiktionary=lookup(surface, use_wiktionary=False) is None)
            # print "word2:", word2.encode('utf-8'), util.render(lu2)
            if word2 is not None: # len(word2.items) > 0: #is not None: and len(lu2) > 0:
                words.append(word2)
                i += 2
                continue
        word = lookup(surface)
        if word is not None:
            words.append(word)
        else:
            words.append(Word(surface, []))
        i += 1

    # 代名詞の sē を、古い前置詞 sē (= sine「〜なしに」) と読まない
    for word in words:
        if word.items and word.surface.lower() in ('sē', 'se') and \
                any(item.pos == 'pronoun' for item in word.items):
            word.items = [item for item in word.items if item.pos != 'preposition']

    # words の中での添字情報をWordインスタンスに保存
    for i, word in enumerate(words):
        word.index = i

    return words



# RFTagger の品詞タグで語の解釈を絞り込むか (環境変数 LATIN_TAGGER=0 で無効。RFTagger が無ければ使わない)
USE_TAGGER = os.environ.get('LATIN_TAGGER', '1') != '0'


def _word_tags(words, tags):
    """文の語ごとのタグを、lookup_all の結果 (2語まとめた語を含む) に位置を合わせる"""
    result = []
    k = 0
    for word in words:
        n = len(word.surface.split(' '))
        result.append(tags[k] if n == 1 and k < len(tags) else None)  # 2語まとめた語 (amātus est) には付けない
        k += n
    return result


def apply_tags(words, tags):
    """タグと矛盾しない辞書の項目を先頭に、その項目の中でもタグに合う格の候補を先頭に並べ替える。
    候補は消さない (タガーの誤りで情報を失わないため。ō の後の呼格のような規則も他の候補を見られる)"""
    for word, tag in zip(words, tags):
        word.tag = tag
        if not tag or not word.items:
            continue
        features = ldt.parse(tag)
        indeclinable = features.get('pos') in ('adv', 'conj', 'preposition')
        if indeclinable:
            # 副詞・接続詞・前置詞の判定は格などの情報を持たないので、並べ替えには使わない
            # (quod の項目の並び順に依存する規則などを壊さないため)。
            # 手作りの辞書にその読みが無い場合だけ Wiktionary から補う (sōlum「〜だけ」(副詞) など)
            if any(ldt.item_matches(item.item, features) for item in word.items) or \
               any(item.attrib('source') == 'wiktionary' for item in word.items):
                continue
            extra = Word(word.surface, latindic.lookup_wiktionary(word.surface) or []).items
            matching = [item for item in extra if ldt.item_matches(item.item, features)]
        else:
            matching = [item for item in word.items
                        if ldt.item_matches(dict(item.item, _=item._), features)]
        if not matching:
            continue
        for item in matching:
            if item._ and 'case' in features:
                first = [cng for cng in item._ if ldt.item_matches({'_': [cng]}, features)]
                item._ = first + [cng for cng in item._ if cng not in first]
        word.items = matching + [item for item in word.items if item not in matching]


def tagger_enabled():
    return USE_TAGGER and rftagger.available()


def attach_praenomina(words):
    """個人名の略 (C. Caesar の C.) を後ろの名の修飾語に (格は後ろの名と同じ。解析の対象からは外れる)"""
    for word, following in zip(words, words[1:]):
        if word.items and word.items[0].attrib('desc') == '個人名の略' and following.items is not None and \
                following.surface[:1].isupper():   # 名は辞書に無いことが多い (Caesar (?)) ので、大文字の語なら付ける
            cases = {c for item in following.items for c, _, _ in item._ or []}
            word.restrict_cases(cases or [c for c, _, _ in word.items[0]._])
            following.add_modifier(word)


def _clause_initial(words, ix):
    """節の頭の語か (文の頭、句読点・et の後ろ。前に出た主語の後ろも: Perseus ubi haec audīvit, …)"""
    k = ix
    while k > 0 and words[k - 1].items and words[k - 1].items[0].pos == 'noun' and \
            any(c == 'Nom' for i in words[k - 1].items for c, _, _ in i._ or []):
        k -= 1
    if k > 0 and words[k - 1].surface.lower() == 'at':
        k -= 1
    return k == 0 or words[k - 1].items is None or words[k - 1].surface.lower() in ('et', 'sed', 'nam', 'autem')


def subordinating_cum_ubi(words):
    """節の頭の cum・ubi を従属接続詞「〜するとき」に (Cum vēnit, eum vīdī.)。cum は奪格の語より先に定動詞が来るときだけ
    (cum amīcīs vēnit「友と」は前置詞)、ubi は疑問文でなく名詞の後ろでもないとき (locus ubi …「そこで」は関係の副詞)"""
    question = any(w.surface in ('?',) for w in words)
    for ix, word in enumerate(words):
        lower = word.surface.lower()
        if lower not in ('cum', 'ubi') or not word.items or not _clause_initial(words, ix):
            continue
        if lower == 'ubi' and question:
            continue
        if lower == 'cum':
            ablative = False
            for w in words[ix + 1:]:
                if w.items is None:
                    break
                if any(i.pos == 'verb' and i.attrib('mood') in ('indicative', 'subjunctive') for i in w.items):
                    break
                if any(c == 'Abl' for i in w.items for c, _, _ in i._ or []):
                    ablative = True
                    break
            if ablative:
                continue
        item = word.items[0]
        word.items = [type(item)(dict(item.item, pos='conj', ja='〜するとき', base=lower, _=None))]


def analyze_sentence(surfaces, tags=None):
    """文 (語の列) を解析する。tags は語ごとの品詞タグ (省略するとこの文だけでタガーを呼ぶ)"""
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    if tagger_enabled():
        if tags is None:
            tags, = rftagger.tag_sentences([list(surfaces)])
        apply_tags(words, _word_tags(words, tags))
    attach_praenomina(words)
    subordinating_cum_ubi(words)
    with language.using(profile.LATIN):
        return analyze_words(surfaces, words, word_details)


def sentences(text):
    """テキストを（句点などで）文に切り分け、各文の語の列を返す"""
    return textutil.sentence_stream(textutil.word_stream_from_text(text))


def analyze_text(text):
    all_surfaces = list(sentences(text))
    # タガーはプログラムの起動が重いので、テキスト全体を1回で処理する
    all_tags = rftagger.tag_sentences(all_surfaces) if tagger_enabled() else [None] * len(all_surfaces)
    for surfaces, tags in zip(all_surfaces, all_tags):
        yield analyze_sentence(surfaces, tags)
