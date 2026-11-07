#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語の語を普通話の語に置き換える (解析は普通話の解析器 chinese/analyzer.py で)。
#   - 文法の語・よく使う語は表 (MANDARIN: 佢 → 他、嘅 → 的、咗 → 了、唔 → 不、係 → 是、喺 → 在、睇 → 看 …)
#   - 表に無い語は簡体字に (OpenCC)。CC-CEDICT に無くて CC-Canto に普通話の語 (Mandarin equivalent) があればそれに
#   - 広東語の構文は普通話の形に並べ替える (rewrite):
#       比較 (我高過佢 → 我比他高)、二重目的語 (畀本書我 → 给我本书)、受動 (畀 + 人 + 動詞 → 被)、V + 先 → 先 + V、
#       反復疑問 (去唔去・係咪・有冇 → 去 + 吗)、文末の 未 (食咗飯未 → 吃了饭吗)、文末の助詞 (喇・啦・㗎・喎 …)
#
import functools

from . import dictionary

# 広東語 (繁体字) → 普通話 (簡体字)。1語を1語に
MANDARIN = {
    # 代名詞・指示詞・疑問詞
    '佢': '他', '佢哋': '他们', '我哋': '我们', '你哋': '你们', '人哋': '别人',
    '呢個': '这个', '嗰個': '那个', '呢啲': '这些', '嗰啲': '那些', '呢度': '这里', '嗰度': '那里', '邊度': '哪里',
    '呢處': '这里', '嗰處': '那里', '邊處': '哪里', '嗰': '那', '邊': '哪', '邊個': '谁', '乜': '什么', '咩': '什么', '少少': '一点', '乜嘢': '什么',
    '咩嘢': '什么', '點': '怎么', '點樣': '怎么样', '點解': '为什么', '幾時': '什么时候', '幾多': '多少', '噉': '这样',
    '咁': '这么', '呢排': '最近',
    # 繋辞・存在・否定・アスペクト
    '係': '是', '喺': '在', '冇': '没有', '唔': '不', '咗': '了', '緊': '着', '過': '过', '晒': '完',
    '唔好': '别', '咪': '别', '唔使': '不用', '未': '没', '嘅': '的', '啲': '一些', '有啲': '有些', '冇問題': '没问题',
    # 動詞
    '食': '吃', '飲': '喝', '睇': '看', '講': '说', '話': '说', '知': '知道', '識': '会', '畀': '给',
    '俾': '给', '嚟': '来', '返': '回', '行': '走', '企': '站', '瞓': '睡', '瞓覺': '睡觉', '鍾意': '喜欢', '中意': '喜欢',
    '搵': '找', '揾': '找', '攞': '拿', '着': '穿', '沖涼': '洗澡', '返工': '上班', '返學': '上学', '放工': '下班',
    '傾偈': '聊天', '做嘢': '工作', '諗': '想', '鬧': '骂', '食飯': '吃饭', '返屋企': '回家', '睇書': '看书',
    '飲茶': '喝茶', '揸車': '开车', '落雨': '下雨', '出街': '出去', '翻': '回', '翻屋企': '回家',
    # 名詞
    '嘢': '东西', '嘢食': '食物', '屋企': '家', '雪櫃': '冰箱', '細路': '孩子', '細路仔': '小孩', '男仔': '男孩',
    '女仔': '女孩', '老豆': '爸爸', '老竇': '爸爸', '阿爸': '爸爸', '爸爸': '爸爸', '阿媽': '妈妈', '媽媽': '妈妈',
    '媽咪': '妈妈', '爹哋': '爸爸', '老公': '丈夫', '老婆': '妻子', '餸': '菜', '衫': '衣服', '巴士': '公共汽车',
    '的士': '出租车', '銀紙': '钞票', '今日': '今天', '琴日': '昨天', '尋日': '昨天', '聽日': '明天', '而家': '现在',
    '宜家': '现在', '頭先': '刚才', '尋晚': '昨晚', '琴晚': '昨晚', '朝早': '早上', '晏晝': '中午', '聽朝': '明早',
    '廣東話': '广东话', '屋': '房子', '啲人': '人们', '入面': '里面', '出面': '外面', '後面': '后面', 
    '戲': '电影', '電影': '电影', '老師': '老师', '學生': '学生', '學校': '学校', '餐廳': '餐厅', '茶餐廳': '餐厅',
    # 形容詞・副詞
    '靚': '漂亮', '好睇': '好看', '好食': '好吃', '好飲': '好喝', '攰': '累', '嬲': '生气', '凍': '冷', '啱': '对',
    '平': '便宜', '細': '小', '肥': '胖', '叻': '聪明', '犀利': '厉害', '得閒': '有空', '開心': '开心',
    '都': '也', '仲': '还', '真係': '真的', '好似': '好像', '一齊': '一起', '啱啱': '刚刚', '成日': '总是', '梗係': '当然',
    # 接続詞・介詞
    '同': '和', '同埋': '和', '定': '还是', '定係': '还是', '但係': '但是', '跟住': '然后', '由': '从',
    # 挨拶
    '唔該': '谢谢', '多謝': '谢谢', '早晨': '早上好', '拜拜': '再见', '唔緊要': '没关系', '對唔住': '对不起',
}
# 文末の助詞 (語気。訳さない): 普通話の 啊 に
FINAL_PARTICLES = set('喇啦嘞囉喎啩吖嘛咋噃啫㗎呀啊吓喳')
PUNCTUATION = set('。，、；：？！…,.?!;:')
PRONOUNS = {'我', '你', '佢', '我哋', '你哋', '佢哋', '人哋', '自己', '大家', '邊個'}
# 好 + 形容詞・心の動詞は「とても」(好靚「とてもきれいだ」)。ほかの 好 は「良い」
ADJECTIVES = {'靚', '好睇', '好食', '攰', '嬲', '凍', '熱', '啱', '錯', '平', '貴', '多', '少', '大', '細', '高', '矮', '肥', '瘦',
              '快', '慢', '開心', '叻', '犀利', '得閒', '忙', '遠', '近', '難', '易', '好', '早', '夜', '長', '短', '新', '舊',
              '乾淨', '污糟', '重', '輕', '鍾意', '中意', '想', '驚', '掛住', '凍', '辛苦', '舒服', '好玩', '得意', '靜', '嘈'}
