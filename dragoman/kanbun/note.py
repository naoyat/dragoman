#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ノート (--html・--pdf) の訓点付きの本文: 縦書きで、字の右に振り仮名 (ひらがな。ruby.py) とその下に送り仮名
# (カタカナ)、左下に返り点、再読文字の二度目の読みの送り仮名は左に
#
import html

from . import kundoku, ruby

# UD-Kanbun の返り点の記号 (漢文用の符号) → 普通の字 (字形の無いフォントでも出るように)
MARKS = dict(zip('㆑㆒㆓㆔㆕㆖㆗㆘㆙㆚㆛㆜㆝㆞㆟', 'レ一二三四上中下甲乙丙丁天地人'))
SMALL = 0.5    # 送り仮名・返り点の字の大きさ (本文の字に対して)
PUNCT = '、。，．！？'
COLUMN = 18    # 縦の列の高さ (本文の字の数)


def katakana(text):
    return ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in text)


def _okurigana(elems):
    """書き下しの要素の列 → {id(token): [右の送り仮名, 左の送り仮名]}。
    漢字の語は書き下しの形から字を除いた残り、助字の助動詞 (不 → ざる) は最初の仮名を字の読みとして除いた残り、
    助詞 (置き字 於 の に・より も) は前の語に。再読文字の二度目の読みは左に (將に…んとす の んと は前の用言に)"""
    out = {}
    prev = None   # 送り仮名の付く前の語

    def put(token, kana, left=False):
        if token is not None and kana:
            out.setdefault(id(token), ['', ''])[1 if left else 0] += kana

    seen = set()
    for e in kundoku._rendered(elems):
        if e.kind == 'punct' or not e.out:
            continue
        t = e.token
        if e.kind == 'particle' or t is None:
            put(prev, e.out)
            continue
        again = id(t) in seen   # 再読文字の二度目
        seen.add(id(t))
        if e.out.startswith(t.form):
            put(t, e.out[len(t.form):], left=again)
        elif again and e.out.startswith('んと'):
            put(prev, 'んと')
            put(t, e.out[2:], left=True)
        else:   # 字を仮名で読む助字 (不 → ず・ざる、可 → べから)
            put(t, e.out[1:], left=again)
        prev = t
    return out


def units(analysis):
    """字ごとの (字, 振り仮名, 右の送り仮名, 返り点, 左の送り仮名)。返り点は UD-Kanbun の返り点付きの白文から。
    振り仮名は JMdict の読みの表 (ja-readings.tsv) が無ければ出さない"""
    yomi = ruby.rubies(analysis) if ruby.available() else {}
    okuri = {}
    for elems in analysis.elems:
        okuri.update(_okurigana(elems))
    text = analysis.kaeriten
    pos = 0
    result = []
    for t in analysis.tokens:
        right, left = okuri.get(id(t), ['', ''])
        rubies = yomi.get(id(t), [])
        for k, ch in enumerate(t.form):
            while pos < len(text) and text[pos] != ch:   # 字の後ろの返り点
                if result:
                    result[-1][3] += MARKS.get(text[pos], text[pos])
                pos += 1
            pos += 1
            last = k == len(t.form) - 1
            result.append([ch, rubies[k] if k < len(rubies) else '', katakana(right) if last else '', '',
                           katakana(left) if last else ''])
    for c in text[pos:]:
        if result:
            result[-1][3] += MARKS.get(c, c)
    return [tuple(u) for u in result]


def html_of(analysis):
    """訓点付きの本文 (縦書き) の HTML。字の高さは送り仮名・返り点の長さに合わせて伸ばす"""
    cells = []
    total = 0
    for ch, yomi, right, marks, left in units(analysis):
        # 振り仮名は字の右 (2字までは字の中ほど)、送り仮名は字の下半分か振り仮名の後ろから、返り点は字の左下、
        # 左の送り仮名は返り点の下
        top = (1 - SMALL * len(yomi)) / 2 if len(yomi) <= 2 else 0
        start = max(0.5, top + SMALL * len(yomi) + 0.15) if yomi else 0.5   # 振り仮名との間を少し空ける
        height = max(0.6 if ch in PUNCT else 1.0, start + SMALL * len(right), 0.7 + SMALL * (len(marks) + len(left)))
        total += height + 0.08
        cells.append('<span class="kc" style="height:%.2fem"><span class="kj">%s</span>%s%s%s%s</span>'
                     % (height + 0.08, html.escape(ch),
                        '<span class="rb" style="top:%.2fem">%s</span>' % (top / SMALL, html.escape(yomi)) if yomi else '',
                        '<span class="ok" style="top:%.2fem">%s</span>' % (start / SMALL, html.escape(right))
                        if right else '',
                        '<span class="kt">%s</span>' % html.escape(marks) if marks else '',
                        '<span class="ol" style="top:%.2fem">%s</span>' % (1.4 + len(marks), html.escape(left))
                        if left else ''))
    # 1行 (縦の列) に収まれば1列で、長ければ COLUMN の高さで折り返す
    return ('<div class="part kunten" lang="ja"><div class="ttl">訓点</div><div class="kv" style="height:%.2fem">%s</div></div>'
            % (min(total + 0.1, COLUMN), ''.join(cells)))
