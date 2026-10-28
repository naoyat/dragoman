#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語 (ハングル) の語をカタカナで書く: 綴り → 標準発音の規則で音 → 共通の規則 (core/kana.py)
#
#   민수 → ミンス、김철수 → キムチョルス、서울 → ソウル、한국어 → ハングゴ、감사합니다 → カムサハムニダ、좋아요 → チョアヨ
#
# 発音どおりに (語の中で。語をまたいでは変えない):
#   - 連音: パッチム + ㅇ は次の音節の頭に (한국어 → ハングゴ、읽어요 → イルゴヨ)。ㅎ のパッチムは ㅇ の前で読まない (좋아요 → チョアヨ)
#   - 鼻音化 (합니다 → ハムニダ、한국말 → ハングンマル、독립 → トンニプ)、流音化 (신라 → シルラ)、ㅎ との激音化 (좋다 → チョタ)、
#     口蓋音化 (같이 → カチ)
#   - 平音 ㄱ・ㄷ・ㅂ・ㅈ は母音・ㄴ・ㄹ・ㅁ・ㅇ の後ろで濁る (민기 → ミンギ)。濃音は語中で「ッ」(아빠 → アッパ)、
#     平音・激音・濃音の区別は書かない
#   - パッチム: ㄱ 類は「ク」、ㅂ 類は「プ」、ㄷ 類 (ㅅ・ㅈ・ㅊ・ㅌ・ㅎ) は「ッ」、ㄴ・ㅇ は「ン」、ㅁ は「ム」、ㄹ は「ル」。
#     同じ所の閉鎖音の前は「ッ」(학교 → ハッキョ)
#   - ㅓ はオ段、ㅡ はウ段、ㅐ・ㅔ はエ段。시・샤 は「シ」「シャ」(ㅅ は ㅣ・ㅑ 類の前で [ɕ])、子音 + ㅘ・ㅝ は「ファ」「クォ」
#
from dragoman.core.kana import kana, text_words

INITIALS = ('ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ')
VOWELS = ('a', 'e', 'ja', 'je', 'o', 'e', 'jo', 'je', 'o', 'wa', 'we', 'we', 'jo', 'u', 'wo', 'we', 'wi', 'ju', 'ɯ',
          'ɰi', 'i')   # ㅏ ㅐ ㅑ ㅒ ㅓ ㅔ ㅕ ㅖ ㅗ ㅘ ㅙ ㅚ ㅛ ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ ㅢ ㅣ (ㅓ [ʌ] は o)
FINALS = ((), ('ㄱ',), ('ㄲ',), ('ㄱ', 'ㅅ'), ('ㄴ',), ('ㄴ', 'ㅈ'), ('ㄴ', 'ㅎ'), ('ㄷ',), ('ㄹ',), ('ㄹ', 'ㄱ'),
          ('ㄹ', 'ㅁ'), ('ㄹ', 'ㅂ'), ('ㄹ', 'ㅅ'), ('ㄹ', 'ㅌ'), ('ㄹ', 'ㅍ'), ('ㄹ', 'ㅎ'), ('ㅁ',), ('ㅂ',), ('ㅂ', 'ㅅ'),
          ('ㅅ',), ('ㅆ',), ('ㅇ',), ('ㅈ',), ('ㅊ',), ('ㅋ',), ('ㅌ',), ('ㅍ',), ('ㅎ',))
# 二重パッチムの子音の前・語末での読み (ㄺ → ㄱ、ㄼ → ㄹ …)
CLUSTER = {('ㄱ', 'ㅅ'): 'ㄱ', ('ㄴ', 'ㅈ'): 'ㄴ', ('ㄴ', 'ㅎ'): 'ㄴ', ('ㄹ', 'ㄱ'): 'ㄱ', ('ㄹ', 'ㅁ'): 'ㅁ', ('ㄹ', 'ㅂ'): 'ㄹ',
           ('ㄹ', 'ㅅ'): 'ㄹ', ('ㄹ', 'ㅌ'): 'ㄹ', ('ㄹ', 'ㅍ'): 'ㅂ', ('ㄹ', 'ㅎ'): 'ㄹ', ('ㅂ', 'ㅅ'): 'ㅂ'}
