#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 生成で選んだ語の、辞書の語義の幅 (比較の表に添える): pirka「良い・きれいだ・具合がよい」
#
#   訳語は一対一に対応しない。選んだ語が元の語より広い・狭い意味を持つことが見えるように、その語の辞書の語義を並べる
#   (英語の語義は日本語に直す。直せなければ英語のまま)
#
import functools

from dragoman.core import en_ja

LIMIT = 4


def _japanese(glosses, pos):
    """語義の列 → 日本語の語義の列 (重複を除き LIMIT まで)"""
    out = []
    for gloss in glosses:
        gloss = gloss.strip()
        if not gloss:
            continue
        if gloss.isascii():
            word = gloss[3:] if gloss.startswith('be ') else gloss
            found = en_ja.lookup(word, {'participle': 'verb'}.get(pos, pos))
            gloss = found[0] if found else gloss
        if gloss not in out:
            out.append(gloss)
        if len(out) >= LIMIT:
            break
    return out


@functools.lru_cache(maxsize=None)
def _transfer_glosses(lang):
    """英語の索引の語 → その語の英語の語義 (transfer の索引の逆引き)"""
    from . import transfer
    out = {}
    for targets in transfer._index(lang).values():
        for _, target in targets:
            out.setdefault(target.lemma, target.english)
    return out


def senses(lang, lex, pos):
    """言語 lang で lex に選ぶ語と、その語義 (日本語) の列。分からなければ None"""
    if lex is None or lex.proper or lex.pos == 'pronoun':
        return None
    pos = {'participle': 'verb', 'name': 'noun'}.get(pos, pos)
    try:
        word, glosses = _choose(lang, lex, pos)
    except Exception:
        return None
    if not word or not glosses:
        return None
    return word, _japanese(glosses, pos)


def _choose(lang, lex, pos):
    if lang in ('ru', 'grc', 'sa', 'id'):
        from . import transfer
        target = transfer.best(lex, lang, pos)
        if target is None:
            return None, None
        # 基本の語の表から選んだ語は合った英語しか持たないので、索引からその語の語義を全部
        return target.lemma, list(_transfer_glosses(lang).get(target.lemma) or target.english)
    if lang == 'tl':
        from . import tagalog
        word = tagalog.to_tagalog(lex, pos)
        if pos == 'verb' and word:   # 動詞は語根 (kita)。辞書の見出しは焦点の接辞の付いた形 (makita)
            for voice in ('object', 'actor'):
                lemma = tagalog.lemma_for(word, voice)
                if _transfer_glosses('tl').get(lemma):
                    return lemma, list(_transfer_glosses('tl')[lemma])
            return word, []
        return word, list(_transfer_glosses('tl').get(word, ()))
    if lang == 'ar':
        from . import arabic
        found = arabic.candidates(lex, pos)
        if not found:
            return None, None
        key, found_pos = found[0]
        # 見出しの鍵の項目のうち品詞の合うもの (鍵 راوَنْد の動詞は رَأَى「見る」、名詞は「大黄」)
        entries = [e for e in arabic._db().lemma_hash.get(key, []) if e.get('pos') == found_pos] or \
            arabic._db().lemma_hash.get(key, [])
        glosses = [g for e in entries for g in (e.get('gloss') or '').replace(';', ',').split(',')]
        word = arabic.generate(key, {'pos': 'verb', 'asp': 'p', 'per': '3', 'gen': 'm', 'num': 's', 'vox': 'a'}) \
            if found_pos == 'verb' else (entries[0].get('lex') if entries else key)
        return word or key, [g.replace('_', ' ') for g in glosses]
    if lang == 'he':
        from . import hebrew
        found = hebrew.to_hebrew(lex, pos)
        entry = hebrew._lexicon().get(found[0]) if found else None
        return (entry[0], list(entry[2])) if entry else (None, None)
    if lang == 'fa':
        from . import persian
        row = persian.to_persian(lex, pos)
        return (row[0], row[5].split(',')) if row else (None, None)
    if lang in ('hi', 'ur'):
        from . import hindi
        row = hindi.to_hindi(lex, pos)
        if not row:
            return None, None
        return (row[4] or row[0]) if lang == 'ur' else row[0], row[5].split(',')
    if lang == 'ain':
        from . import ainu
        from dragoman.ainu import grammar
        word = ainu.to_ainu(lex, pos)
        if not word:
            return None, None
        glosses = (grammar.LEXICON.get(word, ('', ''))[0] or '').split(',')
        for gloss, entries in ainu._by_english().items():
            if any(w == word for _, w, _ in entries) and gloss not in glosses:
                glosses.append(gloss)
        return word, glosses
    if lang == 'bo':
        from . import tibetan
        word = tibetan.to_tibetan(lex, pos)
        if not word:
            return None, None
        rows = tibetan._db().execute('SELECT en FROM words WHERE wylie = ? ORDER BY rank', (word,)).fetchall()
        return word, [g for (en,) in rows for g in (en or '').split(',')]
    return None, None


def note(lang, lex, pos):
    """比較の表の手段の欄に添える文字列 (語義が2つ以上のときだけ): '語義: pirka = 良い・きれいだ'"""
    found = senses(lang, lex, pos)
    if not found or len(found[1]) < 2:
        return ''
    return '語義: %s = %s' % (found[0], '・'.join(found[1]))
