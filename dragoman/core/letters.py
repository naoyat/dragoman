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
# 慣用の名前の表 (CONVENTIONAL: ة → ta marbuta、λ → lambda) か Unicode の名前から (DEVANAGARI VOWEL SIGN I → 母音記号 i)。その言語での
# 呼び名の表があれば (core/letter_names.py) 下に添える (ب → باء bāʾ、ㄱ → 기역 giyeok)
#
import html
import re
import unicodedata

ZWJ = '‍'
# 図にする文字 (ラテン文字・漢字・かなは図にしない)
COMPLEX = re.compile('[Ͱ-ϿЀ-ӿἀ-῿֐-ࣿऀ-෿฀-࿿က-႟'
                     'ᄀ-ᇿ᠀-᢯가-힯יִ-﷿ﹰ-﻿]')
# つなげて書く文字 (凡例の字を語の中の形にする): アラビア文字・シリア文字・ンコ文字・モンゴル文字
JOINING = re.compile('[؀-ࣿ܀-ݏ߀-߿᠀-᢯ﭐ-﷿ﹰ-﻿]')
# 右 (前) の字にだけつながる字 (後ろの字につながらない)
RIGHT_JOINING = set('اأإآٱدذرزوؤةژڈڑےۀەۇۆۈۋڕۊۉ')
VIRAMAS = set('्্੍્୍்్್്්ฺ྄္')
MONGOLIAN = re.compile('[᠀-᢯]')
COLORS = 8
# Unicode の名前の部分 → 日本語の添え書き
KINDS = [('SMALL LETTER ', ''), ('CAPITAL LETTER ', '大文字 '), ('VOWEL SIGN ', '母音記号 '),
         ('SUBJOINED LETTER ', '下に付く '), ('LETTER ', ''), ('POINT ', '点 '), ('SIGN ', '記号 '), ('MARK ', '記号 '),
         ('CHOSEONG ', '初声 '), ('JUNGSEONG ', '中声 '), ('JONGSEONG ', '終声 ')]
SCRIPTS = ('GREEK', 'CYRILLIC', 'COMBINING GREEK', 'COMBINING', 'ARABIC', 'HEBREW', 'SYRIAC', 'THAANA', 'DEVANAGARI',
           'BENGALI', 'GURMUKHI', 'GUJARATI', 'ORIYA', 'TAMIL', 'TELUGU', 'KANNADA', 'MALAYALAM', 'SINHALA', 'THAI', 'LAO',
           'TIBETAN', 'MYANMAR', 'MONGOLIAN', 'HANGUL')
JOINERS = '‌‍᠋᠌᠍᠏'   # 前の字に付ける制御の字 (ZWNJ・ZWJ・字形の選択の記号)
SPECIAL = {'‌': 'ZWNJ (つなげない)', '‍': 'ZWJ (つなげる)', '᠎': '母音分離記号', ' ': '狭い空白',
           '᠋': '字形の選択 1', '᠌': '字形の選択 2', '᠍': '字形の選択 3', '᠏': '字形の選択 4'}


# Unicode の綴りの名前を慣用の名前に (λ: lamda → lambda、е: ie → ye、ӧ・ү …)。小文字で引く
CONVENTIONAL = {
    'λ': 'lambda', '\u0313': 'smooth breathing', '\u0314': 'rough breathing', '\u0342': 'circumflex',
    '\u0345': 'iota subscript',
    'е': 'ye', 'ё': 'yo', 'г': 'ge', 'х': 'kha', 'ы': 'yery', 'й': 'short i', 'ө': 'ö', 'ү': 'ü',
    # ヘブライ文字 (呼び名の転写と同じ綴りに: het → ḥet、dagesh or mapiq → dagesh)
    'ח': 'ḥet', 'ט': 'ṭet', '\u05b0': '点 shva', '\u05b1': '点 ḥataf segol', '\u05b2': '点 ḥataf pataḥ',
    '\u05b3': '点 ḥataf qamats', '\u05b4': '点 ḥiriq', '\u05b7': '点 pataḥ', '\u05b9': '点 ḥolam',
    '\u05ba': '点 ḥolam ḥaser', '\u05bc': '点 dagesh',
    # アラビア文字 (Unicode の綴り beh・jeem・teh marbuta → 慣用の ba・jim・ta marbuta。ペルシア語・ウルドゥー語の字は
    # その言語の名前: keheh → kaf、heh doachashmee → do-chashmi he)
    'ا': 'alif', 'ب': 'ba', 'ت': 'ta', 'ث': 'tha', 'ج': 'jim', 'ح': 'ḥa', 'خ': 'kha', 'د': 'dal', 'ذ': 'dhal',
    'ر': 'ra', 'ز': 'zay', 'س': 'sin', 'ش': 'shin', 'ص': 'ṣad', 'ض': 'ḍad', 'ط': 'ṭa', 'ظ': 'ẓa', 'ع': 'ʿayn',
    'غ': 'ghayn', 'ف': 'fa', 'ق': 'qaf', 'ك': 'kaf', 'ل': 'lam', 'م': 'mim', 'ن': 'nun', 'ه': 'ha', 'و': 'waw',
    'ي': 'ya', 'ء': 'hamza', 'ة': 'ta marbuta', 'ى': 'alif maqsura', 'أ': 'alif with hamza above',
    'إ': 'alif with hamza below', 'آ': 'alif madda', 'ؤ': 'waw with hamza', 'ئ': 'ya with hamza', 'ٱ': 'alif wasla',
    'پ': 'pe', 'چ': 'che', 'ژ': 'zhe', 'ک': 'kaf', 'گ': 'gaf', 'ی': 'ye', 'ٹ': 'ṭe', 'ڈ': 'ḍal', 'ڑ': 'ṛe',
    'ں': 'nun ghunna', 'ھ': 'do-chashmi he', 'ہ': 'gol he', 'ے': 'bari ye', 'ۓ': 'bari ye with hamza',
    '\u064e': 'fatḥa', '\u064f': 'ḍamma', '\u0650': 'kasra', '\u064b': 'tanwin fatḥ', '\u064c': 'tanwin ḍamm',
    '\u064d': 'tanwin kasr', '\u0652': 'sukun', '\u0651': 'shadda', '\u0654': 'hamza above',
    '\u0653': 'madda above', '\u0670': 'dagger alif', '\u0640': 'tatwil',
    # チベット文字 (Wylie の綴り: -a → 'a、vowel sign aa → long ā)
    'འ': "'a (a chung)", '\u0f71': 'long ā (a chung below)', '\u0f84': 'virama (srog med)',
    '\u0f7e': 'anusvara (rjes su nga ro)', '\u0f7f': 'visarga (rnam bcad)',
}
# ハングルの字母の名前 (Unicode の綴り KIYEOK・CIEUC → 改訂ローマ字の呼び名 giyeok・jieut。letter_names.HANGUL)
JAMO_KINDS = [('HANGUL CHOSEONG ', '初声 '), ('HANGUL JUNGSEONG ', '中声 '), ('HANGUL JONGSEONG ', '終声 '),
              ('HANGUL LETTER ', '')]


