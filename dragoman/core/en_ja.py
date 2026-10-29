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
            return ranked(row[0].split(','))
    return []


@functools.lru_cache(maxsize=100000)
def commonness(japanese):
    """日本語の訳語のよく使う度合い (JMdict の news1・ichi1 … と頻度の順位 nf から。0 は JMdict にあって印の無い語、
    None は JMdict に無い語)"""
    db = _connect()
    if db is None:
        return 0
    try:
        row = db.execute('SELECT score FROM common WHERE ja = ?', (japanese,)).fetchone()
    except sqlite3.OperationalError:   # 古い表
        return None
    return row[0] if row else None


def _rare(japanese):
    """JMdict にあって、よく使う語の印の無い訳語 (JMdict に無い句の訳語 (不思議に思う) は数えない)"""
    return commonness(japanese) == 0


def ranked(japanese):
    """訳語の候補の順: 辞書の順のまま、よく使う語の印 (JMdict) のある訳語を印の無い訳語より前に
    (wait: 延期する,待つ → 待つ,延期する)。印の度合いの細かい差では並べ替えない (本・書物 はどちらも印がある)"""
    if len(japanese) < 2:
        return japanese
    rare = [_rare(j) for j in japanese]
    if all(rare) or not any(rare):
        return japanese
    return [j for j, r in zip(japanese, rare) if not r] + [j for j, r in zip(japanese, rare) if r]


@functools.lru_cache(maxsize=100000)
def translate(glosses, pos, limit=1):
    """英語の語義 (カンマ区切り) → 日本語の訳語 (カンマ区切り)。1つも訳せなければ None"""
    if not ENABLED or not glosses or pos not in POS_GROUPS:
        return None
    out, sources = [], []
    for english in glosses.split(','):
        found = lookup(english.strip(), pos)
        if found and found[0] not in out:
            out.append(found[0])  # 語義ごとに一番の訳語 (go → 行く、travel → 旅行する)
            sources.append(english.strip())
        if len(out) >= limit:
            break
    if len(out) > 1:   # 対訳文 (Tatoeba) の英文にまれな語義の訳語は落とす (puissance: power, sovereignty → 力)
        counts = [_english_count(e) for e in sources]
        if counts[0] >= 20:
            out = [out[0]] + [j for j, n in zip(out[1:], counts[1:]) if n * 10 >= counts[0]]
    return ','.join(out) if out else None


def _english_count(english):
    """英語の語義の頭の語が対訳文 (Tatoeba) の英文に出る文の数 (表が無ければ大きい数: 落とさない)"""
    if _corpus_db() is None:
        return 10 ** 6
    words = re.sub(r'\([^)]*\)', '', english.lower()).replace('to ', '', 1).split()
    words = [w for w in words if w not in ('a', 'an', 'the', 'to', 'be', 'of', 'one', "one's", 'something', 'someone')]
    return len(_pair_ids(words[0])) if words else 0


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


@functools.lru_cache(maxsize=2000)
def english_by_japanese(japanese, pos):
    """英和の表を逆に: 日本語の訳語 → それを訳語に持つ英語 (訳語の中で前にあるものを先に: 運転する → drive, jockey)。
    和英 (JMdict) でサ変名詞の英語が名詞の形 (運転: operation, driving) のときに、動詞の英語を引く"""
    db = _connect()
    if db is None or not japanese:
        return ()
    found = []
    for p in POS_GROUPS.get(pos, (pos,)):
        for en, ja in db.execute('SELECT en, ja FROM en_ja WHERE pos = ? AND ja LIKE ?', (p, '%' + japanese + '%')):
            glosses = ja.split(',')
            if japanese in glosses:
                found.append((glosses.index(japanese), en))
    return tuple(dict.fromkeys(en for _, en in sorted(found)))


@functools.lru_cache(maxsize=20000)
def english_for(japanese):
    """日本語の訳語 → 英語の訳語の比べる形の列 (語義の順: 少年 → boy, juvenile, child)。JMdict の表から"""
    return tuple(dict.fromkeys(english_key(e) for e in _ja_en().get(japanese.strip(), '').split(',') if e))


JAPANESE_LEADING = re.compile(r'^[-－～〜]?(?:を|が|に|の|と|で|から|へ)?')
JAPANESE_NOTE = re.compile(r'[(（\[［\^].*$')


def _bare_japanese(text):
    """照合用の日本語の訳語: 前の助詞 (～を与える → 与える)・括弧の注記 (六(6) → 六、肩^([要出典]) → 肩) を除く"""
    return JAPANESE_NOTE.sub('', JAPANESE_LEADING.sub('', text.strip())).strip()


def agrees(japanese, english, pos='noun'):
    """日本語の訳語 (カンマ・読点区切り) が英語の語義 (カンマ区切り) と合うか: 英和で英語の語義の訳語に日本語があるか、
    和英 (JMdict) で日本語の訳語の英語に英語の語義があるか。別の語の訳語の取り違え (母音記号を除いた綴りが同じ
    現代ヘブライ語の גֵּן「遺伝子」を、聖書の גַּן「庭」に付ける) を見分けるのに使う"""
    japanese_items = [_bare_japanese(j) for j in re.split('[,、]', japanese or '')]
    japanese_items = [j for j in japanese_items if j]
    english_items = [english_key(e) for e in (english or '').split(',') if e.strip()]
    if not japanese_items:
        return False
    if not english_items:
        return True   # 英語の語義が無ければ確かめようがない (日本語の訳語を使う)
    translated = set()
    for e in english_items[:8]:
        translated.update(lookup(e, pos))
        if e.startswith(('a ', 'an ', 'the ', 'to ')):
            translated.update(lookup(e.split(' ', 1)[1], pos))
    translated = {_bare_japanese(t) for t in translated}
    if any(j in translated for j in japanese_items):
        return True
    back = {b for j in japanese_items for b in english_for(j)}
    return any(e in back or e.split(' ')[-1] in back for e in english_items)



