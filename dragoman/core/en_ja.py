#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語の訳語を日本語に置き換える (tools/build_en_ja.py で日本語版 Wiktionary の英語の項目から作った表を使う)
#
#   translate('go,travel,go away', 'verb') → '行く,旅行する'     (訳せた語義だけを並べる。訳せなければ None)
#   translate('industrious,diligent', 'adj') → '勤勉な,よく働く'
#
# 各言語の辞書で日本語の訳語が無い語 (Wiktionary の英語の語義、CAMeL Tools の語義など) に、項目を作るところ
# (core/Item.py) で使う。表が無ければ何もしない。ENABLED = False で止める (--english-glosses)
#
import functools
import os
import re
import sqlite3

from dragoman.core import paths

DB_PATH = paths.data('en-ja.sqlite')
ENABLED = True
VERB_ENDINGS = tuple('うくぐすつぬぶむる')
NOTE = re.compile(r'[〔（(\[［【][^〕）)\]］】]*[〕）)\]］】]|\^\([^)]*\)|[\^*]')
POS_GROUPS = {'noun': ('noun', 'name', 'phrase'), 'verb': ('verb',), 'adj': ('adj', 'noun'), 'adv': ('adv', 'adj'),
              'participle': ('adj', 'verb'), 'pronoun': ('noun',), 'name': ('name', 'noun')}

# 表の順位では決めにくい基本語の訳語 (英語, 品詞) → 日本語
OVERRIDES = {('minister', 'noun'): '大臣', ('government', 'noun'): '政府', ('quiet', 'adj'): '静かな',
             ('state', 'noun'): '国家,状態', ('party', 'noun'): '党,パーティー', ('power', 'noun'): '力,権力',
             ('right', 'noun'): '権利,右', ('case', 'noun'): '場合,事件', ('order', 'noun'): '命令,順序',
             ('company', 'noun'): '会社,仲間', ('people', 'noun'): '人々,民族', ('man', 'noun'): '男,人',
             ('look', 'verb'): '見る', ('look at', 'verb'): '見る'}

_db = None


def key(english):
    return english.strip().lower()


def clean(glosses, pos):
    """日本語版 Wiktionary の語義の並び (カンマ区切り) → 訳語のリスト。注記・「～を」を除き、長い説明は捨てる。
    動詞は辞書形 (う段で終わる) のものだけ (日本語の活用に通すため)"""
    out = []
    for g in (glosses or '').split(','):
        g = NOTE.sub('', g).strip()
        g = re.sub('^[～〜~](を|に|が|と|で|から)?', '', g).strip()
        if not g or len(g) > 10 or re.search('[a-zA-Z0-9=;:・。]', g):
            continue
        if pos == 'verb' and not g.endswith(VERB_ENDINGS):
            continue
        if g not in out:
            out.append(g)
    return out


def _connect():
    global _db
    if _db is None and os.path.exists(DB_PATH):
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db


def available():
    return _connect() is not None


@functools.lru_cache(maxsize=100000)
def lookup(english, pos):
    """英語の語句と品詞 → 日本語の訳語のリスト"""
    db = _connect()
    if db is None:
        return []
    phrase = re.sub(r'\s*\([^)]*\)', '', key(english)).strip()  # take (with) → take
    phrase = re.sub(r'^(to|a|an|the) ', '', phrase) if pos != 'noun' or phrase.startswith(('a ', 'an ', 'the ')) \
        else phrase
    if (phrase, pos) in OVERRIDES:
        return OVERRIDES[(phrase, pos)].split(',')
    for p in POS_GROUPS.get(pos, (pos,)):
        row = db.execute('SELECT ja FROM en_ja WHERE en = ? AND pos = ?', (phrase, p)).fetchone()
        if row:
            return row[0].split(',')
    return []


@functools.lru_cache(maxsize=100000)
def translate(glosses, pos, limit=1):
    """英語の語義 (カンマ区切り) → 日本語の訳語 (カンマ区切り)。1つも訳せなければ None"""
    if not ENABLED or not glosses or pos not in POS_GROUPS:
        return None
    out = []
    for english in glosses.split(','):
        found = lookup(english.strip(), pos)
        if found and found[0] not in out:
            out.append(found[0])  # 語義ごとに一番の訳語 (go → 行く、travel → 旅行する)
        if len(out) >= limit:
            break
    return ','.join(out) if out else None


PARTICLE_TAIL = re.compile(r' (?:with|for|on|to|at|of|about|from)$')
JA_EN_PATH = paths.data('ja-en.tsv')


@functools.lru_cache(maxsize=1)
def _ja_en():
    """日本語 → 英語の表 (tools/build_ja_en.py が JMdict から作る)。無ければ空"""
    table = {}
    try:
        with open(JA_EN_PATH, encoding='utf-8') as f:
            for line in f:
                word, _, english = line.rstrip('\n').partition('\t')
                table[word] = english
    except OSError:
        pass
    return table


def agreed_order(sources, japanese):
    """英語の訳語の列のうち和英 (JMdict) にもあるものを、両方の順位の和の小さい順に
    (捕える: Wiktionary の captivate (8番目) より、和英の2番目で Wiktionary にもある capture)"""
    backs = english_for(japanese)
    ranked = [(k + backs.index(english_key(en)), k, en) for k, en in enumerate(sources) if english_key(en) in backs]
    return [en for _, _, en in sorted(ranked)]


def english_key(english):
    """英語の訳語の比べる形 (小文字、末尾の前置詞を除く: commiserate with → commiserate)"""
    return PARTICLE_TAIL.sub('', key(english))


@functools.lru_cache(maxsize=20000)
def english_for(japanese):
    """日本語の訳語 → 英語の訳語の比べる形の列 (語義の順: 少年 → boy, juvenile, child)。JMdict の表から"""
    return tuple(dict.fromkeys(english_key(e) for e in _ja_en().get(japanese.strip(), '').split(',') if e))

