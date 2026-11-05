#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文字の図 (core/letters.py) に添える、その言語での字の呼び名 (呼び名の字と転写)
#
#   ar: ب → باء bāʾ    fa: ب → بِ be    ur: ب → بے be、ے → بڑی یے baṛī ye    he: ב → בית bet
#   ko: ㄱ (初声・終声) → 기역 giyeok    sa: क → ककार kakāra、ि → इकार ikāra    hi: ि → इ की मात्रा i kī mātrā
#   bo: ི → གི་གུ gi gu、ྱ → ཡ་བཏགས ya btags    mn: ᠨ → ᠨᠠ na (на)、ᠠ → ᠠ a (а)、ᠩ → ᠠᠩ ang (анг)
#
import unicodedata

ARABIC = {
    'ا': ('ألف', 'alif'), 'ب': ('باء', 'bāʾ'), 'ت': ('تاء', 'tāʾ'), 'ث': ('ثاء', 'thāʾ'), 'ج': ('جيم', 'jīm'),
    'ح': ('حاء', 'ḥāʾ'), 'خ': ('خاء', 'khāʾ'), 'د': ('دال', 'dāl'), 'ذ': ('ذال', 'dhāl'), 'ر': ('راء', 'rāʾ'),
    'ز': ('زاي', 'zāy'), 'س': ('سين', 'sīn'), 'ش': ('شين', 'shīn'), 'ص': ('صاد', 'ṣād'), 'ض': ('ضاد', 'ḍād'),
    'ط': ('طاء', 'ṭāʾ'), 'ظ': ('ظاء', 'ẓāʾ'), 'ع': ('عين', 'ʿayn'), 'غ': ('غين', 'ghayn'), 'ف': ('فاء', 'fāʾ'),
    'ق': ('قاف', 'qāf'), 'ك': ('كاف', 'kāf'), 'ل': ('لام', 'lām'), 'م': ('ميم', 'mīm'), 'ن': ('نون', 'nūn'),
    'ه': ('هاء', 'hāʾ'), 'و': ('واو', 'wāw'), 'ي': ('ياء', 'yāʾ'), 'ء': ('همزة', 'hamza'),
    'أ': ('همزة على الألف', 'hamza ʿalā al-alif'), 'إ': ('همزة تحت الألف', 'hamza taḥta al-alif'),
    'آ': ('ألف مدة', 'alif madda'), 'ؤ': ('همزة على الواو', 'hamza ʿalā al-wāw'),
    'ئ': ('همزة على الياء', 'hamza ʿalā al-yāʾ'), 'ة': ('تاء مربوطة', 'tāʾ marbūṭa'), 'ى': ('ألف مقصورة', 'alif maqṣūra'),
    'ٱ': ('ألف الوصل', 'alif al-waṣl'),
    'َ': ('فتحة', 'fatḥa'), 'ُ': ('ضمة', 'ḍamma'), 'ِ': ('كسرة', 'kasra'), 'ً': ('تنوين الفتح', 'tanwīn al-fatḥ'),
    'ٌ': ('تنوين الضم', 'tanwīn aḍ-ḍamm'), 'ٍ': ('تنوين الكسر', 'tanwīn al-kasr'), 'ْ': ('سكون', 'sukūn'),
    'ّ': ('شدة', 'shadda'), 'ٰ': ('ألف خنجرية', 'alif khanjariyya'),
}
# ペルシア語 (ペルシア語の字はペルシア語の綴り。共通の記号もペルシア語の呼び名で)
PERSIAN = {
    'ا': ('الف', 'alef'), 'آ': ('الف مد', 'alef-e madd'), 'ب': ('بِ', 'be'), 'پ': ('پِ', 'pe'), 'ت': ('تِ', 'te'),
    'ث': ('ثِ', 'se'), 'ج': ('جیم', 'jim'), 'چ': ('چِ', 'če'), 'ح': ('حِ', 'he'), 'خ': ('خِ', 'xe'), 'د': ('دال', 'dāl'),
    'ذ': ('ذال', 'zāl'), 'ر': ('رِ', 're'), 'ز': ('زِ', 'ze'), 'ژ': ('ژِ', 'že'), 'س': ('سین', 'sin'), 'ش': ('شین', 'šin'),
    'ص': ('صاد', 'sād'), 'ض': ('ضاد', 'zād'), 'ط': ('طا', 'tā'), 'ظ': ('ظا', 'zā'), 'ع': ('عین', 'eyn'), 'غ': ('غین', 'qeyn'),
    'ف': ('فِ', 'fe'), 'ق': ('قاف', 'qāf'), 'ک': ('کاف', 'kāf'), 'گ': ('گاف', 'gāf'), 'ل': ('لام', 'lām'),
    'م': ('میم', 'mim'), 'ن': ('نون', 'nun'), 'و': ('واو', 'vāv'), 'ه': ('هِ', 'he'), 'ی': ('یِ', 'ye'),
    'ء': ('همزه', 'hamze'), 'أ': ('الف همزه', 'alef hamze'), 'ئ': ('یِ همزه', 'ye hamze'), 'ؤ': ('واو همزه', 'vāv hamze'),
    'ة': ('تِ گرد', 'te-ye gerd'),
    'َ': ('زبر', 'zabar'), 'ِ': ('زیر', 'zir'), 'ُ': ('پیش', 'piš'), 'ّ': ('تشدید', 'tašdid'),
    'ْ': ('سکون', 'sokun'), 'ً': ('تنوین', 'tanvin'), 'ٔ': ('همزه', 'hamze'),
}
URDU = {
    'ا': ('الف', 'alif'), 'آ': ('الف مدہ', 'alif madda'), 'ب': ('بے', 'be'), 'پ': ('پے', 'pe'), 'ت': ('تے', 'te'),
    'ٹ': ('ٹے', 'ṭe'), 'ث': ('ثے', 'se'), 'ج': ('جیم', 'jīm'), 'چ': ('چے', 'ce'), 'ح': ('بڑی حے', 'baṛī he'),
    'خ': ('خے', 'khe'), 'د': ('دال', 'dāl'), 'ڈ': ('ڈال', 'ḍāl'), 'ذ': ('ذال', 'zāl'), 'ر': ('رے', 're'), 'ڑ': ('ڑے', 'ṛe'),
    'ز': ('زے', 'ze'), 'ژ': ('ژے', 'zhe'), 'س': ('سین', 'sīn'), 'ش': ('شین', 'shīn'), 'ص': ('صاد', 'suād'),
    'ض': ('ضاد', 'zuād'), 'ط': ('طوئے', 'toe'), 'ظ': ('ظوئے', 'zoe'), 'ع': ('عین', 'ain'), 'غ': ('غین', 'ghain'),
    'ف': ('فے', 'fe'), 'ق': ('قاف', 'qāf'), 'ک': ('کاف', 'kāf'), 'گ': ('گاف', 'gāf'), 'ل': ('لام', 'lām'),
    'م': ('میم', 'mīm'), 'ن': ('نون', 'nūn'), 'ں': ('نون غنہ', 'nūn ghunna'), 'و': ('واؤ', 'wāo'),
    'ہ': ('چھوٹی ہے', 'choṭī he'), 'ھ': ('دو چشمی ہے', 'do-cashmī he'), 'ء': ('ہمزہ', 'hamza'), 'ی': ('چھوٹی یے', 'choṭī ye'),
    'ے': ('بڑی یے', 'baṛī ye'), 'ئ': ('ہمزہ', 'hamza'), 'ۓ': ('بڑی یے ہمزہ', 'baṛī ye hamza'),
    'َ': ('زبر', 'zabar'), 'ِ': ('زیر', 'zer'), 'ُ': ('پیش', 'pesh'), 'ّ': ('تشدید', 'tashdīd'),
    'ْ': ('جزم', 'jazm'), 'ٔ': ('ہمزہ', 'hamza'),
}
HEBREW = {
    'א': ('אלף', 'alef'), 'ב': ('בית', 'bet'), 'ג': ('גימל', 'gimel'), 'ד': ('דלת', 'dalet'), 'ה': ('הא', 'he'),
    'ו': ('וו', 'vav'), 'ז': ('זין', 'zayin'), 'ח': ('חית', 'ḥet'), 'ט': ('טית', 'ṭet'), 'י': ('יוד', 'yod'),
    'כ': ('כף', 'kaf'), 'ך': ('כף סופית', 'kaf sofit'), 'ל': ('למד', 'lamed'), 'מ': ('מם', 'mem'),
    'ם': ('מם סופית', 'mem sofit'), 'נ': ('נון', 'nun'), 'ן': ('נון סופית', 'nun sofit'), 'ס': ('סמך', 'samekh'),
    'ע': ('עין', 'ayin'), 'פ': ('פא', 'pe'), 'ף': ('פא סופית', 'pe sofit'), 'צ': ('צדי', 'tsadi'),
    'ץ': ('צדי סופית', 'tsadi sofit'), 'ק': ('קוף', 'qof'), 'ר': ('ריש', 'resh'), 'ש': ('שין', 'shin'), 'ת': ('תו', 'tav'),
    'ְ': ('שווא', 'shva'), 'ֱ': ('חטף סגול', 'ḥataf segol'), 'ֲ': ('חטף פתח', 'ḥataf pataḥ'),
    'ֳ': ('חטף קמץ', 'ḥataf qamats'), 'ִ': ('חיריק', 'ḥiriq'), 'ֵ': ('צירה', 'tsere'), 'ֶ': ('סגול', 'segol'),
    'ַ': ('פתח', 'pataḥ'), 'ָ': ('קמץ', 'qamats'), 'ֹ': ('חולם', 'ḥolam'), 'ֺ': ('חולם', 'ḥolam'),
    'ֻ': ('קובוץ', 'qubuts'), 'ּ': ('דגש', 'dagesh'), 'ׁ': ('נקודת שין', 'shin dot'),
    'ׂ': ('נקודת שׂין', 'sin dot'),
}
# ハングルの字母 (Unicode の名前の字母の部分 → 呼び名)
HANGUL = {
    'KIYEOK': ('기역', 'giyeok'), 'SSANGKIYEOK': ('쌍기역', 'ssanggiyeok'), 'NIEUN': ('니은', 'nieun'),
    'TIKEUT': ('디귿', 'digeut'), 'SSANGTIKEUT': ('쌍디귿', 'ssangdigeut'), 'RIEUL': ('리을', 'rieul'),
    'MIEUM': ('미음', 'mieum'), 'PIEUP': ('비읍', 'bieup'), 'SSANGPIEUP': ('쌍비읍', 'ssangbieup'), 'SIOS': ('시옷', 'siot'),
    'SSANGSIOS': ('쌍시옷', 'ssangsiot'), 'IEUNG': ('이응', 'ieung'), 'CIEUC': ('지읒', 'jieut'),
    'SSANGCIEUC': ('쌍지읒', 'ssangjieut'), 'CHIEUCH': ('치읓', 'chieut'), 'KHIEUKH': ('키읔', 'kieuk'),
    'THIEUTH': ('티읕', 'tieut'), 'PHIEUPH': ('피읖', 'pieup'), 'HIEUH': ('히읗', 'hieut'),
    'A': ('아', 'a'), 'AE': ('애', 'ae'), 'YA': ('야', 'ya'), 'YAE': ('얘', 'yae'), 'EO': ('어', 'eo'), 'E': ('에', 'e'),
    'YEO': ('여', 'yeo'), 'YE': ('예', 'ye'), 'O': ('오', 'o'), 'WA': ('와', 'wa'), 'WAE': ('왜', 'wae'), 'OE': ('외', 'oe'),
    'YO': ('요', 'yo'), 'U': ('우', 'u'), 'WEO': ('워', 'wo'), 'WE': ('웨', 'we'), 'WI': ('위', 'wi'), 'YU': ('유', 'yu'),
    'EU': ('으', 'eu'), 'YI': ('의', 'ui'), 'I': ('이', 'i'),
}
# デーヴァナーガリーの母音記号 → 独立の母音字
MATRAS = dict(zip('ािीुूृॄेैोौ',
                  'आइईउऊऋॠएऐओऔ'))
