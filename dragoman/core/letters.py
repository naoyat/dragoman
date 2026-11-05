#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ノートの「文字の図」: つながって書く文字・字を組み合わせて書く文字の語の、どの部分が何の文字かを色で示す
#
#   كتاب → ك (kaf) ت (teh) ا (alef) ب (beh) を1字ずつ色を変えて、つながったままの語と、同じ色の凡例 (語の中の形) に
#   स्ति → स्ति を1つの塊 (字の塊の中は色を分けられない) として、凡例で स (sa) ् (virama) त (ta) ि (母音記号 i) に分ける
#
# 塊: 文字 + 後ろの結合記号 (母音記号・点・字形の選択の記号)。ヴィラーマ (्) の後ろの子音は同じ塊に (結合文字)。
# ハングルの音節は字母 (初声・中声・終声) に分ける。凡例の字はアラビア文字・モンゴル文字などのつなげて書く文字なら
# ゼロ幅接合子 (ZWJ) で語の中の形 (語頭・語中・語末) にする。字の名前は言語ごとの関数 (label) が無ければ
# Unicode の名前から (ARABIC LETTER TEH MARBUTA → teh marbuta、DEVANAGARI VOWEL SIGN I → 母音記号 i)
#
import html
import re
import unicodedata

ZWJ = '‍'
# 図にする文字 (ラテン文字・キリル文字・ギリシア文字・漢字・かなは図にしない)
COMPLEX = re.compile('[֐-ࣿऀ-෿฀-࿿က-႟ᄀ-ᇿ᠀-᢯'
                     '가-힯יִ-﷿ﹰ-﻿]')
# つなげて書く文字 (凡例の字を語の中の形にする): アラビア文字・シリア文字・ンコ文字・モンゴル文字
JOINING = re.compile('[؀-ࣿ܀-ݏ߀-߿᠀-᢯ﭐ-﷿ﹰ-﻿]')
# 右 (前) の字にだけつながる字 (後ろの字につながらない)
RIGHT_JOINING = set('اأإآٱدذرزوؤةژڈڑےۀەۇۆۈۋڕۆۊۉآأإا')
VIRAMAS = set('्্੍્୍்్್്්ฺ྄္')
MONGOLIAN = re.compile('[᠀-᢯]')
COLORS = 8
# Unicode の名前の部分 → 日本語の添え書き
KINDS = [('VOWEL SIGN ', '母音記号 '), ('SUBJOINED LETTER ', '下に付く '), ('LETTER ', ''), ('POINT ', '点 '),
         ('SIGN ', '記号 '), ('MARK ', '記号 '), ('CHOSEONG ', '初声 '), ('JUNGSEONG ', '中声 '), ('JONGSEONG ', '終声 ')]
SCRIPTS = ('ARABIC', 'HEBREW', 'SYRIAC', 'THAANA', 'DEVANAGARI', 'BENGALI', 'GURMUKHI', 'GUJARATI', 'ORIYA', 'TAMIL',
           'TELUGU', 'KANNADA', 'MALAYALAM', 'SINHALA', 'THAI', 'LAO', 'TIBETAN', 'MYANMAR', 'MONGOLIAN', 'HANGUL')
SPECIAL = {'‌': 'ZWNJ (つなげない)', '‍': 'ZWJ (つなげる)', '᠎': '母音分離記号', ' ': '狭い空白',
           '᠋': '字形の選択 1', '᠌': '字形の選択 2', '᠍': '字形の選択 3', '᠏': '字形の選択 4'}


def unicode_label(ch):
    """Unicode の名前からの字の名前 (ARABIC LETTER TEH MARBUTA → teh marbuta、DEVANAGARI SIGN VIRAMA → 記号 virama)"""
    if ch in SPECIAL:
        return SPECIAL[ch]
    name = unicodedata.name(ch, '')
    for script in SCRIPTS:
        if name.startswith(script + ' '):
            name = name[len(script) + 1:]
            break
    for key, ja in KINDS:
        if name.startswith(key):
            return ja + name[len(key):].lower()
    return name.lower() or 'U+%04X' % ord(ch)


