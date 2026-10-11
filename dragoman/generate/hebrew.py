#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) から聖書ヘブライ語の文を作る
#
#   語形は聖書 (Open Scriptures Hebrew Bible) に現れた形を辞書 (he/hebrew.sqlite) から引く:
#     動詞は語根・態 (qal・piel …)・型 (完了・未完了・分詞)・人称性数、名詞・形容詞は性・数・冠詞の有無。
#     無い動詞の形は強い語根の型から作る (hebrew/binyan.generate)
#   語は辞書の見出しの日本語・英語の訳語と、元の語の訳語を照らす。基本語は表から
#   語順: 完了・未完了は動詞が先 (動詞 - 主語 - 目的語)、現在は分詞で主語が先 (הַנַּעֲרָה רֹאָה)
#   定まった目的語には目的語の印 אֶת־、冠詞 הַ (次の字を重ねる。前置詞 בְּ・לְ と並べば縮める: בַּגַּן)
#   形容詞は名詞の後ろで性・数・定を一致 (הַנַּעֲרָה הַיָּפָה)。関係節は אֲשֶׁר + 節。否定 לֹא
#   名詞文は繋辞なし (הַנַּעֲרָה יָפָה)、過去は הָיָה
#
import functools
import json
import os
import re
import sqlite3
import unicodedata

from dragoman.core import paths
from . import english
from .frame import Lex, NP

DB_PATH = paths.data('he', 'hebrew.sqlite')
DAGESH = 'ּ'
GUTTURALS = set('אהחער')
STEM_CODES = {'qal': 'q', 'niphal': 'N', 'piel': 'p', 'pual': 'P', 'hiphil': 'h', 'hophal': 'H', 'hithpael': 't'}
PASSIVE_STEMS = {'q': 'N', 'p': 'P', 'h': 'H'}
# 教科書の基本語: 英語 → (辞書の見出しの番号 (Strong の番号), 動詞なら態)
PREFERRED = {('girl', 'noun'): '5291', ('boy', 'noun'): '5288', ('child', 'noun'): '3206', ('man', 'noun'): '376',
             ('woman', 'noun'): '802', ('king', 'noun'): '4428', ('queen', 'noun'): '4436', ('book', 'noun'): '5612a',
             ('garden', 'noun'): '1588', ('rose', 'noun'): '2261', ('city', 'noun'): '5892a', ('house', 'noun'): '1004b',
             ('sea', 'noun'): '3220', ('ship', 'noun'): '591', ('people', 'noun'): '5971a', ('citizen', 'noun'): '5971a',
             ('teacher', 'noun'): '4176', ('sailor', 'noun'): '4419', ('god', 'noun'): '430', ('son', 'noun'): '1121a',
             ('daughter', 'noun'): '1323', ('father', 'noun'): '1', ('mother', 'noun'): '517', ('servant', 'noun'): '5650',
             ('slave', 'noun'): '5650', ('master', 'noun'): '113', ('lord', 'noun'): '113', ('word', 'noun'): '1697',
             ('road', 'noun'): '1870', ('way', 'noun'): '1870', ('land', 'noun'): '776', ('water', 'noun'): '4325',
             ('beautiful', 'adj'): '3303', ('good', 'adj'): '2896a', ('bad', 'adj'): '7451a', ('evil', 'adj'): '7451a',
             ('great', 'adj'): '1419a', ('big', 'adj'): '1419a', ('large', 'adj'): '1419a', ('small', 'adj'): '6996b',
             ('wise', 'adj'): '2450', ('old', 'adj'): '2205', ('new', 'adj'): '2319',
             ('see', 'verb'): ('7200', 'q'), ('praise', 'verb'): ('1984b', 'p'), ('give', 'verb'): ('5414', 'q'),
             ('sing', 'verb'): ('7891', 'q'), ('write', 'verb'): ('3789', 'q'), ('say', 'verb'): ('559', 'q'),
             ('go', 'verb'): ('1980', 'q'), ('walk', 'verb'): ('1980', 'q'), ('come', 'verb'): ('935', 'q'),
             ('love', 'verb'): ('157', 'q'), ('rejoice', 'verb'): ('8055', 'q'), ('weep', 'verb'): ('1058', 'q'),
             ('flee', 'verb'): ('1272', 'q'), ('capture', 'verb'): ('3920', 'q'), ('take', 'verb'): ('3947', 'q'),
             ('die', 'verb'): ('4191', 'q'), ('kill', 'verb'): ('2026', 'q'), ('know', 'verb'): ('3045', 'q'),
             ('hear', 'verb'): ('8085', 'q'), ('ask', 'verb'): ('7592', 'q'), ('send', 'verb'): ('7971', 'q'),
             ('eat', 'verb'): ('398', 'q'), ('keep', 'verb'): ('8104', 'q'), ('dwell', 'verb'): ('3427', 'q'),
             ('live', 'verb'): ('3427', 'q'), ('inhabit', 'verb'): ('3427', 'q'), ('sleep', 'verb'): ('3462', 'q'),
             ('fight', 'verb'): ('3898', 'n'), ('make', 'verb'): ('6213a', 'q'), ('do', 'verb'): ('6213a', 'q')}
