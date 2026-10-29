#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 語の置き換え: 元の言語の語 (Lex) → 作る言語の見出し語
#
#   英語を仲立ちにする: 元の語の英語の訳語の候補 (english.candidates。解析の日本語に合うものが先頭) と、
#   作る言語の見出し語の英語の訳語 ($DRAGOMAN_DATA/<lang>/en-index.tsv。tools/build_english_index.py) を突き合わせる。
#   どちらの訳語の並びでも前にあるほど、語義の多い (よく使う) 語ほど良い。さらに、作る言語の辞書の日本語の訳語
#   (<lang>/wiktionary.sqlite。無ければ英語の訳語を英語 → 日本語の表で) が元の語の日本語の訳語と合えば良くする
#     rēx「王」→ sa: rAjan (君主,王,…) を sTapati より先に
#     puella (girl, lass, maiden …) → ru: девочка (girl, little girl)、sa: kanyA (maiden, daughter …)
#
import csv
import functools
import math
import os
import re
import sqlite3
from dataclasses import dataclass

from dragoman.core import paths, en_ja
from . import english


@dataclass(frozen=True)
class Target:
    lemma: str
    pos: str
    english: tuple
    gender: str = ''
    gana: str = ''     # サンスクリットの動詞の類
    senses: int = 1


# 英語 → 見出し語の表: Wiktionary 由来 (tools/build_english_index.py) と、サンスクリットは Apte の英梵辞典
# (tools/build_sanskrit_apte.py。7列目に英語の見出しの中での候補の順位)
INDEX_FILES = {'sa': ('en-index.tsv', 'en-index-apte.tsv')}