def clusters(word):
    """語 → 塊の列 (文字 + 結合記号。ヴィラーマの後ろの子音は同じ塊に)"""
    out = []
    for ch in word:
        cat = unicodedata.category(ch)
        attach = out and (cat.startswith('M') or ch in '‌‍᠋᠌᠍᠏' or
                          out[-1][-1] in VIRAMAS)
        if attach:
            out[-1] += ch
        else:
            out.append(ch)
    return out


def _parts(cluster):
    """塊の部品 (ハングルの音節は字母に)"""
    if len(cluster) == 1 and '가' <= cluster <= '힣':
        return list(unicodedata.normalize('NFD', cluster))
    return list(cluster)


def _joins_left(cluster):
    base = cluster[0]
    return bool(JOINING.match(base)) and base not in RIGHT_JOINING and base not in '᠎  ' and \
        unicodedata.category(base).startswith('L')


def _form(seq, k):
    """凡例の字: つなげて書く文字なら前後の字とのつながりを ZWJ で示す (語の中の形)"""
    c = seq[k]
    if not JOINING.match(c[0]) or not unicodedata.category(c[0]).startswith('L'):
        return c
    before = ZWJ if k > 0 and _joins_left(seq[k - 1]) else ''
    after = ZWJ if k + 1 < len(seq) and _joins_left(c) and unicodedata.category(seq[k + 1][0]).startswith('L') else ''
    return before + c + after


def wanted(word):
    return bool(COMPLEX.search(word))


def word_html(word, label=None):
    """語の図: 塊ごとに色を変えた語と、同じ色の凡例 (塊の字と、部品ごとの字と名前)"""
    label = label or (lambda ch, w: unicode_label(ch))
    seq = clusters(word)
    colored = ''.join('<span class="l%d">%s</span>' % (k % COLORS, html.escape(c)) for k, c in enumerate(seq))
    cells = []
    for k, c in enumerate(seq):
        parts = _parts(c)
        if len(parts) == 1:   # 1字の塊は名前だけ
            names = '<span class="lp">%s</span>' % html.escape(label(parts[0], word))
        else:
            names = ''.join('<span class="lp"><span class="lc">%s</span>%s</span>'
                            % (html.escape(_carrier(p)), html.escape(label(p, word))) for p in parts)
        form = _carrier(c) if len(c) == 1 else _form(seq, k)
        cells.append('<span class="lk l%d"><span class="lf">%s</span>%s</span>' % (k % COLORS, html.escape(form), names))
    vertical = ' lv' if MONGOLIAN.search(word) else ''
    direction = ' dir="rtl"' if RTL.search(word) else ''
    return ('<div class="lw%s"><span class="lword"%s>%s</span><span class="lkeys"%s>%s</span></div>'
            % (vertical, direction, colored, direction, ''.join(cells)))


def _carrier(p):
    """結合記号を単独で見せる台: アラビア文字の記号はタトウィール (ـَ)、ほかは点線の丸 (◌ि)"""
    if not unicodedata.category(p[0]).startswith('M'):
        return p
    return ('ـ' if ARABIC_MARK.match(p) else '◌') + p


WORD = re.compile('[^\\s.,;:!?"“”«»()\\[\\]、。،؛؟।॥་།]+')
BIDI = re.compile('[‎‏‪-‮⁦-⁩]')   # 方向の制御の文字 (図に載せない)
RTL = re.compile('[֐-ࣿיִ-﷿ﹰ-﻿]')
ARABIC_MARK = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭ࣓-ࣿ]')


def words_of(text):
    """文の語 (句読点・空白・チベット文字の音節の区切りで分ける)"""
    return WORD.findall(text)


def part_html(words, label=None):
    """文の「文字の図」の部品 (図にする文字の語だけ。同じ語は1度)"""
    seen = []
    for w in words:
        w = BIDI.sub('', w)
        if wanted(w) and w not in seen:
            seen.append(w)
    if not seen:
        return ''
    return ('<div class="part letters"><div class="ttl">文字の図 (色は語の中の文字と対応。◌・ـ は前の字に付く記号)</div>'
            '<div class="lws">%s</div></div>' % ''.join(word_html(w, label) for w in seen))
