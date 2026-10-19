#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 発音 (IPA の音素の列) → カタカナ (どの言語にも共通の規則。docs/katakana.md)
#
#   kana(['k', 'a', 'e', 's', 'a', 'r'])            → カエサル
#   kana(['s', 'e', 'l', 'iˑ', 'n'], long='phonetic') → セリーヌ   (long='phonemic' なら セリヌ)
#
# 発音に忠実に書く (慣用の表記には寄せない):
#   - 母音は段 (ア イ ウ エ オ) に寄せる: ɑ・æ → ア、ɛ・e → エ、ɪ・i → イ、ɔ・o → オ、ʊ・u・ɯ → ウ、y・ʏ → ユ (子音の後ろは「キュ」)、
#     ø・œ → エ、ə → エ (あいまい母音は言語ごとの音素の列で綴りに近い母音にしておく)
#   - 長さ: ː (音素として長い母音) は「ー」。ˑ (実際に長く発音される母音: 強勢のある開音節など) は long='phonetic' のときだけ
#   - 子音: v → ヴ行、ʃ → シャ行、ʒ・dʒ → ジャ行、tʃ → チャ行、ts → ツァ行、θ → サ行、ð → ザ行、x・ç → ハ行、ɲ → ニャ行、
#     ɣ → ガ行、ʁ・ʀ・ɾ・r・l → ラ行 (区別しない)、ʔ は書かない
#   - 子音 + j + 母音は拗音 (キャ・シュ)。子音 + w + 母音は「クァ」
#   - 重子音 (ː か同じ子音を2つ): 閉鎖音・摩擦音は「ッ」、n・m は「ン」、ほかは1つに
#   - 母音の続かない子音はウ段 (t・d は「ト・ド」、x・h は「フ」、ʃ は「シュ」、tʃ は「チ」、ʒ・dʒ は「ジ」)。n・ŋ・m (p・b の前) は「ン」
#
VOWELS = {'a': 'a', 'ɑ': 'a', 'æ': 'a', 'ɐ': 'a', 'ʌ': 'a', 'e': 'e', 'ɛ': 'e', 'ə': 'e', 'ø': 'e', 'œ': 'e',
          'i': 'i', 'ɪ': 'i', 'ɨ': 'i', 'o': 'o', 'ɔ': 'o', 'ɒ': 'o', 'u': 'u', 'ʊ': 'u', 'ɯ': 'u',
          'y': 'y', 'ʏ': 'y'}
