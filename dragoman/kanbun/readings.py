#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文訓読の読み: 用言の訓 (送り仮名と活用)、副詞・代名詞の読み、新字体
#
#   用言の訓は、よく出る字は手作りの表 (VERBS。語義 (UD-Kanbun の Gloss) で読み分ける)、無ければ KANJIDIC2 の訓
#   (EDRDG、CC BY-SA 4.0。$DRAGOMAN_DATA/kanjidic/kanjidic2.xml.gz) と JMdict の英語の語義を Gloss と突き合わせて選び、
#   古文の活用の型 (generate/kobun.classical_verb) に直す。どれも無ければ音読み + す (サ変)
#
#   表の書き方: 文語の終止形 (歴史的仮名遣い)。活用の種類は既定で、語尾のかなから四段 (學ぶ・習ふ)、り なら ラ変 (有り)、
#   し なら ク活用 (多し)。ほかは /上二・/下二・/上一・/サ変・/ザ変・/ナ変・/シク・/ナリ で示す。
#   漢字だけで終止形になる語 (得 う) は活用形を6つ並べる
#
import functools
import gzip
import os
import re

from dragoman.core import paths

KANJIDIC_PATH = paths.data('kanjidic', 'kanjidic2.xml.gz')
FORMS = ('未然', '連用', '終止', '連体', '已然', '命令')
ROWS = {'か': 'カ', 'き': 'カ', 'く': 'カ', 'け': 'カ', 'が': 'ガ', 'ぎ': 'ガ', 'ぐ': 'ガ', 'げ': 'ガ', 'さ': 'サ', 'し': 'サ',
        'す': 'サ', 'せ': 'サ', 'ず': 'ザ', 'じ': 'ザ', 'た': 'タ', 'ち': 'タ', 'つ': 'タ', 'て': 'タ', 'だ': 'ダ', 'ぢ': 'ダ',
        'づ': 'ダ', 'な': 'ナ', 'に': 'ナ', 'ぬ': 'ナ', 'ね': 'ナ', 'は': 'ハ', 'ひ': 'ハ', 'ふ': 'ハ', 'へ': 'ハ', 'ば': 'バ',
        'び': 'バ', 'ぶ': 'バ', 'べ': 'バ', 'ま': 'マ', 'み': 'マ', 'む': 'マ', 'め': 'マ', 'ゆ': 'ヤ', 'ら': 'ラ', 'り': 'ラ',
        'る': 'ラ', 'れ': 'ラ', 'う': 'ア'}
KANA_ROWS = {'カ': 'かきくけこ', 'ガ': 'がぎぐげご', 'サ': 'さしすせそ', 'ザ': 'ざじずぜぞ', 'タ': 'たちつてと',
             'ダ': 'だぢづでど', 'ナ': 'なにぬねの', 'ハ': 'はひふへほ', 'バ': 'ばびぶべぼ', 'マ': 'まみむめも',
             'ヤ': 'やいゆえよ', 'ラ': 'らりるれろ', 'ワ': 'わゐうゑを', 'ア': 'あいうえお'}
ENDINGS = {'四段': ('a', 'i', 'u', 'u', 'e', 'e'),
           '上二': ('i', 'i', 'u', 'u+る', 'u+れ', 'i+よ'),
           '下二': ('e', 'e', 'u', 'u+る', 'u+れ', 'e+よ')}
VOWELS = 'aiueo'
IRREGULAR = {'サ変': ('せ', 'し', 'す', 'する', 'すれ', 'せよ'), 'ザ変': ('ぜ', 'じ', 'ず', 'ずる', 'ずれ', 'ぜよ'),
             'ナ変': ('な', 'に', 'ぬ', 'ぬる', 'ぬれ', 'ね'), 'ラ変': ('ら', 'り', 'り', 'る', 'れ', 'れ'),
             'カ変': ('こ', 'き', 'く', 'くる', 'くれ', 'こよ'), '上一': ('', '', 'る', 'る', 'れ', 'よ')}
