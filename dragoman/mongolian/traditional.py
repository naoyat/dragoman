#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# キリル文字のモンゴル語 → 伝統的なモンゴル文字 (縦書きの文字。ノートでは縦に、端末では横に並べる)
#
#   Хүү өчигдөр охинд ном өгсөн. → ᠬᠦᠪᠡᠭᠦᠨ ᠥᠴᠦᠭᠡᠳᠦᠷ ᠥᠬᠢᠨ ᠳᠦᠷ ᠨᠣᠮ ᠥᠭᠦᠭᠰᠡᠨ (köbegün öčügedür ökin-dür nom ögügsen)
#
# 伝統文字の綴りはキリル文字と一対一に対応しない (キリル文字で書かない母音を書く: өчигдөр ↔ öčügedür、長母音を
# 子音 + 母音で: ширээ ↔ sirege、х / г は母音調和で q・k / γ・g と読み分ける同じ字 ᠬ / ᠭ、о / у・ө / ү は語頭の音節の
# ほかでは u・ü …)。語幹は次の順で引く:
#   1. 手作りの表 (WORDS。よく使う語・代名詞・後置詞・小辞)
#   2. 辞書 (Wiktionary の見出しの伝統文字の綴りか、語源の Classical Mongolian の綴り。tools/build_mongolian_dic.py)
#   3. 規則での推定 (_guess: 長母音 аа → aγa、語頭の音節のほかの о / ө → u / ü、語末の子音の連続に u / ü …)
# 接尾辞は語幹の母音調和と最後の音で伝統文字の綴りに (格の接尾辞は狭い空白 U+202F で離して: ökin + dür、
# 動詞の語尾は続けて: yabu + γsan、否定 -гүй は ügei を別の語に)
#
# 転写 (ラテン文字) は q・γ (後舌母音の語)・k・g (前舌母音の語)、ǰ・č・š、語末の母音の前の母音分離記号 (U+180E) と
# 接尾辞の前の狭い空白は -
#
import re

from . import dictionary, morphology

# 伝統文字 ↔ 転写の字 (ᠬ・ᠭ は母音調和で q / k・γ / g)
LETTERS = {'ᠠ': 'a', 'ᠡ': 'e', 'ᠢ': 'i', 'ᠣ': 'o', 'ᠤ': 'u', 'ᠥ': 'ö', 'ᠦ': 'ü', 'ᠧ': 'ē', 'ᠨ': 'n', 'ᠩ': 'ng',
           'ᠪ': 'b', 'ᠫ': 'p', 'ᠬ': 'q', 'ᠭ': 'γ', 'ᠮ': 'm', 'ᠯ': 'l', 'ᠰ': 's', 'ᠱ': 'š', 'ᠲ': 't', 'ᠳ': 'd',
           'ᠴ': 'č', 'ᠵ': 'ǰ', 'ᠶ': 'y', 'ᠷ': 'r', 'ᠸ': 'w', 'ᠹ': 'f', 'ᠺ': 'k', 'ᠻ': 'k', 'ᠼ': 'c', 'ᠽ': 'z',
           'ᠾ': 'h', 'ᠿ': 'ž', 'ᡀ': 'lh', 'ᡁ': 'zh', 'ᡂ': 'ch'}
TO_SCRIPT = {'a': 'ᠠ', 'e': 'ᠡ', 'i': 'ᠢ', 'o': 'ᠣ', 'u': 'ᠤ', 'ö': 'ᠥ', 'ü': 'ᠦ', 'ē': 'ᠧ', 'n': 'ᠨ', 'b': 'ᠪ',
             'p': 'ᠫ', 'q': 'ᠬ', 'k': 'ᠬ', 'γ': 'ᠭ', 'g': 'ᠭ', 'm': 'ᠮ', 'l': 'ᠯ', 's': 'ᠰ', 'š': 'ᠱ', 't': 'ᠲ',
             'd': 'ᠳ', 'č': 'ᠴ', 'ǰ': 'ᠵ', 'y': 'ᠶ', 'r': 'ᠷ', 'w': 'ᠸ', 'f': 'ᠹ', 'c': 'ᠼ', 'z': 'ᠽ', 'h': 'ᠾ',
             '-': '᠎'}
MVS = '᠎'     # 母音分離記号 (語末の a / e を離す: aq-a)
NNBSP = ' '   # 接尾辞の前の狭い空白
FVS = re.compile('[᠋-᠍᠏]')   # 字形の選択の記号 (転写では読まない)
BACK = set('aou')
FRONT = set('eöü')
VOWELS = set('aeiouöüē')

