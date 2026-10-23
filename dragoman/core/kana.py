#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 発音 (IPA の音素の列) → カタカナ (どの言語にも共通の規則。docs/katakana.md)
#
#   kana(['k', 'a', 'e', 's', 'a', 'r'])            → カエサル
#   kana(['s', 'e', 'l', 'iˑ', 'n'], long='phonetic') → セリーヌ   (long='phonemic' なら セリヌ)
#
# 発音に忠実に書く (慣用の表記には寄せない):
#   - 母音は段 (ア イ ウ エ オ) に寄せる: ɑ・æ → ア、ɛ・e → エ、ɪ・i → イ、ɔ・o → オ、ʊ・u・ɯ → ウ、y・ʏ → ユ (子音の後ろは「キュ」)、ɨ → ウ段 + ィ (ムィ)、
#     ø・œ → エ、ə → エ (あいまい母音は言語ごとの音素の列で綴りに近い母音にしておく)
#   - 長さ: ː (音素として長い母音) は「ー」。ˑ (実際に長く発音される母音: 強勢のある開音節など) は long='phonetic' のときだけ
#   - 子音: v → ヴ行、ʃ → シャ行、ʒ・dʒ → ジャ行、tʃ → チャ行、ts → ツァ行、θ → サ行、ð → ザ行、x・ç → ハ行、ɲ → ニャ行、
#     ɣ → ガ行、ʁ・ʀ・ɾ・r・l → ラ行 (区別しない)、ʔ は書かない
#   - [si]・[zi] は「スィ」「ズィ」([ʃi]・[ʒi] の「シ」「ジ」と分ける。si='シ' で慣用の「シ」「ジ」)、s・z + j は「スャ」「ズョ」
#   - 子音 + j + 母音は拗音 (キャ・ピュ)。子音 + w + 母音は「クァ」
#   - [wa] は「ワ」(wa='ウァ' で西洋古典学の慣習の「ウァ」: Minerva → ミネルワ / ミネルウァ)
#   - 重子音 (ː か同じ子音を2つ): 閉鎖音・摩擦音は「ッ」、n・m は「ン」、ほかは1つに
#   - 母音の続かない子音はウ段 (t・d は「ト・ド」、x・h は「フ」、ʃ は「シュ」、tʃ は「チ」、ʒ・dʒ は「ジ」)。n・ŋ・m (p・b の前) は「ン」
#
VOWELS = {'a': 'a', 'ɑ': 'a', 'æ': 'a', 'ɐ': 'a', 'ʌ': 'a', 'e': 'e', 'ɛ': 'e', 'ə': 'e', 'ø': 'e', 'œ': 'e',
          'i': 'i', 'ɪ': 'i', 'ɨ': 'ɨ', 'o': 'o', 'ɔ': 'o', 'ɒ': 'o', 'u': 'u', 'ʊ': 'u', 'ɯ': 'u',
          'y': 'y', 'ʏ': 'y'}