PRONOUNS = {('ego', 'sg'): ('אֲנִי', '1cs'), ('ego', 'pl'): ('אֲנַחְנוּ', '1cp'), ('tū', 'sg'): ('אַתָּה', '2ms'),
            ('tū', 'pl'): ('אַתֶּם', '2mp'), ('is', 'sg'): ('הוּא', '3ms'), ('is', 'pl'): ('הֵם', '3mp')}
OBJECT_PRONOUNS = {'1cs': 'אֹתִי', '1cp': 'אֹתָנוּ', '2ms': 'אֹתְךָ', '2mp': 'אֶתְכֶם', '3ms': 'אֹתוֹ', '3fs': 'אֹתָהּ',
                   '3mp': 'אֹתָם', '3fp': 'אֹתָן'}
DEMONSTRATIVES = {('hic', 'm', 's'): 'הַזֶּה', ('hic', 'f', 's'): 'הַזֹּאת', ('hic', 'm', 'p'): 'הָאֵלֶּה',
                  ('ille', 'm', 's'): 'הַהוּא', ('ille', 'f', 's'): 'הַהִיא', ('ille', 'm', 'p'): 'הָהֵם'}
# ラテン語の前置詞 + 格 → (前置詞, 前に付く形か)
PREPOSITIONS = {('in', 'Abl'): ('בְּ', True), ('in', 'Acc'): ('אֶל־', False), ('ad', 'Acc'): ('אֶל־', False),
                ('ex', 'Abl'): ('מִן־', False), ('ē', 'Abl'): ('מִן־', False), ('ab', 'Abl'): ('מִן־', False),
                ('ā', 'Abl'): ('מִן־', False), ('cum', 'Abl'): ('עִם־', False), ('dē', 'Abl'): ('עַל־', False),
                ('sine', 'Abl'): ('בְּלִי', False), ('per', 'Acc'): ('בְּ', True), ('post', 'Acc'): ('אַחֲרֵי', False),
                ('ante', 'Acc'): ('לִפְנֵי', False), ('sub', 'Abl'): ('תַּחַת', False), ('super', 'Acc'): ('עַל־', False),
                ('apud', 'Acc'): ('אֵצֶל', False), ('prō', 'Abl'): ('בְּעַד', False), ('propter', 'Acc'): ('בִּגְלַל', False),
                ('contrā', 'Acc'): ('עַל־', False), ('inter', 'Acc'): ('בֵּין', False)}
CONNECTIVES = {'et': 'וְ', 'que': 'וְ', 'atque': 'וְ', 'ac': 'וְ', 'sed': 'אֲבָל', 'at': 'אֲבָל', 'autem': 'וְ',
               'enim': 'כִּי', 'nam': 'כִּי', 'igitur': 'לָכֵן', 'itaque': 'לָכֵן', 'tamen': 'אַךְ', 'neque': 'וְלֹא',
               'tum': 'אָז', 'deinde': 'אַחֲרֵי־כֵן', 'ubi': 'כַּאֲשֶׁר', 'cum': 'כַּאֲשֶׁר', 'postquam': 'אַחֲרֵי אֲשֶׁר',
               'dum': 'בְּעוֹד', 'quod': 'כִּי', 'quia': 'כִּי', 'sī': 'אִם', 'ut': 'לְמַעַן', 'quamquam': 'גַּם כִּי',
               'aut': 'אוֹ', 'vel': 'אוֹ'}