SANSKRIT_SIGNS = {'्': ('विरामः', 'virāmaḥ'), 'ं': ('अनुस्वारः', 'anusvāraḥ'), 'ः': ('विसर्गः', 'visargaḥ'),
                  'ँ': ('अनुनासिकः', 'anunāsikaḥ'), 'ऽ': ('अवग्रहः', 'avagrahaḥ')}
HINDI_SIGNS = {'्': ('हलंत', 'halant'), 'ं': ('अनुस्वार', 'anusvār'), 'ः': ('विसर्ग', 'visarg'),
               'ँ': ('चंद्रबिंदु', 'candrabindu'), '़': ('नुक़्ता', 'nuqtā')}
TIBETAN = {'ི': ('གི་གུ', 'gi gu'), 'ུ': ('ཞབས་ཀྱུ', 'zhabs kyu'), 'ེ': ('འགྲེང་བུ', "'greng bu"),
           'ོ': ('ན་རོ', 'na ro'), 'ྱ': ('ཡ་བཏགས', 'ya btags'), 'ྲ': ('ར་བཏགས', 'ra btags'),
           'ླ': ('ལ་བཏགས', 'la btags'), 'ྭ': ('ཝ་ཟུར', 'wa zur'), 'ཱ': ('འ་ཆུང', "'a chung"),
           'ཾ': ('རྗེས་སུ་ང་རོ', 'rjes su nga ro'), '྄': ('སྲོག་མེད', 'srog med')}


