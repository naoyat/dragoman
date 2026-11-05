#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語のノート (--html・--pdf) の部品: 伝統的なモンゴル文字の本文 (縦書き。列は左から右へ) と、
# 語ごとのキリル文字との対照の表 (キリル文字・その転写・伝統文字・その転写・出典・主な違い)
#
import html

from . import traditional


def _words(analysis):
    return getattr(analysis, 'traditional', None) or []


def html_of(analysis):
    words = _words(analysis)
    if not words:
        return ''
    text = ' '.join('<span class="%s">%s</span>' % ('g' if w['source'] == '推定' else 'w', html.escape(w['script']))
                    for w in words)
    rows = ''.join('<tr><td>%s</td><td>%s</td><td class="ms" lang="mn-Mong">%s</td><td>%s</td><td class="src">%s</td>'
                   '<td class="df">%s</td></tr>'
                   % (html.escape(w['cyrillic']), html.escape(traditional.cyrillic_latin(w['cyrillic'])),
                      html.escape(w['script']), html.escape(w['latin']), w['source'],
                      html.escape('、'.join(traditional.differences(w['cyrillic'], w['latin']))))
                   for w in words)
    return ('<div class="part mongol"><div class="ttl">モンゴル文字 (灰色は規則で推定した綴り)</div>'
            '<div class="mv" lang="mn-Mong">%s</div>'
            '<table><tr><th>キリル文字</th><th>転写</th><th>モンゴル文字</th><th>転写</th><th>出典</th><th>主な違い</th></tr>'
            '%s</table></div>' % (text, rows))


def lines(analysis, options):
    """端末の見出しの後ろの2行: 伝統文字 (横に並べる) と、その転写 (* は規則で推定した綴り)"""
    words = _words(analysis)
    if not words:
        return []
    return ['  モンゴル文字 %s' % ' '.join(w['script'] for w in words),
            '  転写         %s' % ' '.join(w['latin'] + ('*' if w['source'] == '推定' else '') for w in words)]