VERBS = {'食', '飲', '睇', '講', '話', '知', '識', '畀', '俾', '嚟', '去', '返', '行', '企', '坐', '瞓', '買', '賣', '做', '寫',
         '讀', '學', '搵', '攞', '着', '玩', '諗', '鬧', '打', '聽', '唱', '跳', '走', '來', '開', '閂', '洗', '煮', '用', '住',
         '教', '問', '叫', '等', '送', '還', '借', '揸', '落', '上', '入', '出', '飛', '游水', '返工', '放工', '瞓覺', '沖涼'}


@functools.lru_cache(maxsize=1)
def _t2s():
    try:
        import opencc
        return opencc.OpenCC('t2s'), opencc.OpenCC('s2t')
    except ImportError:
        return None, None


@functools.lru_cache(maxsize=1)
def _table():
    """MANDARIN の表に簡体字の見出し (佢哋 → 佢们 ではなく、呢个・边度 …) も足す"""
    t2s, _ = _t2s()
    out = dict(MANDARIN)
    if t2s is not None:
        for k, v in MANDARIN.items():
            s = t2s.convert(k)
            out.setdefault(s, v)
    return out


def traditional(word):
    """簡体字で書いた広東語 (边度・呢个) → 繁体字 (表を引くため)。字の数が変われば元のまま"""
    _, s2t = _t2s()
    if s2t is None:
        return word
    out = s2t.convert(word)
    return out if len(out) == len(word) else word


def mandarin(word):
    """広東語の語 → 普通話の語 (簡体字)"""
    from dragoman.chinese import dictionary as cedict, segment as zh_segment
    table = _table()
    if word in table:
        return table[word]
    simple = zh_segment.simplified(word)
    if simple in table:
        return table[simple]
    keys, _ = cedict.keys()
    if simple not in keys:
        for r in dictionary.rows(word):
            if r['mandarin']:
                return zh_segment.simplified(r['mandarin'])
    return simple


def known(word):
    """語の切り分けの見出しか (広東語の表・CC-Canto・CC-CEDICT)"""
    from dragoman.chinese import dictionary as cedict
    keys, _ = cedict.keys()
    return word in _table() or word in dictionary.keys() or word in keys


