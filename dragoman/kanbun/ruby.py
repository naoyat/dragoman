#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢字の読み (振り仮名): 字ごとの読みと、書き下し文の読み (ひらがな)
#
#   助字・副詞・代名詞      手作りの表 (歴史的仮名遣い: 則 すなは・焉 いづ・汝 なんぢ)
#   用言 (送り仮名のある字)  KANJIDIC2 の訓 (まな.ぶ) から、送り仮名の行が合う語幹 (學び → まな)
#   名詞・熟語              JMdict の表記と読み ($DRAGOMAN_DATA/ja-readings.tsv。tools/build_ja_readings.py)。
#                           語義 (UD-Kanbun の Gloss) が合い、字ごとの音・訓に分けられる読み (遠方 えん・ぽう)
#   字を仮名で読む助字      書き下しの仮名の初めの字 (不 ず・可 べ)
#
# 用言・名詞の読み (KANJIDIC2・JMdict は現代仮名遣い) は、Wiktionary の語の歴史的仮名遣いから作った表
# ($DRAGOMAN_DATA/ja/historical-kana.tsv。tools/build_ja_historical.py) で歴史的仮名遣いに (王 わう・遠方 ゑんぱう)。
# 表に無いものは現代仮名遣いのまま
#
import functools
import os
import re

from dragoman.core import paths
from . import kundoku, readings

# 字 → 読み (送り仮名を除く)。(字, 送り仮名) で引けるものが先
RUBY = {
    # 副詞・接続
    '亦': 'ま', '又': 'また', '復': 'ま', '必': 'かなら', '常': 'つね', '嘗': 'かつ', '曾': 'かつ', '甚': 'はなは',
    '皆': 'みな', '獨': 'ひと', '既': 'すで', '已': 'すで', '方': 'まさ', '乃': 'すなは', '卽': 'すなは', '即': 'すなは',
    '則': 'すなは', '遂': 'つひ', '終': 'つひ', '共': 'とも', '俱': 'とも', '尙': 'な', '猶': 'な', '相': 'あひ',
    '徒': 'いたづ', '稍': 'やや', '益': 'ますます', '愈': 'いよいよ', '豈': 'あ', '寧': 'むし', '唯': 'た', '惟': 'た',
    '只': 'た', '但': 'た', '果': 'は', '敢': 'あ', '能': 'よ', '頗': 'すこぶ', '殆': 'ほとん', '蓋': 'けだ', '竊': 'ひそ',
    '故': 'ゆゑ', '安': 'いづ', '焉': 'いづ', '惡': 'いづ', '奚': 'なん', '胡': 'なん', '曷': 'なん', '盍': 'なん',
    '未': 'いま', '將': 'まさ', '當': 'まさ', '應': 'まさ', '宜': 'よろ', '須': 'すべか', '雖': 'いへど', '自': 'みづか',
    # 代名詞・指示詞
    '之': 'これ', '我': 'われ', '吾': 'われ', '予': 'われ', '余': 'われ', '汝': 'なんぢ', '爾': 'なんぢ', '女': 'なんぢ',
    '若': 'なんぢ', '其': 'そ', '此': 'こ', '是': 'こ', '彼': 'か', '斯': 'こ', '夫': 'そ', '誰': 'たれ', '孰': 'いづ',
    '己': 'おのれ', '朕': 'ちん', '或': 'ある', '諸': 'もろもろ', '每': 'ごと', '各': 'おのおの',
    # 用言・助字の訓 (KANJIDIC2 に無いもの・歴史的仮名遣いの違うもの)
    '說': 'よろこ', '悅': 'よろこ', '曰': 'い', '謂': 'い', '云': 'い', '言': 'い', '所': 'ところ', '者': 'もの',
    '以': 'もつ', '如': 'ごと', '勿': 'な', '毋': 'な', '莫': 'な', '無': 'な', '非': 'あら', '有': 'あ', '在': 'あ',
    '欲': 'ほつ', '敎': 'をし', '教': 'をし', '用': 'もち', '居': 'を', '與': 'あた', '爲': 'な', '見': 'み',
    '省': 'かへり', '罔': 'くら',
}
RUBY_WITH = {('且', 'つ'): 'か', ('且', 'に'): 'まさ', ('何', 'ぞ'): 'なん', ('何', ''): 'なに', ('自', 'ら'): 'みづか',
             ('自', 'り'): 'よ', ('三', 'たび'): 'み', ('爲', 'に'): 'ため', ('與', ''): 'と', ('如', 'し'): 'ごと',
             ('若', 'し'): 'ごと', ('若', 'くは'): 'し', ('見', 'る'): 'み', ('使', ''): 'し', ('令', ''): 'し',
             ('如', 'か'): 'し', ('若', 'か'): 'し', ('是', ''): 'これ', ('此', ''): 'これ', ('斯', ''): 'これ',
             ('其', ''): 'それ', ('已', 'む'): 'や',
             ('易', 'し'): 'やす', ('易', 'く'): 'やす', ('易', 'き'): 'やす', ('易', 'から'): 'やす', ('易', 'けれ'): 'やす', ('彼', ''): 'かれ', ('夫', ''): 'それ'}