ADJECTIVE_FORMS = {'ク': ('く', 'く', 'し', 'き', 'けれ', 'かれ'), 'シク': ('しく', 'しく', 'し', 'しき', 'しけれ', 'しかれ')}
ADJECTIVE_AUX = {'ク': ('から', 'かり', 'し', 'かる', 'けれ', 'かれ'), 'シク': ('しから', 'しかり', 'し', 'しかる', 'しけれ', 'しかれ')}
NARI = ('なら', 'に', 'なり', 'なる', 'なれ', 'なれ')
NARI_AUX = ('なら', 'なり', 'なり', 'なる', 'なれ', 'なれ')


class Predicate:
    """用言の活用: form('未然') → 入ら、form('未然', aux=True) → 楽しから (形容詞は助動詞の前でカリ活用)"""

    def __init__(self, forms, aux_forms=None, kind='', base=''):
        self.forms, self.aux_forms, self.kind, self.base = forms, aux_forms or forms, kind, base

    def form(self, name, aux=False):
        return (self.aux_forms if aux else self.forms)[FORMS.index(name)]

    @property
    def adjective(self):
        return self.kind in ('ク', 'シク', 'ナリ')

    def __repr__(self):
        return '%s(%s)' % (self.forms[2], self.kind)


def predicate(spec):
    """表の書き方 (學ぶ / 改む/下二 / 樂し/シク / 6つの活用形の組) → Predicate"""
    if isinstance(spec, tuple):
        return Predicate(spec, kind='下二', base=spec[2])
    word, _, kind = spec.partition('/')
    last = word[-1]
    if not kind:
        kind = 'ラ変' if last == 'り' else 'ク' if last == 'し' else '四段'
    if kind in ('ク', 'シク'):
        stem = word[:-1]
        return Predicate(tuple(stem + e for e in ADJECTIVE_FORMS[kind]), tuple(stem + e for e in ADJECTIVE_AUX[kind]),
                         kind, word)
    if kind == 'ナリ':
        stem = word[:-2] if word.endswith('なり') else word
        return Predicate(tuple(stem + e for e in NARI), tuple(stem + e for e in NARI_AUX), kind, word)
    if kind in IRREGULAR:
        cut = {'サ変': 1, 'ザ変': 1, 'ナ変': 1, 'ラ変': 1, 'カ変': 1, '上一': 1}[kind]
        stem = word[:-cut]
        return Predicate(tuple(stem + e for e in IRREGULAR[kind]), kind=kind, base=word)
    row = 'ハ' if last == 'う' and kind == '四段' else ROWS.get(last, 'ラ')
    if kind in ('上二', '下二') and last == 'う':
        row = 'ア'
    stem = word[:-1]
    forms = []
    for ending in ENDINGS[kind]:
        vowel, _, tail = ending.partition('+')
        forms.append(stem + KANA_ROWS[row][VOWELS.index(vowel)] + tail)
    return Predicate(tuple(forms), kind=kind, base=word)


