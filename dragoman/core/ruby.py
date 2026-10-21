#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ルビ (フリガナ) 用のカタカナ: 元の文の語ごとに、文字の範囲とその上に載せるカナ (カラオケの字幕などの外から呼ぶ口)
#
#   ruby("Les enfants sont arrivés.", "fr")
#   → [{"text": "Les", "start": 0, "end": 3, "kana": "レ"}, {"text": "enfants", "start": 4, "end": 11, "kana": "ザンファン"},
#      {"text": "sont", "start": 12, "end": 16, "kana": "ソン"}, {"text": "arrivés", "start": 17, "end": 24, "kana": "タリヴェ"},
#      {"text": ".", "start": 24, "end": 25, "kana": ""}]
#
# 語をまたぐ音 (フランス語のリエゾン・アンシェヌマン、ロシア語の母音の無い前置詞) は liaison で載せ方を選ぶ:
#   'next' (既定): 次の語に (レ / ザンファン、Il / y / a → イ / リ / ヤ)
#   'prev': 前の語に残す (レズ / アンファン)
#   'merge': つながった語をまとめて1つの区切りに (Les enfants → レザンファン)
# 句読点はカナを空にして区切りに残す (区切りの text をつなげば元の文に戻る。空白は区切りの間)。
# カナは発音に忠実なもの (dragoman の --kana と同じ規則と設定)。読みやすさのための崩しは呼ぶ側で
#
import importlib
import re

PUNCT = '.,;:!?…«»"“”„()[]{}—–¡¿、。・'
# 言語 → (モジュール, 語のカタカナの関数の名前)。語をまたぐ音を扱う言語は ruby_words (語の列 → (カナの列, つながり))
WORD_KANA = {
    'grc': ('dragoman.greek.katakana', 'katakana'),
    'sa': ('dragoman.sanskrit.katakana', 'katakana'), 'de': ('dragoman.german.katakana', 'katakana'),
    'fi': ('dragoman.finnish.katakana', 'katakana'),
    'tr': ('dragoman.turkish.katakana', 'katakana'), 'mn': ('dragoman.mongolian.katakana', 'katakana'),
    'ko': ('dragoman.korean.katakana', 'katakana'), 'haw': ('dragoman.hawaiian.phonology', 'katakana'),
    'ang': ('dragoman.oldenglish.phonology', 'katakana'),
}
RUBY_WORDS = {'fr': 'dragoman.french.katakana', 'en': 'dragoman.english.katakana', 'ru': 'dragoman.core.ruby', 'la': 'dragoman.core.ruby'}


def available(lang):
    return lang in WORD_KANA or lang in RUBY_WORDS


def tokens(text):
    """文 → [(text, start, end, 語か)]。語の前後の句読点は分ける (語の中のアポストロフィ・ハイフンはそのまま)"""
    out = []
    for m in re.finditer(r'\S+', text):
        s, e = m.start(), m.end()
        a, b = s, e
        while a < b and text[a] in PUNCT:
            a += 1
        while b > a and text[b - 1] in PUNCT:
            b -= 1
        for k in range(s, a):
            out.append((text[k], k, k + 1, False))
        if a < b:
            out.append((text[a:b], a, b, True))
        for k in range(b, e):
            out.append((text[k], k, k + 1, False))
    return out


def _word_kana(lang, words, liaison, options):
    """語の列 → (カナの列, 語の間でつながったか)"""
    if lang in RUBY_WORDS:
        module = importlib.import_module(RUBY_WORDS[lang])
        func = {'ru': russian_ruby_words, 'la': latin_ruby_words}.get(lang) or module.ruby_words
        return func(words, liaison=liaison, **options)
    module_name, name = WORD_KANA[lang]
    func = getattr(importlib.import_module(module_name), name)
    return [func(w, **options) for w in words], [False] * max(0, len(words) - 1)