# デーヴァナーガリーの字の転写 (IAST)
IAST = dict(zip('अआइईउऊऋॠऌएऐओऔ', ['a', 'ā', 'i', 'ī', 'u', 'ū', 'ṛ', 'ṝ', 'ḷ', 'e', 'ai', 'o', 'au']))
IAST.update(zip('कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह',
                ['ka', 'kha', 'ga', 'gha', 'ṅa', 'ca', 'cha', 'ja', 'jha', 'ña', 'ṭa', 'ṭha', 'ḍa', 'ḍha', 'ṇa', 'ta', 'tha',
                 'da', 'dha', 'na', 'pa', 'pha', 'ba', 'bha', 'ma', 'ya', 'ra', 'la', 'va', 'śa', 'ṣa', 'sa', 'ha']))
IAST.update({'ळ': 'ḷa', 'क़': 'qa', 'ख़': 'xa', 'ग़': 'ġa', 'ज़': 'za', 'ड़': 'ṛa', 'ढ़': 'ṛha', 'फ़': 'fa'})


def _devanagari_roman(ch):
    """デーヴァナーガリーの字の転写 (IAST: क → ka、आ → ā、ढ → ḍha)"""
    return IAST.get(ch, '')


# 悉曇文字 (梵字) の字母の日本の読み (IAST → 読み)。ka の a は「キャ」、na は「ナウ」(悉曇の字母表の読み)
SHITTAN = {'a': 'ア', 'ā': 'アー', 'i': 'イ', 'ī': 'イー', 'u': 'ウ', 'ū': 'ウー', 'ṛ': 'キリ', 'ṝ': 'キリー',
           'ḷ': 'リョ', 'ḹ': 'リョー', 'e': 'エイ', 'ai': 'アイ', 'o': 'オウ', 'au': 'アウ',
           'ka': 'キャ', 'kha': 'キャ', 'ga': 'ギャ', 'gha': 'ギャ', 'ṅa': 'ギャウ',
           'ca': 'シャ', 'cha': 'シャ', 'ja': 'ジャ', 'jha': 'ジャ', 'ña': 'ジャ',
           'ṭa': 'タ', 'ṭha': 'タ', 'ḍa': 'ダ', 'ḍha': 'ダ', 'ṇa': 'ダ',
           'ta': 'タ', 'tha': 'タ', 'da': 'ダ', 'dha': 'ダ', 'na': 'ナウ',
           'pa': 'ハ', 'pha': 'ハ', 'ba': 'バ', 'bha': 'バ', 'ma': 'マ',
           'ya': 'ヤ', 'ra': 'ラ', 'la': 'ラ', 'va': 'バ', 'śa': 'シャ', 'ṣa': 'シャ', 'sa': 'サ', 'ha': 'カ'}