def _final(words, k):
    """k の後ろが句読点か文末の助詞だけか"""
    return all(w in PUNCTUATION or w in FINAL_PARTICLES for w in words[k + 1:])


def _is_adjective(word):
    return word in ADJECTIVES or traditional(word) in ADJECTIVES


def _is_nominal(word):
    return word not in PUNCTUATION and word not in FINAL_PARTICLES and not _is_verb(word)


def _is_verb(word):
    return word in VERBS or traditional(word) in VERBS


def rewrite(words):
    """広東語の語の列 → (表示の語, 普通話の語) の組の列。広東語の構文は普通話の語順に並べ替える"""
    pairs = []
    n = len(words)
    for k, w in enumerate(words):
        t = traditional(w)
        nxt = words[k + 1] if k + 1 < n else ''
        if t == '好' and nxt and (_is_adjective(nxt) or nxt in ('多', '少')) and not _final(words, k):
            m = '很'   # 好靚「とてもきれい」
        elif t == '幾' and nxt and _is_adjective(nxt):
            m = '挺'   # 幾好「なかなか良い」
        elif t == '呢':
            m = '呢' if _final(words, k) else '这'   # 文末の 呢 は疑問・語気、ほかは指示詞「この」
        elif t in ('咩', '未') and _final(words, k):
            m = '吗'   # 你食咗飯未？「もう ご飯を 食べたか」
        elif t == '喺度':
            m = '在'   # 佢喺度食飯「彼は ご飯を 食べている」(進行)、佢喺度「彼は ここに いる」
        elif t == '同' and nxt and traditional(nxt) in PRONOUNS | {'朋友', '媽媽', '阿媽', '爸爸', '老師'} and \
                any(_is_verb(x) or traditional(x) in ('一齊', '講', '傾偈') for x in words[k + 2:]) and k > 0:
            m = '跟'   # 同 + 人 + 動詞「〜と 一緒に」(我同佢去「私は 彼と 行く」)
        elif t in FINAL_PARTICLES and _final(words, k):
            m = '啊'
        elif t in ('畀', '俾') and _passive(words, k):
            m = '被'   # 畀 + 人 + 動詞: 受動 (我畀老師鬧「私は 先生に 叱られた」)
        else:
            m = mandarin(w)
        pairs.append([w, m])
    pairs = _bare_classifiers(pairs)
    pairs = _comparatives(pairs)
    pairs = _double_objects(pairs)
    pairs = _progressives(pairs)
    pairs = _xian(pairs)
    pairs = _a_not_a(pairs)
    return pairs


CLASSIFIERS = set('個隻條張間架部對本件位粒樽枝支把封首套份輛')
NUMERALS = set('一二三四五六七八九十百千萬万兩两幾几') | {'呢', '嗰', '邊', '每', '第', '这', '那', '哪'}


def _bare_classifiers(pairs):
    """数詞・指示詞の無い 量詞 + 名詞 (本書「その本」、隻貓「その猫」) は名詞1つに (普通話では量詞だけで名詞の前に置かない)"""
    out = []
    k = 0
    while k < len(pairs):
        w, m = pairs[k]
        prev = traditional(out[-1][0]) if out else ''
        nxt = pairs[k + 1] if k + 1 < len(pairs) else None
        if traditional(w) in CLASSIFIERS and nxt is not None and _is_nominal(nxt[0]) and \
                traditional(nxt[0]) not in PRONOUNS and not (prev and (prev[-1] in NUMERALS or prev.isdigit())):
            out.append([w + nxt[0], nxt[1]])
            k += 2
            continue
        out.append([w, m])
        k += 1
    return out


def _passive(words, k):
    """畀 の後ろが 名詞・代名詞 + 動詞 なら受動"""
    return k + 2 < len(words) and _is_nominal(words[k + 1]) and _is_verb(words[k + 2])


def _comparatives(pairs):
    """形容詞 + 過 + 名詞 (我高過佢「私は 彼より 高い」) → 比 + 名詞 + 形容詞"""
    out = list(pairs)
    for k in range(1, len(out) - 1):
        if traditional(out[k][0]) == '過' and _is_adjective(out[k - 1][0]) and _is_nominal(out[k + 1][0]):
            end = k + 1
            while end + 1 < len(out) and _is_nominal(out[end + 1][0]) and not _is_adjective(out[end + 1][0]):
                end += 1
            adj = out[k - 1]
            compared = out[k + 1:end + 1]
            out[k - 1:end + 1] = [[out[k][0], '比']] + compared + [adj]
            break
    return out