QUESTION_WORDS = {'cūr': 'לָמָּה', 'quārē': 'לָמָּה', 'quōmodo': 'אֵיךְ', 'ubi': 'אֵיפֹה', 'quō': 'אָנָה',
                  'unde': 'מֵאַיִן', 'quandō': 'מָתַי', 'num': 'אִם', 'utrum': 'אִם'}


def available():
    return os.path.exists(DB_PATH)


@functools.lru_cache(maxsize=1)
def _db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _pointed(text):
    return any('ְ' <= c <= 'ׇ' for c in text)


@functools.lru_cache(maxsize=1)
def _lexicon():
    """見出しの番号 → (見出し, 品詞, 訳語の列, 語根, 態ごとの英語の訳語)"""
    out = {}
    for aug, word, pos, ja, root, stems in _db().execute('SELECT aug, word, pos, ja, root, stems FROM lexicon'):
        out[aug] = (word, pos, [g.strip() for g in (ja or '').split(',') if g.strip()], root,
                    json.loads(stems) if stems else {})
    return out


@functools.lru_cache(maxsize=1)
def _gloss_index():
    """訳語 (日本語・英語) → [(見出しの番号, 品詞, 順位)]。動詞は態ごとの英語の訳語 (qal: see …) も"""
    index = {}
    for aug, (word, pos, glosses, root, stems) in _lexicon().items():
        p = {'N': 'noun', 'A': 'adj', 'V': 'verb', 'D': 'adv'}.get(pos)
        if p is None:
            continue
        for rank, g in enumerate(glosses):
            index.setdefault(g.lower(), []).append((aug, p, rank, None))
        for stem, glosses_ in stems.items():
            for rank, g in enumerate(glosses_):
                index.setdefault(g.lower(), []).append((aug, p, rank, STEM_CODES.get(stem)))
    return index


@functools.lru_cache(maxsize=1)
def _counts():
    """見出しの番号 → 聖書に現れた回数 (よく使う語を先に)"""
    counts = {}
    for lemmas, count in _db().execute('SELECT lemmas, count FROM forms'):
        for aug in json.loads(lemmas):
            if aug[:1].isdigit():
                counts[aug] = counts.get(aug, 0) + count
    return counts


def to_hebrew(lex, pos=None):
    """語 → (見出しの番号, 態の符号)。見つからなければ None"""
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    sources = english.candidates(lex) or ([e for e in (lex.en or '').split(',') if e])
    for en in sources[:1]:
        found = PREFERRED.get((en.lower(), pos)) or PREFERRED.get((en.lower().split(' ')[-1], pos))
        if found:
            return found if isinstance(found, tuple) else (found, None)
    from .japanese import gloss as ja_gloss
    keys = [ja_gloss(lex)] + [e.lower() for e in sources[:4]]
    for key in keys:
        hits = [(rank, -_counts().get(aug, 0), aug, stem) for aug, p, rank, stem in _gloss_index().get(key, [])
                if p == pos]
        if hits:
            _, _, aug, stem = min(hits, key=lambda h: (h[0], h[1], h[2], h[3] or ''))   # 態の符号の無いものも
            return aug, stem or 'q'
    return None


# ----------------------------------------------------------------------
# 名詞・形容詞

@functools.lru_cache(maxsize=20000)
def _noun_forms(aug):
    """見出しの番号 → [(語形 (区切り), 形態の符号, 回数)]"""
    rows = _db().execute("SELECT segments, morph, count FROM forms WHERE lemmas LIKE ?", ('%"' + aug + '"%',)).fetchall()
    return [(json.loads(seg), morph, count) for seg, morph, count in rows]


def _morph_parts(morph):
    """'HTd/Ncfsa' → ['Td', 'Ncfsa']"""
    return morph[1:].split('/')