# 手作りの表: キリル文字 (小文字) → 伝統文字の綴りの転写 (動詞は不定形 -qu / -kü)
WORDS = {
    # 代名詞
    'би': 'bi', 'намайг': 'namayi', 'надад': 'nadur', 'над': 'nadur', 'миний': 'minu', 'надаас': 'nadača', 'надтай': 'nadtai',
    'чи': 'či', 'чамайг': 'čimayi', 'чамд': 'čimadur', 'чиний': 'činu', 'чамаас': 'čimača', 'чамтай': 'čimatai',
    'та': 'ta', 'таныг': 'tan-i', 'танд': 'tan-dur', 'таны': 'tan-u', 'тэр': 'tere', 'түүний': 'tegün-ü',
    'түүнийг': 'tegün-i', 'түүнд': 'tegün-dür', 'бид': 'bida', 'бидний': 'bidan-u', 'манай': 'manu', 'тэд': 'tede',
    'энэ': 'ene', 'үүний': 'egün-ü', 'үүнийг': 'egün-i', 'юу': 'yaγu', 'хэн': 'ken', 'өөрөө': 'öber-iyen',
    'өөрийн': 'öber-ün', 'хаана': 'qamiγ-a', 'энд': 'ende', 'тэнд': 'tende',
    # 小辞・接続・否定
    'бол': 'bol', 'нь': 'ni', 'уу': 'uu', 'үү': 'üü', 'вэ': 'be', 'бэ': 'be', 'ба': 'ba', 'болон': 'bolun',
    'биш': 'busu', 'үгүй': 'ügei', 'юм': 'yum', 'ч': 'ču', 'гэж': 'geǰü', 'харин': 'qarin', 'бөгөөд': 'bögetele',
    'эсвэл': 'esebel',
    # 後置詞
    'дээр': 'degere', 'доор': 'door-a', 'дотор': 'dotor-a', 'өмнө': 'emün-e', 'хойно': 'qoyin-a', 'дараа': 'daraγ-a',
    'тухай': 'tuqai', 'төлөө': 'tölöge', 'хамт': 'qamtu', 'шиг': 'sig', 'хүртэл': 'kürtele', 'дунд': 'dumda',
    # 数
    'нэг': 'nigen', 'хоёр': 'qoyar', 'гурав': 'γurba', 'гурван': 'γurban', 'дөрөв': 'dörbe', 'дөрвөн': 'dörben',
    'тав': 'tabu', 'таван': 'tabun', 'зургаа': 'ǰirγuγ-a', 'долоо': 'doluγ-a', 'найм': 'naim-a', 'ес': 'yisü',
    'арав': 'arba', 'зуу': 'ǰaγu', 'мянга': 'mingγ-a',
    # 名詞
    'хүү': 'köbegün', 'охин': 'ökin', 'ном': 'nom', 'гэр': 'ger', 'хүн': 'kümün', 'эх': 'eke', 'ээж': 'eke',
    'аав': 'aba', 'эцэг': 'ečige', 'ах': 'aq-a', 'эгч': 'egeči', 'дүү': 'degüü', 'найз': 'nayiǰa', 'багш': 'baγsi',
    'сурагч': 'suruγči', 'сургууль': 'surγaγuli', 'ус': 'usu', 'хоол': 'qoγol-a', 'цай': 'čai', 'сүү': 'sün',
    'мах': 'miq-a', 'морь': 'mori', 'нохой': 'noqai', 'заан': 'ǰaγan', 'хот': 'qota', 'улс': 'ulus', 'газар': 'γaǰar',
    'тэнгэр': 'tngri', 'нар': 'naran', 'сар': 'sar-a', 'од': 'odu', 'уул': 'aγula', 'гол': 'γool', 'нуур': 'naγur',
    'өдөр': 'edür', 'шөнө': 'söni', 'өглөө': 'örlüge', 'цаг': 'čaγ', 'жил': 'ǰil', 'хэл': 'kele', 'үг': 'üge',
    'нэр': 'nere', 'захиа': 'ǰaqiy-a', 'сандал': 'sandali', 'ширээ': 'sirege', 'мөнгө': 'mönggü', 'ажил': 'aǰil',
    'дуу': 'daγu', 'нүд': 'nidü', 'гар': 'γar', 'толгой': 'toloγai', 'хаан': 'qaγan', 'хатан': 'qatun',
    'цэрэг': 'čerig', 'бурхан': 'burqan', 'монгол': 'mongγol', 'улаанбаатар': 'ulaγanbaγatur', 'хүүхэд': 'keüked',
    'кино': 'kino',
    # 形容詞・副詞
    'сайн': 'sayin', 'муу': 'maγu', 'том': 'tomu', 'шинэ': 'sine', 'хуучин': 'qaγučin', 'сайхан': 'sayiqan',
    'өндөр': 'öndür', 'урт': 'urtu', 'их': 'yeke', 'бага': 'baγ-a', 'маш': 'masi', 'хүйтэн': 'küiten',
    'халуун': 'qalaγun', 'одоо': 'odo', 'өнөөдөр': 'önödür', 'өчигдөр': 'öčügedür', 'маргааш': 'maγaši',
    # 動詞 (不定形)
    'байх': 'bayiqu', 'болох': 'bolqu', 'гэх': 'gekü', 'хийх': 'kikü', 'явах': 'yabuqu', 'ирэх': 'irekü',
    'очих': 'očiqu', 'үзэх': 'üǰekü', 'харах': 'qaraqu', 'унших': 'ungsiqu', 'бичих': 'bičikü', 'идэх': 'idekü',
    'уух': 'uuqu', 'өгөх': 'ögkü', 'авах': 'abqu', 'мэдэх': 'medekü', 'хэлэх': 'kelekü', 'ярих': 'yariqu',
    'сурах': 'surqu', 'заах': 'ǰiγaqu', 'амьдрах': 'amidaraqu', 'унтах': 'umtaqu', 'суух': 'saγuqu', 'босох': 'bosqu',
    'хүлээх': 'küliyekü', 'хайх': 'qayiqu', 'олох': 'olqu', 'мартах': 'martaqu', 'санах': 'sanaqu',
    'асуух': 'asaγuqu', 'ажиллах': 'aǰillaqu', 'тоглох': 'toγlaqu', 'дуулах': 'daγulaqu', 'гарах': 'γarqu',
    'орох': 'orqu', 'буцах': 'bučaqu', 'нээх': 'negekü', 'хаах': 'qaγaqu',
}