# 悉曇文字の点 (日本の名前と読み): ā の画は修行点、ṃ は空点 (菩提点)、ḥ は涅槃点、ँ は仰月点
SHITTAN_SIGNS = {'\U000115af': ('修行点', 'アー'), '\U000115bd': ('空点', 'ン'), '\U000115be': ('涅槃点', 'ク'),
                 '\U000115bc': ('仰月点', 'ン')}


def _siddham(ch):
    """悉曇文字の字の日本の読み (\U0001158e → キャ、\U000115bd → 空点 ン)。同じ名前のデーヴァナーガリーの字から"""
    if ch in SHITTAN_SIGNS:
        return SHITTAN_SIGNS[ch]
    try:
        d = unicodedata.lookup('DEVANAGARI' + unicodedata.name(ch)[len('SIDDHAM'):])
    except KeyError:
        return None
    roman = IAST.get(MATRAS.get(d, d), '')
    reading = SHITTAN.get(roman)
    return (reading, '') if reading else None


def _sanskrit(ch):
    if unicodedata.name(ch, '').startswith('SIDDHAM '):
        return _siddham(ch)
    if ch in SANSKRIT_SIGNS:
        return SANSKRIT_SIGNS[ch]
    if ch in MATRAS:   # ि → इकार ikāra
        vowel = MATRAS[ch]
        return vowel + 'कार', _devanagari_roman(vowel) + 'kāra'
    if unicodedata.name(ch, '').startswith('DEVANAGARI LETTER '):   # क → ककार kakāra、इ → इकार ikāra
        return ch + 'कार', _devanagari_roman(ch) + 'kāra'
    return None