def latin_ruby_words(words, liaison='next', **options):
    """ラテン語: 解析で選んだ読みの綴り (マクロン付き: 格の決まった Gallia・dīvīsa) から語ごとに (--kana と同じ)。
    解析の語の数が合わなければマクロンを推定して"""
    from dragoman.latin import latindic, analyzer, macronizer
    from dragoman.latin.katakana import katakana
    latindic.load()
    analysis = next(iter(analyzer.analyze_text(' '.join(words) + '.')), None)
    analysed = [w for w in (analysis.words if analysis else []) if re.search('[A-Za-zāēīōūȳ]', w.surface)]
    out = []
    for k, word in enumerate(words):
        spelling = None
        if len(analysed) == len(words):
            w = analysed[k]
            spelling = (w.items[0].attrib('surface') if w.items else None) or None
            for enclitic in ('que', 'ne', 've'):   # 後接語 (virumque の -que)
                if spelling and word.lower().endswith(enclitic) and not spelling.lower().endswith(enclitic) and \
                        len(word) > len(enclitic) + 1:
                    spelling += enclitic
                    break
        if not spelling:
            spelling = macronizer.macronize_text(word).strip() or word
        out.append(katakana(spelling, **options))
    return out, [False] * max(0, len(words) - 1)


# 母音の無い前置詞を次の語に続けるのは、次の語が母音で始まるときだけ (в Италии → ヴィターリイ)。子音で始まる語の前では
# 前置詞だけで読む (в Москве → ヴ / マスクヴェー、в театр → フ / チアトル: 次の語の頭の子音との有声・無声の同化は残す)。
# False にすると子音の前でも続ける (検討中: 2026-10-21)
SEPARATE_BEFORE_CONSONANT = True
RUSSIAN_VOWELS = 'аеёиоуыэюя'


def russian_ruby_words(words, liaison='next', **options):
    """ロシア語: 強勢を辞書から付けて読み、母音の無い前置詞 (в・к・с) は次の語と続けて読む ('next' なら前置詞の上は空で
    次の語に、'prev' なら前置詞だけの読み)。次の語が子音で始まるなら前置詞だけで読む (SEPARATE_BEFORE_CONSONANT)"""
    from dragoman.russian import morphology, katakana, script
    from dragoman.core.kana import CODA, CONSONANTS
    stressed = [morphology.stressed(w) for w in words]
    out, links = [], [False] * max(0, len(words) - 1)
    k = 0
    while k < len(words):
        plain = script.strip_stress(words[k]).lower()
        following = script.strip_stress(words[k + 1]).lower() if k + 1 < len(words) else ''
        if plain in ('в', 'к', 'с', 'б') and following and SEPARATE_BEFORE_CONSONANT and \
                following[:1] not in RUSSIAN_VOWELS:
            # 子音の前: 前置詞だけの読み (次の語の頭の子音で有声・無声を決める: в театр → フ)
            first = katakana.phonemes(stressed[k] + stressed[k + 1])[0]
            out.append(CODA.get(CONSONANTS.get(first, first), ''))
            k += 1
            continue
        if plain in ('в', 'к', 'с', 'б') and k + 1 < len(words):
            links[k] = True
            if liaison == 'prev':
                out.append(katakana.katakana(stressed[k], **options))
            else:
                out.append('')
                words_joined = stressed[k] + stressed[k + 1]
                out.append(katakana.katakana(words_joined, **options))
                k += 2
                continue
        else:
            out.append(katakana.katakana(stressed[k], **options))
        k += 1
    return out, links


def ruby(text, lang, liaison='next', **options):
    """文 → ルビの区切りの列 [{text, start, end, kana}] (上の説明)"""
    if not available(lang):
        raise ValueError('ルビのカタカナが無い言語: %s' % lang)
    toks = tokens(text)
    word_ix = [k for k, t in enumerate(toks) if t[3]]
    kanas, links = _word_kana(lang, [toks[k][0] for k in word_ix], liaison, options) if word_ix else ([], [])
    segments = [{'text': t[0], 'start': t[1], 'end': t[2], 'kana': ''} for t in toks]
    for n, k in enumerate(word_ix):
        segments[k]['kana'] = kanas[n]
    if liaison != 'merge':
        return segments
    # つながった語 (間に句読点の無いもの) をまとめる
    merged = []
    n = 0
    for k, seg in enumerate(segments):
        if k in word_ix:
            pos = word_ix.index(k)
            if merged and merged[-1].get('_link') and pos and word_ix[pos - 1] == k - 1:
                last = merged[-1]
                last['text'] = text[last['start']:seg['end']]
                last['end'] = seg['end']
                last['kana'] += seg['kana']
                last['_link'] = pos < len(links) and links[pos]
                continue
            merged.append(dict(seg, _link=pos < len(links) and links[pos]))
        else:
            merged.append(dict(seg))
    for seg in merged:
        seg.pop('_link', None)
    return merged