DAN = 'aiueo'
# 行: 子音 → 段ごとのカナ (y は「ュ」の段)
ROWS = {
    '':  {'a': 'ア', 'i': 'イ', 'u': 'ウ', 'e': 'エ', 'o': 'オ', 'y': 'ユ'},
    'k': {'a': 'カ', 'i': 'キ', 'u': 'ク', 'e': 'ケ', 'o': 'コ', 'y': 'キュ'},
    'g': {'a': 'ガ', 'i': 'ギ', 'u': 'グ', 'e': 'ゲ', 'o': 'ゴ', 'y': 'ギュ'},
    's': {'a': 'サ', 'i': 'シ', 'u': 'ス', 'e': 'セ', 'o': 'ソ', 'y': 'シュ'},
    'z': {'a': 'ザ', 'i': 'ジ', 'u': 'ズ', 'e': 'ゼ', 'o': 'ゾ', 'y': 'ジュ'},
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
# 子音の記号の読み替え (行の表に無い子音 → 近い行)
CONSONANTS = {'dʒ': 'ʒ', 'dz': 'z', 'θ': 's', 'ð': 'z', 'x': 'h', 'ç': 'h', 'χ': 'h', 'ħ': 'h', 'ɦ': 'h', 'ɸ': 'f',
              'β': 'b', 'ɣ': 'g', 'ʁ': 'r', 'ʀ': 'r', 'ɾ': 'r', 'ɹ': 'r', 'l': 'r', 'ɫ': 'r', 'ʎ': 'r', 'ŋ': 'N',
              'ɡ': 'g', 'q': 'k', 'ɕ': 'ʃ', 'ʂ': 'ʃ', 'ʑ': 'ʒ', 'ʐ': 'ʒ', 'tɕ': 'tʃ', 'ʈʂ': 'tʃ', 'c': 'k', 'ɟ': 'g',
              'ʋ': 'v', 'ɥ': 'j'}
# 拗音にする行 (子音 + j + 母音): 行の「イ段」+ 小さいャュェョ
YOON = {'a': 'ャ', 'u': 'ュ', 'o': 'ョ', 'e': 'ェ', 'y': 'ュ'}
# 母音の続かない子音
CODA = {'k': 'ク', 'g': 'グ', 's': 'ス', 'z': 'ズ', 't': 'ト', 'd': 'ド', 'n': 'ン', 'N': 'ン', 'h': 'フ', 'f': 'フ',
        'v': 'ヴ', 'p': 'プ', 'b': 'ブ', 'm': 'ム', 'r': 'ル', 'j': 'イ', 'w': 'ウ', 'ʃ': 'シュ', 'ʒ': 'ジ', 'tʃ': 'チ',
        'ts': 'ツ', 'ɲ': 'ニュ'}
SOKUON = {'p', 'b', 't', 'd', 'k', 'g', 's', 'f', 'z', 'ʃ', 'tʃ', 'ts', 'h', 'v', 'ʒ'}
LONG = 'ː'
HALF_LONG = 'ˑ'
IGNORE = {'ˈ', 'ˌ', '.', 'ʔ', '-', '‿', 'ʰ'}
WORD_BREAK = ' '   # 語の区切り (拗音・重子音をまたがない)


def _vowel(ph):
    """母音の音素 → (段, 長さの印) / None"""
    base = ph.rstrip(LONG + HALF_LONG).replace('̃', '')   # 鼻母音の印は外す (言語ごとの音素の列で「ン」を足す)
    if base in VOWELS:
        return VOWELS[base], ph[len(base):] if ph.startswith(base) else ''
    return None


def _raw(ph):
    return ph.rstrip(LONG).replace('ʰ', '').replace('ʲ', '')


def _consonant(ph):
    """子音の音素 → (行の鍵, 重子音か)"""
    base = _raw(ph)
    return CONSONANTS.get(base, base), ph.endswith(LONG)


def kana(phonemes, long='phonemic'):
    """IPA の音素の列 → カタカナ。long='phonemic' なら ː だけ「ー」、'phonetic' なら ˑ も「ー」"""
    if WORD_BREAK in phonemes:   # 語ごとに書いてつなぐ (Pāx Jūlia の s + j を「シュ」にしない)
        words, current = [], []
        for p in list(phonemes) + [WORD_BREAK]:
            if p == WORD_BREAK:
                if current:
                    words.append(kana(current, long))
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
            out.append(ROWS[''][dan] + lengthen(length))
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
        if geminate:
            if consonant in SOKUON:
                out.append('ッ')
            elif consonant in ('n', 'm', 'N'):
                out.append('ン')
        # 子音 + j + 母音 → 拗音 (キャ・シュ・ヴィェ)
        if nxt == 'j' and consonant not in ('j', 'w', '') and consonant in ROWS and i + 2 < len(phs) and \
                _vowel(phs[i + 2]) is not None:
            dan, length = _vowel(phs[i + 2])
            stem = ROWS[consonant]['i']
            out.append(stem + YOON[dan] + lengthen(length) if dan in YOON else stem + lengthen(length))
            i += 3
            continue
        v = _vowel(nxt) if nxt is not None else None
        if v is not None and consonant in ROWS:
            dan, length = v
            out.append(ROWS[consonant][dan] + lengthen(length))
            i += 2
        elif v is not None and consonant == 'N':
            out.append('ン' + ROWS['g'][v[0]] + lengthen(v[1]))   # 音節の頭の ŋ はガ行 (ンガ)
            i += 2
        elif consonant == 'm' and nxt is not None and _consonant(nxt)[0] in ('p', 'b'):
            out.append('ン')   # Pompēius → ポンペーイウス
            i += 1
        else:
            out.append(CODA.get(consonant, ''))
            i += 1
    return ''.join(out)