# 用言の訓: 字 → [(読み, 語義の正規表現 / None (既定))]。語義は UD-Kanbun の Gloss (英語)
VERBS = {
    '學': [('學ぶ', None)], '習': [('習ふ', None)], '說': [('說ばし/シク', 'relax|pleas|happ|glad|delight'), ('說く', None)],
    '悅': [('悅ぶ', None)], '樂': [('樂し/シク', None)], '知': [('知る', None)], '見': [('見る/上一', None)],
    '聞': [('聞く', None)], '言': [('言ふ', None)], '謂': [('謂ふ', None)], '云': [('云ふ', None)], '曰': [('曰ふ', None)],
    '行': [('行ふ', 'do|perform|practi|carry'), ('行く', None)], '來': [('來たる', None)], '往': [('往く', None)],
    '之': [('之く', None)], '至': [('至る', None)], '入': [('入る', None)], '出': [('出づ/下二', None)],
    '得': [(('得', '得', '得', '得る', '得れ', '得よ'), None)], '施': [('施す', None)], '爲': [('爲す', None)],
    '為': [('為す', None)], '立': [('立つ', None)], '生': [('生ず/ザ変', 'born|produc|arise|grow'), ('生く', None)],
    '死': [('死す/サ変', None)], '食': [('食らふ', None)], '飮': [('飮む', None)], '飲': [('飲む', None)],
    '思': [('思ふ', None)], '念': [('念ふ', None)], '好': [('好む', None)], '惡': [('惡む', None)], '愛': [('愛す/サ変', None)],
    '問': [('問ふ', None)], '對': [('對ふ/下二', None)], '答': [('答ふ/下二', None)], '使': [('使ふ', None)],
    '用': [('用ふ/上二', None)], '求': [('求む/下二', None)], '去': [('去る', None)], '歸': [('歸る', None)],
    '居': [('居り/ラ変', None)], '在': [('在り', None)], '有': [('有り', None)], '無': [('無し', None)], '莫': [('莫し', None)],
    '多': [('多し', None)], '少': [('少なし', None)], '寡': [('寡なし', None)], '大': [('大いなり/ナリ', None)],
    '小': [('小なり/ナリ', None)], '善': [('善し', None)], '美': [('美し/シク', None)], '貴': [('貴し', None)],
    '賤': [('賤し/シク', None)], '亡': [('亡ぶ/上二', None)], '攻': [('攻む/下二', None)], '守': [('守る', None)],
    '戰': [('戰ふ', None)], '勝': [('勝つ', None)], '敗': [('敗る/下二', None)], '殺': [('殺す', None)], '取': [('取る', None)],
    '與': [('與ふ/下二', None)], '告': [('告ぐ/下二', None)], '敎': [('敎ふ/下二', None)], '教': [('教ふ/下二', None)],
    '憂': [('憂ふ/下二', None)], '患': [('患ふ/下二', None)], '怒': [('怒る', None)], '畏': [('畏る/下二', None)],
    '恐': [('恐る/下二', None)], '信': [('信ず/ザ変', None)], '及': [('及ぶ', None)],
    '過': [('過つ', 'err|mistake|fault'), ('過ぐ/上二', None)], '改': [('改む/下二', None)], '遊': [('遊ぶ', None)],
    '待': [('待つ', None)], '讀': [('讀む', None)], '書': [('書す/サ変', None)], '作': [('作る', None)], '成': [('成る', None)],
    '終': [('終はる', None)], '始': [('始む/下二', None)], '聽': [('聽く', None)], '視': [('視る/上一', None)],
    '觀': [('觀る/上一', None)], '望': [('望む', None)], '登': [('登る', None)], '遇': [('遇ふ', None)], '逢': [('逢ふ', None)],
    '會': [('會す/サ変', None)], '送': [('送る', None)], '別': [('別る/下二', None)], '臥': [('臥す', None)],
    '眠': [('眠る', None)], '醉': [('醉ふ', None)], '飛': [('飛ぶ', None)], '落': [('落つ/上二', None)], '開': [('開く', None)],
    '照': [('照らす', None)], '流': [('流る/下二', None)], '鳴': [('鳴く', None)], '啼': [('啼く', None)], '笑': [('笑ふ', None)],
    '泣': [('泣く', None)], '喜': [('喜ぶ', None)], '悲': [('悲しむ', None)], '覺': [('覺ゆ/下二', None)],
    '破': [('破る/下二', None)], '溫': [('溫む/下二', None)], '温': [('温む/下二', None)], '新': [('新し/シク', None)],
    '故': [('故し', None)], '長': [('長ず/ザ変', None)], '青': [('青し', None)], '白': [('白し', None)], '赤': [('赤し', None)],
    '黑': [('黑し', None)], '遠': [('遠し', None)], '近': [('近し', None)], '高': [('高し', None)], '深': [('深し', None)],
    '淺': [('淺し', None)], '老': [('老ゆ/上二', None)], '易': [('易し', None)], '難': [('難し', None)], '安': [('安んず/ザ変', None)],
    '欲': [('欲す/サ変', None)], '如': [('如く', None)], '若': [('若く', None)], '非': [('非ず', None)], '罔': [('罔し', None)],
    '殆': [('殆し', None)], '仁': [('仁なり/ナリ', None)], '可': [('可なり/ナリ', None)], '寒': [('寒し', None)],
    '暖': [('暖かなり/ナリ', None)], '明': [('明らかなり/ナリ', None)], '靜': [('靜かなり/ナリ', None)],
    '盡': [('盡く/上二', None)], '窮': [('窮まる', None)], '止': [('止む', None)], '休': [('休む', None)], '息': [('息む', None)],
    '慕': [('慕ふ', None)], '懷': [('懷ふ', None)], '憐': [('憐れむ', None)], '畜': [('畜ふ', None)], '養': [('養ふ', None)],
    '治': [('治む/下二', None)], '亂': [('亂る/下二', None)], '定': [('定む/下二', None)], '學問': [('學問す/サ変', None)],
    '致': [('致す', None)], '格': [('格る', None)], '誠': [('誠にす/サ変', None)], '正': [('正す', None)], '修': [('修む/下二', None)],
    '齊': [('齊ふ/下二', None)], '平': [('平らかにす/サ変', None)], '還': [('還る', None)], '返': [('返る', None)],
    '令': [('令す/サ変', None)], '命': [('命ず/ザ変', None)], '從': [('從ふ', None)], '隨': [('隨ふ', None)],
    '奪': [('奪ふ', None)], '失': [('失ふ', None)], '捨': [('捨つ/下二', None)], '棄': [('棄つ/下二', None)],
    '逃': [('逃ぐ/下二', None)], '走': [('走る', None)], '射': [('射る/上一', None)], '釣': [('釣る', None)],
    '耕': [('耕す', None)], '折': [('折る', None)], '觸': [('觸る/下二', None)],
    '譽': [('譽む/下二', None)], '陷': [('陷す', None)], '誨': [('誨ふ/下二', None)], '省': [('省みる/上一', None)], '慍': [('慍る', None)],
    '然': [('然り', None)], '冀': [('冀ふ', None)], '因': [('因る', None)], '釋': [('釋つ/下二', None)], '倦': [('倦む', None)],
    '厭': [('厭く', None)], '惑': [('惑ふ', None)], '懼': [('懼る/下二', None)], '鬻': [('鬻ぐ', None)], '耕': [('耕す', None)], '應': [('應ふ/下二', None)],
}
# 送り仮名の要る副詞・接続の語: 字 → 書き下しの形
ADVERBS = {
    '亦': '亦た', '又': '又', '復': '復た', '必': '必ず', '常': '常に', '嘗': '嘗て', '曾': '曾て', '甚': '甚だ', '皆': '皆',
    '獨': '獨り', '且': '且つ', '既': '既に', '已': '已に', '方': '方に', '乃': '乃ち', '卽': '卽ち', '即': '即ち',
    '則': '則ち', '遂': '遂に', '終': '終に', '共': '共に', '俱': '倶に', '尙': '尙ほ', '相': '相', '徒': '徒らに',
    '稍': '稍', '益': '益', '愈': '愈', '豈': '豈に', '寧': '寧ろ', '唯': '唯だ', '惟': '惟だ', '只': '只だ', '但': '但だ',
    '果': '果たして', '敢': '敢へて', '能': '能く', '頗': '頗る', '殆': '殆ど', '蓋': '蓋し', '竊': '竊かに', '故': '故に',
    '何': '何ぞ', '安': '安くんぞ', '焉': '焉くんぞ', '惡': '惡くんぞ', '誰': '誰か', '孰': '孰れか', '奚': '奚ぞ',
    '胡': '胡ぞ', '曷': '曷ぞ', '幾': '幾ど', '縱': '縱ひ', '苟': '苟くも', '若': '若し', '如': '如し', '時': '時に',
    '初': '初め', '先': '先づ', '後': '後', '今': '今', '昔': '昔', '少': '少しく', '固': '固より', '良': '良に', '實': '實に',
    '誠': '誠に', '凡': '凡そ', '倂': '倂せて', '自': '自ら', '親': '親ら', '數': '數', '屢': '屢', '各': '各', '俄': '俄かに',
    '忽': '忽ち', '暫': '暫く', '偶': '偶', '適': '適', '終日': '終日', '嗚呼': '嗚呼', '多': '多く', '善': '善く',
    '再': '再び', '三': '三たび', '弗': '弗', '專': '專ら', '頻': '頻りに', '然': '然り', '於是': '是に於いて', '是以': '是を以て',
}
# 疑問・反語の副詞 (文末を未然形 + ん にする): 何ぞ〜ん・安くんぞ〜ん
QUESTION_ADVERBS = {'何', '安', '焉', '惡', '奚', '胡', '曷', '豈', '寧', '誰', '孰'}
# 代名詞・指示詞
PRONOUNS = {'之': '之', '我': '我', '吾': '吾', '予': '予', '余': '余', '汝': '汝', '爾': '爾', '女': '女', '其': '其れ',
            '此': '此れ', '是': '是れ', '彼': '彼', '斯': '斯れ', '夫': '夫れ', '或': '或るひと', '何': '何', '誰': '誰',
            '孰': '孰れ', '己': '己', '自': '自ら', '若': '若', '朕': '朕', '寡人': '寡人', '焉': '焉'}
