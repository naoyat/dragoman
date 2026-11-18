#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# タガログ語の文の解析
#
# 語を解析し (tagalog/morphology.py)、名詞句の標識と動詞の焦点から格を決めてから、並列・係り先・格の枠・日本語訳は
# 共通の解析器 (core/analyzer.py) をタガログ語の設定 (TAGALOG) で使う:
#   - 名詞句の標識: ang / si (焦点)、ng / ni (焦点でない中心の参与者)、sa / kay (場所・受け手: 「に」「で」)。
#     代名詞は形で決まる (ako / ko / akin)。標識の語は訳に出さない
#   - 動詞の焦点 (接辞) で ang と ng の役割が決まる:
#       行為者焦点 (-um-, mag-)  ang = 動作主 (主格)、ng = 対象 (対格)   Bumili ang lalaki ng isda「男は魚を買った」
#       対象焦点 (-in, i-, ma-)  ang = 対象 (対格)、ng = 動作主 (主格)   Binili ng lalaki ang isda「魚は男が買った」
#       場所焦点 (-an)           ang = 場所・受け手 (与格)、ng = 動作主・対象
#     焦点の名詞 (ang) は日本語では主題「は」にする (Language.particle)
#   - 名詞の後ろの ng 名詞句・ng の代名詞は所有 (bahay ng lalaki「男の家」、bahay ko「私の家」)
#   - 繋ぎ (na / -ng) でつながった形容詞は名詞に掛ける (magandang bahay「美しい家」)。名詞 + 繋ぎ + 動詞は関係節
#     (lalaking bumili ng isda「魚を買った男」)
#   - ay の倒置 (Ang bata ay kumain「子供は食べた」)、動詞の無い文 (Maganda ang bahay「家は美しい」) には見えない繋辞
#
import re

from dragoman.core import analyzer as common
from dragoman.core import animacy
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, script

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', ',': 'comma', ';': 'comma', ':': 'comma',
               '"': None, '“': None, '”': None, '(': 'comma', ')': 'comma', '–': 'comma', '—': 'comma'}
TOKEN = re.compile(r"[A-Za-zÀ-ÿñÑ']+(?:-[A-Za-zÀ-ÿñÑ']+)*|[0-9]+(?:[.,][0-9]+)*|[.!?,;:\"“”()–—]")
CLAUSE_PARTICLES = {'Nom': 'が', 'Acc': 'を', 'Dat': 'に'}
FOCUS_PARTICLES = {'Nom': 'は', 'Acc': 'は', 'Dat': 'には'}


def particle(case, obj, pred):
    """焦点の名詞 (ang) は主題「は」"""
    if isinstance(obj, Word) and getattr(obj, 'also', False):
        return 'にも' if case == 'Dat' else 'も'   # pati「〜も」
    if isinstance(obj, Word) and getattr(obj, 'focus', False):
        if pred is not None and pred.first_item.attrib('in_clause'):
            return CLAUSE_PARTICLES.get(case)   # 副詞節の中の焦点は主題にしない ({私が 子供だった}とき)
        return FOCUS_PARTICLES.get(case)
    return None


def predicative_adjective(adj, noun):
    """繋ぎ (na / -ng) でつながった形容詞だけを名詞に掛ける。ほかは述語 (Maganda ang bahay)"""
    if not isinstance(adj, Word) or not isinstance(noun, Word):
        return False
    return getattr(adj, 'linked_to', None) is not noun


def _root_items(lemma):
    return []


# 副詞節の従属接続詞 → (節の後ろに付ける形, 節の動詞の時制) (core/Adverbial.py)
# (nang は主節に合わせる: Nang makita ko siya, umiyak ako「{私が 彼を 見た}とき」。kapag・pag は条件「〜たら」)
SUBORDINATORS = {'nang': ('とき', 'relative'), 'noong': ('とき', None), 'kapag': ('ら', 'perfect'), 'pag': ('ら', 'perfect'),
                 'dahil': ('ので', None), 'sapagkat': ('ので', None), 'kasi': ('ので', None), 'bagaman': ('けれども', None),
                 'kahit': ('けれども', None), 'bago': ('前に', 'present'), 'habang': ('間に', None)}