# 形の上では男性 (語末に ה も ת も無い) でも、文法の上では女性の名詞 (形容詞・動詞が女性形で一致する)。
# 形態の注記 (Ncmsa) は形を見ているので、ここで直す
FEMININE = {'5892a', '5892b', '776', '5315', '2719', '5869', '3027', '7272', '6106'}


def noun_form(aug, number='s', definite=False, kind='N'):
    """名詞・形容詞の語形 (冠詞の有無を含む)。(語形, 性)"""
    word, gender = _noun_form(aug, number, definite, kind)
    return word, ('f' if aug in FEMININE else gender)


def _noun_form(aug, number, definite, kind):
    best = {}
    for segments, morph, count in _noun_forms(aug):
        parts = _morph_parts(morph)
        main = parts[-1]
        if not main.startswith(kind) or len(main) < 5:
            continue
        gender, num, state = main[-3], main[-2], main[-1]
        prefixes = parts[:-1]
        if num != number or state != 'a' or not _pointed(''.join(segments)):
            continue
        if prefixes == (['Td'] if definite else []):
            key = 'exact'
        elif not prefixes:
            key = 'bare'
        else:
            continue
        if key not in best or count > best[key][2]:
            best[key] = (''.join(segments), gender, count)
    if 'exact' in best:
        return best['exact'][0], best['exact'][1]
    if 'bare' in best:
        word, gender, _ = best['bare']
        return (article(word) if definite else word), gender
    entry = _lexicon().get(aug)
    if entry is None:
        return '[%s]' % aug, 'm'   # 表の番号の誤り (語形を作らない)
    word = entry[0]
    return (article(word) if definite else word), 'm'


def article(word):
    """冠詞 הַ + 次の字を重ねる (喉音・ר の前は הָ / הַ で重ねない)"""
    first = word[:1]
    if first in 'אער':
        return 'הָ' + word
    if first in 'הח':
        return 'הַ' + word
    rest = word[1:]
    if rest.startswith(DAGESH) or (len(rest) > 1 and rest[1:2] == DAGESH):
        return 'הַ' + word
    return unicodedata.normalize('NFC', 'הַ' + first + DAGESH + rest)


# 前置詞 + 代名詞の接尾辞 (לָנוּ「私たちに」・בּוֹ)。人称性数は PRONOUNS の符号 (1cp・3ms …)
SUFFIXED_PREPOSITIONS = {
    'לְ': {'1cs': 'לִי', '1cp': 'לָנוּ', '2ms': 'לְךָ', '2mp': 'לָכֶם', '3ms': 'לוֹ', '3fs': 'לָהּ', '3mp': 'לָהֶם'},
    'בְּ': {'1cs': 'בִּי', '1cp': 'בָּנוּ', '2ms': 'בְּךָ', '2mp': 'בָּכֶם', '3ms': 'בּוֹ', '3fs': 'בָּהּ', '3mp': 'בָּהֶם'},
    'כְּ': {'1cs': 'כָּמוֹנִי', '1cp': 'כָּמוֹנוּ', '2ms': 'כָּמוֹךָ', '2mp': 'כְּמוֹכֶם', '3ms': 'כָּמוֹהוּ',
           '3fs': 'כָּמוֹהָ', '3mp': 'כְּמוֹהֶם'},
    'מִן־': {'1cs': 'מִמֶּנִּי', '1cp': 'מִמֶּנּוּ', '2ms': 'מִמְּךָ', '2mp': 'מִכֶּם', '3ms': 'מִמֶּנּוּ', '3fs': 'מִמֶּנָּה',
           '3mp': 'מֵהֶם'},
    'עִם־': {'1cs': 'עִמִּי', '1cp': 'עִמָּנוּ', '2ms': 'עִמְּךָ', '2mp': 'עִמָּכֶם', '3ms': 'עִמּוֹ', '3fs': 'עִמָּהּ',
           '3mp': 'עִמָּם'},
    'עַל־': {'1cs': 'עָלַי', '1cp': 'עָלֵינוּ', '2ms': 'עָלֶיךָ', '2mp': 'עֲלֵיכֶם', '3ms': 'עָלָיו', '3fs': 'עָלֶיהָ',
            '3mp': 'עֲלֵיהֶם'},
    'אֶל־': {'1cs': 'אֵלַי', '1cp': 'אֵלֵינוּ', '2ms': 'אֵלֶיךָ', '2mp': 'אֲלֵיכֶם', '3ms': 'אֵלָיו', '3fs': 'אֵלֶיהָ',
            '3mp': 'אֲלֵיהֶם'},
}