# 動詞の語尾: (形, 時制 / 働き) → (後舌母音の語の綴り, 前舌母音の語の綴り)。C は子音の後ろで母音を挟むもの
VERB_SUFFIXES = {
    ('finite', 'present'): ('n-a', 'n-e'), ('finite', 'perfect'): ('luγ-a', 'lüg-e'), ('finite', 'future'): ('qu', 'kü'),
    ('participle', 'perfect'): ('γsan', 'gsen'), ('participle', 'habitual'): ('daγ', 'deg'),
    ('participle', 'future'): ('qu', 'kü'), ('participle', 'imperfective'): ('γ-a', 'g-e'),
    ('participle', 'agent'): ('γči', 'gči'), ('finite', 'habitual'): ('daγ', 'deg'),
    ('converb', 'after'): ('γad', 'ged'), ('converb', 'if'): ('bal', 'bel'), ('converb', 'until'): ('tala', 'tele'),
    ('converb', 'purpose'): ('qar-a', 'ker-e'), ('converb', 'while'): ('γsaγar', 'gseger'),
    ('converb', 'as_soon'): ('maγča', 'megče'), ('converb', 'when'): ('qui-dur', 'küi-dür'),
    ('converb', 'manner'): ('n', 'n'), ('imperative', 'polite'): ('γarai', 'gerei'),
    ('imperative', 'hortative'): ('y-a', 'y-e'),
}
# 語尾の形 → 時制 (-лаа と -в・-жээ の綴りを分ける)
ENDING_SPELLING = {'в': ('ba', 'be'), 'жээ': ('ǰai', 'ǰei'), 'чээ': ('ǰai', 'ǰei'), 'ж': ('ǰu', 'ǰü'), 'ч': ('ǰu', 'ǰü')}
VOICELESS_AFTER = set('bγgrsdkq')   # -ж → -ču、与位格 -dur → -tur の前の子音
CASE_SUFFIXES = {'Acc': ('i', 'i'), 'Dat': ('dur', 'dür'), 'Abl': ('ača', 'eče'), 'Com': ('tai', 'tei')}