def _double_objects(pairs):
    """畀 + 物 + 人 (畀本書我「私に 本を くれる」) → 给 + 人 + 物"""
    out = list(pairs)
    for k, (w, m) in enumerate(out):
        if m != '给':
            continue
        end = k + 1
        while end < len(out) and out[end][0] not in PUNCTUATION and out[end][0] not in FINAL_PARTICLES:
            end += 1
        if end - k >= 3 and traditional(out[end - 1][0]) in PRONOUNS and \
                not any(traditional(x[0]) in PRONOUNS for x in out[k + 1:end - 1]):
            out[k + 1:end] = [out[end - 1]] + out[k + 1:end - 1]
        break
    return out


def _progressives(pairs):
    """動詞 + 緊 (+ 目的語) (佢食緊飯「彼は ご飯を 食べている」) → 在 + 動詞。離合詞 (瞓緊覺) は動詞1つに (在 + 睡觉)"""
    out = list(pairs)
    for k in range(1, len(out)):
        if traditional(out[k][0]) == '緊' and _is_verb(out[k - 1][0]):
            gan = out.pop(k)
            verb = out[k - 1]
            if k < len(out) and traditional(verb[0] + out[k][0]) in MANDARIN:
                obj = out.pop(k)
                verb = [verb[0] + obj[0], MANDARIN[traditional(verb[0] + obj[0])]]
            out[k - 1:k] = [[gan[0], '在'], verb]
            break
    return out


def _xian(pairs):
    """動詞 (+ 目的語) + 先 (你食先「あなたが 先に 食べる」) → 先 + 動詞"""
    out = list(pairs)
    for k, (w, m) in enumerate(out):
        if traditional(w) == '先' and k > 0 and (k + 1 == len(out) or out[k + 1][0] in PUNCTUATION or
                                                 out[k + 1][0] in FINAL_PARTICLES):
            v = next((j for j in range(k - 1, -1, -1) if _is_verb(out[j][0])), None)
            if v is not None:
                out.insert(v, out.pop(k))
            break
    return out


def _a_not_a(pairs):
    """反復疑問 (去唔去「行くか」、係咪、有冇) → 動詞 + 文末の 吗"""
    out = list(pairs)
    for k, (w, m) in enumerate(out):
        t = traditional(w)
        if (t, traditional(out[k + 1][0]) if k + 1 < len(out) else '') in (('係', '咪'), ('有', '冇')):
            again = out.pop(k + 1)
            out[k] = [w, {'係': '是', '有': '有'}[t]]
            return _with_question(out, again[0])
        if t in ('係咪', '有冇'):
            out[k] = [w, {'係咪': '是', '有冇': '有'}[t]]
            return _with_question(out, w[-1])
        if t == '唔' and 0 < k < len(out) - 1 and out[k + 1][0].startswith(out[k - 1][0]):
            neg = out.pop(k)
            again = out.pop(k)
            if again[0] != out[k - 1][0]:
                out[k - 1] = again   # 得唔得閒 → 得閒 + 吗
                again = [out[k - 1][0][:len(neg[0])], '']
            return _with_question(out, neg[0] + again[0])
    return out


def _with_question(pairs, surface):
    """文末 (句読点の前) に 吗 を足す。表示の語は反復した部分 (解析では文末の 吗 は訳さない)"""
    end = len(pairs)
    while end > 0 and (pairs[end - 1][0] in PUNCTUATION or pairs[end - 1][0] in FINAL_PARTICLES):
        end -= 1
    pairs.insert(end, [surface, '吗'])
    return pairs


def jyutping(word):
    """語の粤拼 (PyCantonese。無ければ辞書)"""
    try:
        import pycantonese
        out = [j for _, j in pycantonese.characters_to_jyutping(word) if j]
        if out:
            return ' '.join(out)
    except ImportError:
        pass
    return dictionary.jyutping(word)


def available():
    try:
        import pycantonese   # noqa: F401
    except ImportError:
        return False
    from dragoman.chinese import morphology as zh
    return dictionary.available() and zh.available()