DETERMINERS = {'其': '其の', '此': '此の', '是': '是の', '彼': '彼の', '斯': '斯の', '諸': '諸', '每': '每', '各': '各', '夫': '夫の'}
# 旧字体 → 新字体 (UD-Kanbun の見出しの簡体字・KANJIDIC2 の異体字で引けないもの)
SHINJITAI = {'說': '説', '來': '来', '爲': '為', '與': '与', '學': '学', '樂': '楽', '歸': '帰', '對': '対', '惡': '悪',
             '敎': '教', '戰': '戦', '讀': '読', '聽': '聴', '觀': '観', '會': '会', '醉': '酔', '覺': '覚', '溫': '温',
             '黑': '黒', '淺': '浅', '靜': '静', '盡': '尽', '亂': '乱', '齊': '斉', '從': '従', '隨': '随', '譽': '誉',
             '陷': '陥', '應': '応', '國': '国', '獸': '獣', '飮': '飲', '悅': '悦', '實': '実', '數': '数', '專': '専',
             '卽': '即', '尙': '尚', '獨': '独', '竊': '窃', '縱': '縦', '倂': '併', '觸': '触', '氣': '気', '聲': '声',
             '萬': '万', '舊': '旧', '經': '経', '歲': '歳', '晝': '昼', '鬪': '闘', '殘': '残', '處': '処', '虛': '虚',
             '禮': '礼', '體': '体', '號': '号', '佛': '仏', '傳': '伝', '圖': '図', '壽': '寿', '將': '将', '當': '当',
             '畫': '画', '發': '発', '盜': '盗', '眞': '真', '稱': '称', '絕': '絶', '續': '続', '總': '総', '聽': '聴',
             '藝': '芸', '變': '変', '豐': '豊', '轉': '転', '辭': '辞', '遲': '遅', '邊': '辺', '釋': '釈', '鐵': '鉄',
             '關': '関', '險': '険', '雙': '双', '靈': '霊', '顯': '顕', '驛': '駅', '驗': '験', '髮': '髪', '麥': '麦'}