def _hindi(ch):
    if ch in HINDI_SIGNS:
        return HINDI_SIGNS[ch]
    if ch in MATRAS:   # ि → इ की मात्रा i kī mātrā
        vowel = MATRAS[ch]
        return vowel + ' की मात्रा', _devanagari_roman(vowel) + ' kī mātrā'
    return None


def _korean(ch):
    name = unicodedata.name(ch, '')
    for kind in ('HANGUL CHOSEONG ', 'HANGUL JUNGSEONG ', 'HANGUL JONGSEONG ', 'HANGUL LETTER '):
        if name.startswith(kind):
            return HANGUL.get(name[len(kind):])
    return None


# モンゴル文字: 母音は字そのもの、子音は a を付けた音節 (字母表の呼び方: na・ba・qa …)。ᠩ は ang。
# 呼び名は伝統文字の綴りと、転写 (キリル文字の書き方)
MONGOLIAN_LETTERS = [('ᠠ', 'a', 'а'), ('ᠡ', 'e', 'э'), ('ᠢ', 'i', 'и'), ('ᠣ', 'o', 'о'), ('ᠤ', 'u', 'у'), ('ᠥ', 'ö', 'ө'),
                     ('ᠦ', 'ü', 'ү'), ('ᠨ', 'na', 'на'), ('ᠪ', 'ba', 'ба'), ('ᠬ', 'qa', 'ха'), ('ᠭ', 'γa', 'га'),
                     ('ᠮ', 'ma', 'ма'), ('ᠯ', 'la', 'ла'), ('ᠰ', 'sa', 'са'), ('ᠱ', 'ša', 'ша'), ('ᠲ', 'ta', 'та'),
                     ('ᠳ', 'da', 'да'), ('ᠴ', 'ča', 'ча'), ('ᠵ', 'ǰa', 'жа'), ('ᠶ', 'ya', 'яа'), ('ᠷ', 'ra', 'ра'),
                     ('ᠸ', 'wa', 'ва'), ('ᠫ', 'pa', 'па'), ('ᠹ', 'fa', 'фа'), ('ᠺ', 'ka', 'ка'), ('ᠼ', 'ca', 'ца'),
                     ('ᠽ', 'za', 'за'), ('ᠾ', 'ha', 'һа')]
MONGOLIAN = {ch: (ch if roman in 'aeiouöü' else ch + 'ᠠ', '%s (%s)' % (roman, cyr)) for ch, roman, cyr in MONGOLIAN_LETTERS}
MONGOLIAN['ᠩ'] = ('ᠠᠩ', 'ang (анг)')
# 前舌母音の語 (a・o・u の無い語) の ᠬ・ᠭ は ke・ge (転写の k・g に合わせて)
MONGOLIAN_FRONT = {'ᠬ': ('ᠬᠡ', 'ke (кэ)'), 'ᠭ': ('ᠭᠡ', 'ge (гэ)')}


def _mongolian(ch, word=''):
    if ch.lower() in MONGOLIAN_CYRILLIC and not ('\u1800' <= ch <= '\u18af'):   # キリル文字の語
        return MONGOLIAN_CYRILLIC[ch.lower()]
    if ch in MONGOLIAN_FRONT and word and not any(c in word for c in 'ᠠᠣᠤ'):
        return MONGOLIAN_FRONT[ch]
    return MONGOLIAN.get(ch)