def pronoun_with_preposition(prep, np):
    """前置詞 + 代名詞 → 接尾辞の形 (לָנוּ)。代名詞でないか表に無ければ None"""
    head = np.head
    if head is None or head.pos != 'pronoun' or (head.lemma, np.number) not in PRONOUNS or np.members:
        return None
    key = PRONOUNS[(head.lemma, np.number)][1]
    if key == '3ms' and np.gender == 'f':
        key = '3fs'
    return SUFFIXED_PREPOSITIONS.get(prep, {}).get(key)


def with_preposition(prep, word):
    """前に付く前置詞 (בְּ・לְ・כְּ): 冠詞があれば縮める (בְּ + הַגַּן → בַּגַּן)"""
    if word.startswith(('הַ', 'הָ', 'הֶ')):
        return unicodedata.normalize('NFC', prep[0] + (DAGESH if prep[0] in 'בכ' else '') + word[1:])   # בַּגָּן
    return prep + word


def adjective(lex, gender, number, definite):
    found = to_hebrew(lex, 'adj')
    if found is None:
        return '[%s]' % english.word(lex)
    aug = found[0]
    best = None
    for segments, morph, count in _noun_forms(aug):
        parts = _morph_parts(morph)
        main = parts[-1]
        if not main.startswith('Aa') or len(main) < 5 or not _pointed(''.join(segments)):
            continue
        g, n, s = main[-3], main[-2], main[-1]
        if (g, n, s) == (gender, number, 'a') and parts[:-1] in ([], ['Td']):
            score = (parts[:-1] == (['Td'] if definite else []), count)
            if best is None or score > best[0]:
                best = (score, ''.join(segments), parts[:-1])
    if best is None:
        word = _lexicon().get(aug, (aug,))[0]
        return article(word) if definite else word
    word = best[1]
    if definite and best[2] != ['Td']:
        word = article(word)
    return word


def noun_phrase(np, prep=None, definite=True):
    """名詞句 (前に付く前置詞があれば付けて)。(語の列の文字列, 性, 数)"""
    if np.members:
        parts = [noun_phrase(m, None, definite)[0] for m in np.members]
        text = ' וְ'.join(parts)
        return (with_preposition(prep, text) if prep else text), 'm', 'p'
    head = np.head
    if head is None:
        return '', 'm', 's'
    if head.pos == 'pronoun' and (head.lemma, np.number) in PRONOUNS:
        attached = pronoun_with_preposition(prep, np) if prep else None   # לָנוּ (לְ + אֲנַחְנוּ でなく)
        return attached or PRONOUNS[(head.lemma, np.number)][0], 'm', 'p' if np.number == 'pl' else 's'
    if head.proper:
        return ((prep + head.lemma) if prep else head.lemma), 'm', 's'
    found = to_hebrew(head, 'noun')
    if found is None:
        return '[%s]' % english.word(head), 'm', 's'
    number = 'p' if np.number == 'pl' else 's'
    definite = definite and not np.genitives
    word, gender = noun_form(found[0], number, definite)
    if gender == 'b':
        gender = 'm'   # 両性 (גַּן)
    if gender not in ('m', 'f'):
        gender = 'f' if np.gender == 'f' else 'm'
    words = [word]
    for g in np.genitives:
        words.append(noun_phrase(g)[0])
    for m in np.modifiers:
        if isinstance(m, NP):
            words.append(' וְ'.join(adjective(x.head, gender, number, definite) for x in m.members))
        elif m.pos == 'pronoun' and m.lemma in ('hic', 'ille'):
            words.append(DEMONSTRATIVES.get((m.lemma, gender, number)) or DEMONSTRATIVES[(m.lemma, 'm', 's')])
        else:
            words.append(adjective(m, gender, number, definite))
    for r in np.relatives:
        words.append('אֲשֶׁר ' + realize(r, gap=r.gap if r.gap in ('subject', 'object') else 'subject'))
    text = ' '.join(words)
    if prep:   # 1字の前置詞 (בְּ・לְ・כְּ) は前に付けて冠詞と縮める
        proclitic = len([c for c in prep if not unicodedata.combining(c)]) == 1
        text = with_preposition(prep, text) if proclitic else prep + text
    return text, gender, number