def shinjitai(text, simplified=''):
    """旧字体の字を新字体に (表に無ければ見出しの簡体字が日本の字にもあればそれ)"""
    out = ''.join(SHINJITAI.get(c, c) for c in text)
    if out == text and simplified and len(simplified) == len(text) and simplified != text and _kanjidic().get(simplified):
        return simplified
    return out


@functools.lru_cache(maxsize=1)
def _kanjidic():
    """KANJIDIC2 → {字: (訓読み (送り仮名は . で区切る) の列, 音読みの列)}"""
    if not os.path.exists(KANJIDIC_PATH):
        return {}
    out = {}
    with gzip.open(KANJIDIC_PATH, 'rt', encoding='utf-8') as f:
        text = f.read()
    for m in re.finditer(r'<character>(.*?)</character>', text, re.S):
        body = m.group(1)
        literal = re.search(r'<literal>([^<]*)</literal>', body).group(1)
        kun = re.findall(r'<reading r_type="ja_kun">([^<]*)</reading>', body)
        on = re.findall(r'<reading r_type="ja_on">([^<]*)</reading>', body)
        out[literal] = (tuple(kun), tuple(on))
    return out


def kanjidic_available():
    return bool(_kanjidic())


def _gloss_words(gloss):
    return set(w for w in re.split(r'[^a-z]+', gloss.lower().replace('-', ' ')) if len(w) > 2)