def unicode_label(ch):
    """字の英語の名前: 慣用の名前の表 (ة → ta marbuta) か、Unicode の名前から (DEVANAGARI SIGN VISARGA → 記号 visarga)"""
    if ch in SPECIAL:
        return SPECIAL[ch]
    if ch.lower() in CONVENTIONAL:
        return ('大文字 ' if ch != ch.lower() else '') + CONVENTIONAL[ch.lower()]
    from .letter_names import IAST, MATRAS, HANGUL
    for prefix, kind in JAMO_KINDS:
        key = unicodedata.name(ch, '')[len(prefix):]
        if unicodedata.name(ch, '').startswith(prefix) and key in HANGUL:
            return kind + HANGUL[key][1]
    if ch in IAST:   # デーヴァナーガリーは IAST で (ढ → ḍha。Unicode の名前の ddha でなく)
        return IAST[ch]
    if ch in MATRAS:
        return '母音記号 ' + IAST[MATRAS[ch]]
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
        attach = out and (cat.startswith('M') or ch in JOINERS or
                          out[-1][-1] in VIRAMAS)
        if attach:
            out[-1] += ch
        else:
            out.append(ch)
    return out


def _parts(cluster):
    """塊の部品 (合成済みの字は分解して: ハングルの音節は字母に、ἄ は α + ̓ + ́、أ は ا + ٔ)"""
    return list(unicodedata.normalize('NFD', cluster))


def _joins_left(cluster):
    base = cluster[0]
    return bool(JOINING.match(base)) and base not in RIGHT_JOINING and base not in '᠎  ' and \
        unicodedata.category(base).startswith('L') and '‌' not in cluster   # ZWNJ の後ろはつなげない (می‌روم)


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


def _native_html(native, ch, word=''):
    """その言語での字の呼び名 (呼び名の字と転写: باء bāʾ)"""
    found = native(ch, word) if native else None
    if not found:
        return ''
    script, roman = found
    return '<span class="ln"><bdi>%s</bdi> %s</span>' % (html.escape(script), html.escape(roman))


def word_html(word, label=None, native=None):
    """語の図: 塊ごとに色を変えた語と、同じ色の凡例 (塊の字と、部品ごとの字と名前、その言語での呼び名)"""
    label = label or (lambda ch, w: unicode_label(ch))
    seq = clusters(word)
    colored = ''.join('<span class="l%d">%s</span>' % (k % COLORS, html.escape(c)) for k, c in enumerate(seq))
    cells = []
    for k, c in enumerate(seq):
        parts = _parts(c)
        if len(parts) == 1:   # 1字の塊は名前だけ
            names = '<span class="lp">%s</span>%s' % (html.escape(label(parts[0], word)), _native_html(native, parts[0], word))
        else:
            names = ''.join('<span class="lp"><span class="lc">%s</span>%s</span>%s'
                            % (html.escape(_carrier(p)), html.escape(label(p, word)), _native_html(native, p, word))
                            for p in parts)
        form = _carrier(c) if unicodedata.category(c[0]).startswith('M') else _form(seq, k)
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


WORD = re.compile('[^\\s.,;:!?"“”«»()\\[\\]、。،؛؟۔।॥་།]+')
BIDI = re.compile('[‎‏‪-‮⁦-⁩]')   # 方向の制御の文字 (図に載せない)
RTL = re.compile('[֐-ࣿיִ-﷿ﹰ-﻿]')
ARABIC_MARK = re.compile('[ؐ-ًؚ-ٰٟۖ-ۭ࣓-ࣿ]')


def words_of(text):
    """文の語 (句読点・空白・チベット文字の音節の区切りで分ける)"""
    return WORD.findall(text)


def part_html(words, label=None, lang=''):
    """文の「文字の図」の部品 (図にする文字の語だけ。同じ語は1度)"""
    seen = []
    for w in words:
        w = BIDI.sub('', w)
        if wanted(w) and w not in seen:
            seen.append(w)
    if not seen:
        return ''
    from .letter_names import native
    names = native(lang)
    return ('<div class="part letters"%s><div class="ttl">文字の図 (色は語の中の文字と対応。◌・ـ は前の字に付く記号)</div>'
            '<div class="lws">%s</div></div>' % (' lang="%s"' % lang if lang else '', ''.join(word_html(w, label, names) for w in seen)))