def latin(script):
    """伝統文字の綴り → 転写 (ᠬᠦᠪᠡᠭᠦᠨ → köbegün、ᠵᠠᠬᠢᠶ᠎ᠠ → ǰaqiy-a)"""
    out = []
    for word in script.split(' '):
        parts = []
        for part in word.split(NNBSP):
            text = ''.join(LETTERS.get(c, '-' if c == MVS else c) for c in FVS.sub('', part))
            parts.append(text)
        back = any(c in BACK for c in ''.join(parts))
        if not back:
            parts = [p.replace('q', 'k').replace('γ', 'g') for p in parts]
        out.append('-'.join(parts))
    return ' '.join(out)


def to_script(text):
    """転写 → 伝統文字 (- は語末の母音の前なら母音分離記号、ほかは接尾辞の前の狭い空白)"""
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if text.startswith('ng', i) and (i + 2 >= len(text) or text[i + 2] not in VOWELS):
            out.append('ᠩ')
            i += 2
            continue
        if c == '-':
            rest = text[i + 1:]
            out.append(MVS if rest[:1] in ('a', 'e') and rest[1:2] in ('', '-') else NNBSP)   # aq-a / ökin-dür
            i += 1
            continue
        out.append(TO_SCRIPT.get(c, c))
        i += 1
    return ''.join(out)


def _back(text):
    return any(c in BACK for c in text)


def _harmony(word_latin, cyrillic=''):
    """後舌母音の語か (転写に a・o・u があれば。i だけの語は前舌)"""
    if any(c in BACK for c in word_latin):
        return True
    if any(c in FRONT for c in word_latin):
        return False
    return any(c in 'аоуяёы' for c in cyrillic.lower())


# 規則での推定: キリル文字 → 転写
CONSONANTS = {'б': 'b', 'в': 'b', 'д': 'd', 'ж': 'ǰ', 'з': 'ǰ', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
              'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ф': 'f', 'ц': 'č', 'ч': 'č', 'ш': 's', 'щ': 's', 'ъ': ''}
LONG = {'аа': 'aγa', 'ээ': 'ege', 'оо': 'oγo', 'өө': 'ege', 'уу': 'uγu', 'үү': 'ügü', 'ий': 'i', 'ай': 'ai',
        'эй': 'ei', 'ой': 'oi', 'уй': 'ui', 'үй': 'üi', 'ия': 'iya', 'иа': 'iya', 'иу': 'iyu', 'ио': 'iyo'}
CYR_VOWELS = set('аэиоуөүыяеёю')


def _guess(cyr):
    """辞書に無い語の伝統文字の綴りを規則で推定する (転写で返す)。長母音は子音 + 母音 (ширээ → sirege)、語頭の音節の
    ほかの о・ө は u・ü、х・г は母音調和で q / k・γ / g、ш は s、ц・з は č・ǰ、語末の ь は i、語末の子音の連続は
    u / ü で終える (урт → urtu)、語末の短い а・э は母音分離記号で離す (бага → baγ-a)"""
    low = cyr.lower()
    back = any(c in 'аоуяёы' for c in low) or not any(c in 'эөүе' for c in low) and any(c in 'аоу' for c in low)
    out = ''
    i = 0
    syllable = 0
    while i < len(low):
        c = low[i]
        pair = low[i:i + 2]
        if pair in LONG:
            out += LONG[pair] if pair not in ('аа', 'оо', 'уу') or back else LONG[pair]
            syllable += 1
            i += 2
            continue
        if c in CYR_VOWELS:
            v = {'а': 'a', 'э': 'e', 'и': 'i', 'о': 'o', 'у': 'u', 'ө': 'ö', 'ү': 'ü', 'ы': 'i', 'я': 'ya', 'е': 'ye',
                 'ё': 'yo', 'ю': 'yu' if back else 'yü'}[c]
            if syllable > 0:
                v = {'o': 'u', 'ö': 'ü', 'yo': 'yu'}.get(v, v)
            if i == len(low) - 1 and v in ('a', 'e') and out and out[-1] not in VOWELS:
                v = '-' + v   # 語末の短い母音 (бага → baγ-a)
            out += v
            syllable += 1
        elif c == 'х':
            out += 'q' if back else 'k'
        elif c == 'г':
            out += 'γ' if back else 'g'
        elif c == 'ь':
            out += 'i' if i == len(low) - 1 else ''
        else:
            out += CONSONANTS.get(c, c)
        i += 1
    # 語末の子音の連続 (ng・n で終わるものを除く) は u / ü で終える
    tail = re.search(r'([^aeiouöü-])([^aeiouöü-])$', out)
    if tail and not out.endswith('ng') and tail.group(2) not in 'n':
        out += 'u' if back else 'ü'
    return out


