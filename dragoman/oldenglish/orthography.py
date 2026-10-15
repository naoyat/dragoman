#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の綴り: 辞書を引く鍵と、綴りの揺れ
#
# 辞書 (Wiktionary) は長音符と口蓋音の点の付いた標準化した綴り (cyning・sēo・ġiefan・ċild) で、写本の翻刻は
# 長音符を書かず、þ と ð を区別せずに使う (onginneð = onginneþ)。鍵は長音符・点を除き、ð → þ、ƿ (ウィン) → w、
# 7・⁊ (ティロ式の and) → and にして小文字にしたもの。
#
# 辞書に無い綴りは、後期ウェストサクソン方言・アングリア方言などの揺れを1つずつ読み替えて引き直す
# (variants: hyran → hieran・hiran、mon → man、ald → eald、heofonas → heofenas …)
#
import re
import unicodedata

LETTERS = {'ð': 'þ', 'Ð': 'þ', 'Þ': 'þ', 'ƿ': 'w', 'Ƿ': 'w', 'ꝥ': 'þæt', 'Ꝥ': 'þæt', 'ǣ': 'æ', 'Ǣ': 'æ', 'Æ': 'æ',
           'ǽ': 'æ', 'ǝ': 'e', 'ſ': 's', 'ᵹ': 'g', 'Ᵹ': 'g'}
TIRONIAN = ('⁊', '7', '&')


def key(text):
    """照合用の鍵: 長音符・点・アクセントを除き、ð → þ、ƿ → w にして小文字に (Sēo → seo、ġiefan → giefan)"""
    if text in TIRONIAN:
        return 'and'
    text = ''.join(LETTERS.get(c, c) for c in text)
    nfd = unicodedata.normalize('NFD', text)
    return unicodedata.normalize('NFC', ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')).lower()


def lemma_key(text):
    """訳語の表の鍵: 長音符は残し、口蓋音の点を除き ð → þ にして小文字に (gōd「良い」と god「神」を分ける)"""
    text = ''.join(LETTERS.get(c, c) if c not in 'ǣǢ' else c for c in text)
    nfd = unicodedata.normalize('NFD', text)
    return unicodedata.normalize('NFC', ''.join(c for c in nfd if c not in '\u0307\u0301')).lower()


def is_old_english(text):
    """古英語らしい文字 (þ ð æ ƿ ġ ċ ǣ) を含むか"""
    return bool(re.search('[þðÞÐæÆƿǷġċĠĊǣǢ]', text))


# 綴りの揺れ (古い / 標準の綴り → 別の綴り)。左を右に読み替えて引き直す
VARIANTS = (
    ('(?<=[wh])ur', 'eor'), ('(?<=[wh])yr', 'eor'), ('(?<=w)or', 'eor'),   # wurþan・worþan = weorþan
    ('io', 'i'), ('eo', 'i'), ('y', 'i'),          # cliopian・cleopian = clipian
    ('y', 'ie'), ('y', 'i'), ('i', 'ie'), ('i', 'y'), ('ie', 'y'), ('ie', 'i'),   # hyran・hiran = hieran
    ('eo', 'io'), ('io', 'eo'), ('ea', 'a'), ('a', 'ea'), ('ea', 'e'), ('e', 'ea'), ('eo', 'e'),
    ('o(?=[nm])', 'a'), ('a(?=[nm])', 'o'),   # mon = man、lond = land
    ('æ', 'e'), ('e', 'æ'), ('æ', 'a'), ('a', 'æ'), ('e', 'i'), ('i', 'e'), ('u', 'o'), ('o', 'u'),
    ('k', 'c'), ('c', 'k'), ('uu', 'w'), ('ð', 'þ'), ('d', 'þ'), ('th', 'þ'),
    ('(?<=[aeiouyæ])(.)(?=\\1)', ''),          # 重子音を1つに (mann → man。tellan は辞書にある)
    ('(?<=[^aeiouyæ])$', '@'),                  # 語末の子音を重ねる (man → mann): @ は後で直前の文字に
    ('an$', 'on'), ('on$', 'an'), ('un$', 'on'), ('en$', 'on'), ('on$', 'en'), ('um$', 'on'), ('an$', 'um'),
    ('od$', 'ed'), ('ed$', 'od'), ('ode$', 'ede'), ('odon$', 'edon'),   # 弱変化の過去 (getimbrod = getimbred)
    ('a$', 'e'), ('e$', 'a'), ('es$', 'æs'), ('as$', 'es'),   # 後期の語尾の弱まり (lufodan = lufodon)
    ('^ge', ''), ('^i(?=[^aeiouy])', 'ge'), ('^y', 'ge'),  # 完了分詞の ge- (iseon・ywriten)
)
_VARIANTS = [(re.compile(a), b) for a, b in VARIANTS]


def _double_last(text):
    return text.replace('@', text[text.index('@') - 1]) if '@' in text else text


def variants(word, depth=1):
    """綴りの揺れを読み替えた鍵 (近いものから。depth=2 なら2か所まで)"""
    base = key(word)
    seen = {base}
    frontier = [base]
    for _ in range(depth):
        nxt = []
        for w in frontier:
            for pattern, repl in _VARIANTS:
                for m in pattern.finditer(w):
                    v = _double_last(w[:m.start()] + m.expand(repl) + w[m.end():])
                    if v and v not in seen:
                        seen.add(v)
                        nxt.append(v)
                        yield v
        frontier = nxt