DAN = 'aiueo'
CENTRAL_I = 'ɨ'   # ロシア語の ы: ウ段 + 小さい「ィ」(крылья → クルィリヤ、мы → ムィ)。子音の無いときは「ウィ」
# 行: 子音 → 段ごとのカナ (y は「ュ」の段)
ROWS = {
    '':  {'a': 'ア', 'i': 'イ', 'u': 'ウ', 'e': 'エ', 'o': 'オ', 'y': 'ユ'},
    'k': {'a': 'カ', 'i': 'キ', 'u': 'ク', 'e': 'ケ', 'o': 'コ', 'y': 'キュ'},
    'g': {'a': 'ガ', 'i': 'ギ', 'u': 'グ', 'e': 'ゲ', 'o': 'ゴ', 'y': 'ギュ'},
    's': {'a': 'サ', 'i': 'スィ', 'u': 'ス', 'e': 'セ', 'o': 'ソ', 'y': 'シュ'},
    'z': {'a': 'ザ', 'i': 'ズィ', 'u': 'ズ', 'e': 'ゼ', 'o': 'ゾ', 'y': 'ジュ'},
    't': {'a': 'タ', 'i': 'ティ', 'u': 'トゥ', 'e': 'テ', 'o': 'ト', 'y': 'テュ'},
    'd': {'a': 'ダ', 'i': 'ディ', 'u': 'ドゥ', 'e': 'デ', 'o': 'ド', 'y': 'デュ'},
    'n': {'a': 'ナ', 'i': 'ニ', 'u': 'ヌ', 'e': 'ネ', 'o': 'ノ', 'y': 'ニュ'},
    'h': {'a': 'ハ', 'i': 'ヒ', 'u': 'フ', 'e': 'ヘ', 'o': 'ホ', 'y': 'ヒュ'},
    'f': {'a': 'ファ', 'i': 'フィ', 'u': 'フ', 'e': 'フェ', 'o': 'フォ', 'y': 'フュ'},
    'v': {'a': 'ヴァ', 'i': 'ヴィ', 'u': 'ヴ', 'e': 'ヴェ', 'o': 'ヴォ', 'y': 'ヴュ'},
    'p': {'a': 'パ', 'i': 'ピ', 'u': 'プ', 'e': 'ペ', 'o': 'ポ', 'y': 'ピュ'},
    'b': {'a': 'バ', 'i': 'ビ', 'u': 'ブ', 'e': 'ベ', 'o': 'ボ', 'y': 'ビュ'},
    'm': {'a': 'マ', 'i': 'ミ', 'u': 'ム', 'e': 'メ', 'o': 'モ', 'y': 'ミュ'},
    'r': {'a': 'ラ', 'i': 'リ', 'u': 'ル', 'e': 'レ', 'o': 'ロ', 'y': 'リュ'},
    'j': {'a': 'ヤ', 'i': 'イ', 'u': 'ユ', 'e': 'イェ', 'o': 'ヨ', 'y': 'ユ'},
    'w': {'a': 'ウァ', 'i': 'ウィ', 'u': 'ウ', 'e': 'ウェ', 'o': 'ウォ', 'y': 'ウュ'},
    'ʃ': {'a': 'シャ', 'i': 'シ', 'u': 'シュ', 'e': 'シェ', 'o': 'ショ', 'y': 'シュ'},
    'ʒ': {'a': 'ジャ', 'i': 'ジ', 'u': 'ジュ', 'e': 'ジェ', 'o': 'ジョ', 'y': 'ジュ'},
    'tʃ': {'a': 'チャ', 'i': 'チ', 'u': 'チュ', 'e': 'チェ', 'o': 'チョ', 'y': 'チュ'},
    'ts': {'a': 'ツァ', 'i': 'ツィ', 'u': 'ツ', 'e': 'ツェ', 'o': 'ツォ', 'y': 'ツュ'},
    'ɲ': {'a': 'ニャ', 'i': 'ニ', 'u': 'ニュ', 'e': 'ニェ', 'o': 'ニョ', 'y': 'ニュ'},
    'kw': {'a': 'クァ', 'i': 'クィ', 'u': 'ク', 'e': 'クェ', 'o': 'クォ', 'y': 'クュ'},
    'gw': {'a': 'グァ', 'i': 'グィ', 'u': 'グ', 'e': 'グェ', 'o': 'グォ', 'y': 'グュ'},
}
for _key, _row in ROWS.items():
    _row[CENTRAL_I] = 'ウィ' if _key in ('', 'w') else _row['u'] + 'ィ'
# 子音の記号の読み替え (行の表に無い子音 → 近い行)
CONSONANTS = {'dʒ': 'ʒ', 'dz': 'z', 'θ': 's', 'ð': 'z', 'x': 'h', 'ç': 'h', 'χ': 'h', 'ħ': 'h', 'ɦ': 'h', 'ɸ': 'f',
              'β': 'b', 'ɣ': 'g', 'ʁ': 'r', 'ʀ': 'r', 'ɾ': 'r', 'ɹ': 'r', 'l': 'r', 'ɫ': 'r', 'ʎ': 'r', 'ŋ': 'N',
              'ɡ': 'g', 'q': 'k', 'ɕ': 'ʃ', 'ʂ': 'ʃ', 'ʑ': 'ʒ', 'ʐ': 'ʒ', 'tɕ': 'tʃ', 'ʈʂ': 'tʃ', 'c': 'k', 'ɟ': 'g',
              'ʋ': 'v', 'ɥ': 'j'}
# 拗音にする行 (子音 + j + 母音): 行の「イ段」+ 小さいャュェョ
YOON = {'a': 'ャ', 'u': 'ュ', 'o': 'ョ', 'e': 'エ', 'y': 'ュ'}   # e は小書きにしない (ピエール・ジュリエット)
# 母音の続かない子音
CODA = {'k': 'ク', 'g': 'グ', 's': 'ス', 'z': 'ズ', 't': 'ト', 'd': 'ド', 'n': 'ン', 'N': 'ン', 'h': 'フ', 'f': 'フ',
        'v': 'ヴ', 'p': 'プ', 'b': 'ブ', 'm': 'ム', 'r': 'ル', 'j': 'イ', 'w': 'ウ', 'ʃ': 'シュ', 'ʒ': 'ジ', 'tʃ': 'チ',
        'ts': 'ツ', 'ɲ': 'ニュ',
        'k̚': 'ク', 't̚': 'ッ', 'p̚': 'プ', 'm̚': 'ム', 'ɭ': 'ル', 'ɴ': 'ン'}   # 韓国語のパッチム (内破音・ㄹ・ㅇ)