# パッチムの代表音 (k・t・p・n・l・m・ŋ)
CODA_CLASS = {'ㄱ': 'k', 'ㄲ': 'k', 'ㅋ': 'k', 'ㄷ': 't', 'ㅅ': 't', 'ㅆ': 't', 'ㅈ': 't', 'ㅊ': 't', 'ㅌ': 't', 'ㅎ': 't',
              'ㅂ': 'p', 'ㅍ': 'p', 'ㄴ': 'n', 'ㄹ': 'l', 'ㅁ': 'm', 'ㅇ': 'ŋ'}
NASAL = {'k': 'ŋ', 't': 'n', 'p': 'm'}
ASPIRATE = {'ㄱ': 'ㅋ', 'ㄷ': 'ㅌ', 'ㅂ': 'ㅍ', 'ㅈ': 'ㅊ', 'ㅅ': 'ㅆ'}
TENSE = {'ㄱ': 'ㄲ', 'ㄷ': 'ㄸ', 'ㅂ': 'ㅃ', 'ㅅ': 'ㅆ', 'ㅈ': 'ㅉ'}
# 初声の音: (平音の無声, 濁った音)
ONSET = {'ㄱ': 'k', 'ㄲ': 'k', 'ㅋ': 'k', 'ㄷ': 't', 'ㄸ': 't', 'ㅌ': 't', 'ㅂ': 'p', 'ㅃ': 'p', 'ㅍ': 'p', 'ㅅ': 's',
         'ㅆ': 's', 'ㅈ': 'tʃ', 'ㅉ': 'tʃ', 'ㅊ': 'tʃ', 'ㄴ': 'n', 'ㄹ': 'r', 'ㅁ': 'm', 'ㅎ': 'h', 'ㅇ': ''}
VOICED = {'ㄱ': 'g', 'ㄷ': 'd', 'ㅂ': 'b', 'ㅈ': 'dʒ'}
CODA_KANA = {'k': 'k̚', 't': 't̚', 'p': 'p̚', 'n': 'n', 'l': 'ɭ', 'm': 'm̚', 'ŋ': 'ɴ'}   # ㅁ は ㅂ の前でも「ム」(김밥 → キムバプ)
PLACE = {'k': ('k',), 't': ('t', 's', 'tʃ'), 'p': ('p',)}