# 同じ字で活用の型により読みの違う用言: (字, 型) → 読み (苦し: ク にが、シク くる)
RUBY_KIND = {('苦', 'ク'): 'にが', ('苦', 'シク'): 'くる'}
# 歴史的仮名遣いの送り仮名 → 現代仮名遣い (KANJIDIC2 の訓と行を突き合わせるため。語幹の後ろなので語頭の規則は要らない)
MODERN_KANA = str.maketrans('はひふへほゐゑを', 'わいうえおいえお')
ROWS = ['あいうえお', 'かきくけこ', 'がぎぐげご', 'さしすせそ', 'ざじずぜぞ', 'たちつてと', 'だぢづでど', 'なにぬねの',
        'はひふへほ', 'ばびぶべぼ', 'ぱぴぷぺぽ', 'まみむめも', 'やゆよ', 'らりるれろ', 'ん', 'っ']
ROW = {c: n for n, row in enumerate(ROWS) for c in row}
ROW.update({c: 0 for c in 'わゐゑを'})   # 思は → 思わ と おも.う (ワ行とア行の五段)
VOICED = dict(zip('かきくけこさしすせそたちつてとはひふへほ', 'がぎぐげござじずぜぞだぢづでどばびぶべぼ'))
SEMIVOICED = dict(zip('はひふへほ', 'ぱぴぷぺぽ'))


def hiragana(kana):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in kana)


@functools.lru_cache(maxsize=1)
def _jmdict():
    """JMdict → {表記: [(読み, 英語の訳語の語の集合)]} (見出しの順)"""
    path = paths.data('ja-readings.tsv')
    out = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                word, reading, english = line.rstrip('\n').split('\t')
                out.setdefault(word, []).append((reading, english))
    return out


def available():
    return bool(_jmdict())


@functools.lru_cache(maxsize=1)
def _historical_table():
    """→ ({語: (字ごとの現代仮名遣い, 字ごとの歴史的仮名遣い)}, {(字, 現代仮名遣い): 歴史的仮名遣い})"""
    words, chars = {}, {}
    path = paths.data('ja', 'historical-kana.tsv')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                row = line.rstrip('\n').split('\t')
                if row[0] == 'W':
                    words[row[1]] = (tuple(row[2].split('|')), tuple(row[3].split('|')))
                elif row[0] == 'C':
                    chars.setdefault((row[1], row[2]), row[3])   # 語の多いものが先
    return words, chars


def historical(word, parts):
    """字ごとの現代仮名遣いの読み → 歴史的仮名遣い (遠方 [えん, ぽう] → [ゑん, ぱう])。語の表、無ければ字の表で"""
    words, chars = _historical_table()
    new = readings.shinjitai(word)
    entry = words.get(new) or words.get(word)
    if entry and entry[0] == tuple(parts):
        return list(entry[1])
    out = []
    for c, p in zip(word, parts):
        key = readings.shinjitai(c)
        out.append(chars.get((key, p)) or chars.get((c, p)) or p)
    return out


@functools.lru_cache(maxsize=10000)
def _char_readings(char):
    """字の音 (ひらがな) と、送り仮名の無い訓・訓の語幹"""
    kun, on = readings._kanjidic().get(readings.shinjitai(char), None) or readings._kanjidic().get(char, ((), ()))
    out = [hiragana(r).strip('-') for r in on]
    out += [r.split('.')[0].strip('-') for r in kun]
    return tuple(r for r in out if r)


def _kun(char):
    kun = (readings._kanjidic().get(readings.shinjitai(char), None) or readings._kanjidic().get(char, ((), ())))[0]
    return set(r.split('.')[0] for r in kun if '-' not in r)   # 接辞の訓 (人 -と) は除く


def _variants(reading, first, last):
    """熟語の中の字の読みの変わり方 (連濁・半濁音・促音)"""
    out = {reading}
    if not first and reading[0] in VOICED:
        out.add(VOICED[reading[0]] + reading[1:])
    if not first and reading[0] in SEMIVOICED:
        out.add(SEMIVOICED[reading[0]] + reading[1:])
    if not last and len(reading) > 1 and reading[-1] in 'つちくき':
        out.add(reading[:-1] + 'っ')
    return out


def split(word, reading):
    """熟語の読みを字ごとに分ける (遠方 えんぽう → [えん, ぽう])。字の音・訓で分けられなければ None"""
    def walk(k, rest):
        if k == len(word):
            return [] if not rest else None
        for r in _char_readings(word[k]):
            for v in _variants(r, k == 0, k == len(word) - 1):
                if rest.startswith(v):
                    tail = walk(k + 1, rest[len(v):])
                    if tail is not None:
                        return [v] + tail
        return None
    return walk(0, reading)


def _words(text):
    return set(w for w in re.split(r'[^a-z]+', (text or '').lower().replace('-', ' ')) if len(w) > 2)


