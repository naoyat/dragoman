#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語のコマンドの設定 (core/cli.py)
#
from dragoman.core.cli import Command
from . import analyzer, dictionary

USAGE = '''
  ./dragoman.py haw -e "Ua hele ke kanaka i ke kula."
  語順 (動詞 - 主語 - 目的語) と小辞 (ua・e … ana・ke … nei、i / iā、ʻo、o / a …) から語の役割を決め、格の枠で日本語に訳す。
  ʻokina・長音符の無い綴り (19世紀の本文) も読む。辞書は tools/build_hawaiian_dic.py (Wiktionary)
'''


def original(analysis):
    words = getattr(analysis, 'original', None) or analysis.surfaces
    text = ''
    for w in words:
        text += w if w in analyzer.PUNCTUATION and w not in '("“' else (' ' if text else '') + w
    return text


CASE_NAMES = {'Nom': '主格', 'Acc': '対格', 'Gen': '属格', 'Dat': '与格'}
ARTICLE_NOTES = {'ke': '冠詞「その」(単数)', 'ka': '冠詞「その」(単数)', 'nā': '冠詞「その」(複数)', 'he': '冠詞「ある〜」(不定)',
                 'kekahi': '冠詞「ある〜」(不定)', 'i': '目的語の印「〜を」', 'iā': '目的語の印「〜を」(名前・代名詞の前)'}


def _words_by_position(analysis):
    """元の語の位置 → 語 (名詞に掛けた冠詞・目的語の印も)"""
    out = {}

    def add(word):
        k = getattr(word, 'token_ix', None)
        if k is not None and k not in out:
            out[k] = word
        for m in getattr(word, 'modifiers', []):
            add(m)
    for w in analysis.words:
        add(w)
    return out


def token_rows(analysis):
    """元の語ごとの (表記, 説明, 注)。解析で語の列から外した小辞 (ua・ʻia …) と名詞に掛けた冠詞も出す"""
    rows = []
    by_ix = _words_by_position(analysis)
    notes = getattr(analysis, 'notes', {})
    for k, surface in enumerate(analysis.original):
        if surface in analyzer.PUNCTUATION:
            rows.append((surface, '', []))
            continue
        if k in notes:
            base, text = notes[k]
            rows.append((surface, '(%s) 小辞' % base, [text]))
            continue
        word = by_ix.get(k)
        relative = getattr(analysis, 'relative_words', {}).get(k)
        if word is None and relative is not None:   # 関係節の語
            w, head = relative
            item = w.items[0]
            rows.append((surface, '(%s) %s%s' % (item.attrib('base') or surface, 'v.' if item.pos == 'verb' else '',
                                                (item.ja or '').split(',')[0]),
                         ['関係節の語 (%s に掛かる)' % head.surface]))
            continue
        if word is None or not word.items:
            rows.append((surface, '(?)', []))
            continue
        item = word.items[0]
        if item.pos == 'article':
            base = item.attrib('base') or surface
            rows.append((surface, '(%s) 小辞' % base, [ARTICLE_NOTES.get(base, '冠詞') + ' (後ろの名詞に掛かる。訳さない)']))
            continue
        detail = '(%s) %s%s' % (item.attrib('base') or surface,
                                {'verb': 'v.', 'pronoun': 'pron.', 'adj': 'a.', 'preposition': 'prep.'}.get(item.pos, ''),
                                (item.ja or '').split(',')[0])
        cases = sorted({c[0] for c in (item._ or [])}, key=list(CASE_NAMES).index) if item._ else []
        if cases:
            detail += ' [%s%s]' % ('|'.join(CASE_NAMES.get(c, c) for c in cases),
                                   '.複数' if any(c[1] == 'pl' for c in item._) else '')
        extra = []
        if item.pos == 'verb':
            extra.append({'perfect': '完了', 'future': '未完了・未来', 'progressive': '進行'}.get(item.attrib('tense'), '現在') +
                         ('・受け身' if item.attrib('voice') == 'passive' else '') +
                         ('・命令' if item.attrib('mood') == 'imperative' else ''))
        if item.attrib('possessive') and item.attrib('class'):
            extra.append('所有の語 (%s 類)' % item.attrib('class'))
        if getattr(word, 'focus', False):
            extra.append('ʻo の句 (主題「は」)')
        rows.append((surface, detail, extra))
    return rows


def render(analysis, options):
    from dragoman.core import render as core_render
    if options.show_word_detail:
        core_render.render_tokens(token_rows(analysis))
    core_render.render_analysis(analysis, show_word_detail=False)


def speech_text(analysis, options):
    """音読: 解析で選んだ読みの綴りを音素の列に (ʻokina を [ʔ] に。hawaiian/phonology.py)"""
    from . import phonology
    return phonology.espeak_words(analyzer.spelled(analysis))


def available():
    return None if dictionary.available() else 'no Hawaiian dictionary (python3 tools/build_hawaiian_dic.py)'


COMMAND = Command(lang='haw', name='ハワイ語', analyzer=analyzer, dictionary=dictionary, available=available,
                  usage=USAGE, header=lambda a, o: original(a), speech_text=speech_text, render=render,
                  descendant_langs=('en',), speech_lang='haw')