def prepositional(np, passive=False):
    import dataclasses
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
        return 'עַל־יְדֵי ' + noun_phrase(inner)[0]   # 受動の動作主
    prep, attached = PREPOSITIONS.get((np.prep.lemma, np.case), ('בְּ', True))
    suffixed = pronoun_with_preposition(prep, inner)
    if suffixed:
        return suffixed
    if attached:
        return noun_phrase(inner, prep)[0]
    return prep + ('' if prep.endswith('־') else ' ') + noun_phrase(inner)[0]


# ----------------------------------------------------------------------
# 動詞

def _verb_forms(root, stem, vtype, pgn):
    rows = _db().execute('SELECT form, count, bare FROM verbs WHERE root = ? AND stem = ? AND type = ? AND pgn = ? '
                         "AND lang = 'H'", (root, stem, vtype, pgn)).fetchall()
    rows = [r for r in rows if _pointed(r[0])]   # 母音記号の無い形 (ケティーブ הלכתי) は使わない
    return sorted(rows, key=lambda r: (-r[2], -r[1]))


def verb_form(aug, stem, vtype, pgn):
    """動詞の語形: 聖書に現れた形 (接辞の無い形を先に)、無ければ強い語根の型 (3人称男性単数だけ)"""
    entry = _lexicon().get(aug)
    if entry is None:
        return None
    root = ''.join(c for c in (entry[3] or '') if not unicodedata.combining(c))   # 動詞の表の語根は点なし (שׁיר → שיר)
    if vtype in ('p', 'q') and pgn[0] == '3' and pgn[2] == 'p':
        pgn = '3cp'   # 完了の3人称複数は男女共通
    forms = _verb_forms(root, stem, vtype, pgn)
    if forms:
        return forms[0][0]
    if vtype == 'r' and pgn != 'msa':   # 分詞: 男性単数から規則で (שָׁר → שָׁרָה・שָׁרִים)
        masc = _verb_forms(root, stem, 'r', 'msa')
        masc = masc[0][0] if masc else _from_template(root, stem, 'participle')
        if masc:
            return _participle_from(masc, pgn)
    if vtype == 'v' and pgn == '2mp':   # 命令の男性複数: 単数 + וּ は作らず、聖書の形が無ければ単数の形
        return verb_form(aug, stem, 'v', '2ms')
    if (pgn == '3ms' and vtype in ('p', 'i')) or (pgn == 'msa' and vtype == 'r') or (pgn == '2ms' and vtype == 'v'):
        return _from_template(root, stem, {'p': 'qatal', 'i': 'yiqtol', 'r': 'participle', 'v': 'imperative'}[vtype])
    return None


def _from_template(root, stem, column):
    """強い語根の型 (binyan) から作る。語末形は普通の形に直して渡す"""
    from dragoman.hebrew import binyan
    stem_name = {v: k for k, v in STEM_CODES.items()}.get(stem, 'qal')
    return binyan.generate(root.translate(str.maketrans('ךםןףץ', 'כמנפצ')), stem_name, column) or None


def _participle_from(masc, pgn):
    """男性単数の分詞 → 女性単数 (+ ָה。語末の ֶה は ָה に)・男性複数 (+ ִים)・女性複数 (+ וֹת)"""
    base = masc[:-2] if masc.endswith('ֶה') or masc.endswith('ֵה') else masc
    if pgn == 'fsa':
        return unicodedata.normalize('NFC', base + 'ָה') if base != masc else unicodedata.normalize('NFC', masc + 'ָה')
    if pgn == 'mpa':
        return unicodedata.normalize('NFC', base + 'ִים')
    if pgn == 'fpa':
        return unicodedata.normalize('NFC', base + 'וֹת')
    return masc