def stem_spelling(lemma, pos=None):
    """見出し語 → (伝統文字の綴りの転写, 出典 表 / 辞書 / 推定)。動詞は不定形 (-qu / -kü) のまま"""
    low = lemma.lower()
    if low in WORDS:
        return WORDS[low], '表'
    rows = [r for r in dictionary.lemmas(low) if r.get('script')] + \
        [r for r in dictionary._rows(low) if r.get('script')]
    if pos is not None:
        rows = [r for r in rows if r['pos'] == pos] or rows
    if rows:
        return latin(rows[0]['script'].split(' ')[0]), '辞書'
    return _guess(low), '推定'


def _ends_vowel(text):
    t = text.rstrip('-')
    return bool(t) and t[-1] in VOWELS


def _case(stem, case, back, reflexive=False):
    """格の接尾辞 (狭い空白で離す)"""
    k = 0 if back else 1
    v = _ends_vowel(stem.replace('-', ''))
    last = stem.replace('-', '')[-1:] if stem else ''
    if case == 'Gen':
        suffix = 'yin' if v else ('u' if back else 'ü') if last == 'n' else ('un' if back else 'ün')
    elif case == 'Acc':
        suffix = 'yi' if v else 'i'
    elif case == 'Dat':
        hard = last in VOICELESS_AFTER and not stem.endswith('ng')
        suffix = ('tur', 'tür')[k] if hard else ('dur', 'dür')[k]
        if reflexive:
            return stem + '-' + suffix[0] + ('aγan' if back else 'egen')
    elif case == 'Abl':
        suffix = ('ača', 'eče')[k]
    elif case == 'Ins':
        suffix = ('bar', 'ber')[k] if v else ('iyar', 'iyer')[k]
    elif case == 'Com':
        suffix = ('tai', 'tei')[k]
    elif case == 'Dir':
        suffix = ('ruγu', 'rügü')[k] if v else ('luγu', 'lügü')[k] if last == 'r' else ('uruγu', 'ürügü')[k]
    else:
        suffix = ''
    out = stem + ('-' + suffix if suffix else '')
    if reflexive:
        out += '-' + ((('ban', 'ben')[k]) if _ends_vowel(suffix or stem) else ('iyan', 'iyen')[k])
    return out


def _plural(stem, surface, back):
    low = surface.lower()
    if 'нууд' in low or 'нүүд' in low:
        return stem + ('nuγud' if back else 'nügüd')
    if 'чууд' in low or 'чүүд' in low:
        return stem + ('čuγud' if back else 'čügüd')
    if 'нар' in low:
        return stem + '-' + ('nar' if back else 'ner')
    stem = stem[:-1] if stem.endswith('n') and len(stem) > 2 else stem
    return stem + ('ud' if back else 'üd')


def _verb(rec):
    """動詞の記録 → 転写 (語幹 + 語尾、否定は ügei を別の語に)"""
    inf, source = stem_spelling(rec['lemma'], 'verb')
    back = _harmony(inf, rec['lemma'])
    stem = inf[:-2] if inf.endswith(('qu', 'kü')) else inf
    k = 0 if back else 1
    key = (rec.get('form'), rec.get('tense'))
    ending = rec.get('ending') or ''
    if ending in ENDING_SPELLING and key in (('finite', 'perfect'), ('converb', 'and')):
        suffix = ENDING_SPELLING[ending][k]
    elif key == ('finite', 'perfect') and ending.startswith('с'):   # 文末の -сан (өгсөн → ögügsen)
        suffix = ('γsan', 'gsen')[k]
    elif rec.get('form') == 'converb' and rec.get('tense') == 'and' or ending in ('ж', 'ч'):
        suffix = ('ǰu', 'ǰü')[k]
    else:
        suffix = VERB_SUFFIXES.get(key, ('', ''))[k]
    if suffix.startswith('ǰ') and stem[-1:] in VOICELESS_AFTER:
        suffix = 'č' + suffix[1:]
    if suffix.startswith(('γs', 'gs', 'γ-', 'g-')) and stem and not _ends_vowel(stem):   # ög + ügsen
        suffix = ('u' if back else 'ü') + suffix
    text = stem + suffix
    if rec.get('case') and rec['case'] != 'Nom':
        text = _case(text, rec['case'], back, rec.get('reflexive'))
    if rec.get('negated'):
        text += ' ügei'
    return text, source


