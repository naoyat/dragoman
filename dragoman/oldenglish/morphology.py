#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の機能語の表 (代名詞・前置詞・接続詞・否定の縮約・話法の動詞) と、訳語を決めておく語
#
# 鍵はどれも orthography.key の形 (長音符・点を除き、ð → þ)
#
from . import orthography

ALL_GENDERS = ('m', 'f', 'n')


def _cng(cases, number, genders=ALL_GENDERS):
    return [(c, number, g) for c in cases for g in genders]


# 人称代名詞: 鍵 → [(訳, 人称, 数, 格・数・性のリスト)]
PRONOUNS = {
    'ic': [('私', 1, 'sg', _cng(('Nom',), 'sg'))],
    'me': [('私', 1, 'sg', _cng(('Acc', 'Dat'), 'sg'))],
    'mec': [('私', 1, 'sg', _cng(('Acc',), 'sg'))],
    'þu': [('君', 2, 'sg', _cng(('Nom',), 'sg'))],
    'þe': [('君', 2, 'sg', _cng(('Acc', 'Dat'), 'sg'))],
    'þec': [('君', 2, 'sg', _cng(('Acc',), 'sg'))],
    'he': [('彼', 3, 'sg', [('Nom', 'sg', 'm')])],
    'hine': [('彼', 3, 'sg', [('Acc', 'sg', 'm')])],
    'him': [('彼', 3, 'sg', [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')]), ('彼ら', 3, 'pl', _cng(('Dat',), 'pl'))],
    'heo': [('彼女', 3, 'sg', [('Nom', 'sg', 'f')]), ('彼ら', 3, 'pl', _cng(('Nom', 'Acc'), 'pl'))],
    'hio': [('彼女', 3, 'sg', [('Nom', 'sg', 'f')])],
    'hie': [('彼女', 3, 'sg', [('Acc', 'sg', 'f')]), ('彼ら', 3, 'pl', _cng(('Nom', 'Acc'), 'pl'))],
    'hi': [('彼ら', 3, 'pl', _cng(('Nom', 'Acc'), 'pl')), ('彼女', 3, 'sg', [('Acc', 'sg', 'f')])],
    'hig': [('彼ら', 3, 'pl', _cng(('Nom', 'Acc'), 'pl'))],
    'hy': [('彼ら', 3, 'pl', _cng(('Nom', 'Acc'), 'pl'))],
    'hire': [('彼女', 3, 'sg', [('Dat', 'sg', 'f')])],
    'hyre': [('彼女', 3, 'sg', [('Dat', 'sg', 'f')])],
    'hit': [('それ', 3, 'sg', [('Nom', 'sg', 'n'), ('Acc', 'sg', 'n')])],
    'we': [('私たち', 1, 'pl', _cng(('Nom',), 'pl'))],
    'us': [('私たち', 1, 'pl', _cng(('Acc', 'Dat'), 'pl'))],
    'usic': [('私たち', 1, 'pl', _cng(('Acc',), 'pl'))],
    'ge': [('君たち', 2, 'pl', _cng(('Nom',), 'pl'))],
    'eow': [('君たち', 2, 'pl', _cng(('Acc', 'Dat'), 'pl'))],
    'eowic': [('君たち', 2, 'pl', _cng(('Acc',), 'pl'))],
    'heom': [('彼ら', 3, 'pl', _cng(('Dat',), 'pl'))],
    'wit': [('私たち二人', 1, 'du', _cng(('Nom',), 'du'))],
    'unc': [('私たち二人', 1, 'du', _cng(('Acc', 'Dat'), 'du'))],
    'git': [('君たち二人', 2, 'du', _cng(('Nom',), 'du'))],
    'inc': [('君たち二人', 2, 'du', _cng(('Acc', 'Dat'), 'du'))],
    'man': [('人々', 3, 'sg', _cng(('Nom',), 'sg', ('m',)))],
    'mon': [('人々', 3, 'sg', _cng(('Nom',), 'sg', ('m',)))],
    'hiene': [('彼', 3, 'sg', [('Acc', 'sg', 'm')])], 'hyne': [('彼', 3, 'sg', [('Acc', 'sg', 'm')])],
    'hiom': [('彼ら', 3, 'pl', _cng(('Dat',), 'pl'))], 'hym': [('彼', 3, 'sg', [('Dat', 'sg', 'm')])],
    'ðu': [('君', 2, 'sg', _cng(('Nom',), 'sg'))],
    'hwa': [('誰', 3, 'sg', [('Nom', 'sg', 'm'), ('Nom', 'sg', 'f')])],
    'hwæt': [('何', 3, 'sg', [('Nom', 'sg', 'n'), ('Acc', 'sg', 'n')])],
    'hwone': [('誰', 3, 'sg', [('Acc', 'sg', 'm')])],
    'hwæm': [('誰', 3, 'sg', [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')])],
    'hwam': [('誰', 3, 'sg', [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')])],
}
# 人称代名詞の属格: 所有者「〜の」(名詞の前の形容詞のように使う)
POSSESSIVE_GENITIVES = {'his': '彼の', 'hire': '彼女の', 'hyre': '彼女の', 'hiera': '彼らの', 'heora': '彼らの',
                        'hira': '彼らの', 'hyra': '彼らの', 'hiora': '彼らの', 'hwæs': '誰の',
                        'heore': '彼らの', 'hiere': '彼女の'}
# 所有の形容詞 (変化する): 見出し → 訳
# 綴りの揺れで別の語に当たる形 (men は mān「悪事」の複数でもあるが、ふつうは mann の複数 menn)
SPELLINGS = {'men': 'menn', 'mon': 'mann', 'monn': 'mann'}
POSSESSIVES = {'min': '私の', 'þin': '君の', 'ure': '私たちの', 'eower': '君たちの', 'sin': '自分の', 'uncer': '私たち二人の',
               'incer': '君たち二人の'}
# 指示詞 sē (冠詞「その」・指示代名詞「その人・それ」・関係代名詞) と þes「この」の形: 鍵 → 格・数・性
SE_FORMS = {
    'se': [('Nom', 'sg', 'm')], 'sio': [('Nom', 'sg', 'f')], 'seo': [('Nom', 'sg', 'f')],
    'þæt': [('Nom', 'sg', 'n'), ('Acc', 'sg', 'n')], 'þone': [('Acc', 'sg', 'm')], 'þane': [('Acc', 'sg', 'm')],
    'þa': [('Acc', 'sg', 'f')] + _cng(('Nom', 'Acc'), 'pl'), 'þæs': [('Gen', 'sg', 'm'), ('Gen', 'sg', 'n')],
    'þære': [('Gen', 'sg', 'f'), ('Dat', 'sg', 'f')], 'þare': [('Gen', 'sg', 'f'), ('Dat', 'sg', 'f')],
    'þæm': [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')] + _cng(('Dat',), 'pl'),
    'þam': [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')] + _cng(('Dat',), 'pl'),
    'þy': [('Ins', 'sg', 'm'), ('Ins', 'sg', 'n')], 'þon': [('Ins', 'sg', 'm'), ('Ins', 'sg', 'n')],
    'þara': _cng(('Gen',), 'pl'), 'þæra': _cng(('Gen',), 'pl'),
}
THES_FORMS = {
    'þes': [('Nom', 'sg', 'm')], 'þeos': [('Nom', 'sg', 'f')], 'þis': [('Nom', 'sg', 'n'), ('Acc', 'sg', 'n')],
    'þisne': [('Acc', 'sg', 'm')], 'þas': [('Acc', 'sg', 'f')] + _cng(('Nom', 'Acc'), 'pl'),
    'þisses': [('Gen', 'sg', 'm'), ('Gen', 'sg', 'n')], 'þisse': [('Gen', 'sg', 'f'), ('Dat', 'sg', 'f')],
    'þissere': [('Gen', 'sg', 'f'), ('Dat', 'sg', 'f')], 'þysse': [('Gen', 'sg', 'f'), ('Dat', 'sg', 'f')],
    'þissum': [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')] + _cng(('Dat',), 'pl'),
    'þisum': [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')] + _cng(('Dat',), 'pl'),
    'þysum': [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')] + _cng(('Dat',), 'pl'),
    'þissa': _cng(('Gen',), 'pl'), 'þys': [('Ins', 'sg', 'm'), ('Ins', 'sg', 'n')],
}
# 前置詞: 鍵 → [(支配する格, 訳)] (最初のものが既定。後ろの語の格で選ぶ)
PREPOSITIONS = {
    'on': [('Dat', '〜で,〜の上で'), ('Acc', '〜へ,〜の上へ')], 'in': [('Dat', '〜で,〜の中で'), ('Acc', '〜の中へ')],
    'to': [('Dat', '〜へ,〜に')], 'mid': [('Dat', '〜と共に,〜で'), ('Acc', '〜と共に'), ('Ins', '〜で')],
    'fram': [('Dat', '〜から,〜によって')], 'from': [('Dat', '〜から,〜によって')], 'of': [('Dat', '〜から,〜の')],
    'be': [('Dat', '〜について,〜のそばで')], 'bi': [('Dat', '〜について,〜のそばで')],
    'for': [('Dat', '〜のために,〜の前で'), ('Acc', '〜の代わりに')], 'æfter': [('Dat', '〜の後で,〜に従って')],
    'ofer': [('Acc', '〜を越えて,〜の上へ'), ('Dat', '〜の上で')], 'under': [('Dat', '〜の下で'), ('Acc', '〜の下へ')],
    'þurh': [('Acc', '〜を通って,〜によって')], 'wiþ': [('Acc', '〜に向かって,〜に対して'), ('Dat', '〜に対して'), ('Gen', '〜の方へ')],
    'ymb': [('Acc', '〜の周りに,〜について')], 'ymbe': [('Acc', '〜の周りに,〜について')],
    'oþ': [('Acc', '〜まで')], 'æt': [('Dat', '〜で,〜のところで')],
    'buton': [('Dat', '〜なしに,〜を除いて')], 'betweox': [('Dat', '〜の間に')], 'betwux': [('Dat', '〜の間に')],
    'betwyx': [('Dat', '〜の間に')], 'betweonan': [('Dat', '〜の間に')], 'geond': [('Acc', '〜じゅうに')],
    'ongean': [('Dat', '〜に対して,〜に向かって'), ('Acc', '〜に向かって')], 'togeanes': [('Dat', '〜に向かって')],
    'beforan': [('Dat', '〜の前で')], 'ætforan': [('Dat', '〜の前で')], 'toforan': [('Dat', '〜の前で')],
    'binnan': [('Dat', '〜の中で,〜以内に')], 'innan': [('Dat', '〜の中で')], 'butan': [('Dat', '〜の外で,〜なしに')],
    'wiþutan': [('Dat', '〜の外で')], 'uppan': [('Dat', '〜の上で')], 'ufan': [('Dat', '〜の上で')],
    'neah': [('Dat', '〜の近くに')], 'forþ': [('Acc', '〜を越えて')], 'ær': [('Dat', '〜の前に')],
    'siþþan': [('Dat', '〜以来')], 'andlang': [('Gen', '〜に沿って')], 'toweard': [('Dat', '〜の方へ')],
}
# 接続詞: 鍵 → 訳。並列は and・oþþe、否定の並列は ne
CONJUNCTIONS = {
    'and': 'そして', 'ond': 'そして', 'ac': 'しかし', 'oþþe': 'または', 'oþþon': 'または', 'gif': '〜なら',
    'þeah': '〜けれども', 'forþam': '〜なので', 'forþæm': '〜なので', 'forþon': '〜なので', 'forþi': '〜なので',
    'swa': '〜のように', 'swilce': '〜のように', 'siþþan': '〜した後で', 'syþþan': '〜した後で', 'oþ': '〜まで',
    'ær': '〜する前に', 'hwæþer': '〜かどうか', 'þenden': '〜する間に', 'nu': '今や', 'þa': 'その時', 'þonne': 'その時',
    'eac': 'また', 'hwonne': '〜する時', 'butan': '〜でなければ', 'buton': '〜でなければ',
}
# 補文の接続詞 þæt「〜ということ」、関係の小辞 þe「〜するところの」
COMPLEMENTIZER = 'þæt'
RELATIVE_PARTICLE = 'þe'
ADVERBS = {
    'ne': '〜ない', 'na': '決して〜ない', 'no': '決して〜ない', 'næfre': '決して〜ない', 'nawiht': '何も〜ない',
    'naht': '何も〜ない', 'þa': 'その時', 'þær': 'そこで', 'her': 'ここで', 'nu': '今', 'eft': '再び', 'swiþe': 'とても',
    'eac': 'また', 'ealswa': '同じように', 'swa': 'そのように', 'hwær': 'どこで', 'hu': 'どのように', 'hwy': 'なぜ',
    'hwi': 'なぜ', 'hwonne': 'いつ', 'sona': 'すぐに', 'oft': 'しばしば', 'symle': 'いつも', 'simle': 'いつも',
    'giet': 'まだ', 'gyt': 'まだ', 'ær': '以前に', 'þonne': 'その時', 'þider': 'そこへ', 'hider': 'ここへ', 'ut': '外へ',
    'up': '上へ', 'ofdune': '下へ', 'forþ': '前へ', 'hwæt': 'さて', 'eala': 'ああ', 'gea': 'はい', 'gise': 'はい',
    'witodlice': 'まことに', 'soþlice': 'まことに', 'ealles': 'まったく', 'ana': 'ひとりで', 'þus': 'このように',
}
NEGATIONS = frozenset({'ne', 'na', 'no', 'næfre'})
# 否定の縮約: 鍵 → 元の動詞の形 (nis = ne is、nolde = ne wolde、næfde = ne hæfde)
NEGATIVE_CONTRACTIONS = {
    'nis': 'is', 'nys': 'is', 'næs': 'wæs', 'nære': 'wære', 'næron': 'wæron', 'nænig': 'ænig', 'neom': 'eom',
    'neart': 'eart', 'nolde': 'wolde', 'noldon': 'woldon', 'nyle': 'wile', 'nylle': 'wille', 'nellaþ': 'willaþ',
    'nat': 'wat', 'nyste': 'wiste', 'nyston': 'wiston', 'nyton': 'witon', 'næfþ': 'hæfþ', 'næfde': 'hæfde',
    'næfdon': 'hæfdon', 'nabbaþ': 'habbaþ', 'næbbe': 'hæbbe', 'nænne': 'ænne', 'nan': 'an', 'nanne': 'anne',
    'nanum': 'anum', 'nane': 'ane', 'nanre': 'anre', 'naþor': 'awþer', 'nahte': 'ahte', 'nah': 'ah',
}
# 否定の代名詞・形容詞 (nān「ひとつも〜ない」、nǣniġ「誰も〜ない」): 否定の副詞と同じく述語を否定に
NEGATIVE_WORDS = {'nan': '誰も〜ない', 'nanne': '誰も〜ない', 'nænig': '誰も〜ない', 'nanum': '誰も〜ない',
                  'nane': '誰も〜ない', 'nanre': '誰も〜ない', 'nænne': '誰も〜ない', 'nawiht': '何も〜ない',
                  'naht': '何も〜ない'}
# 話法の動詞 (過去現在動詞): 見出し → 本動詞の不定詞に付ける形
MODALS = {'sculan': 'なければならない', 'magan': 'ことができる', 'cunnan': 'ことができる', 'willan': 'たい',
          'motan': 'てもよい', 'þurfan': '必要がある', 'durran': 'あえて'}
# 完了・受動の助動詞
PERFECT_AUXILIARIES = ('habban',)
PASSIVE_AUXILIARIES = ('beon', 'wesan', 'weorþan')
COPULAS = frozenset({'wesan', 'bēon', 'beon'})
# 訳語を決めておく語 (見出しの鍵 → 訳)
GLOSSES = {
    'wesan': 'ある,いる', 'bēon': 'ある,いる', 'habban': '持つ', 'weorþan': 'なる', 'cuman': '来る', 'gān': '行く',
    'faran': '行く', 'fēran': '行く', 'sēon': '見る', 'gesēon': '見る', 'secgan': '言う', 'cweþan': '言う',
    'sprecan': '話す', 'dōn': 'する', 'niman': '取る', 'giefan': '与える', 'gifan': '与える', 'sellan': '与える',
    'witan': '知る', 'hīeran': '聞く', 'gehīeran': '聞く', 'singan': '歌う', 'lufian': '愛する', 'findan': '見つける',
    'macian': '作る', 'wyrċan': '作る,働く', 'wyrcan': '作る,働く', 'libban': '生きる', 'sittan': '座る',
    'standan': '立つ', 'feohtan': '戦う', 'slēan': '打つ,殺す', 'ofslēan': '殺す', 'etan': '食べる', 'drincan': '飲む',
    'wrītan': '書く', 'rǣdan': '読む', 'beran': '運ぶ,産む', 'healdan': '保つ', 'bringan': '持って来る',
    'sendan': '送る', 'lǣdan': '導く', 'cennan': '産む', 'cȳþan': '知らせる', 'onginnan': '始める',
    'beginnan': '始める', 'hātan': '命じる,呼ぶ', 'nemnan': '名付ける', 'wunian': '住む', 'sweltan': '死ぬ',
    'steorfan': '死ぬ', 'slǣpan': '眠る', 'rīdan': '馬で行く', 'scēawian': '見る', 'gelīefan': '信じる',
    'gelȳfan': '信じる', 'biddan': '頼む,祈る', 'þancian': '感謝する', 'helpan': '助ける', 'andswarian': '答える',
    'fōn': '捕らえる', 'onfōn': '受け取る', 'forlǣtan': '去る,許す', 'flēon': '逃げる', 'wēnan': '思う',
    'þenċan': '考える', 'þencan': '考える', 'þynċan': '思われる', 'leornian': '学ぶ', 'tǣċan': '教える',
    'timbran': '建てる', 'getimbran': '建てる', 'rīcsian': '支配する', 'gefrignan': '聞き知る', 'frignan': '尋ねる',
    'cyning': '王', 'cyng': '王', 'god': '神', 'drihten': '主', 'dryhten': '主', 'hlāford': '主人', 'mann': '人',
    'wer': '男', 'wīf': '女', 'ċild': '子供', 'cild': '子供', 'sunu': '息子', 'dohtor': '娘', 'fæder': '父',
    'mōdor': '母', 'brōþor': '兄弟', 'sweostor': '姉妹', 'eorþe': '大地', 'heofon': '天', 'heofonrīċe': '天の国',
    'land': '国,土地', 'stān': '石', 'hūs': '家', 'word': '言葉', 'dæġ': '日', 'dæg': '日', 'niht': '夜',
    'ġēar': '年', 'gēar': '年', 'tīd': '時', 'weġ': '道', 'weg': '道', 'here': '軍', 'fyrd': '軍', 'scip': '船',
    'burg': '町', 'burh': '町', 'bōc': '本', 'gerecednes': '物語', 'lēod': '民', 'folc': '民', 'þēod': '民',
    'gāst': '霊', 'līf': '命', 'dēaþ': '死', 'sāwol': '魂', 'heorte': '心', 'hand': '手', 'ēage': '目', 'sǣ': '海',
    'wæter': '水', 'hlāf': 'パン', 'gold': '金', 'sweord': '剣', 'mearh': '馬', 'hors': '馬', 'hund': '犬',
    'wulf': '狼', 'fugol': '鳥', 'nama': '名前', 'rīċe': '国', 'þrym': '栄光', 'gēardagas': '昔の日々',
    'gōd': '良い', 'miċel': '大きい', 'micel': '大きい', 'lȳtel': '小さい', 'eald': '古い', 'nīwe': '新しい',
    'strang': '強い', 'hāliġ': '聖なる', 'halig': '聖なる', 'eall': 'すべての', 'maniġ': '多くの', 'manig': '多くの',
    'fela': '多くの', 'sum': 'ある', 'ān': 'ひとつの', 'twēġen': '二つの', 'þrīe': '三つの', 'ǣlċ': '各々の',
    'ǣniġ': '何かの', 'ōþer': 'ほかの', 'self': '自身', 'sylf': '自身', 'wīs': '賢い',
    'gōd#noun': '財産,良いもの', 'gēardæg': '昔の日々', 'ġēardæġ': '昔の日々', 'þrymm': '栄光', 'þēodcyning': '王',
    'Gārdene': 'デーン人', 'Westseaxe': 'ウェストサクソン', 'Westseaxan': 'ウェストサクソン',
    'Westseaxa': 'ウェストサクソン人', 'Lundenburg': 'ロンドン', 'Lundenbyrig': 'ロンドン', 'Lunden': 'ロンドン',
    'Cantwaraburg': 'カンタベリー', 'Wintanceaster': 'ウィンチェスター', 'Rōm': 'ローマ', 'Dene': 'デーン人', 'Engle': 'アングル人', 'Seaxe': 'サクソン人',
}
GLOSSES = {orthography.lemma_key(k): v for k, v in GLOSSES.items()}
# 手で書いた表の語の長音符付きの綴り (音読で母音の長さに)
LONG_SPELLINGS = {
    'he': 'hē', 'heo': 'hēo', 'hie': 'hīe', 'we': 'wē', 'me': 'mē', 'ge': 'ġē', 'us': 'ūs', 'eow': 'ēow', 'þu': 'þū',
    'ic': 'iċ', 'hwa': 'hwā', 'se': 'sē', 'seo': 'sēo', 'þa': 'þā', 'þæm': 'þǣm', 'þam': 'þām', 'þære': 'þǣre',
    'þara': 'þāra', 'þæra': 'þǣra', 'þy': 'þȳ', 'þeos': 'þēos', 'þas': 'þās', 'ure': 'ūre', 'min': 'mīn',
    'þin': 'þīn', 'sin': 'sīn', 'si': 'sī', 'sie': 'sīe', 'swa': 'swā', 'na': 'nā', 'no': 'nō', 'nu': 'nū',
    'to': 'tō', 'her': 'hēr', 'þær': 'þǣr', 'ær': 'ǣr', 'hu': 'hū', 'hwær': 'hwǣr', 'hwy': 'hwȳ', 'sona': 'sōna',
    'næfre': 'nǣfre', 'nan': 'nān', 'nis': 'nis', 'eala': 'ēalā', 'gea': 'ġēa', 'þeah': 'þēah', 'butan': 'būtan',
    'ymbe': 'ymbe', 'ðu': 'þū', 'hiora': 'hiora', 'heora': 'heora', 'hire': 'hire', 'his': 'his', 'him': 'him',
}
NUMBERS_JA = {'an': '一', 'twegen': '二', 'twa': '二', 'tu': '二', 'þrie': '三', 'þreo': '三', 'feower': '四',
              'fif': '五', 'siex': '六', 'six': '六', 'seofon': '七', 'eahta': '八', 'nigon': '九', 'tien': '十',
              'tyn': '十', 'hund': '百', 'hundred': '百', 'þusend': '千'}


def gloss(base, pos):
    """見出し (長音符付き) → 訳語 (手で決めたもの)。無ければ None。god「神」と gōd「良い」は長音符で分ける"""
    if pos not in ('verb', 'noun', 'adj'):
        return None
    k = orthography.lemma_key(base)
    return GLOSSES.get('%s#%s' % (k, pos)) or GLOSSES.get(k)