def _pgn(clause, subject):
    """人称性数 (3ms …)。分詞は性数と状態 (msa …)"""
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            (subject.head.lemma, subject.number) in PRONOUNS:
        return PRONOUNS[(subject.head.lemma, subject.number)][1]
    if subject is not None:
        _, gender, number = noun_phrase(subject)
        return '3%s%s' % (gender, number)
    return '%d%s%s' % (clause.person, 'm' if clause.person != 1 else 'c', 'p' if clause.number == 'pl' else 's')


def verb_words(clause, subject):
    """(語の列, 分詞か)"""
    found = to_hebrew(clause.verb, 'verb')
    if found is None:
        return ['[%s]' % english.word(clause.verb)], False
    aug, stem = found
    if clause.voice == 'passive':
        stem = PASSIVE_STEMS.get(stem, 'N')
    pgn = _pgn(clause, subject)
    if clause.mood == 'imperative':   # 命令形 (שְׁמֹר)。禁止は אַל + 未完了形 (אַל תִּירָא)
        pgn = '2m' + ('p' if clause.number == 'pl' else 's')
        if clause.negated:
            form = verb_form(aug, stem, 'i', pgn) or verb_form(aug, stem, 'v', pgn)
            return ['אַל', form or _lexicon()[aug][0]], False
        return [verb_form(aug, stem, 'v', pgn) or _lexicon()[aug][0]], False
    participle = clause.tense in ('present', 'imperfect')
    if participle:
        g = pgn[1] if pgn[1] in 'mf' else 'm'
        form = verb_form(aug, stem, 'r' if clause.voice != 'passive' else 'r', g + pgn[2] + 'a') or \
            verb_form(aug, stem, 'p', pgn)
    elif clause.tense in ('future', 'future-perfect'):
        form = verb_form(aug, stem, 'i', pgn)
    else:
        form = verb_form(aug, stem, 'p', pgn)
    if form is None:
        form = verb_form(aug, stem, 'p', '3ms') or _lexicon()[aug][0]
    words = [form]
    if clause.tense == 'imperfect' and participle:
        hayah = {'3ms': 'הָיָה', '3fs': 'הָיְתָה', '3mp': 'הָיוּ', '3fp': 'הָיוּ'}.get(pgn[:3], 'הָיָה')
        words = [hayah, form]
    return words, participle


def realize(clause, gap=None):
    """節 → ヘブライ語。gap は関係節の空所の役割 (その名詞句は書かない)"""
    from .frame import lexical_negation, periphrastic, dative_as_object
    clause = dative_as_object(lexical_negation(periphrastic(clause)), 'he')
    out = []
    for p in clause.adjuncts:
        if p.kind == 'absolute' and p.subject is not None:
            out.append(_absolute(p) + ',')
    if clause.copula:
        return ' '.join(out + _nominal(clause, gap))
    subject = (clause.role('subject') or [None])[0]
    verb, participle = verb_words(clause, subject)
    if clause.negated and clause.mood != 'imperative':
        verb = ['לֹא'] + verb
    subject_text = noun_phrase(subject)[0] if subject is not None and gap != 'subject' and not (
        subject.head is not None and subject.head.pos == 'pronoun' and not participle) else ''
    if participle and gap != 'subject':   # 分詞は主語が先 (代名詞の主語も書く)
        if not subject_text and subject is None:
            key = ({1: 'ego', 2: 'tū'}.get(clause.person, 'is'), clause.number)
            subject_text = PRONOUNS.get(key, ('הוּא',))[0]
        out += [subject_text] + verb
    else:
        out += verb + [subject_text]
    for np in clause.role('object'):
        if gap == 'object':
            continue
        if np.head is not None and np.head.pos == 'pronoun' and (np.head.lemma, np.number) in PRONOUNS:
            out.append(OBJECT_PRONOUNS.get(PRONOUNS[(np.head.lemma, np.number)][1], 'אֹתוֹ'))
        else:
            out.append('אֶת־' + noun_phrase(np)[0])   # 定まった目的語の印
    for np in clause.role('recipient'):
        out.append(noun_phrase(np, 'לְ')[0])
    for inner in clause.infinitives:
        out.append(_infinitive(inner))
    for inner in clause.questions:
        out.append(_question(inner))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement'):
            continue
        if role == 'prep':
            out.append(prepositional(np, clause.voice == 'passive'))
        elif role == 'means':
            out.append(noun_phrase(np, 'לְ' if np.animate else 'בְּ')[0])
        else:
            out.append(noun_phrase(np, 'בְּ')[0])
    return ' '.join(w for w in out if w)