def _noun(rec):
    stem, source = stem_spelling(rec['lemma'], 'name' if rec.get('proper') else 'noun')
    back = _harmony(stem, rec['lemma'])
    if rec.get('number') == 'pl':
        stem = _plural(stem, rec['surface'], back)
    case = rec.get('case') or 'Nom'
    if case != 'Nom' or rec.get('reflexive'):
        return _case(stem, case, back, rec.get('reflexive')), source
    return stem, source


def _word(rec):
    kind = rec.get('kind')
    surface = rec['surface']
    if kind == 'verb':
        return _verb(rec)
    if kind == 'noun' and rec.get('lemma'):
        return _noun(rec)
    return stem_spelling(surface)


def _verb_part(word):
    """副動詞 + 助動詞 (уншиж байна) の語ごとの記録"""
    for r in morphology.analyses(word):
        if r['kind'] == 'verb':
            return dict(r, surface=word)
    return {'kind': 'other', 'surface': word}


def sentence(recs):
    """解析の記録の列 → [{cyrillic, latin, script, source}] (句読点は除く)"""
    out = []
    for rec in recs:
        if rec.get('kind') == 'punct':
            continue
        parts = rec['surface'].split(' ')
        if len(parts) > 1 and rec.get('kind') == 'verb':
            recs2 = [_verb_part(p) for p in parts[:-1]] + [dict(rec, surface=parts[-1],
                                                             lemma=_verb_part(parts[-1]).get('lemma', rec['lemma']))]
            for r in recs2:
                text, source = _word(r) if r.get('kind') != 'other' else stem_spelling(r['surface'])
                out.append({'cyrillic': r['surface'], 'latin': text, 'script': to_script_words(text), 'source': source})
            continue
        text, source = _word(rec)
        out.append({'cyrillic': rec['surface'], 'latin': text, 'script': to_script_words(text), 'source': source})
    return out


def to_script_words(text):
    return ' '.join(to_script(w) for w in text.split(' '))


# キリル文字の転写 (Wiktionary の流儀: хүү → xüü、өчигдөр → öčigdör)
CYR_LATIN = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'je', 'ё': 'jo', 'ж': 'ž', 'з': 'z', 'и': 'i',
             'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'ө': 'ö', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
             'у': 'u', 'ү': 'ü', 'ф': 'f', 'х': 'x', 'ц': 'c', 'ч': 'č', 'ш': 'š', 'щ': 'šč', 'ъ': 'ʺ', 'ы': 'y',
             'ь': 'ʹ', 'э': 'e', 'ю': 'ju', 'я': 'ja'}


def cyrillic_latin(word):
    return ''.join(CYR_LATIN.get(c, c) for c in word.lower())


def differences(cyrillic, translit):
    """キリル文字の綴りと伝統文字の綴りの違いの主なもの (ノートの表の注)"""
    low = cyrillic.lower()
    base = translit.split(' ')[0].replace('-', '')
    notes = []
    longs = [p for p in ('аа', 'ээ', 'оо', 'өө', 'уу', 'үү') if p in low]
    if longs and re.search('[aeiouöü][γg][aeiouöü]', base):
        notes.append('長母音 %s を 母音 + γ/g + 母音 で' % '・'.join(longs))
    count = lambda text, vs: len(re.findall('[%s]+' % vs, text))
    if count(base, 'aeiouöü') > count(low, 'аэиоуөүыяеёю') and not longs:
        notes.append('キリル文字で書かない母音を書く')
    first = re.match('[^аэиоуөүыяеёю]*[аэиоуөүыяеёю]+', low)
    if first and re.search('[оө]', low[first.end():]) and re.search('[uü]', re.sub('^[^aeiouöü]*[aeiouöü]+', '', base)):
        notes.append('語頭の音節のほかの о・ө は u・ü')
    cv = re.search('[аэиоуөү]', low)
    lv = re.search('[aeiouöü]', base)
    if cv and lv and dict(zip('аэиоуөү', 'aeiouöü'))[cv.group()] != lv.group():
        notes.append('語頭の音節の母音 %s ↔ %s' % (cv.group(), lv.group()))   # охин ↔ ökin
    if 'ш' in low and 's' in base:
        notes.append('ш は s (ᠰ)')
    if ('ц' in low and 'č' in base) or ('з' in low and 'ǰ' in base):
        notes.append('ц・з は č・ǰ')
    if base.endswith('n') and not low.endswith('н') and ' ' not in translit:
        notes.append('語末に n')
    if NNBSP in to_script(translit.split(' ')[0]):
        notes.append('接尾辞は離して書く')
    if ' ' in translit:
        notes.append('否定は別の語 ügei')
    return notes