SOKUON = {'p', 'b', 't', 'd', 'k', 'g', 's', 'f', 'z', 'ʃ', 'tʃ', 'ts', 'h', 'v', 'ʒ'}
LONG = 'ː'
HALF_LONG = 'ˑ'
IGNORE = {'ˈ', 'ˌ', '.', 'ʔ', '-', '‿', 'ʰ'}
WORD_BREAK = ' '   # 語の区切り (拗音・重子音をまたがない)


AFFRICATES = ('tʃ', 'dʒ', 'ts', 'dz', 'tɕ', 'dʑ', 'ʈʂ', 'ɖʐ', 'pf')
COMBINING = '\u0327\u0303\u032a\u0329\u032f\u0325\u0324\u031e\u031d\u0308\u0361'   # 鼻母音・歯音・音節・非音節 …
MODIFIERS = 'ʰʲʷʱˠˤ'


def split_ipa(text):
    """IPA の文字列 → 音素の列 (ɛmanyˈɛl → ['ɛ', 'm', 'a', 'n', 'y', 'ˈ', 'ɛ', 'l'])。結合文字・長さ ː ˑ・ʰ などは前の音素に、
    破擦音 (tʃ・dʒ・ts …) は1つに、空白は語の区切り"""
    import unicodedata
    text = unicodedata.normalize('NFD', text).replace('\u0361', '')
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            if out and out[-1] != WORD_BREAK:
                out.append(WORD_BREAK)
            i += 1
            continue
        if (ch in COMBINING or ch in MODIFIERS or ch in (LONG, HALF_LONG)) and out and out[-1] != WORD_BREAK:
            out[-1] += ch
            i += 1
            continue
        two = text[i:i + 2]
        if two in AFFRICATES:
            out.append(two)
            i += 2
            continue
        out.append(ch)
        i += 1
    import unicodedata as u
    return [u.normalize('NFC', p) for p in out]


def _vowel(ph):
    """母音の音素 → (段, 長さの印) / None"""
    import unicodedata
    ph = unicodedata.normalize('NFD', ph)   # 合成済みの鼻母音 (ã) も母音 + 鼻音の印に
    base = ph.rstrip(LONG + HALF_LONG).replace('\u0303', '')   # 鼻母音の印は外す (後ろに「ン」)
    if base in VOWELS:
        return VOWELS[base], ph[len(base):] if ph.startswith(base) else ''
    return None


def _nasal(ph):
    """鼻母音 (ɑ̃・ɛ̃) は母音の後ろに「ン」"""
    import unicodedata
    return 'ン' if ph and '\u0303' in unicodedata.normalize('NFD', ph) else ''


def _raw(ph):
    return ph.rstrip(LONG).replace('ʰ', '').replace('ʲ', '')


def _consonant(ph):
    """子音の音素 → (行の鍵, 重子音か)"""
    base = _raw(ph)
    return CONSONANTS.get(base, base), ph.endswith(LONG)