@functools.lru_cache(maxsize=1)
def _ja_en():
    path = paths.data('ja-en.tsv')
    out = {}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                ja, _, en = line.rstrip('\n').partition('\t')
                out.setdefault(ja, en)
    return out


def _to_hiragana(kana):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in kana)


def _from_kanjidic(char, simplified, gloss):
    """KANJIDIC2 の訓 (送り仮名付き) から、JMdict の語義が Gloss に合う用言を選ぶ → 現代語の形 (学ぶ) / None"""
    new = shinjitai(char, simplified)
    kun = _kanjidic().get(new, ((), ()))[0] or _kanjidic().get(char, ((), ()))[0]
    wanted = _gloss_words(gloss)
    best, best_score = None, 0
    for reading in kun:
        if '.' not in reading or reading.startswith('-') or reading.endswith('-'):
            continue
        okuri = reading.split('.', 1)[1]
        word = new + okuri
        english = _ja_en().get(word, '')
        if not english:
            continue
        score = len(wanted & _gloss_words(english)) + 0.5
        if score > best_score:
            best, best_score = word, score
    return best


@functools.lru_cache(maxsize=10000)
def verb(char, simplified='', gloss=''):
    """用言の字 → Predicate (表 → KANJIDIC2 の訓 → 音読み + す)。字は元の字のまま (送り仮名だけ足す)"""
    for spec, pattern in VERBS.get(char, ()):
        if pattern is None or re.search(pattern, gloss or ''):
            return predicate(spec)
    modern = _from_kanjidic(char, simplified, gloss)
    if modern:
        from dragoman.generate.kobun import classical_verb, adjective_forms
        if modern.endswith('い') and adjective_forms(modern):
            stem, kind = adjective_forms(modern)
            return predicate(char + stem[len(shinjitai(char, simplified)):] + 'し' + ('/シク' if kind == 'シク' else ''))
        try:
            v = classical_verb(modern)
        except Exception:
            v = None
        if v is not None:
            kind = {'四段': '四段', '上二段': '上二', '下二段': '下二'}.get(v.kind, v.kind)
            forms = tuple(v.form(name) for name in FORMS)
            new = shinjitai(char, simplified)
            forms = tuple(char + f[len(new):] if f.startswith(new) else f for f in forms)
            return Predicate(forms, kind=kind, base=forms[2])
    if len(char) == 1:
        return predicate(char + 'す/サ変')
    return predicate(char + 'す/サ変')