# ギリシア文字 (古典ギリシア語の呼び名) と、アクセント・気息記号 (分解した結合記号)
GREEK = {
    'α': ('ἄλφα', 'alpha'), 'β': ('βῆτα', 'bēta'), 'γ': ('γάμμα', 'gamma'), 'δ': ('δέλτα', 'delta'),
    'ε': ('ἒ ψιλόν', 'e psilon'), 'ζ': ('ζῆτα', 'zēta'), 'η': ('ἦτα', 'ēta'), 'θ': ('θῆτα', 'thēta'), 'ι': ('ἰῶτα', 'iōta'),
    'κ': ('κάππα', 'kappa'), 'λ': ('λάμβδα', 'lambda'), 'μ': ('μῦ', 'mu'), 'ν': ('νῦ', 'nu'), 'ξ': ('ξῖ', 'xi'),
    'ο': ('ὂ μικρόν', 'o mikron'), 'π': ('πῖ', 'pi'), 'ρ': ('ῥῶ', 'rhō'), 'σ': ('σῖγμα', 'sigma'),
    'ς': ('σῖγμα τελικόν', 'sigma telikon'), 'τ': ('ταῦ', 'tau'), 'υ': ('ὖ ψιλόν', 'u psilon'), 'φ': ('φῖ', 'phi'),
    'χ': ('χῖ', 'chi'), 'ψ': ('ψῖ', 'psi'), 'ω': ('ὦ μέγα', 'ō mega'),
    '\u0301': ('ὀξεῖα', 'oxeia (鋭アクセント)'), '\u0300': ('βαρεῖα', 'bareia (重アクセント)'),
    '\u0342': ('περισπωμένη', 'perispōmenē (曲アクセント)'), '\u0313': ('ψιλή', 'psilē (無気記号)'),
    '\u0314': ('δασεῖα', 'daseia (有気記号)'), '\u0345': ('ὑπογεγραμμένη', 'hypogegrammenē (下書きのイオタ)'),
    '\u0308': ('διαλυτικά', 'dialytika (分音記号)'),
}
RUSSIAN = {
    'а': ('а', 'a'), 'б': ('бэ', 'be'), 'в': ('вэ', 've'), 'г': ('гэ', 'ge'), 'д': ('дэ', 'de'), 'е': ('е', 'ye'),
    'ё': ('ё', 'yo'), 'ж': ('жэ', 'zhe'), 'з': ('зэ', 'ze'), 'и': ('и', 'i'), 'й': ('и краткое', 'i kratkoye'),
    'к': ('ка', 'ka'), 'л': ('эль', 'el'), 'м': ('эм', 'em'), 'н': ('эн', 'en'), 'о': ('о', 'o'), 'п': ('пэ', 'pe'),
    'р': ('эр', 'er'), 'с': ('эс', 'es'), 'т': ('тэ', 'te'), 'у': ('у', 'u'), 'ф': ('эф', 'ef'), 'х': ('ха', 'kha'),
    'ц': ('цэ', 'tse'), 'ч': ('че', 'che'), 'ш': ('ша', 'sha'), 'щ': ('ща', 'shcha'), 'ъ': ('твёрдый знак', 'tvyordyy znak'),
    'ы': ('ы', 'y'), 'ь': ('мягкий знак', 'myagkiy znak'), 'э': ('э', 'e'), 'ю': ('ю', 'yu'), 'я': ('я', 'ya'),
    '\u0301': ('знак ударения', 'znak udareniya (アクセント記号)'),
}
# モンゴル語のキリル文字 (ロシア語の字に ө・ү を足し、呼び名はモンゴル語の)
MONGOLIAN_CYRILLIC = dict(RUSSIAN)
MONGOLIAN_CYRILLIC.update({
    'л': ('эл', 'el'), 'й': ('хагас и', 'khagas i'), 'ө': ('ө', 'ö'), 'ү': ('ү', 'ü'), 'ф': ('фэ', 'fe'),
    'х': ('хэ', 'khe'), 'ч': ('чэ', 'che'), 'ъ': ('хатуугийн тэмдэг', 'khatuugiin temdeg'),
    'ь': ('зөөлний тэмдэг', 'zööln temdeg'), 'е': ('йе', 'ye'), 'ё': ('йо', 'yo'), 'ю': ('йү', 'yü'), 'я': ('йа', 'ya'),
})


def _lower_table(table):
    return lambda ch, word='': table.get(ch.lower())


TABLES = {'ar': ARABIC, 'fa': PERSIAN, 'ur': URDU, 'he': HEBREW, 'bo': TIBETAN}
FUNCTIONS = {'ko': _korean, 'sa': _sanskrit, 'hi': _hindi, 'mn': _mongolian}


def native(lang):
    """言語の字の呼び名の関数 ((字, 語) → (呼び名の字, 転写) / None。語は母音調和で呼び名の変わる字のため)。
    呼び名の表の無い言語は None"""
    if lang in ('grc', 'el'):
        return _lower_table(GREEK)
    if lang == 'ru':
        return _lower_table(RUSSIAN)
    if lang in TABLES:
        table = TABLES[lang]
        return lambda ch, word='': table.get(ch)
    f = FUNCTIONS.get(lang)
    if f is None:
        return None
    return f if f is _mongolian else (lambda ch, word='': f(ch))