def noun_reading(word, gloss=''):
    """名詞・熟語の読みを字ごとに ([せい]・[えん, ぽう])。JMdict の読みのうち、字ごとに分けられて語義が合うもの"""
    wanted = _words(gloss)
    best, best_score = None, (-1, -1)
    for key in dict.fromkeys((readings.shinjitai(word), word)):
        for reading, english in _jmdict().get(key, ()):
            parts = split(word, reading)
            if parts is None:
                continue
            # 語義が合うかどうか (語形の違う語義 harmonious ↔ harmony は語の初めの6字で)、1字なら訓を先に (人 ひと・じん)。同じなら JMdict の見出しの順
            kun = len(word) == 1 and reading in _kun(word)
            words = _words(english)
            match = 2 if wanted & words else 1 if {w[:6] for w in wanted if len(w) >= 6} & {w[:6] for w in words} else 0
            score = (match, 1 if kun else 0)
            if score > best_score:
                best, best_score = parts, score
    return best


def verb_stem(char, okuri):
    """送り仮名のある字の読み (語幹)。KANJIDIC2 の訓のうち、送り仮名の初めの字と行が合うもの (學び → まな)"""
    kun = readings._kanjidic().get(readings.shinjitai(char), None) or readings._kanjidic().get(char, ((), ()))
    modern = okuri.translate(MODERN_KANA)
    fallback = None
    for r in kun[0]:
        if '.' not in r or r.startswith('-'):
            continue
        stem, tail = r.split('.', 1)
        if not modern:   # 送り仮名の無い用言 (得)
            return stem
        if ROW.get(tail[0]) == ROW.get(modern[0]):
            return stem
        if tail in ('い', 'しい') and modern[0] in 'しきくけか':   # 形容詞の文語の活用 (深し・深く ↔ ふか.い)
            return stem
        whole = stem + tail   # き.たる と きた.る のように区切りの違う訓
        for k in range(1, len(whole)):
            if ROW.get(whole[k]) == ROW.get(modern[0]) and fallback is None:
                fallback = whole[:k]
    return fallback


def _okuri_of(e):
    return e.out[len(e.token.form):] if e.out.startswith(e.token.form) else None


def rubies(analysis):
    """{id(token): [字ごとの読み]}。読めない字は ''"""
    out = {}
    for elems in analysis.elems:
        shown = [e for e in kundoku._rendered(elems) if e.token is not None and e.kind not in ('punct', 'particle')
                 and e.out]
        n = 0
        while n < len(shown):
            e = shown[n]
            t = e.token
            if id(t) in out:
                n += 1
                continue
            okuri = _okuri_of(e)
            # 書き下しで続いている名詞 (送り仮名の無い語の後ろに、原文で次の語) は熟語として JMdict で引く
            run = [e]
            while okuri == '' and n + len(run) < len(shown):
                nxt = shown[n + len(run)]
                noun = nxt.kind == 'noun' or nxt.token.upos in ('NOUN', 'PROPN') or \
                    run[-1].token.rel == 'compound' and run[-1].token.head == nxt.token.i   # 晩成す
                if nxt.token.i != run[-1].token.i + 1 or _okuri_of(nxt) is None or not noun:
                    break
                run.append(nxt)
                if _okuri_of(nxt) != '':
                    break
            while len(run) > 1:
                word = ''.join(x.token.form for x in run)
                parts = noun_reading(word, ' '.join(x.token.gloss or '' for x in run))
                if parts:
                    parts = historical(word, parts)
                    k = 0
                    for x in run:
                        out[id(x.token)] = parts[k:k + len(x.token.form)]
                        k += len(x.token.form)
                    break
                run.pop()
            if len(run) > 1:
                n += len(run)
                continue
            out[id(t)] = _token_ruby(e, okuri)
            n += 1
    return out


def _token_ruby(e, okuri):
    t = e.token
    if okuri is None:   # 字を仮名で読む助字 (不 → ず、可 → べから)
        return [e.out[0]]
    for (char, tail), reading in RUBY_WITH.items():   # 送り仮名の初めで引く (如かざる → 如か)
        if char == t.form and (okuri.startswith(tail) if tail else not okuri):
            return [reading]
    if t.form in RUBY:
        return [RUBY[t.form]]
    if e.pred is not None and (t.form, e.pred.kind) in RUBY_KIND:
        return [RUBY_KIND[t.form, e.pred.kind]]
    if len(t.form) == 1 and (okuri or e.kind == 'pred' or t.upos == 'VERB'):
        stem = verb_stem(t.form, okuri)
        if stem:
            return historical(t.form, [stem])
    parts = noun_reading(t.form, t.gloss) or [(_char_readings(c) or ('',))[0] for c in t.form]
    return historical(t.form, parts)


def yomi(analysis):
    """書き下し文の読み (ひらがな。漢字を振り仮名に置き換える)"""
    ruby = rubies(analysis)
    out = ''
    for elems in analysis.elems:
        for e in kundoku._rendered(elems):
            t = e.token
            if t is not None and e.out.startswith(t.form) and all(ruby.get(id(t), [''])):
                out += ''.join(ruby[id(t)]) + e.out[len(t.form):]
            else:
                out += e.out
    return out