@functools.lru_cache(maxsize=4)
def _index(lang):
    """英語 → [(訳語の中の順位, Target)]"""
    if lang == 'la':
        return _latin_index()
    index = {}
    for name in INDEX_FILES.get(lang, ('en-index.tsv',)):
        path = paths.data(lang, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            for row in csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                if len(row) not in (6, 7):
                    continue
                lemma, pos, en, gender, gana, senses = row[:6]
                glosses = tuple(g.strip() for g in en.split(',') if g.strip())
                target = Target(lemma, pos, glosses, gender, gana, int(senses))
                if len(row) == 7:   # 英梵辞典: 見出しの英語ひとつ (chest=box は chest で引き、box で日本語と照らす)
                    key, _, ref = en.partition('=')
                    target = Target(lemma, pos, (ref or key,), gender, gana, int(senses))
                    index.setdefault(key.lower(), []).append((int(row[6]), target))
                    continue
                for rank, g in enumerate(glosses):
                    index.setdefault(g.lower(), []).append((rank, target))
    _add_hand_glosses(lang, index)
    return index


def _guess_pos(lang, lemma, known):
    if known:
        return known
    if lang == 'ko' and lemma.endswith('다') or lang == 'mn' and lemma.endswith('х') or \
            lang == 'tr' and lemma.endswith(('mak', 'mek')) or lang == 'de' and lemma.islower() and lemma.endswith('en'):
        return 'verb'
    return 'noun'


def _add_hand_glosses(lang, index):
    """解析器の手作りの訳語の表の語を、日本語の訳語から和英 (JMdict) で引いた英語の索引にも入れる (辞書に無い基本語:
    モンゴル語の сарнай「バラ」)"""
    table = hand_glosses(lang)
    if not table:
        return
    poses = {}
    for entries in index.values():
        for _, target in entries:
            poses.setdefault(target.lemma, target.pos)
    for lemma, jas in table.items():
        pos = _guess_pos(lang, lemma, poses.get(lemma))
        english_words = []
        for ja in jas:
            english_words += [e for e in _ja_english(ja)[:3] if e not in english_words]
        if not english_words:
            continue
        target = Target(lemma, pos, tuple(english_words), '', '', 3)
        for rank, en in enumerate(english_words[:4]):
            index.setdefault(en.lower(), []).append((rank, target))


@functools.lru_cache(maxsize=1)
def _latin_index():
    """ラテン語を作るとき: 英語 → ラテン語の見出し (la-en.tsv。english._table を逆に)"""
    table, _ = english._table()
    index = {}
    for (lemma, pos), entries in table.items():
        for glosses in entries:
            target = Target(lemma, pos, tuple(glosses), '', '', len(glosses))
            for rank, g in enumerate(glosses):
                index.setdefault(g.lower(), []).append((rank, target))
    return index


@functools.lru_cache(maxsize=4)
def _by_lemma(lang):
    """見出し → [英語] (ロシア語・サンスクリットの語の英語の訳語。en-index.tsv を見出しで)"""
    out = {}
    for name in INDEX_FILES.get(lang, ('en-index.tsv',))[:1]:
        path = paths.data(lang, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            for row in csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                if len(row) >= 6:
                    out.setdefault((row[0], row[1]), []).extend(g.strip() for g in row[2].split(',') if g.strip())
    return out


def _in_hand_dictionary(lemma):
    from . import latin
    return lemma in latin._hand_index()


# 解析器の手作りの訳語の表 (基本の語の日本語。Wiktionary の語義の順だけでは 계집・tappo のような語が先に来る) を、
# ラテン語の手作りの辞書と同じく語の選択に使う言語
HAND_GLOSSES = {'ko': 'korean', 'de': 'german', 'fr': 'french', 'tr': 'turkish', 'mn': 'mongolian', 'fi': 'finnish',
                'ang': 'oldenglish', 'pt': 'portuguese', 'zh': 'chinese'}


class _KeyedTable(dict):
    """見出しを鍵の形にして引く表 (古英語: 手の表は口蓋音の点を除いた形、辞書の見出しは ġiefan)"""
    def __init__(self, table, key):
        super().__init__(table)
        self.key = key

    def get(self, lemma, default=None):
        return super().get(self.key(lemma), default)

    def __contains__(self, lemma):
        return super().__contains__(self.key(lemma))


@functools.lru_cache(maxsize=None)
def hand_glosses(lang):
    """見出し → 日本語の訳語の集合 (解析器の GLOSSES)"""
    if lang not in HAND_GLOSSES:
        return {}
    import importlib
    try:
        table = importlib.import_module('dragoman.%s.morphology' % HAND_GLOSSES[lang]).GLOSSES
    except ImportError:
        return {}
    table = {lemma: frozenset(j.strip() for j in ja.split(',')) for lemma, ja in table.items() if '#' not in lemma}
    if lang == 'ang':
        from dragoman.oldenglish import orthography
        return _KeyedTable(table, orthography.lemma_key)
    return table


def source_key(lang, lemma):
    """元の言語の見出しを表の形に (サンスクリットは IAST → SLP1)"""
    if lang == 'sa':
        from dragoman.sanskrit import script
        return script.to_slp1(lemma.replace('-', ''))   # 複合語・語根の切れ目 (rāma-lakṣmaṇa、ud-i) は除く
    if lang == 'ru':
        from dragoman.russian import script
        return script.key(lemma)
    return lemma


def english_glosses(lang, lemma, pos):
    """元の言語の語の英語の訳語 (表から)"""
    pos = {'participle': 'verb', 'name': 'noun'}.get(pos, pos)
    glosses = list(dict.fromkeys(OPEN_END.sub('', g) for g in _by_lemma(lang).get((source_key(lang, lemma), pos), [])))
    for k, g in enumerate(glosses):
        m = FORM_OF.search(g)
        if m and m.group(1) != lemma:   # strengthened form of θνῄσκω with the same meaning → θνῄσκω の訳語
            glosses = glosses[:k] + english_glosses(lang, m.group(1), pos) + glosses[k + 1:]
            break
    first = FIRST_GLOSSES.get(lang, {}).get(lemma)
    return [first] + [g for g in glosses if g != first] if first in glosses else glosses


# 教科書の基本の語の表 (PREFERRED) を逆に引いて、元の言語の語の英語の訳語を決める言語 (rosa → rose、玫瑰 → rose。
# 辞書の最初の語義が外れる: rugosa rose)
PREFERRED_AS_ENGLISH = ('pt', 'zh')


@functools.lru_cache(maxsize=None)
def _preferred_by_lemma(lang):
    out = {}
    for (en, pos), value in PREFERRED.get(lang, {}).items():
        lemma = value[0] if isinstance(value, tuple) else value
        out.setdefault((lemma, pos), []).append(en)
    return out


def preferred_english(lang, lemma, pos):
    """教科書の基本の語の表でこの語を選ぶ英語 (無ければ [])"""
    if lang not in PREFERRED_AS_ENGLISH:
        return []
    return _preferred_by_lemma(lang).get((lemma, {'participle': 'verb', 'name': 'noun'}.get(pos, pos)), [])


OPEN_END = re.compile(r'(?:\s+that)?\s*(?:\.\.\.|…)$')   # CC-CEDICT の語義の後ろの空所 (to think that ... → think)
FORM_OF = re.compile(r'\bform of ([^\sA-Za-z,]+)')   # 説明の語義 (… form of + 元の言語の語)
# 表の最初の訳語が教科書の意味でない語 (βασιλεύς: chief, emperor, … king): 先に使う訳語
FIRST_GLOSSES = {'fr': {'partir': 'leave'},   # 辞書に古い語源 (share) の項目しか無い
                 'ang': {'mann': 'man', 'weġ': 'road', 'here': 'army'},
                 'grc': {'βασιλεύς': 'king', 'ὁράω': 'see', 'λόγος': 'word', 'ἀνήρ': 'man', 'κόρη': 'girl',
                         'λέγω': 'say', 'γράφω': 'write', 'παῖς': 'child', 'πόλις': 'city', 'ἔχω': 'have'}}


def available(lang):
    return bool(_index(lang))


@functools.lru_cache(maxsize=4)
def _db(lang):
    path = paths.data(lang, 'wiktionary.sqlite')
    return sqlite3.connect(path, check_same_thread=False) if os.path.exists(path) else None


@functools.lru_cache(maxsize=8)
def _has_japanese(lang):
    db = _db(lang)
    return db is not None and 'ja' in [row[1] for row in db.execute('PRAGMA table_info(lemmas)')]


@functools.lru_cache(maxsize=50000)
def japanese(lang, target):
    """作る言語の見出し語の日本語の訳語 (の集合)"""
    out = set()
    if lang == 'la':   # ラテン語の辞書 (手作りの辞書・Wiktionary) の項目の訳語
        from . import latin
        from .ja_lexicon import _keys
        for _, item in latin._forms(target.lemma, target.pos)[:20]:
            out.update(_keys(item.get('ja')))
        return frozenset(out)
    out.update(hand_glosses(lang).get(target.lemma, ()))
    db = _db(lang) if _has_japanese(lang) else None   # 日本語の訳語の列が無い辞書 (ギリシア語・インドネシア語) は英語から
    if db is not None:
        pos = 'root' if target.pos == 'verb' and lang == 'sa' else target.pos
        for ja, gloss_lang in db.execute('SELECT ja, gloss_lang FROM lemmas WHERE key = ? AND pos IN (?, ?)',
                                         (target.lemma, pos, target.pos)):
            if gloss_lang == 'ja':
                out.update(j.strip() for j in ja.split(','))
    for en in target.english[:2]:
        out.update(en_ja.lookup(en, target.pos))
    return frozenset(out)


# 基本の語は、教科書でよく使う語を先に (英語の訳語の表と語義の数だけでは、девушка / kanyakA のような語が先に来る)。
# (英語, 品詞) → (見出し語, 性または語根の類)
PREFERRED = {
    'ru': {('world', 'noun'): ('мир', 'm'), ('only-begotten', 'adj'): ('единородный', ''), ('human', 'noun'): ('человек', 'm'), ('human being', 'noun'): ('человек', 'm'), ('pity', 'verb'): ('жалеть', ''), ('feel pity', 'verb'): ('жалеть', ''),
           ('have mercy on', 'verb'): ('помиловать', ''),
           ('girl', 'noun'): ('девочка', 'f'), ('book', 'noun'): ('книга', 'f'), ('king', 'noun'): ('царь', 'm'),
           ('farmer', 'noun'): ('крестьянин', 'm'), ('sailor', 'noun'): ('моряк', 'm'),
           ('slave', 'noun'): ('раб', 'm'), ('lord', 'noun'): ('господин', 'm'), ('master', 'noun'): ('господин', 'm'),
           ('teacher', 'noun'): ('учитель', 'm'), ('letter', 'noun'): ('письмо', 'n'),
           ('walk', 'verb'): ('гулять', ''), ('love', 'verb'): ('любить', ''), ('sing', 'verb'): ('петь', ''),
           ('praise', 'verb'): ('хвалить', ''), ('see', 'verb'): ('видеть', ''), ('give', 'verb'): ('давать', ''),
           ('carry', 'verb'): ('нести', ''), ('convey', 'verb'): ('нести', ''), ('say', 'verb'): ('говорить', ''),
           ('beautiful', 'adj'): ('красивый', ''), ('great', 'adj'): ('великий', ''),
           ('good', 'adj'): ('хороший', ''), ('long', 'adj'): ('длинный', ''), ('city', 'noun'): ('город', 'm'),
           ('town', 'noun'): ('город', 'm'), ('road', 'noun'): ('дорога', 'f'), ('forest', 'noun'): ('лес', 'm'),
           ('field', 'noun'): ('поле', 'n'), ('flower', 'noun'): ('цветок', 'm'), ('friend', 'noun'): ('друг', 'm'),
           ('male friend', 'noun'): ('друг', 'm'), ('man', 'noun'): ('мужчина', 'm'),
           ('people', 'noun'): ('народ', 'm'), ('queen', 'noun'): ('царица', 'f'), ('mother', 'noun'): ('мать', 'f'),
           ('soldier', 'noun'): ('солдат', 'm'), ('enemy', 'noun'): ('враг', 'm'), ('sword', 'noun'): ('меч', 'm'),
           ('thing', 'noun'): ('дело', 'n'), ('camp', 'noun'): ('лагерь', 'm'), ('word', 'noun'): ('слово', 'n'),
           ('messenger', 'noun'): ('вестник', 'm'), ('life', 'noun'): ('жизнь', 'f'), ('temple', 'noun'): ('храм', 'm'),
           ('think', 'verb'): ('думать', ''), ('consider', 'verb'): ('думать', ''), ('come', 'verb'): ('приходить', ''),
           ('weep', 'verb'): ('плакать', ''), ('laugh', 'verb'): ('смеяться', ''), ('sleep', 'verb'): ('спать', ''),
           ('wait', 'verb'): ('ждать', ''), ('fear', 'verb'): ('бояться', ''), ('fight', 'verb'): ('сражаться', ''),
           ('take', 'verb'): ('брать', ''), ('capture', 'verb'): ('брать', ''), ('move', 'verb'): ('двигать', ''),
           ('pluck', 'verb'): ('рвать', ''), ('learn', 'verb'): ('узнавать', ''), ('know', 'verb'): ('знать', ''),
           ('play', 'verb'): ('играть', ''), ('labor', 'verb'): ('трудиться', ''), ('work', 'verb'): ('работать', ''),
           ('order', 'verb'): ('велеть', ''), ('command', 'verb'): ('велеть', ''), ('read', 'verb'): ('читать', ''),
           ('crowd', 'noun'): ('народ', 'm'), ('die', 'verb'): ('умирать', ''), ('kill', 'verb'): ('убивать', ''),
           ('brother', 'noun'): ('брат', 'm'),
           ('receive', 'verb'): ('получать', ''), ('ask', 'verb'): ('спрашивать', ''),
           ('want', 'verb'): ('хотеть', ''), ('wish', 'verb'): ('хотеть', ''), ('greatly', 'adv'): ('очень', ''), ('suddenly', 'adv'): ('вдруг', ''),
           ('willingly', 'adv'): ('охотно', ''), ('gladly', 'adv'): ('охотно', ''), ('uselessly', 'adv'): ('напрасно', ''),
           ('in vain', 'adv'): ('напрасно', ''), ('heavily', 'adv'): ('тяжело', ''), ('by chance', 'adv'): ('случайно', ''),
           ('kindly', 'adv'): ('ласково', ''), ('everywhere', 'adv'): ('везде', ''),
           ('golden', 'adj'): ('золотой', ''), ('happy', 'adj'): ('счастливый', ''), ('glad', 'adj'): ('радостный', '')},
    'la': {('see', 'verb'): ('videō', ''), ('rejoice', 'verb'): ('gaudeō', ''), ('be happy', 'verb'): ('gaudeō', ''), ('die', 'verb'): ('morior', ''), ('give', 'verb'): ('dō', ''),
           ('love', 'verb'): ('amō', ''), ('like', 'verb'): ('amō', ''), ('praise', 'verb'): ('laudō', ''),
           ('read', 'verb'): ('legō', ''), ('weep', 'verb'): ('fleō', ''), ('cry', 'verb'): ('fleō', ''),
           ('boy', 'noun'): ('puer', 'm'), ('girl', 'noun'): ('puella', 'f'), ('teacher', 'noun'): ('magister', 'm'),
           ('book', 'noun'): ('liber', 'm'), ('king', 'noun'): ('rēx', 'm'), ('tsar', 'noun'): ('rēx', 'm'),
           ('people', 'noun'): ('populus', 'm'), ('garden', 'noun'): ('hortus', 'm'), ('winter', 'noun'): ('hiems', 'f'),
           ('say', 'verb'): ('dīcō', ''), ('come', 'verb'): ('veniō', ''), ('go', 'verb'): ('eō', ''),
           ('know', 'verb'): ('sciō', ''), ('want', 'verb'): ('volō', ''), ('sing', 'verb'): ('cantō', ''),
           ('write', 'verb'): ('scrībō', ''), ('live', 'verb'): ('vīvō', ''), ('city', 'noun'): ('urbs', 'f'),
           ('house', 'noun'): ('domus', 'f'), ('water', 'noun'): ('aqua', 'f'), ('man', 'noun'): ('vir', 'm'),
           ('woman', 'noun'): ('fēmina', 'f'), ('mother', 'noun'): ('māter', 'f'), ('father', 'noun'): ('pater', 'm')},
    'sa': {('only-begotten', 'adj'): ('ekaja', ''), ('girl', 'noun'): ('bAlikA', 'f'), ('boy', 'noun'): ('bAlaka', 'm'), ('king', 'noun'): ('nfpa', 'm'),
           ('book', 'noun'): ('pustaka', 'n'), ('farmer', 'noun'): ('kfzaka', 'm'), ('slave', 'noun'): ('dAsa', 'm'),
           ('lord', 'noun'): ('svAmin', 'm'), ('master', 'noun'): ('svAmin', 'm'),
           ('teacher', 'noun'): ('aDyApaka', 'm'), ('friend', 'noun'): ('mitra', 'm'),
           ('city', 'noun'): ('nagara', 'n'), ('town', 'noun'): ('nagara', 'n'), ('garden', 'noun'): ('udyAna', 'n'),
           ('forest', 'noun'): ('vana', 'n'), ('field', 'noun'): ('kzetra', 'n'), ('sea', 'noun'): ('samudra', 'm'),
           ('flower', 'noun'): ('puzpa', 'n'), ('sailor', 'noun'): ('nAvika', 'm'), ('letter', 'noun'): ('patra', 'n'),
           ('sing', 'verb'): ('gE', '1'), ('love', 'verb'): ('snih', '4'), ('say', 'verb'): ('vad', '1'),
           ('speak', 'verb'): ('vad', '1'), ('see', 'verb'): ('dfS', '1'), ('give', 'verb'): ('dA', '3'),
           ('praise', 'verb'): ('praSaMs', '1'), ('walk', 'verb'): ('cal', '1'), ('carry', 'verb'): ('vah', '1'),
           ('convey', 'verb'): ('vah', '1'), ('live', 'verb'): ('jIv', '1'), ('reside', 'verb'): ('vas', '1'),
           ('beautiful', 'adj'): ('sundara', ''), ('great', 'adj'): ('viSAla', ''), ('good', 'adj'): ('sADu', ''),
           ('daughter', 'noun'): ('duhitf', 'f'), ('man', 'noun'): ('nara', 'm'), ('road', 'noun'): ('mArga', 'm'),
           ('mother', 'noun'): ('mAtf', 'f'), ('queen', 'noun'): ('rAjYI', 'f'), ('word', 'noun'): ('vacana', 'n'),
           ('soldier', 'noun'): ('sEnika', 'm'), ('people', 'noun'): ('jana', 'm'), ('crowd', 'noun'): ('jana', 'm'),
           ('temple', 'noun'): ('mandira', 'n'), ('enemy', 'noun'): ('ari', 'm'), ('sword', 'noun'): ('Kaqga', 'm'),
           ('thing', 'noun'): ('vastu', 'n'), ('life', 'noun'): ('jIvana', 'n'), ('messenger', 'noun'): ('dUta', 'm'),
           ('happy', 'adj'): ('prasanna', ''), ('glad', 'adj'): ('prasanna', ''),
           ('labor', 'verb'): ('Sram', '4'), ('work', 'verb'): ('Sram', '4'), ('leave', 'verb'): ('nirgam', '1'),
           ('depart', 'verb'): ('nirgam', '1'), ('wait', 'verb'): ('pratiIkz', '1'), ('fear', 'verb'): ('BI', '3'),
           ('think', 'verb'): ('cint', '10'), ('consider', 'verb'): ('cint', '10'), ('learn', 'verb'): ('jYA', '9'),
           ('know', 'verb'): ('jYA', '9'), ('command', 'verb'): ('AdiS', '6'), ('order', 'verb'): ('AdiS', '6'),
           ('move', 'verb'): ('cal', '1'), ('fight', 'verb'): ('yuD', '4'), ('die', 'verb'): ('mf', '6'),
           ('weep', 'verb'): ('rud', '2'), ('laugh', 'verb'): ('has', '1'), ('sleep', 'verb'): ('svap', '2'),
           ('play', 'verb'): ('krIq', '1'), ('read', 'verb'): ('paW', '1'), ('come', 'verb'): ('Agam', '1'),
           ('receive', 'verb'): ('grah', '9'), ('greatly', 'adv'): ('atIva', ''), ('suddenly', 'adv'): ('sahasA', ''),
           ('willingly', 'adv'): ('sAnandam', ''), ('gladly', 'adv'): ('sAnandam', ''), ('uselessly', 'adv'): ('vfTA', ''),
           ('in vain', 'adv'): ('vfTA', ''), ('heavily', 'adv'): ('BfSam', ''), ('by chance', 'adv'): ('daivAt', ''),
           ('kindly', 'adv'): ('snehena', ''), ('everywhere', 'adv'): ('sarvatra', ''),
           ('place', 'noun'): ('sTAna', 'n'), ('kill', 'verb'): ('han', '2'), ('slay', 'verb'): ('han', '2'), ('reply', 'verb'): ('prativac', '2'),
           ('answer', 'verb'): ('prativac', '2'), ('stretch', 'verb'): ('tan', '8'), ('greek', 'adj'): ('yavana', ''),
           ('greek', 'noun'): ('yavana', 'm'), ('flee', 'verb'): ('palAy', '1'),
           ('ask', 'verb'): ('praC', '6'), ('begin', 'verb'): ('Arab', '1'), ('seize', 'verb'): ('grah', '9'),
           ('drag', 'verb'): ('kfz', '1'), ('climb up', 'verb'): ('Aruh', '1'), ('climb', 'verb'): ('Aruh', '1'),
           ('carefully', 'adv'): ('yatnena', ''), ('centaur', 'noun'): ('kinnara', 'm'),
           ('boat', 'noun'): ('nOkA', 'f'), ('ship', 'noun'): ('nO', 'f'), ('cattle', 'noun'): ('go', 'm'),
           ('fruit', 'noun'): ('Pala', 'n'), ('priestess', 'noun'): ('tApasI', 'f'), ('victim', 'noun'): ('paSu', 'm')},
    'mn': {('great', 'adj'): ('том', ''), ('big', 'adj'): ('том', ''), ('large', 'adj'): ('том', '')},
    'id': {('only-begotten', 'adj'): ('tunggal', ''), ('leave', 'verb'): ('pergi', ''), ('depart', 'verb'): ('pergi', ''),
           ('desire', 'verb'): ('ingin', ''), ('girl', 'noun'): ('gadis', ''), ('boy', 'noun'): ('anak laki-laki', ''), ('child', 'noun'): ('anak', ''),
           ('son', 'noun'): ('putra', ''), ('daughter', 'noun'): ('putri', ''), ('teacher', 'noun'): ('guru', ''),
           ('master', 'noun'): ('tuan', ''), ('lord', 'noun'): ('tuan', ''), ('book', 'noun'): ('buku', ''),
           ('rose', 'noun'): ('mawar', ''), ('garden', 'noun'): ('taman', ''), ('king', 'noun'): ('raja', ''),
           ('queen', 'noun'): ('ratu', ''), ('city', 'noun'): ('kota', ''), ('citizen', 'noun'): ('warga', ''),
           ('man', 'noun'): ('laki-laki', ''), ('woman', 'noun'): ('perempuan', ''), ('slave', 'noun'): ('budak', ''),
           ('sailor', 'noun'): ('pelaut', ''), ('farmer', 'noun'): ('petani', ''), ('soldier', 'noun'): ('prajurit', ''),
           ('god', 'noun'): ('dewa', ''), ('goddess', 'noun'): ('dewi', ''), ('war', 'noun'): ('perang', ''),
           ('letter', 'noun'): ('surat', ''), ('word', 'noun'): ('kata', ''), ('road', 'noun'): ('jalan', ''),
           ('way', 'noun'): ('jalan', ''), ('house', 'noun'): ('rumah', ''), ('friend', 'noun'): ('teman', ''),
           ('ship', 'noun'): ('kapal', ''), ('island', 'noun'): ('pulau', ''), ('horse', 'noun'): ('kuda', ''),
           ('sea', 'noun'): ('laut', ''), ('land', 'noun'): ('tanah', ''), ('water', 'noun'): ('air', ''),
           ('field', 'noun'): ('ladang', ''), ('forest', 'noun'): ('hutan', ''), ('wood', 'noun'): ('hutan', ''),
           ('people', 'noun'): ('rakyat', ''), ('father', 'noun'): ('ayah', ''), ('mother', 'noun'): ('ibu', ''),
           ('brother', 'noun'): ('saudara laki-laki', ''), ('sister', 'noun'): ('saudara perempuan', ''),
           ('hero', 'noun'): ('pahlawan', ''), ('monster', 'noun'): ('monster', ''), ('wife', 'noun'): ('istri', ''),
           ('see', 'verb'): ('lihat', ''), ('praise', 'verb'): ('puji', ''), ('compliment', 'verb'): ('puji', ''),
           ('give', 'verb'): ('beri', ''),
           ('have', 'verb'): ('memiliki', ''), ('say', 'verb'): ('berkata', ''), ('ask', 'verb'): ('tanya', ''),
           ('love', 'verb'): ('mencintai', ''), ('sing', 'verb'): ('nyanyi', ''), ('walk', 'verb'): ('berjalan', ''),
           ('write', 'verb'): ('tulis', ''), ('read', 'verb'): ('baca', ''), ('come', 'verb'): ('datang', ''),
           ('go', 'verb'): ('pergi', ''), ('flee', 'verb'): ('lari', ''), ('run', 'verb'): ('lari', ''),
           ('rejoice', 'verb'): ('bergembira', ''), ('be happy', 'verb'): ('bergembira', ''),
           ('carry', 'verb'): ('bawa', ''), ('bear', 'verb'): ('bawa', ''), ('lead', 'verb'): ('pimpin', ''),
           ('send', 'verb'): ('kirim', ''), ('teach', 'verb'): ('ajar', ''), ('hear', 'verb'): ('dengar', ''),
           ('fight', 'verb'): ('bertempur', ''), ('kill', 'verb'): ('bunuh', ''), ('take', 'verb'): ('ambil', ''),
           ('capture', 'verb'): ('rebut', ''), ('seize', 'verb'): ('rebut', ''), ('know', 'verb'): ('tahu', ''),
           ('want', 'verb'): ('ingin', ''), ('wish', 'verb'): ('ingin', ''), ('weep', 'verb'): ('menangis', ''),
           ('cry', 'verb'): ('menangis', ''), ('laugh', 'verb'): ('tertawa', ''), ('sleep', 'verb'): ('tidur', ''),
           ('live', 'verb'): ('tinggal', ''), ('inhabit', 'verb'): ('tinggal', ''), ('call', 'verb'): ('panggil', ''),
           ('kill', 'verb'): ('bunuh', ''), ('build', 'verb'): ('bangun', ''), ('make', 'verb'): ('buat', ''),
           ('do', 'verb'): ('buat', ''), ('die', 'verb'): ('mati', ''), ('grow', 'verb'): ('tumbuh', ''),
           ('beautiful', 'adj'): ('cantik', ''), ('pretty', 'adj'): ('cantik', ''), ('good', 'adj'): ('baik', ''),
           ('bad', 'adj'): ('buruk', ''), ('evil', 'adj'): ('jahat', ''), ('great', 'adj'): ('besar', ''),
           ('big', 'adj'): ('besar', ''), ('large', 'adj'): ('besar', ''), ('small', 'adj'): ('kecil', ''),
           ('long', 'adj'): ('panjang', ''), ('wise', 'adj'): ('bijaksana', ''), ('brave', 'adj'): ('berani', ''),
           ('new', 'adj'): ('baru', ''), ('old', 'adj'): ('tua', ''), ('many', 'adj'): ('banyak', ''),
           ('happy', 'adj'): ('bahagia', ''), ('high', 'adj'): ('tinggi', ''), ('deep', 'adj'): ('dalam', ''),
           ('famous', 'adj'): ('terkenal', ''), ('dear', 'adj'): ('tersayang', ''), ('certain', 'adj'): ('pasti', ''),
           ('same', 'adj'): ('sama', ''), ('upper', 'adj'): ('atas', ''), ('pain', 'noun'): ('rasa sakit', ''),
           ('insanity', 'noun'): ('kegilaan', ''), ('madness', 'noun'): ('kegilaan', ''),
           ('frighten', 'verb'): ('takuti', ''), ('terrify', 'verb'): ('takuti', ''), ('cease', 'verb'): ('berhenti', ''),
           ('stop', 'verb'): ('berhenti', ''), ('transfix', 'verb'): ('tusuk', ''), ('pierce', 'verb'): ('tusuk', '')},
    # φοβέω は中動態で「恐れる」(greek.MIDDLE_VERBS)
    'grc': {('fear', 'verb'): ('φοβέω', ''), ('read', 'verb'): ('ἀναγιγνώσκω', ''), ('only-begotten', 'adj'): ('μονογενής', ''), ('capture', 'verb'): ('λαμβάνω', ''), ('human', 'noun'): ('ἄνθρωπος', 'm'), ('human being', 'noun'): ('ἄνθρωπος', 'm'), ('world', 'noun'): ('κόσμος', 'm'), ('sin', 'noun'): ('ἁμαρτία', 'f'), ('glory', 'noun'): ('δόξα', 'f'),
            ('peace', 'noun'): ('εἰρήνη', 'f'), ('sky', 'noun'): ('οὐρανός', 'm'), ('heaven', 'noun'): ('οὐρανός', 'm'),
            ('pity', 'verb'): ('ἐλεέω', ''), ('feel pity', 'verb'): ('ἐλεέω', ''), ('have mercy on', 'verb'): ('ἐλεέω', ''),
            ('remove', 'verb'): ('ἀφαιρέω', ''), ('take away', 'verb'): ('ἀφαιρέω', ''),   # αἴρω は語形の表に無い
            ('girl', 'noun'): ('κόρη', 'f'), ('boy', 'noun'): ('παῖς', 'm'), ('child', 'noun'): ('παῖς', 'm'),
            ('king', 'noun'): ('βασιλεύς', 'm'), ('queen', 'noun'): ('βασίλεια', 'f'), ('book', 'noun'): ('βιβλίον', 'n'),
            ('teacher', 'noun'): ('διδάσκαλος', 'm'), ('master', 'noun'): ('δεσπότης', 'm'),
            ('lord', 'noun'): ('δεσπότης', 'm'), ('slave', 'noun'): ('δοῦλος', 'm'), ('sailor', 'noun'): ('ναύτης', 'm'),
            ('farmer', 'noun'): ('γεωργός', 'm'), ('man', 'noun'): ('ἀνήρ', 'm'), ('woman', 'noun'): ('γυνή', 'f'),
            ('city', 'noun'): ('πόλις', 'f'), ('god', 'noun'): ('θεός', 'm'), ('goddess', 'noun'): ('θεά', 'f'),
            ('war', 'noun'): ('πόλεμος', 'm'), ('letter', 'noun'): ('ἐπιστολή', 'f'), ('word', 'noun'): ('λόγος', 'm'),
            ('road', 'noun'): ('ὁδός', 'f'), ('way', 'noun'): ('ὁδός', 'f'), ('house', 'noun'): ('οἰκία', 'f'),
            ('friend', 'noun'): ('φίλος', 'm'), ('soldier', 'noun'): ('στρατιώτης', 'm'), ('ship', 'noun'): ('ναῦς', 'f'),
            ('island', 'noun'): ('νῆσος', 'f'), ('horse', 'noun'): ('ἵππος', 'm'), ('sea', 'noun'): ('θάλαττα', 'f'),
            ('land', 'noun'): ('γῆ', 'f'), ('earth', 'noun'): ('γῆ', 'f'), ('water', 'noun'): ('ὕδωρ', 'n'),
            ('see', 'verb'): ('ὁράω', ''), ('praise', 'verb'): ('ἐπαινέω', ''), ('give', 'verb'): ('δίδωμι', ''),
            ('love', 'verb'): ('φιλέω', ''), ('say', 'verb'): ('λέγω', ''), ('have', 'verb'): ('ἔχω', ''),
            ('write', 'verb'): ('γράφω', ''), ('carry', 'verb'): ('φέρω', ''), ('bear', 'verb'): ('φέρω', ''),
            ('lead', 'verb'): ('ἄγω', ''), ('come', 'verb'): ('ἔρχομαι', ''), ('go', 'verb'): ('ἔρχομαι', ''),
            ('send', 'verb'): ('πέμπω', ''), ('teach', 'verb'): ('διδάσκω', ''), ('hear', 'verb'): ('ἀκούω', ''),
            ('sing', 'verb'): ('ἀείδω', ''), ('want', 'verb'): ('βούλομαι', ''),
            ('wish', 'verb'): ('βούλομαι', ''), ('weep', 'verb'): ('κλαίω', ''), ('cry', 'verb'): ('κλαίω', ''),
            ('grow', 'verb'): ('αὐξάνω', ''), ('sleep', 'verb'): ('καθεύδω', ''), ('ask', 'verb'): ('ἐρωτάω', ''), ('walk', 'verb'): ('βαδίζω', ''), ('fight', 'verb'): ('μάχομαι', ''),
            ('kill', 'verb'): ('ἀποκτείνω', ''), ('take', 'verb'): ('λαμβάνω', ''), ('know', 'verb'): ('γιγνώσκω', ''),
            ('beautiful', 'adj'): ('καλός', ''), ('good', 'adj'): ('ἀγαθός', ''), ('bad', 'adj'): ('κακός', ''),
            ('evil', 'adj'): ('κακός', ''), ('great', 'adj'): ('μέγας', ''), ('big', 'adj'): ('μέγας', ''),
            ('large', 'adj'): ('μέγας', ''), ('small', 'adj'): ('μικρός', ''), ('long', 'adj'): ('μακρός', ''),
            ('wise', 'adj'): ('σοφός', ''), ('brave', 'adj'): ('ἀνδρεῖος', ''), ('new', 'adj'): ('νέος', ''),
            ('old', 'adj'): ('παλαιός', ''), ('many', 'adj'): ('πολύς', ''), ('dear', 'adj'): ('φίλος', '')},
    # ポルトガル語 (ブラジル)・中国語: 教科書の基本の語 (英語の索引の語義の順・UD の小さいコーパスの数だけでは
    # lavrador・庄稼汉・辟 (王) のような古い語や方言の語が先に来る)
    'pt': {('girl', 'noun'): ('menina', 'f'), ('boy', 'noun'): ('menino', 'm'),
           ('farmer', 'noun'): ('agricultor', 'm'), ('sailor', 'noun'): ('marinheiro', 'm'),
           ('people', 'noun'): ('povo', 'm'), ('crowd', 'noun'): ('multidão', 'f'),
           ('master', 'noun'): ('senhor', 'm'), ('lord', 'noun'): ('senhor', 'm'),
           ('slave', 'noun'): ('escravo', 'm'), ('field', 'noun'): ('campo', 'm'),
           ('country house', 'noun'): ('casa de campo', 'f'), ('villa', 'noun'): ('casa de campo', 'f'),
           ('encampment', 'noun'): ('acampamento', 'm'), ('camp', 'noun'): ('acampamento', 'm'),
           ('king', 'noun'): ('rei', 'm'), ('queen', 'noun'): ('rainha', 'f'), ('soldier', 'noun'): ('soldado', 'm'),
           ('enemy', 'noun'): ('inimigo', 'm'), ('enemy of the state', 'noun'): ('inimigo', 'm'),
           ('wood', 'noun'): ('floresta', 'f'), ('forest', 'noun'): ('floresta', 'f'),
           ('garden', 'noun'): ('jardim', 'm'), ('road', 'noun'): ('estrada', 'f'),
           ('letter', 'noun'): ('carta', 'f'), ('temple', 'noun'): ('templo', 'm'), ('man', 'noun'): ('homem', 'm'),
           ('woman', 'noun'): ('mulher', 'f'), ('town', 'noun'): ('cidade', 'f'), ('city', 'noun'): ('cidade', 'f'),
           ('thing', 'noun'): ('coisa', 'f'), ('teacher', 'noun'): ('professor', 'm'),
           ('book', 'noun'): ('livro', 'm'), ('rose', 'noun'): ('rosa', 'f'), ('flower', 'noun'): ('flor', 'f'),
           ('water', 'noun'): ('água', 'f'), ('sea', 'noun'): ('mar', 'm'), ('mother', 'noun'): ('mãe', 'f'),
           ('father', 'noun'): ('pai', 'm'), ('daughter', 'noun'): ('filha', 'f'), ('son', 'noun'): ('filho', 'm'),
           ('friend', 'noun'): ('amigo', 'm'), ('sky', 'noun'): ('céu', 'm'), ('heaven', 'noun'): ('céu', 'm'),
           ('house', 'noun'): ('casa', 'f'), ('word', 'noun'): ('palavra', 'f'),
           ('messenger', 'noun'): ('mensageiro', 'm'), ('wolf', 'noun'): ('lobo', 'm'),
           ('sword', 'noun'): ('espada', 'f'), ('tear', 'noun'): ('lágrima', 'f'), ('island', 'noun'): ('ilha', 'f'),
           ('give', 'verb'): ('dar', ''), ('die', 'verb'): ('morrer', ''), ('fight', 'verb'): ('lutar', ''),
           ('take', 'verb'): ('pegar', ''), ('capture', 'verb'): ('capturar', ''), ('play', 'verb'): ('brincar', ''),
           ('carry', 'verb'): ('levar', ''), ('praise', 'verb'): ('elogiar', ''), ('pluck', 'verb'): ('colher', ''),
           ('think', 'verb'): ('achar', ''), ('judge', 'verb'): ('achar', ''), ('reckon', 'verb'): ('achar', ''), ('object', 'noun'): ('coisa', 'f'), ('suppose', 'verb'): ('achar', ''), ('order', 'verb'): ('mandar', ''),
           ('command', 'verb'): ('mandar', ''), ('bid', 'verb'): ('mandar', ''), ('wound', 'verb'): ('ferir', ''),
           ('move', 'verb'): ('mover', ''), ('leave', 'verb'): ('partir', ''), ('depart', 'verb'): ('partir', ''),
           ('weep', 'verb'): ('chorar', ''), ('cry', 'verb'): ('chorar', ''), ('sing', 'verb'): ('cantar', ''),
           ('read', 'verb'): ('ler', ''), ('know', 'verb'): ('saber', ''), ('fear', 'verb'): ('temer', ''),
           ('laugh', 'verb'): ('rir', ''), ('wait for', 'verb'): ('esperar', ''), ('see', 'verb'): ('ver', ''),
           ('love', 'verb'): ('amar', ''), ('say', 'verb'): ('dizer', ''), ('work', 'verb'): ('trabalhar', ''),
           ('labor', 'verb'): ('trabalhar', ''), ('toil', 'verb'): ('trabalhar', ''),
           ('walk', 'verb'): ('andar', ''), ('live', 'verb'): ('morar', ''), ('dwell', 'verb'): ('morar', ''),
           ('inhabit', 'verb'): ('morar', ''), ('sleep', 'verb'): ('dormir', ''), ('come', 'verb'): ('vir', ''),
           ('go', 'verb'): ('ir', ''), ('hear', 'verb'): ('ouvir', ''), ('write', 'verb'): ('escrever', ''),
           ('call', 'verb'): ('chamar', ''), ('flee', 'verb'): ('fugir', ''), ('wait', 'verb'): ('esperar', ''),
           ('be able', 'verb'): ('poder', ''), ('want', 'verb'): ('querer', ''),
           ('beautiful', 'adj'): ('bonito', ''), ('pretty', 'adj'): ('bonito', ''), ('great', 'adj'): ('grande', ''),
           ('big', 'adj'): ('grande', ''), ('large', 'adj'): ('grande', ''), ('long', 'adj'): ('longo', ''),
           ('wide', 'adj'): ('largo', ''), ('broad', 'adj'): ('largo', ''), ('happy', 'adj'): ('feliz', ''),
           ('glad', 'adj'): ('feliz', ''), ('good', 'adj'): ('bom', ''), ('bad', 'adj'): ('mau', ''),
           ('new', 'adj'): ('novo', ''), ('old', 'adj'): ('velho', ''), ('golden', 'adj'): ('dourado', ''),
           ('Made of gold', 'adj'): ('de ouro', ''), ('strong', 'adj'): ('forte', ''),
           ('brave', 'adj'): ('corajoso', ''), ('courageous', 'adj'): ('corajoso', ''),
           ('sharp', 'adj'): ('afiado', ''), ('small', 'adj'): ('pequeno', ''), ('wise', 'adj'): ('sábio', ''),
           ('dear', 'adj'): ('querido', ''), ('open', 'adj'): ('aberto', '')},
    'zh': {('girl', 'noun'): ('女孩', ''), ('boy', 'noun'): ('男孩', ''), ('child', 'noun'): ('孩子', ''),
           ('farmer', 'noun'): ('农夫', ''), ('sailor', 'noun'): ('水手', ''), ('people', 'noun'): ('人民', ''),
           ('crowd', 'noun'): ('人群', ''), ('master', 'noun'): ('主人', ''), ('lord', 'noun'): ('主人', ''),
           ('slave', 'noun'): ('奴隶', ''), ('field', 'noun'): ('田野', ''), ('country house', 'noun'): ('别墅', ''),
           ('villa', 'noun'): ('别墅', ''), ('encampment', 'noun'): ('营地', ''), ('camp', 'noun'): ('营地', ''),
           ('king', 'noun'): ('国王', ''), ('queen', 'noun'): ('王后', ''), ('soldier', 'noun'): ('士兵', ''),
           ('enemy', 'noun'): ('敌人', ''), ('enemy of the state', 'noun'): ('敌人', ''), ('wood', 'noun'): ('森林', ''),
           ('forest', 'noun'): ('森林', ''), ('garden', 'noun'): ('花园', ''), ('road', 'noun'): ('路', ''),
           ('way', 'noun'): ('路', ''), ('letter', 'noun'): ('信', ''), ('temple', 'noun'): ('寺庙', ''),
           ('man', 'noun'): ('男人', ''), ('woman', 'noun'): ('女人', ''), ('town', 'noun'): ('城镇', ''),
           ('city', 'noun'): ('城市', ''), ('thing', 'noun'): ('东西', ''), ('teacher', 'noun'): ('老师', ''),
           ('book', 'noun'): ('书', ''), ('rose', 'noun'): ('玫瑰', ''), ('flower', 'noun'): ('花', ''),
           ('water', 'noun'): ('水', ''), ('sea', 'noun'): ('海', ''), ('mother', 'noun'): ('母亲', ''),
           ('father', 'noun'): ('父亲', ''), ('daughter', 'noun'): ('女儿', ''), ('son', 'noun'): ('儿子', ''),
           ('friend', 'noun'): ('朋友', ''), ('sky', 'noun'): ('天空', ''), ('heaven', 'noun'): ('天空', ''),
           ('house', 'noun'): ('房子', ''), ('word', 'noun'): ('话', ''), ('messenger', 'noun'): ('使者', ''),
           ('wolf', 'noun'): ('狼', ''), ('sword', 'noun'): ('剑', ''), ('tear', 'noun'): ('眼泪', ''),
           ('island', 'noun'): ('岛', ''), ('matter', 'noun'): ('事情', ''), ('affair', 'noun'): ('事情', ''),
           ('give', 'verb'): ('给', ''), ('die', 'verb'): ('死', ''), ('fight', 'verb'): ('战斗', ''),
           ('take', 'verb'): ('拿', ''), ('capture', 'verb'): ('抓住', ''), ('play', 'verb'): ('玩', ''),
           ('carry', 'verb'): ('搬', ''), ('praise', 'verb'): ('称赞', ''), ('pluck', 'verb'): ('摘', ''),
           ('think', 'verb'): ('认为', ''), ('judge', 'verb'): ('认为', ''), ('reckon', 'verb'): ('认为', ''), ('object', 'noun'): ('东西', ''), ('suppose', 'verb'): ('认为', ''), ('order', 'verb'): ('命令', ''),
           ('command', 'verb'): ('命令', ''), ('bid', 'verb'): ('命令', ''), ('wound', 'verb'): ('打伤', ''),
           ('move', 'verb'): ('移动', ''), ('leave', 'verb'): ('离开', ''), ('depart', 'verb'): ('离开', ''),
           ('weep', 'verb'): ('哭', ''), ('cry', 'verb'): ('哭', ''), ('sing', 'verb'): ('唱歌', ''),
           ('read', 'verb'): ('读', ''), ('know', 'verb'): ('知道', ''), ('fear', 'verb'): ('害怕', ''),
           ('laugh', 'verb'): ('笑', ''), ('wait for', 'verb'): ('等', ''), ('see', 'verb'): ('看见', ''),
           ('love', 'verb'): ('爱', ''), ('say', 'verb'): ('说', ''), ('work', 'verb'): ('工作', ''),
           ('labor', 'verb'): ('工作', ''), ('toil', 'verb'): ('工作', ''), ('walk', 'verb'): ('走', ''),
           ('live', 'verb'): ('住', ''), ('dwell', 'verb'): ('住', ''), ('inhabit', 'verb'): ('住', ''),
           ('sleep', 'verb'): ('睡觉', ''), ('come', 'verb'): ('来', ''), ('go', 'verb'): ('去', ''),
           ('hear', 'verb'): ('听', ''), ('write', 'verb'): ('写', ''), ('call', 'verb'): ('叫', ''),
           ('flee', 'verb'): ('逃跑', ''), ('wait', 'verb'): ('等', ''), ('want', 'verb'): ('想要', ''),
           ('beautiful', 'adj'): ('美丽', ''), ('pretty', 'adj'): ('漂亮', ''), ('great', 'adj'): ('大', ''),
           ('big', 'adj'): ('大', ''), ('large', 'adj'): ('大', ''), ('long', 'adj'): ('长', ''),
           ('wide', 'adj'): ('宽', ''), ('broad', 'adj'): ('宽', ''), ('happy', 'adj'): ('高兴', ''),
           ('glad', 'adj'): ('高兴', ''), ('good', 'adj'): ('好', ''), ('bad', 'adj'): ('坏', ''),
           ('new', 'adj'): ('新', ''), ('old', 'adj'): ('老', ''), ('golden', 'adj'): ('金色', ''),
           ('Made of gold', 'adj'): ('金', ''), ('strong', 'adj'): ('强壮', ''), ('brave', 'adj'): ('勇敢', ''),
           ('courageous', 'adj'): ('勇敢', ''), ('sharp', 'adj'): ('锋利', ''), ('small', 'adj'): ('小', ''),
           ('wise', 'adj'): ('聪明', ''), ('dear', 'adj'): ('亲爱', ''), ('open', 'adj'): ('开阔', '')},
}


# 英語の miss は「恋しく思う」(フランス語の manquer à を入れ替えた枠: Tu me manques → I miss you)。的を外す意味にしない
for _lang, _lemma in (('de', 'vermissen'), ('fi', 'kaivata'), ('tr', 'özlemek'), ('ko', '그리워하다')):
    PREFERRED.setdefault(_lang, {})[('miss', 'verb')] = (_lemma, '')
# フランス語の content「うれしい」は英語 glad (content より自然: I am glad that you come)
FIRST_GLOSSES.setdefault('fr', {})['content'] = 'glad'
# 英語の like は人を主語にした「好む」(plaire à を入れ替えた枠。gefallen・piacere のような物が主語の動詞にしない)
for _lang, _lemma in (('de', 'mögen'), ('fi', 'pitää'), ('tr', 'sevmek'), ('ko', '좋아하다')):
    PREFERRED.setdefault(_lang, {})[('like', 'verb')] = (_lemma, '')
# 英語の watch は「見る」(映画・試合を。hüten・vartioida のような「見張る」にしない)
for _lang, _lemma in (('de', 'ansehen'), ('fi', 'katsoa')):
    PREFERRED.setdefault(_lang, {})[('watch', 'verb')] = (_lemma, '')
# 英語の lord・master (dominus) はドイツ語の Herr (英語からの借用の Lord にしない)
for _en in ('lord', 'master'):
    PREFERRED.setdefault('de', {})[(_en, 'noun')] = ('Herr', 'm')
# 英語の teach・praise はドイツ語の lehren・loben (語義の多い beibringen・anpreisen にしない)
PREFERRED['de'].update({('teach', 'verb'): ('lehren', ''), ('praise', 'verb'): ('loben', '')})
# 文の枠で文脈から決めた意味 (frame.OBJECT_SENSES) → 言語ごとの語 (英語の drive だけでは運転の fahren と区別できない)
SENSE_TARGETS = {}
for _lang, _lemma in (('de', 'treiben'), ('ru', 'гнать'), ('ko', '몰다'), ('zh', '驱赶'), ('ang', 'drīfan'),
                      ('grc', 'ἐλαύνω'), ('fi', 'ajaa'), ('tr', 'sürmek')):
    SENSE_TARGETS.setdefault(_lang, {})['drive (animals)'] = _lemma
# 英語の drive は車を運転する意味 (辞書の筆頭の verschlagen・달리다 にしない。家畜を追う意味は上の SENSE_TARGETS)
for _lang, _lemma in (('de', 'fahren'), ('ru', 'водить'), ('ko', '운전하다'), ('zh', '驾驶')):
    PREFERRED.setdefault(_lang, {})[('drive', 'verb')] = (_lemma, '')
# 英語の player はドイツ語の Spieler (語義の多い Werderaner「Werder Bremen の選手」にしない)
PREFERRED['de'][('player', 'noun')] = ('Spieler', 'm')
PARTICLES = ('to', 'as', 'at', 'on', 'for', 'with', 'into', 'upon', 'in', 'from', 'of', 'out', 'up', 'away',
             'off', 'down', 'by')


def _variants(sources):
    """英語の訳語と、その簡単な形 (順位は少し下げる): drive or move to → drive, move;
    address as → address; look at → look; put together → put"""
    out = []
    for i, en in enumerate(sources):
        out.append((i, en))
        m = re.match(r'^(?:any |a )?(?:head|heads|type|kind|sort|piece|species) of (.+)$', en)
        if m:
            out.append((i + 0.3, m.group(1)))   # head of cattle → cattle, any type of fruit → fruit
        elif ' of ' in en and not en.startswith('of '):
            out.append((i + 0.6, en.split(' of ')[0]))   # priestess of Pythian Apollo → priestess
        if en.startswith('of '):
            out.append((i + 0.6, en[3:].split(' ')[0]))   # of such size → such
        words = en.split()
        if 1 < len(words) <= 3 and ' of ' not in en and ' or ' not in en:
            out.append((i + 0.8, words[-1]))   # sacrificial victim → victim, light boat → boat (名詞の頭)
        for part in en.split(' or '):
            words = part.split()
            while len(words) > 1 and words[-1] in PARTICLES:
                words = words[:-1]
            simple = ' '.join(words)
            if simple and simple != en:
                out.append((i + 0.5, simple))
            if len(words) > 1 and part != en:
                out.append((i + 0.7, words[0]))
    return out


def candidates(lex, lang, pos=None):
    """Lex → [(点, Target)] (点の小さいほうが良い)。元の言語と作る言語が同じなら置き換えない"""
    pos = pos or {'participle': 'verb'}.get(lex.pos, lex.pos)
    if (lex.lang or 'la') == lang:
        return [(-1000, Target(source_key(lang, lex.lemma), pos, (), '', '', 1))]
    if lex.sense in SENSE_TARGETS.get(lang, {}):   # 文脈で決まった意味の語 (家畜を drive → treiben)
        return [(-100, Target(SENSE_TARGETS[lang][lex.sense], pos, (lex.sense,), '', ''))]
    sources = english.candidates(lex) or ([e for e in lex.en.split(',') if e] if lex.en else [])
    for en in sources[:1] + [e.replace(' for', '') for e in sources[:1] if e.endswith(' for')]:   # wait for → wait
        words = en.lower().split(' ')
        preferred = PREFERRED.get(lang, {}).get((en.lower(), pos)) or \
            PREFERRED.get(lang, {}).get((words[-1], pos)) or \
            (PREFERRED.get(lang, {}).get((words[0], pos)) if pos == 'verb' else None)   # die of … → die
        if preferred:
            lemma, extra = preferred
            gender, gana = (extra, '') if pos != 'verb' else ('', extra)
            return [(-100, Target(lemma, pos, (en,), gender, gana))]
    wanted = [j.strip() for j in (lex.ja or '').split(',') if j.strip()]
    if pos == 'noun' and english.female_counterpart(lex):
        wanted = []   # 女性の人の名詞 (magistra) は英語の teacher から。日本語の訳語 (主婦) で選ばない
    if (lex.lang or 'la') == 'la':   # 日本語の訳語が手作りの辞書のもの (ほかの言語の語の日本語は英語から作ったもの)
        sources = _with_japanese(sources[:6], wanted)
    scored, matched = {}, {}
    for i, en in _variants(sources[:8]):
        for j, target in _index(lang).get(en.lower(), []):
            if target.pos != pos or j > 5:
                continue
            # 出現数は、元の語の筆頭の英語が語の筆頭の語義のときだけ (よく出る хороший を great で、πόλις を villa の
            # 4番目の city で取らない)
            score = 3 * i + j - math.log(1 + target.senses) - (_frequency(lang, target) if i == 0 and j == 0 else 0)
            if lang == 'la' and _in_hand_dictionary(target.lemma) or target.lemma in hand_glosses(lang):
                score -= 3   # 手作りの辞書にある (よく使う) 語 (hortus を gardīnum より、소녀 を 계집 より)
            ja = japanese(lang, target)
            if wanted and wanted[0] in ja:
                score -= 3     # 日本語の一番の訳語が合う
            elif any(w in ja for w in wanted):
                score -= 2
            if i < 3:   # 上位の英語の訳語だけ数える (pater の5番目 priest で батюшка・pari を良くしない)
                matched.setdefault((target.lemma, target.pos), set()).add(int(i))
            if target not in scored or score < scored[target]:
                scored[target] = score
    # 元の語の英語の訳語の複数に合う語を良くする (arca: chest, box → 「胸」の uras より、chest と box の両方にある「箱」)
    best_by_lemma = {}
    for target, score in scored.items():
        score -= MULTIPLE_MATCH_WEIGHT * max(0, len(matched.get((target.lemma, target.pos), ())) - 1)
        key = (target.lemma, target.pos)
        if key not in best_by_lemma or score < best_by_lemma[key][0]:
            best_by_lemma[key] = (score, target)
    return sorted(best_by_lemma.values(), key=lambda st: st[0])


# コーパスでの出現数 (tools/build_lemma_counts.py が UD から作る) の重み: よく使う語を先に (εἰρήνη を ἡσυχία より)
# 見出し語の形がコーパスと索引で揃うところだけ (サンスクリットの UD の動詞は語根の形が違うので名詞・形容詞だけ。
# タガログ語・ポルトガル語 (UD の test だけ)・中国語はコーパスが小さいので軽く)
FREQUENCY_WEIGHT = {'grc': 1.0, 'ru': 1.0, 'id': 1.0, 'sa': 1.0, 'tl': 0.5, 'pt': 0.5, 'zh': 0.5}
# 元の語の上位の英語の訳語の複数に合う語の重み (arca: chest, box →「箱」)。大きいと語義の多い語 (ἡσυχία: peace, rest) が勝つ
MULTIPLE_MATCH_WEIGHT = 1.0


@functools.lru_cache(maxsize=None)
def _counts(lang):
    table = {}
    try:
        with open(paths.data(lang, 'lemma-counts.tsv'), encoding='utf-8') as f:
            for line in f:
                lemma, _, n = line.rstrip('\n').partition('\t')
                table[lemma] = int(n)
    except OSError:
        pass
    return table


@functools.lru_cache(maxsize=None)
def _pos_counts(lang):
    """(見出し語, 品詞) → 出現数 (tools/build_lemma_counts.py の lemma-pos-counts.tsv)。無ければ空"""
    table = {}
    try:
        with open(paths.data(lang, 'lemma-pos-counts.tsv'), encoding='utf-8') as f:
            for line in f:
                lemma, pos, n = line.rstrip('\n').split('\t')
                table[lemma, pos] = int(n)
    except (OSError, ValueError):
        pass
    return table


def _count(lang, lemma, pos=None):
    """出現数。品詞ごとの表があればその品詞の数 (serang「広い」に menyerang「攻撃する」の数を足さない)"""
    by_pos = _pos_counts(lang)
    if pos in ('noun', 'verb', 'adj', 'adv') and by_pos:
        return by_pos.get((lemma, pos), 0)
    return _counts(lang).get(lemma, 0)


def _frequency(lang, target):
    """コーパスでの出現数の点 (多いほど良い: 小さくする分)"""
    if lang == 'sa' and target.pos == 'verb':
        return 0
    return FREQUENCY_WEIGHT.get(lang, 0) * math.log(1 + _count(lang, target.lemma, target.pos))


def _with_japanese(sources, wanted):
    """英語の訳語の並びを、元の語の一番の日本語の訳語 (手作りの辞書: tollō「取り去る」・homō「人間」) に合わせる:
    和英 (JMdict) にもある英語を先に (remove・human・person)、残りはそのまま、和英だけにある英語 (human being) を最後に"""
    if not wanted or (wanted[0].isascii()):
        return list(sources)
    back = en_ja.english_for(wanted[0])
    if not back:
        return list(sources)
    # 和英にもある英語は、まず英語の訳語の並びの頭 (english.candidates が日本語に合わせて選んだもの) を、残りは和英の順に
    if sources and en_ja.english_key(sources[0]) in back:
        confirmed = []   # 筆頭の訳語が日本語にも合う (habitō: reside は「住む」の訳語) なら並べ替えない
    else:   # 和英にもある訳語を、元の並びと和英の順位の和の順に先へ (lātus: broad, wide, spacious → wide, spacious)
        confirmed = en_ja.agreed_order(sources, wanted[0])
    from_japanese = [en for en in _ja_english(wanted[0]) if en_ja.english_key(en) not in
                     {en_ja.english_key(s) for s in sources}][:3]
    rest = [en for en in sources if en not in confirmed]
    return confirmed + rest + from_japanese


def _ja_english(japanese):
    """日本語の訳語 → 和英 (JMdict) の英語の訳語 (語義の順)"""
    return [e for e in en_ja._ja_en().get(japanese, '').split(',') if e]


def by_english(words, lang, pos):
    """英語の語の列 (前ほど良い) → 作る言語の見出し語の候補 (分詞の英語の訳語から動詞を引く)"""
    scored = {}
    for i, en in _variants(list(words)[:8]):
        for j, target in _index(lang).get(en.lower(), []):
            if target.pos == pos and j <= 5:
                score = 3 * i + j - math.log(1 + target.senses)
                key = (target.lemma, target.gana)
                if key not in scored or score < scored[key][0]:
                    scored[key] = (score, target)
    return sorted(scored.values(), key=lambda st: st[0])


def best(lex, lang, pos=None):
    found = candidates(lex, lang, pos)
    return found[0][1] if found else None