@functools.lru_cache(maxsize=20000)
def phrasal(phrase):
    """句動詞 → 日本語の訳語のリスト (give up → 諦める,見限る …。JMdict の英訳から: tools/build_en_ja.py)"""
    db = _connect()
    if db is None or not ENABLED:
        return []
    try:
        row = db.execute('SELECT ja FROM phrasal WHERE phrase = ?', (key(phrase),)).fetchone()
    except sqlite3.OperationalError:   # 古い表 (句動詞の表が無い)
        return []
    return row[0].split(',') if row else []


@functools.lru_cache(maxsize=20000)
def _verb_contexts(verb):
    db = _connect()
    if db is None:
        return ()
    try:
        return tuple(db.execute('SELECT context, ja FROM verb_context WHERE verb = ?', (key(verb),)).fetchall())
    except sqlite3.OperationalError:
        return ()


def _singular(word):
    if len(word) > 4 and word.endswith('ies'):
        return word[:-3] + 'y'
    if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def verb_in_context(verb, words):
    """動詞と、その目的語・主語の語 (英語) → その場面の訳語のリスト (pass + exam → 受かる、take + medicine → 飲む)。
    場面の語は JMdict の英訳の括弧の書き込み (to pass (examination))。短い形も前方一致で (exam → examination)"""
    if not ENABLED:
        return []
    contexts = _verb_contexts(verb)
    if not contexts:
        return []
    for word in words:
        w = _singular(key(word))
        for context, ja in contexts:
            if context == w:
                return ja.split(',')
        if len(w) >= 4:
            for context, ja in contexts:
                if len(context) >= 4 and (context.startswith(w) or w.startswith(context)):
                    return ja.split(',')
    return []


CORPUS_PATH = paths.data('en', 'tatoeba.sqlite')
_corpus = None


def _corpus_db():
    global _corpus
    if _corpus is None and os.path.exists(CORPUS_PATH):
        _corpus = sqlite3.connect(CORPUS_PATH, check_same_thread=False)
    return _corpus


def _stem(japanese):
    """訳語が和訳の文にあるかを見る形 (活用語尾を除く: 待つ → 待、勉強する → 勉強、美しい → 美し、静かな → 静か)"""
    j = _bare_japanese(japanese)
    if j.endswith('する') and len(j) > 2:
        j = j[:-2]
    elif j.endswith(VERB_ENDINGS + ('い', 'な')) and len(j) > 1 and re.search('[一-龥]', j[:-1]):
        j = j[:-1]
    return j if len(j) > 1 or re.match('[一-龥]', j) else ''


@functools.lru_cache(maxsize=20000)
def _pair_ids(lemma):
    db = _corpus_db()
    if db is None:
        return frozenset()
    return frozenset(i for i, in db.execute('SELECT id FROM lemmas WHERE lemma = ?', (lemma.lower(),)))


@functools.lru_cache(maxsize=20000)
def _japanese(pair_id):
    return _corpus_db().execute('SELECT ja FROM pairs WHERE id = ?', (pair_id,)).fetchone()[0]


def corpus_ranked(english, candidates, context=(), prune=False):
    """英語の語の訳語の候補を、対訳文 (Tatoeba) の数で並べ替える: その語を含む英文の和訳に訳語が現れる数と、
    周りの語 (context の原形) も含む英文に絞った数 (3倍に数える)。辞書の順の最初の訳語より、2倍以上・3文以上
    多く現れる訳語だけを先頭に (medicine: 医学,薬 → 薬、take + medicine の文脈)。prune なら、先頭の訳語の1割に満たない
    訳語を落とす (hand: 手,針 → 手)。対訳文の表が無ければそのまま"""
    candidates = list(candidates)
    if len(candidates) < 2 or not ENABLED:
        return candidates
    ids = _pair_ids(english)
    if not ids:
        return candidates
    near = set()
    for c in context:
        if c and c.lower() != english.lower():
            near |= ids & _pair_ids(c)

    def score(ja):
        stem = _stem(ja)
        if not stem:
            return 0
        return sum(1 for i in ids if stem in _japanese(i)) + 3 * sum(1 for i in near if stem in _japanese(i))

    scores = [score(j) for j in candidates]
    best = max(range(len(candidates)), key=lambda k: scores[k])
    if best != 0 and scores[best] >= max(3, 2 * scores[0]):
        order = [best] + [k for k in range(len(candidates)) if k != best]
    else:
        order = list(range(len(candidates)))
    if prune and scores[order[0]] >= 5:
        # prune なら、先頭の訳語の1割に満たない訳語を落とす (hand: 手,針 → 手)
        order = [order[0]] + [k for k in order[1:] if scores[k] * 10 >= scores[order[0]]]
    return [candidates[k] for k in order]