TAGALOG = language.Language(
    name='tl',
    subordinators=SUBORDINATORS,
    and_words=('at', 'pati'),
    or_words=('o',),
    copulas=frozenset({'ay'}),
    negations=frozenset({'hindi', 'huwag', 'di', "'di"}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Gen': 'の', 'Dat': 'に'},
    absolute_case=None,
    lookup=_root_items,
    particle=particle,
    predicative_adjective=predicative_adjective,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
    topic_first=True,
    possessor_cases=(),
)

COPULA = {'pos': 'verb', 'pres1sg': 'ay', 'lemma': 'ay', 'base': '(繋辞なし)', 'ja': 'である', 'gloss_lang': 'ja',
          'voice': 'active', 'mood': 'indicative', 'tense': 'present', 'person': None, 'number': None,
          'copula': True, 'surface': '(ay)'}


# 縮約形 (話し言葉・歌): 書かれた形 → 語の列
CONTRACTIONS = {"sa'kin": ['sa', 'akin'], "sa'yo": ['sa', 'iyo'], "'pagkat": ['sapagkat'], "pagkat": ['sapagkat'],
                'nung': ['noong'], "'di": ['hindi'], "'yan": ['iyan'], "'yun": ['iyon'], 'yung': ['iyong'],
                "'yung": ['iyong'], "'to": ['ito'], 'eto': ['ito']}


def tokens(text):
    """語の列。縮約形を戻す: X'y → X + ay (ngayo'y → ngayon ay)、X't → X + at (ligaya't → ligaya at)、sa'kin → sa akin"""
    out = []
    for token in TOKEN.findall(text):
        low = token.lower()
        if low in CONTRACTIONS:
            out += CONTRACTIONS[low]
            continue
        m = re.match(r"^(.+[aeiou])'([yt])$", low)
        if m:
            host = m.group(1)
            if not dictionary.lemmas(host) and dictionary.lemmas(host + 'n') or host + 'n' in morphology.PRONOUNS:
                host += 'n'   # ngayo'y ← ngayon ay
            out += [token[:len(m.group(1))] if host == m.group(1) else host, 'ay' if m.group(2) == 'y' else 'at']
            continue
        out.append(token)
    return out


def sentences(text):
    """文に分ける: 句点・疑問符 (改行でも区切るのは共通のオプション --sentence-per-line)"""
    current = []
    for line in text.splitlines():
        for token in tokens(line):
            current.append(token)
            if PUNCTUATION.get(token) in ('period', 'question'):
                yield current
                current = []
    if current:
        yield current


def _item(word):
    return word.items[0] if isinstance(word, Word) and word.items else None


def _pos(word):
    item = _item(word)
    return item.pos if item is not None else None


def _restrict(word, cases):
    for item in word.items or []:
        if item._:
            kept = [c for c in item._ if c[0] in cases]
            if kept:
                item._ = kept


def _rebuild(word, **changes):
    item = _item(word)
    word.items = [type(item)(dict(item.item, **changes))]
    return word.items[0]


# ----------------------------------------------------------------------
# 語

def _choose(items, prev, first):
    """読みの選択: 標識・繋ぎ・形容詞の後ろは名詞類、文頭・否定の後ろは動詞を先に"""
    def score(item):
        s = 0
        if prev in ('marker', 'plural', 'linker', 'adj') and item['pos'] in ('noun', 'adj', 'pronoun'):
            s -= 2
        if (first or prev in ('negation', 'enclitic', 'ay')) and item['pos'] == 'verb':
            s -= 1
        if item.get('unknown'):
            s += 5
        return s
    return sorted(items, key=score)


def _words(surfaces):
    out = []
    prev = None
    for ix, token in enumerate(surfaces):
        if token in PUNCTUATION:
            word = Word(token, None)
            word.token_ix = ix
            out.append(word)
            prev = None
            continue
        key = script.key(token)
        items, linker = morphology.analyze(key)
        first = not [w for w in out if w.items is not None]
        items = _choose(items, prev, first)
        if key == 'pati' and (first or prev in ('ay', 'conj')):
            items = [dict(items[0], pos='adv', ja='〜も', base='pati (〜も)', also=True)]   # 文頭・節の頭の pati
        if key == 'linggo' and token[:1].isupper():
            items = [dict(items[0], ja='日曜日', gloss_lang='ja')] + items[1:]   # Linggo「日曜日」、linggo「週」
        word = Word(token, [dict(items[0], surface=token)])
        word.original_item = dict(items[0], surface=token)  # 表示用 (関係節を組み込む前の訳語)
        word.alternatives = items[1:]
        word.token_ix = ix
        word.linker = linker
        out.append(word)
        item = items[0]
        prev = ('negation' if item.get('negation') else 'linker' if linker else item['pos'])
    return out


# si・ni・kay の後ろで呼び名に使う親族の名詞 (si Nanay「母」、kay Lola「祖母に」)
KIN_TITLES = {'nanay', 'inay', 'tatay', 'itay', 'lola', 'lolo', 'kuya', 'ate', 'tita', 'tito', 'ina', 'ama', 'bunso'}

TIME_ADVERBS = {'bukas': '明日', 'kahapon': '昨日', 'ngayon': '今日'}
TIME_OF_DAY = {'umaga': '朝', 'tanghali': '昼', 'hapon': '午後', 'gabi': '夜'}
SKIP_ENCLITICS = ('na', 'pa', 'ba', 'po', 'ho')


def choose_bukas(words):
    """bukas: 副詞「明日」と形容詞「開いている」。述語 (文頭で ang・si が続く、ay の後ろ) と
    名詞の前 (bukas na pinto) は形容詞、標識の後ろは名詞類のまま、ほかは「明日」"""
    keys = [script.key(w.surface) if w.items is not None else None for w in words]
    for i, word in enumerate(words):
        if keys[i] != 'bukas' or _pos(word) != 'adv':
            continue
        j = i + 1
        while j < len(keys) and keys[j] in SKIP_ENCLITICS:
            j += 1
        nxt = keys[j] if j < len(keys) else None
        first = not [k for k in keys[:i] if k is not None]
        prev = keys[i - 1] if i else None
        attributive = i + 2 < len(keys) and keys[i + 1] == 'na' and keys[i + 2] not in (None, 'ang', 'si', 'sina') + SKIP_ENCLITICS
        if (first and nxt in ('ang', 'si', 'sina')) or prev == 'ay' or attributive:
            adj = [a for a in word.alternatives if a['pos'] == 'adj']
            if adj:
                word.alternatives = [dict(word.items[0].item)] + [a for a in word.alternatives if a is not adj[0]]
                word.items = [type(word.items[0])(dict(adj[0], surface=word.surface))]
                word.original_item = dict(adj[0], surface=word.surface)
    return words


def merge_time_phrases(words):
    """時の副詞 + ng + 朝・夜 (bukas ng umaga「明日の朝」、kahapon ng gabi「昨日の夜」) を1つの副詞に"""
    out = []
    i = 0
    while i < len(words):
        word = words[i]
        key = script.key(word.surface) if word.items is not None else None
        if key in TIME_ADVERBS and _pos(word) == 'adv' and i + 2 < len(words) and words[i + 2].items is not None and \
                script.key(words[i + 1].surface) == 'ng' and script.key(words[i + 2].surface) in TIME_OF_DAY:
            _rebuild(word, ja='%sの%s' % (TIME_ADVERBS[key], TIME_OF_DAY[script.key(words[i + 2].surface)]),
                     gloss_lang='ja', base='%s ng %s' % (key, script.key(words[i + 2].surface)))
            out.append(word)
            i += 3
            continue
        nxt = words[i + 1] if i + 1 < len(words) else None
        if key in ('noong', 'nung') and nxt is not None and nxt.items is not None and _time_gloss(nxt):
            # noong + 年・曜日・月・時 (noong 1990「1990年に」、noong Lunes「月曜日に」): 過去の時の副詞
            _rebuild(nxt, pos='adv', ja=_time_gloss(nxt) + 'に', gloss_lang='ja', base='noong ' + script.key(nxt.surface),
                     _=morphology._nominal_cngs())
            item = _rebuild(word, ja='', base='noong (過去の時)')
            word.original_item = dict(item.item, surface=word.surface)   # 語ごとの表は「過去の時」(noo「額」でなく)
            out.append(nxt)
            i += 2
            continue
        out.append(word)
        i += 1
    return out


def _time_gloss(word):
    """時を表す語の訳 (年 1990 → 1990年、曜日・月・朝・夜)。時の語でなければ None"""
    surface = word.surface
    if re.match(r'^[0-9]{3,4}$', surface):
        return surface + '年'
    item = _item(word)
    ja = (item.ja or '').split(',')[0] if item is not None else ''
    if _pos(word) == 'noun' and (ja.endswith('曜日') or re.match(r'^[0-9]+月$', ja) or script.key(surface) in TIME_OF_DAY):
        return ja
    return None


# 数詞 + 繋ぎ + 名詞: 期間の単位は「二週間」、ほかは「二つの」
NUMERALS = {'isa': ('一', '一つの'), 'dalawa': ('二', '二つの'), 'tatlo': ('三', '三つの'), 'apat': ('四', '四つの'),
            'lima': ('五', '五つの'), 'anim': ('六', '六つの'), 'pito': ('七', '七つの'), 'walo': ('八', '八つの'),
            'siyam': ('九', '九つの'), 'sampu': ('十', '十の')}
ANIMAL_COUNTERS = {'魚': '匹', '犬': '匹', '猫': '匹', '豚': '匹', '鳥': '羽', '鶏': '羽', '馬': '頭', '牛': '頭',
                   '水牛': '頭', '山羊': '匹', '羊': '匹'}
COUNTED_UNITS = {'linggo': '週間', 'araw': '日', 'taon': '年', 'buwan': 'か月', 'oras': '時間', 'minuto': '分'}


def mark_linkers(words):
    """繋ぎ: 単独の na (名詞類と名詞類・動詞の間) と、語に付いた -ng。形容詞は繋ぎの向こうの名詞に掛ける。
    名詞 + 繋ぎ + 動詞は関係節の印 (relative)。単独の na は除く"""
    out = []
    for i, word in enumerate(words):
        item = _item(word)
        prev = out[-1] if out else None
        nxt = words[i + 1] if i + 1 < len(words) else None
        if item is not None and word.surface.lower() == 'na' and prev is not None and _pos(prev) in ('noun', 'adj', 'pronoun') \
                and nxt is not None and _pos(nxt) in ('noun', 'adj', 'verb'):
            prev.linker = True  # 単独の繋ぎ na (bahay na maganda)
            word.is_linker = True
            continue
        out.append(word)
    merged = set()
    for i, word in enumerate(out[:-1]):
        if not getattr(word, 'linker', False):
            continue
        nxt = out[i + 1]
        number = NUMERALS.get(script.key(word.surface)[:-2] if script.key(word.surface).endswith('ng') else
                              script.key(word.surface)[:-1])
        if number and _pos(nxt) in ('noun', 'adj'):
            unit = COUNTED_UNITS.get(script.key(nxt.surface)) if _pos(nxt) == 'noun' else None
            if unit:
                _rebuild(nxt, ja=number[0] + unit, gloss_lang='ja')    # dalawang linggo「二週間」
                merged.add(i)
                continue
            # dalawang libro「二つの本」、isang magandang bahay「一つの美しい家」(形容詞の向こうの名詞に掛ける)
            j = i + 1
            while j < len(out) and _pos(out[j]) == 'adj' and getattr(out[j], 'linker', False):
                j += 1
            if j < len(out) and _pos(out[j]) == 'noun':
                noun = _item(out[j])
                counter = ANIMAL_COUNTERS.get((noun.ja or '').split(',')[0]) or ('人' if animacy.is_animate(noun) else None)
                ja = number[0] + counter + 'の' if counter else number[1]   # isang lalaki「一人の男」
                if j > i + 1:
                    # 形容詞を挟む (isang magandang bahay「一つの美しい家」): 数詞を形容詞の訳語の前に付ける
                    # (「一つの & 美しい」と並べない)
                    adj = _item(out[i + 1])
                    _rebuild(out[i + 1], ja=','.join(ja + g for g in (adj.ja or '').split(',')),
                             gloss_lang=adj.attrib('gloss_lang'))
                    merged.add(i)
                else:
                    _rebuild(word, pos='adj', ja=ja, gloss_lang='ja', _=morphology._adj_cngs())
                    word.linked_to = out[j]
            continue
        if _pos(word) == 'adj' and _pos(nxt) == 'noun':
            word.linked_to = nxt                    # magandang bahay
        elif _pos(word) == 'noun' and _pos(nxt) == 'adj':
            nxt.linked_to = word                    # bahay na maganda
        elif _pos(word) in ('noun', 'pronoun') and _pos(nxt) == 'verb':
            nxt.relative_head = word                # lalaking bumili …
        elif _pos(word) == 'pronoun' and _item(word).attrib('marker') == 'sa' and _pos(nxt) == 'noun':
            # aking bahay「私の家」(sa の代名詞 + 繋ぎ + 名詞)
            _rebuild(word, pos='noun', _=[('Gen', 'sg', morphology.GENDER)], possessor=True)
    return [w for i, w in enumerate(out) if i not in merged]


def mark_phrases(words):
    """標識の後ろの名詞句の語に標識の種類 (ang / ng / sa) を付ける。標識の語は句の頭の名詞の修飾語 (訳に出さない) か、
    sa / kay は前置詞 (に)。代名詞は自分の形の標識"""
    out = []
    i = 0
    while i < len(words):
        word = words[i]
        item = _item(word)
        if item is None or item.pos != 'marker':
            if item is not None and item.pos == 'pronoun':
                word.marker = item.attrib('marker')
            out.append(word)
            i += 1
            continue
        kind = item.attrib('marker')
        word.marker_role = kind
        j = i + 1
        phrase = []
        while j < len(words) and _pos(words[j]) in ('noun', 'adj', 'plural', 'pronoun') and \
                not (_pos(words[j]) == 'pronoun' and phrase):
            phrase.append(words[j])
            j += 1
            if phrase and _pos(phrase[-1]) in ('noun', 'pronoun') and not getattr(phrase[-1], 'linker', False) and \
                    not (j < len(words) and getattr(words[j], 'linked_to', None) is not None) and \
                    not (j < len(words) and _pos(words[j]) == 'noun' and _pos(phrase[-1]) == 'noun'):
                break  # 名詞が続けば同じ句 (ng farm visits、ang security guard)
        heads = [w for w in phrase if _pos(w) in ('noun', 'pronoun')] or [w for w in phrase if _pos(w) == 'adj']
        if not heads:
            i += 1
            continue
        personal = word.surface.lower() in ('si', 'ni', 'kay', 'sina', 'nina', 'kina')
        for w in phrase:
            w.marker = kind
            if personal and _pos(w) == 'noun' and script.key(w.surface) in KIN_TITLES:
                _rebuild(w, proper=True)   # si Nanay「母」(呼び名に使う親族の名詞は訳す)
            elif personal and _pos(w) == 'noun':
                _rebuild(w, ja=w.surface, gloss_lang='ja', proper=True)  # si Juan → Juan (人の名前)
            if item.attrib('plural') or any(_pos(p) == 'plural' for p in phrase):
                for it in w.items:
                    if it._:
                        it._ = [(c, 'pl', g) for c, n, g in it._]
        head = heads[-1]
        when = _time_gloss(phrase[0]) if len(phrase) == 1 else None
        if kind == 'sa' and when:
            # 時の sa の句 (sa Linggo「日曜日に」、sa Mayo「5月に」、sa gabi「夜に」、sa 2020「2020年に」) は副詞
            # (場所の sa の句と並べて「教会に=日曜日に」としない)
            _rebuild(phrase[0], pos='adv', ja=when + 'に', gloss_lang='ja', _=morphology._nominal_cngs())
            out.append(phrase[0])
            i = j
            continue
        if kind == 'sa':
            prep = Word(word.surface, [dict(item.item, pos='preposition', ja='に', dominates='Gen')])
            prep.token_ix = word.token_ix
            prep.marker = 'sa'
            out.append(prep)
            for w in phrase:
                _restrict(w, ('Gen',))
        else:
            article = Word(word.surface, [dict(item.item, pos='article')])
            article.token_ix = word.token_ix
            article.original_marker = word
            head.add_modifier(article)
        out += [w for w in phrase if _pos(w) != 'plural']
        i = j
    return out


# 場所焦点 -an でも ang の名詞が動作の対象 (を) になる語根 (binuksan niya ang pinto「彼がドアを開けた」。
# tinuruan・sinulatan の「〜に」はそのまま)
PATIENT_LOCATIVE = {'bukas', 'buksan', 'sara', 'linis', 'hugas', 'ting', 'tingin', 'tulong', 'tulungan', 'bayar', 'bayad'}
# 場所の sa の句を「〜で」と訳す動作の語根 (移動・存在・授受・置くは「〜に」のまま)
ACTIVITY_VERBS = {'kain', 'inom', 'aral', 'laro', 'luto', 'basa', 'trabaho', 'kanta', 'awit', 'sayaw', 'linis', 'bili',
                  'hugas', 'tulog', 'lakad', 'takbo', 'langoy', 'hintay', 'kita', 'tagpo', 'nood', 'turo', 'gawa',
                  'panganak', 'silang', 'ligo', 'usap', 'laba'}
NG_SLOTS = {'actor': 1, 'object': 1, 'conveyance': 1, 'locative': 2, 'existential': 1}


def mark_possessors(words):
    """所有: 名詞の後ろの ng の代名詞 (bahay ko「私の家」) と、名詞の後ろの ng 名詞句のうち、動詞が取る ng の補語の数
    (行為者・対象焦点は1つ、場所焦点は2つ) を超えたもの (Binili ng lalaki ang libro ng bata「子供の本」)、sa 句の中の
    名詞の後ろのもの (sa bahay ng lalaki)、動詞の無い節のもの (Maganda ang bahay ng lalaki)"""
    clause = []
    for word in words + [None]:
        if word is None or word.items is None or _pos(word) == 'conj':
            _mark_clause_possessors(clause)
            clause = []
        else:
            clause.append(word)


def _mark_clause_possessors(clause):
    verb = next((_item(w) for w in clause if _pos(w) == 'verb'), None)
    slots = NG_SLOTS.get(verb.attrib('focus'), 1) if verb is not None else 0
    used = 0
    for i, word in enumerate(clause):
        if getattr(word, 'marker', None) != 'ng' or _pos(word) not in ('noun', 'pronoun'):
            continue
        prev = clause[i - 1] if i > 0 else None
        pronoun = _pos(word) == 'pronoun'
        after_noun = prev is not None and _pos(prev) == 'noun' and (pronoun or not getattr(prev, 'is_possessor', False))
        in_sa = after_noun and getattr(prev, 'marker', None) == 'sa'
        if after_noun and (pronoun or in_sa or used >= slots):
            _rebuild(word, pos='noun', _=[('Gen', 'sg', morphology.GENDER)])
            word.is_possessor = True
            word.marker = 'gen'
            continue
        if not getattr(word, 'linked_to', None):
            used += 1


def mark_relatives(words):
    """名詞 + 繋ぎ + 動詞 (+ 補語): 連体節にして名詞の訳語に付ける (lalaking bumili ng isda → 魚を買った男、
    isdang binili ng lalaki → 男が買った魚)。節の語は除く"""
    from dragoman.core import en_ja
    from dragoman.kobun.modernize import Modern
    out = []
    i = 0
    while i < len(words):
        word = words[i]
        head = getattr(word, 'relative_head', None)
        item = _item(word)
        if head is None or item is None or item.pos != 'verb':
            out.append(word)
            i += 1
            continue
        verb = (item.ja or '').split(',')[0]
        if item.attrib('gloss_lang') == 'en' or re.search('[a-z]', verb):
            verb = (en_ja.translate(item.ja or '', 'verb') or verb).split(',')[0]
        if item.attrib('aspect') == 'completive':
            try:
                verb = Modern.past_form(verb)
            except Exception:
                pass
        elif item.attrib('aspect') == 'progressive':
            try:
                verb = Modern.te(verb) + 'いる'
            except Exception:
                pass
        j = i + 1
        parts = []
        focus = item.attrib('focus')
        while j < len(words) and getattr(words[j], 'marker', None) in ('ng', 'sa') and words[j].items:
            w = words[j]
            if _pos(w) == 'preposition':
                j += 1
                continue
            ja = (_item(w).ja or '').split(',')[0]
            if _item(w).attrib('gloss_lang') == 'en' or re.search('[a-z]', ja):
                ja = (en_ja.translate(_item(w).ja or '', 'noun') or ja).split(',')[0]
            if w.marker == 'sa':
                parts.append(ja + 'に')
            else:
                parts.append(ja + ('を' if focus == 'actor' else 'が'))
            j += 1
        hitem = _item(head)
        hja = (hitem.ja or '').split(',')[0]
        for w in words[i:j]:
            w.relative_of = head
            for m in w.modifiers:
                m.relative_of = head
                if getattr(m, 'original_marker', None) is not None:
                    m.original_marker.relative_of = head
        span = ' '.join(' '.join([m.surface for m in w.modifiers if isinstance(m, Word) and m.items and
                                  m.items[0].pos == 'article'] + [w.surface]) for w in words[i:j] if w.items)
        head.items = [type(hitem)(dict(hitem.item, ja=''.join(parts) + verb + hja, gloss_lang='ja', relative=span))]
        i = j
    return out


def assign_cases(words):
    """節 (動詞から次の動詞・接続詞・句読点まで、前の ay の句を含む) ごとに、焦点から ang / ng の格を決める"""
    clauses, current = [], []
    for word in words + [None]:
        if word is None or word.items is None or _pos(word) == 'conj':
            clauses.append(current)
            current = []
        else:
            current.append(word)
    for clause in clauses:
        verbs = [w for w in clause if _pos(w) == 'verb']
        verb = _item(verbs[0]) if verbs else None
        focus = verb.attrib('focus') if verb is not None else None
        angs = [w for w in clause if getattr(w, 'marker', None) == 'ang' and _pos(w) in ('noun', 'pronoun')]
        ngs = [w for w in clause if getattr(w, 'marker', None) == 'ng' and _pos(w) in ('noun', 'pronoun')]
        if verb is None or verb.attrib('copula'):
            for w in angs:
                _restrict(w, ('Nom',))
                w.focus = True
            continue
        if focus in ('object', 'conveyance'):
            ang_case, ng_cases = 'Acc', ['Nom', 'Nom']
        elif focus == 'locative' and verb.attrib('root') in PATIENT_LOCATIVE:
            ang_case, ng_cases = 'Acc', ['Nom', 'Nom']
        elif focus == 'locative':
            ang_case, ng_cases = 'Dat', ['Nom', 'Acc']
        elif focus == 'existential' and any(_pos(w) == 'noun' and getattr(w, 'marker', None) is None for w in clause):
            ang_case, ng_cases = 'Dat', ['Nom', 'Acc']   # 所有 (May libro ako「私には本がある」)
        elif focus == 'existential':
            ang_case, ng_cases = 'Nom', ['Nom', 'Acc']
        else:
            ang_case, ng_cases = 'Nom', ['Acc', 'Acc']
        for w in angs:
            _restrict(w, (ang_case,))
            w.focus = True
        if verb.attrib('root') in ACTIVITY_VERBS:
            # 動作の場所の sa は「で」(Kumain kami sa bahay「家で食べた」)。人の sa (受け手) は「に」のまま
            for k, w in enumerate(clause[:-1]):
                if _pos(w) != 'preposition' or getattr(w, 'marker', None) != 'sa' or _pos(clause[k + 1]) != 'noun':
                    continue
                person = w.surface.lower() in ('kay', 'kina') or animacy.is_animate(_item(clause[k + 1]))
                if not person:
                    _rebuild(w, ja='で')
                elif verb.attrib('root') == 'bili':
                    _rebuild(w, ja='から')   # bumili kay Juan「Juanから買った」
        for w in clause:
            item = _item(w)
            if _pos(w) == 'pronoun' and item.attrib('marker') == 'sa' and not item.attrib('possessor'):
                _restrict(w, ('Dat',))   # sa の代名詞 (dito「ここに」、sa akin「私に」)
        heads = [w for w in ngs]
        for k, w in enumerate(heads):
            _restrict(w, (ng_cases[min(k, 1)],))
        # 標識の無い名詞 (may の後ろなど) は主格
        if focus == 'existential':
            for w in clause:
                if _pos(w) == 'noun' and getattr(w, 'marker', None) is None:
                    _restrict(w, ('Nom',))
            # 生き物の存在は「いる」(May aso sa bahay「犬が家にいる」、may isang lalaki「一人の男がいる」)
            subjects = [w for w in clause if _pos(w) == 'noun' and getattr(w, 'marker', None) is None]
            if subjects and animacy.is_animate(_item(subjects[0])) and verb.ja in ('ある', 'ない'):
                _rebuild(verbs[0], ja={'ある': 'いる', 'ない': 'いない'}[verb.ja])


def handle_ay(words):
    """ay の倒置: ay を除く (前の句が主題、後ろが述語)。後ろが名詞類・形容詞だけなら見えない繋辞を補う"""
    out = []
    for i, word in enumerate(words):
        if _pos(word) != 'ay':
            out.append(word)
            continue
        rest = words[i + 1:]
        if not any(_pos(w) == 'verb' for w in rest[:4]):
            copula = Word('(ay)', [dict(COPULA)])
            copula.token_ix = word.token_ix
            out.append(copula)
    return out


def supply_copula(words):
    """動詞の無い節 (接続詞・句読点で区切る): 標識の無い述語 (形容詞・名詞) の後ろに ang 名詞句があれば、
    述語の後ろに繋辞を補う (Maganda ang bahay「家は美しい」、Guro si Juan「Juan は先生である」)"""
    out, clause = [], []
    for word in words + [None]:
        if word is None or word.items is None or _pos(word) == 'conj':
            out += _supply_copula(clause) + ([word] if word is not None else [])
            clause = []
        else:
            clause.append(word)
    return out


def _supply_copula(clause):
    if not clause or any(_pos(w) == 'verb' for w in clause):
        return clause
    if script.key(clause[0].surface) == 'nasaan' and any(_pos(x) in ('pronoun', 'noun') for x in clause[1:]):
        # nasaan「どこにある・いる」: Nasaan ka?「あなたは どこに いるか」
        _rebuild(clause[0], pos='adv', ja='どこに', interrogative=True)
        for x in clause[1:]:
            if _pos(x) in ('pronoun', 'noun'):
                _restrict(x, ('Nom',))
        copula = Word('(nasaan)', [dict(COPULA, existential=True)])
        copula.token_ix = clause[0].token_ix
        return clause + [copula]
    if script.key(clause[0].surface) == 'nasa' and any(getattr(x, 'marker', None) == 'ang' or
                                                       _pos(x) == 'pronoun' for x in clause[1:]):
        # nasa「〜にある・いる」(na + sa): Nasa bahay si Nanay「母は 家に いる」
        k = 1
        while k < len(clause) and getattr(clause[k], 'marker', None) == 'sa':
            k += 1
        copula = Word('(nasa)', [dict(COPULA, existential=True)])
        copula.token_ix = clause[0].token_ix
        return clause[:k] + [copula] + clause[k:]
    for k, w in enumerate(clause):
        # 代名詞の述語 (Ikaw ang …「〜はあなたである」): ang の形の代名詞のすぐ後ろに ang 名詞句
        predicate_pronoun = _pos(w) == 'pronoun' and k == 0 and \
            any(getattr(x, 'marker', None) == 'ang' and x is not w for x in clause[k + 1:])
        if predicate_pronoun:
            w.marker = None
            w.predicate = True
        if getattr(w, 'marker', None) is None and _pos(w) in ('adj', 'noun', 'pronoun') and \
                not getattr(w, 'linked_to', None) and any(getattr(x, 'marker', None) == 'ang' for x in clause[k + 1:]):
            copula = Word('(ay)', [dict(COPULA)])
            copula.token_ix = w.token_ix
            _restrict(w, ('Nom',))
            j = k + 1
            while j < len(clause) and getattr(clause[j], 'marker', None) is None and \
                    _pos(clause[j]) in ('adj', 'noun', 'adv') and getattr(clause[j], 'linked_to', None):
                j += 1
            return clause[:j] + [copula] + clause[j:]
    content = [w for w in clause if w.items is not None]
    nouns = [w for w in content if _pos(w) == 'noun' and getattr(w, 'marker', None) is None]
    if len(nouns) == 1 and all(w is nouns[0] or _pos(w) == 'adv' for w in content) and len(content) >= 2:
        # 名詞 + 時の副詞だけの文 (Sabado kahapon「昨日は 土曜日であった」): 名詞は補語、見えない繋辞を補う
        noun = nouns[0]
        _rebuild(noun, complement=True)
        copula = Word('(ay)', [dict(COPULA, shared_subject=True)])
        copula.token_ix = noun.token_ix
        k = clause.index(noun) + 1
        return clause[:k] + [copula] + clause[k:]
    return clause


def drop_enclitics(words):
    """丁寧の po / ho、疑問の ba などの小辞: 丁寧・疑問は訳に出さない。ほかは副詞 (na「もう」、din「〜も」)"""
    out = []
    for word in words:
        item = _item(word)
        if item is not None and item.pos == 'enclitic':
            if item.attrib('enclitic') in ('polite', 'question') or not item.ja:
                continue
            _rebuild(word, pos='adv')
        out.append(word)
    return out


def collapse_pati(words):
    """pati na rin・pati rin・pati na (「〜も、それに」) は1つの pati に: 後ろの na・rin・din と前の読点は
    語ごとの表に残し、訳の語の列からは除く。名詞類の間の pati は「と」、文頭・節の頭の pati
    (Pati si Juan ay dumating「Juanも着いた」) は後ろの名詞類の「〜も」 (attach_also)"""
    drop = set()
    keys = [script.key(w.surface) for w in words]
    for i, key in enumerate(keys):
        if key != 'pati':
            continue
        if i and words[i - 1].surface == ',':
            drop.add(i - 1)   # mansanas, pati saging: 読点は並列の「と」に含める
        end = i + 1
        while end < len(words) and keys[end] in ('na', 'rin', 'din') and end - i <= 2:
            end += 1
        for j in range(i + 1, end):
            item = _rebuild(words[j], ja='', base='%s (%s の一部)' % (keys[j], ' '.join(keys[i:end])))
            words[j].original_item = dict(item.item)   # 語ごとの表も「pati na rin の一部」
            drop.add(j)
    return [w for i, w in enumerate(words) if i not in drop]


def attach_also(words):
    """文頭の pati「〜も」は後ろの名詞類の助詞に (Pati si Juan ay dumating「Juanも着いた」)"""
    out = []
    for i, word in enumerate(words):
        item = _item(word)
        if item is not None and item.attrib('also'):
            nxt = next((w for w in words[i + 1:] if _pos(w) in ('noun', 'pronoun')), None)
            if nxt is not None:
                nxt.also = True
                continue
        out.append(word)
    return out


def lookup_all(surfaces):
    words = choose_bukas(_words(surfaces))
    global _display
    _display = [w for w in words]
    words = collapse_pati(words)
    words = merge_time_phrases(words)
    words = mark_linkers(words)
    words = attach_also(mark_phrases(words))
    mark_possessors(words)
    words = mark_relatives(words)
    words = drop_enclitics(words)
    words = handle_ay(words)
    words = supply_copula(words)
    for i, word in enumerate(words):
        word.index = i
    assign_cases(words)
    past_context(words)
    choose_ngayon(words)
    choose_saan(words)
    return words


def choose_saan(words):
    """saan「どこ」: 住む・行く・来るの文なら「どこに」、ほかの動詞なら「どこで」(Saan ka nakatira?「どこに 住んでいるか」)"""
    verb = next((_item(w) for w in words if _pos(w) == 'verb'), None)
    if verb is None:
        return
    goal = (verb.ja or '').split(',')[0] in ('住む', '行く', '来る', '帰る', '着く', '置く')
    for word in words:
        if _pos(word) == 'adv' and script.key(word.surface) == 'saan' and _item(word).ja == 'どこ':
            _rebuild(word, ja='どこに' if goal else 'どこで')


def choose_ngayon(words):
    """ngayon「今」は、完了の動詞の文では「今日」(Kumain si Nanay ngayon「母は 今日 食べた」)"""
    if not any(_pos(w) == 'verb' and _item(w).attrib('tense') in ('perfect', 'pluperfect') for w in words):
        return
    for word in words:
        if _pos(word) == 'adv' and script.key(word.surface) == 'ngayon' and _item(word).ja == '今':
            _rebuild(word, ja='今日')


# 過去の時の副詞 (kahapon「昨日」、kanina「さっき」): 文の進行・不定の動詞を過去に
PAST_ADVERBS = {'kahapon', 'kanina', 'noon'}


def past_context(words):
    """noong「〜したとき」の節・過去の時の副詞 (kahapon) のある文は過去のこと: 進行・状態は「〜していた」、不定・繋辞は「〜した・だった」
    (Noong bata pa ako, nakatira ako sa Maynila「{私が まだ 子供だった}とき 私は マニラに 住んでいた」)。
    タガログ語の動詞は相だけで時制を持たないので、過去の時の節に合わせる"""
    past = lambda w: _pos(w) == 'conj' and script.key(w.surface) in ('noong', 'nung') or \
        script.key(w.surface) in PAST_ADVERBS and _pos(w) == 'adv' or (_item(w) is not None and (_item(w).attrib('base') or '').startswith('noong '))
    if not any(past(w) for w in words):
        return
    for word in words:
        item = _item(word)
        if item is None or item.pos != 'verb':
            continue
        tense = item.attrib('tense')
        if tense == 'progressive':
            _rebuild(word, tense='imperfect')
        elif tense in (None, 'present'):
            _rebuild(word, tense='perfect')


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(TAGALOG):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)  # 見出しの行・音読は元の文 (標識・関係節の語はまとめた後の語の列に無い)
    analysis.display = _display        # 語ごとの表は元の語 (標識・関係節の語を含む)
    return analysis


_display = []


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
