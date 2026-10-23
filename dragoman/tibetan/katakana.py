#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# チベット語の語をカタカナで書く: ラサ発音 (tibetan/phonology.word_syllables。綴りの前置字・後置字から声調・母音の変化を
# 決めたもの) の音素 → 共通の規則 (core/kana.py)。声調と有気・無気は書かない
#
#   བོད → ペ、ལྷ་ས → ラサ、བཀྲ་ཤིས་བདེ་ལེགས → タシデレ、སངས་རྒྱས → サンギェ、ཆོས → チェ、ཐུགས་རྗེ་ཆེ → トゥジェチェ
#
#   - 変音した母音 ɛ・ø はエ段 (ø は --kana-oe=オ でオ段)、y は「ユ」、長母音は「ー」
#   - 硬口蓋音 c・cʰ・ɟ は「キャ」の行 (ギャ)、そり舌音 ʈ・ʈʰ・ɖ は t・d、無声の l̥ (ལྷ) は「ラ」、ɕ はシャ行、tɕ はチャ行
#   - 音節末の声門閉鎖音 ʔ (-g) は書かない、-ŋ・-n・-m は「ン」「ム」、-p は「プ」
#   - 語の2音節目からの低い声調の無気音は有声 (デ・ジェ)。語頭の低い声調は無声のまま (རྒྱལ → キェー)
#
import re

from dragoman.core.kana import kana
from . import phonology

REPLACE = [('ʈʰ', 't'), ('ʈ', 't'), ('ɖ', 'd'), ('cʰ', 'kj'), ('c', 'kj'), ('ɟ', 'gj'), ('l̥', 'l'), ('ʰ', ''),
           ('dʑ', 'dʒ'), ('ɕ', 'ʃ'), ('ʑ', 'ʒ'), ('ʔ', '')]
SMALL_E = {'キエ': 'キェ', 'ギエ': 'ギェ'}   # 硬口蓋音 + e は小さい「ェ」(サンギェー。共通の規則の「ピエール」でなく)


VOICING = {'k': 'g', 't': 'd', 'p': 'b', 'c': 'ɟ', 'ʈ': 'ɖ', 'ts': 'dz', 'tɕ': 'dʑ'}
LOW_TONE = '35'


def _syllable_ipa(s, initial_syllable=True):
    first = s['initial']
    if not initial_syllable and s['tone'] == LOW_TONE and first in VOICING:
        first = VOICING[first]   # 語の2音節目からの低い声調の無気音は有声 (བཀྲ་ཤིས་བདེ་ལེགས → タシデレ、ཐུགས་རྗེ → トゥジェ)
    text = first + s['vowel'] + ('ː' if s['long'] else '') + s['coda']
    for a, b in REPLACE:
        text = text.replace(a, b)
    return text


def word_katakana(word, enclitic=False, pron='lhasa', **options):
    """チベット文字の語 (ツェクで区切った音節) → カタカナ"""
    syllables = phonology.word_syllables(word, pron, enclitic)
    out = kana('.'.join(_syllable_ipa(s, k == 0 and not enclitic) for k, s in enumerate(syllables)), **options)
    for a, b in SMALL_E.items():
        out = out.replace(a, b)
    return out


def katakana(analysis, kana_options):
    """カタカナ読み (--kana): 解析の語の区切り (助詞は前の語に) ごとに"""
    return [word_katakana(text, enclitic, **kana_options) for text, enclitic in analysis.word_texts()
            if not re.fullmatch('[།༎༏༐༑༔ ]+', text)]