def _nominal(clause, gap=None):
    """名詞文: 主語 + 述語 (繋辞なし)。過去は הָיָה、否定は לֹא"""
    subject = (clause.role('subject') or [None])[0]
    complements = clause.role('complement') + clause.role('object')
    text, gender, number = noun_phrase(subject) if subject is not None else ('', 'm', 's')
    out = [text] if gap != 'subject' else []
    if clause.tense in ('perfect', 'imperfect', 'past-perfect'):
        out.append({('m', 's'): 'הָיָה', ('f', 's'): 'הָיְתָה'}.get((gender, number), 'הָיוּ'))
    if clause.negated:
        out.append('לֹא')
    if not complements:
        return out
    np = complements[0]
    if np.head is not None and np.head.pos in ('adj', 'participle') and not np.members:
        out.append(adjective(np.head, gender, number, False))
    else:
        out.append(noun_phrase(np, definite=False)[0])
    return out


def _infinitive(inner):
    import dataclasses
    finite = dataclasses.replace(inner, mood='indicative', infinitive_kind='')
    if inner.infinitive_kind in ('saying', 'perception') and inner.role('subject'):
        return 'כִּי ' + realize(finite)
    return realize(dataclasses.replace(finite, args=[(r, np) for r, np in finite.args if r != 'subject']))


def _question(inner):
    import dataclasses
    from .frame import interrogative_np, without_interrogative
    owner, role, wh = interrogative_np(inner)
    finite = dataclasses.replace(inner, mood='indicative', question_word='')
    if wh is None:
        return QUESTION_WORDS.get(inner.question_word, 'אִם') + ' ' + realize(finite)
    word = 'מִי' if inner.question_word in ('quis', 'quem', 'cui', 'cūius', 'cuius') and wh.gender != 'n' else 'מָה'
    return word + ' ' + realize(without_interrogative(finite), gap=role if role in ('subject', 'object') else None)


def _absolute(p):
    from .frame import Clause
    clause = Clause(Lex(p.verb.verb, 'verb', p.verb.verb_ja or _latin_verb_ja(p.verb), lang=p.verb.lang),
                    tense='perfect' if p.tense != 'present' else 'present',
                    voice='passive' if p.voice == 'passive' else 'active', args=[('subject', p.subject)])
    return ('כַּאֲשֶׁר ' if p.tense == 'present' else 'אַחֲרֵי אֲשֶׁר ') + realize(clause)


def _latin_verb_ja(participle):
    if participle.lang not in ('', 'la') or not participle.verb:
        return ''
    from . import latin
    return next((item['ja'] for _, item in latin._forms(participle.verb, 'verb')[:5] if item.get('ja')), '')


def wrap(text, clause):
    for key in reversed(clause.connectives + ([clause.subordinator] if clause.subordinator else [])):
        if key in CONNECTIVES:
            word = CONNECTIVES[key]
            text = (word + text) if word == 'וְ' else (word + ' ' + text)   # וְ は次の語に付ける
    return text


def transliterate(text):
    from dragoman.hebrew import script
    return ' '.join(script.translit(w) if re.search('[֐-׿]', w) else w for w in text.split(' '))


def vocative(np):
    """呼びかけ: 冠詞付き (הַמֶּלֶךְ「王よ」。固有名詞はそのまま)"""
    return noun_phrase(np)[0]


def sentence(clauses):
    """ヘブライ文字 (と転写の行)"""
    if not clauses:
        return ''
    from .frame import with_address
    text = unicodedata.normalize('NFC', ', '.join(wrap(with_address(c, realize, vocative), c) for c in clauses)) + '.'
    return '%s\n            %s' % (text, transliterate(text))