def _syllables(word):
    out = []
    for ch in word:
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            out.append([INITIALS[code // 588], VOWELS[code % 588 // 28], list(FINALS[code % 28])])
    return out


def _rules(syls):
    """標準発音の規則 (連音・鼻音化・流音化・激音化・口蓋音化・濃音化)。初声は字母、パッチムは代表音か字母の列"""
    for k in range(len(syls) - 1):
        final, nxt = syls[k][2], syls[k + 1]
        if not final:
            continue
        initial = nxt[0]
        if initial == 'ㅇ':
            if final[-1] == 'ㅎ':
                final.pop()                                  # 좋아요 → 조아요、많이 → 마니
                if not final:
                    continue
            if final[-1] == 'ㅇ':
                continue
            moved = final.pop()                              # 連音 (한국어 → 한구거、읽어 → 일거)
            if moved in ('ㄷ', 'ㅌ') and nxt[1] == 'i':
                moved = 'ㅈ' if moved == 'ㄷ' else 'ㅊ'      # 口蓋音化 (같이 → 가치)
            nxt[0] = moved
            continue
        if final[-1] == 'ㅎ' and initial in ASPIRATE:
            final.pop()
            nxt[0] = ASPIRATE[initial]                       # 좋다 → 조타
            continue
        if final[-1] == 'ㅎ' and initial == 'ㄴ':
            final[-1] = 'ㄴ'                                 # 놓는 → 논는
        last = CLUSTER.get(tuple(final), final[-1])
        cls = CODA_CLASS.get(last, '')
        if initial == 'ㅎ' and cls in ('k', 't', 'p'):
            syls[k][2] = []
            nxt[0] = {'k': 'ㅋ', 't': 'ㅌ', 'p': 'ㅍ'}[cls] if last != 'ㅈ' else 'ㅊ'   # 축하 → 추카、입학 → 이팍
            continue
        if initial == 'ㄹ':
            if cls == 'n':
                syls[k][2] = ['ㄹ']                          # 신라 → 실라
                continue
            if cls in ('k', 't', 'p', 'm', 'ŋ'):
                nxt[0] = initial = 'ㄴ'                      # 독립 → 독닙 → 동닙、종로 → 종노
        if cls == 'l' and initial == 'ㄴ':
            nxt[0] = 'ㄹ'                                    # 설날 → 설랄
        if cls in NASAL and initial in ('ㄴ', 'ㅁ'):
            syls[k][2] = [{'ŋ': 'ㅇ', 'n': 'ㄴ', 'm': 'ㅁ'}[NASAL[cls]]]   # 합니다 → 함니다
            continue
        if cls in ('k', 't', 'p') and initial in TENSE:
            nxt[0] = TENSE[initial]                          # 학교 → 학꾜
    return syls


def phonemes(word):
    return [ph for group in syllable_phonemes(word) for ph in group]


def syllable_phonemes(word):
    """音節 (ハングルの字) ごとの音素の列。連音で動いた子音は次の音節に (한국어 → 한|구|거)、
    促音になる子音 (학교 の ㄱ、아빠 の ㅃ の前半) は前の音節に"""
    syls = _rules(_syllables(word))
    out = []
    starts = []
    prev_coda = None   # None: 語頭、'' : 母音の後ろ、ほかは代表音
    for initial, vowel, final in syls:
        starts.append(len(out))
        # 初声
        if initial == 'ㅇ':
            onset = ''
        elif initial in VOICED and prev_coda in ('', 'n', 'l', 'm', 'ŋ'):
            onset = VOICED[initial]                          # 母音・鼻音・流音の後ろで濁る
        elif initial in ('ㄲ', 'ㄸ', 'ㅃ', 'ㅆ', 'ㅉ') and prev_coda == '':
            onset = ONSET[initial]
            out.append(onset)                                # 語中の濃音は「ッ」(아빠 → アッパ)
            starts[-1] += 1                                  # 「ッ」は前の音節に (아 アッ・빠 パ)
        else:
            onset = ONSET[initial]
        if initial == 'ㄹ' and prev_coda == 'l':
            onset = 'l'
        if onset in ('s',) and (vowel[:1] in ('i', 'j') or vowel == 'wi'):
            onset = 'ɕ'                                      # 시 → シ、샤 → シャ
        if onset in ('tʃ', 'dʒ', 'ɕ') and vowel[:1] == 'j':
            vowel = vowel[1:]                                # 쟈・져 → チャ・チョ
        if onset in ('tʃ', 'dʒ', 'ɕ') and vowel == 'we':
            vowel = 'e'                                      # 최 → チェ、죄 → チェ (硬口蓋音の後ろの w は弱い)
        if vowel == 'ɰi':
            vowel = 'i' if onset else 'ɯi'                   # 희 → ヒ、의 → ウイ
        if onset:
            out.append(onset)
        if vowel == 'ɯi':
            out += ['ɯ', 'i']
        elif vowel[:1] in ('j', 'w') and len(vowel) == 2:
            out += [vowel[0], vowel[1]]
        else:
            out.append(vowel)
        # パッチム
        if final:
            last = CLUSTER.get(tuple(final), final[-1])
            cls = CODA_CLASS[last]
            out.append(CODA_KANA[cls])
            prev_coda = cls
        else:
            prev_coda = ''
    # 同じ所の閉鎖音の前のパッチムは「ッ」(학꾜 → ハッキョ)
    fixed = []
    for k, ph in enumerate(out):
        nxt = out[k + 1] if k + 1 < len(out) else ''
        if ph in ('k̚', 't̚', 'p̚') and nxt in PLACE[ph[0]]:
            fixed.append(nxt)
            continue
        fixed.append(ph)
    return [fixed[a:b] for a, b in zip(starts, starts[1:] + [len(fixed)])]


def katakana(word, long='phonemic', **options):
    options.setdefault('labial_glide', True)
    return kana(phonemes(word), long=long, **options)


def syllable_katakana(word, long='phonemic', **options):
    """語 → ハングルの字ごとのカタカナ (つなげば語のカタカナ)。音節の終わりの促音の子音は「ッ」"""
    options.setdefault('labial_glide', True)
    out = []
    for group in syllable_phonemes(word):
        if group and group[-1] in ONSET.values() and group[-1] not in ('', 'n', 'm', 'r'):
            group = group[:-1] + ['t̚']                    # 次の音節の子音と重なる子音 (학 の k) は「ッ」
        out.append(kana(group, long=long, **options))
    return out


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列)"""
    return [katakana(w, **options) for w in text_words(text)]