def kana(phonemes, long='phonemic', wa='ワ', final_sokuon=False, si='スィ', liquid_sokuon=False, labial_glide=False,
         oe='エ', accent=None, small=None, kobun=None):
    """IPA の音素の列 (または IPA の文字列) → カタカナ。long='phonemic' なら ː だけ「ー」、'phonetic' なら ˑ も「ー」。
    wa は [wa] の書き方 (「ワ」か「ウァ」)。si は [si]・[zi] の書き方 (「スィ」「ズィ」か、慣用の「シ」「ジ」)。final_sokuon なら、短い母音の後ろの語末の無声閉鎖音の前に「ッ」
    (Juliette → ジュリエット。日本語の耳に近い書き方。ラテン語の amat は「アマト」のまま)。liquid_sokuon なら重子音の l・r も
    「ッ」(フィンランド語・トルコ語の長い子音: Ville → ヴィッレ)。labial_glide なら子音 + w + 母音をウ段 + 小さい母音
    (韓国語: 화 → ファ、뒤 → トゥィ。既定では k・g だけ: クァ)。oe は [ø]・[œ] の段 (「エ」: Niinistö → ニーニステ、
    「オ」: ニーニスト)。accent は英語の設定 (english/katakana.py が使う。ここでは使わない)"""
    if isinstance(phonemes, str):
        phonemes = split_ipa(phonemes)
    if oe == 'オ':   # [ø]・[œ] をオ段に (印はそのまま: øː → oː)
        phonemes = ['o' + p[1:] if p[:1] in ('ø', 'œ') else p for p in phonemes]
    rows = ROWS if wa == 'ウァ' else dict(ROWS, w=dict(ROWS['w'], a=wa))
    if si == 'シ':
        rows = dict(rows, s=dict(rows['s'], i='シ'), z=dict(rows['z'], i='ジ'))
    if WORD_BREAK in phonemes:   # 語ごとに書いてつなぐ (Pāx Jūlia の s + j を「シュ」にしない)
        words, current = [], []
        for p in list(phonemes) + [WORD_BREAK]:
            if p == WORD_BREAK:
                if current:
                    words.append(kana(current, long, wa, final_sokuon, si, liquid_sokuon, labial_glide, oe))
                current = []
            else:
                current.append(p)
        return ''.join(words)
    phs = [p for p in phonemes if p and p not in IGNORE]
    marks = (LONG, HALF_LONG) if long == 'phonetic' else (LONG,)

    def lengthen(length):
        return 'ー' if length and any(m in length for m in marks) else ''

    out = []
    i = 0
    while i < len(phs):
        ph = phs[i]
        v = _vowel(ph)
        if v is not None:
            dan, length = v
            out.append(rows[''][dan] + lengthen(length) + _nasal(ph))
            i += 1
            continue
        consonant, geminate = _consonant(ph)
        nxt = phs[i + 1] if i + 1 < len(phs) else None
        # 同じ子音を2つ並べた重子音 (t t → tː)。読み替える前の音素で比べる (r と l は別の子音)
        if nxt is not None and _vowel(nxt) is None and _raw(nxt) == _raw(ph) and consonant not in ('j', 'w'):
            geminate = True
            i += 1
            nxt = phs[i + 1] if i + 1 < len(phs) else None
        # kw・gw (+ 母音)
        if consonant in ('k', 'g') and nxt == 'w' and i + 2 < len(phs) and _vowel(phs[i + 2]) is not None:
            consonant += 'w'
            i += 1
            nxt = phs[i + 1]
        if labial_glide and consonant in rows and consonant not in ('', 'j', 'w', 'kw', 'gw') and nxt == 'w' and \
                i + 2 < len(phs) and _vowel(phs[i + 2]) is not None and _vowel(phs[i + 2])[0] in 'aieo':
            dan, length = _vowel(phs[i + 2])
            out.append(('ッ' if geminate and consonant in SOKUON else '') + rows[consonant]['u'] +
                       {'a': 'ァ', 'i': 'ィ', 'e': 'ェ', 'o': 'ォ'}[dan] + lengthen(length))
            i += 3
            continue
        if geminate:
            if consonant in SOKUON:
                out.append('ッ')
            elif consonant in ('n', 'm', 'N'):
                out.append('ン')
            elif liquid_sokuon and consonant == 'r':
                out.append('ッ')
        # 子音 + j + 母音 → 拗音 (キャ・シュ・ヴィェ)
        if nxt == 'j' and consonant not in ('j', 'w', '') and consonant in rows and i + 2 < len(phs) and \
                _vowel(phs[i + 2]) is not None:
            dan, length = _vowel(phs[i + 2])
            stem = rows[consonant]['i']
            if len(stem) == 2 and dan in ('a', 'u', 'o', 'y'):
                stem = stem[0]   # スィ・ヴィ・フィ・ティ + j は「スャ」「ヴョ」「フュ」「テュ」(シャ・ショは [ʃ])
            sokuon = final_sokuon and not length and i + 4 == len(phs) and _consonant(phs[i + 3])[0] in ('p', 't', 'k')
            out.append((stem + YOON[dan] if dan in YOON else stem) + lengthen(length) + _nasal(phs[i + 2]) +
                       ('ッ' if sokuon else ''))
            i += 3
            continue
        v = _vowel(nxt) if nxt is not None else None
        if v is not None and consonant in rows:
            dan, length = v
            # 語末の無声閉鎖音の前の短い母音の後ろに「ッ」(final_sokuon: Juliette → ジュリエット)
            sokuon = final_sokuon and not length and not _nasal(nxt) and i + 3 == len(phs) and \
                _consonant(phs[i + 2])[0] in ('p', 't', 'k')
            out.append(rows[consonant][dan] + lengthen(length) + _nasal(nxt) + ('ッ' if sokuon else ''))
            i += 2
        elif v is not None and consonant == 'N':
            out.append('ン' + rows['g'][v[0]] + lengthen(v[1]))   # 音節の頭の ŋ はガ行 (ンガ)
            i += 2
        elif consonant == 'm' and nxt is not None and _consonant(nxt)[0] in ('p', 'b'):
            out.append('ン')   # Pompēius → ポンペーイウス
            i += 1
        else:
            out.append(CODA.get(consonant, ''))
            i += 1
    return ''.join(out)


def text_words(text):
    """文 → 語の列 (前後の句読点を除く。文字の無い語は除く)"""
    words = [w.strip('.,;:!?()[]«»„“”"\'‘’—–…') for w in text.split()]
    return [w for w in words if any(c.isalpha() for c in w)]
