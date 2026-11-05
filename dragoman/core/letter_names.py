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


def _sanskrit(ch):
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

TABLES = {'ar': ARABIC, 'fa': PERSIAN, 'ur': URDU, 'he': HEBREW, 'bo': TIBETAN, 'mn': MONGOLIAN}
FUNCTIONS = {'ko': _korean, 'sa': _sanskrit, 'hi': _hindi}


def native(lang):
    """言語の字の呼び名の関数 (字 → (呼び名の字, 転写) / None)。呼び名の表の無い言語は None"""
    if lang in TABLES:
        return TABLES[lang].get
    return FUNCTIONS.get(lang)
