#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 聖書ヘブライ語の文の解析
#
# 語を OSHB の解析で切れ目 (接続詞 ו、定冠詞 ה、前置詞 ב ל כ מ、本体、人称接尾辞) ごとの語に分け、
# 格の代わりの手がかりで名詞の「格」を絞ってから、並列・係り先・前置詞句・格の枠・日本語訳を共通の解析器
# (core/analyzer.py) をヘブライ語の設定 (HEBREW) で使う:
#   - 定冠詞 ה と目的語の標識 אֵת は名詞の修飾語として付け、訳に出さない。אֵת の後ろの名詞は対格
#   - 連語形 (construct) の名詞の後ろの名詞・人称接尾辞は属格「〜の」(בֵּית הַמֶּלֶךְ「王の家」、בְּנוֹ「彼の息子」)
#   - 動詞の人称接尾辞は対格「〜を」、前置詞の人称接尾辞は前置詞の目的語
#   - 主語は動詞と性・数が合う名詞 (ヘブライ語の動詞は性も変わる)
#   - 動詞の無い文 (名詞文) には見えない繋辞を補う (יְהוָה רֹעִי「主は私の羊飼い」)
#
import dataclasses
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, script

PUNCTUATION = {script.SOF_PASUQ: 'period', '.': 'period', ',': 'comma', ';': 'comma', ':': 'comma', '?': 'question',
               '!': 'period', '׀': None, '׀': None}
TOKEN = re.compile('[֑-ׂׄ-ׇא-ת͏‌‍]+|[׃.,;:?!]')
AND_WORDS = ('ו', 'וְ', 'וּ', 'וַ', 'וָ', 'וֶ', 'וִ', 'וֵ')


def _root_items(lemma):
    return []


# 副詞節の従属接続詞 (見出し) → (節の後ろに付ける形, 節の動詞の時制) (core/Adverbial.py。כִּי は「〜ということ」とも
# 読むので入れない)
SUBORDINATORS = {'כַּאֲשֶׁר': ('とき', None), 'אִם': ('なら', None)}


HEBREW = language.Language(
    name='he',
    subordinators=SUBORDINATORS,
    and_words=AND_WORDS,
    copulas=frozenset({'הָיָה'}),
    negations=frozenset({'לֹא', 'אַל', 'לֹא־', 'אַל־'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Gen': 'の', 'Dat': 'に', 'Voc': 'よ'},
    absolute_case=None,
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
    particle=lambda case, obj, pred: 'と' if getattr(obj, 'quote', False) else None,   # 引用「〜と言った」
)


ATNAH = '\u0591'  # 節を前半と後半に分ける朗唱記号 (アトナハ ֑)


# 聖書アラム語: 繋辞 הֲוָא「〜である」、否定 לָא。ほかはヘブライ語と同じ。
# 文の中で言語が混ざっても否定・繋辞を取りこぼさないよう、どちらの設定にも両方の語を入れる
COPULAS = frozenset({'הָיָה', 'הֲוָא'})
NEGATIONS = frozenset({'לֹא', 'אַל', 'לֹא־', 'אַל־', 'לָא', 'לָא־'})
HEBREW = dataclasses.replace(HEBREW, copulas=COPULAS, negations=NEGATIONS)
ARAMAIC = dataclasses.replace(HEBREW, name='arc')


def tokens(text):
    """語 (マカフ ־ でつながった語は分ける) と句読点 (ソフ・パスーク ׃)。アトナハのある語の後ろには節の切れ目 (,) を"""
    out = []
    for token in TOKEN.findall(text.replace(script.MAQAF, ' ')):
        out.append(token)
        if ATNAH in token:
            out.append(',')
    return out


def sentences(text):
    current = []
    for token in tokens(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def _languages(token):
    """語の OSHB の解析にある言語の集合 (H / A)"""
    return {f['morph'][:1] for f in morphology.analyses(token)} if token not in PUNCTUATION else set()


def choose_languages(surfaces):
    """語ごとの言語 (H ヘブライ語 / A アラム語)。どちらにも読める語は前 (無ければ後ろ) の語に合わせる
    (ダニエル書 2:4 は文の途中でアラム語に変わる)"""
    langs = [_languages(s) for s in surfaces]
    out = [next(iter(l)) if len(l) == 1 else None for l in langs]
    for i in range(len(out)):
        if out[i] is None and langs[i]:
            prev = next((out[j] for j in range(i - 1, -1, -1) if out[j]), None)
            nxt = next((out[j] for j in range(i + 1, len(out)) if out[j]), None)
            out[i] = prev or nxt or 'H'
    return out


def _words(token, ix, prefer='H'):
    """1語 → 切れ目ごとの Word のリスト。prefer はどちらにも読める語の言語"""
    if token in PUNCTUATION:
        word = Word(token, None)
        word.token_ix = ix
        return [word]
    found = morphology.analyses(token, prefer or 'H')
    if not found:
        word = Word(script.pointed(token), [])
        word.token_ix = ix
        return [word]
    out = []
    for k, (surface, item) in enumerate(morphology.segments(found[0])):
        word = Word(surface, [item])
        word.token_ix = ix
        # 同じ綴りで連語形の解析もある名詞 (רוּחַ「霊」は絶対形と連語形が同じ形) は、その項目を持っておく
        construct = _construct_alternative(found, k)
        if construct is not None and item.get('state') == 'absolute':
            word.construct_item = construct
        out.append(word)
    # 普通名詞と同じ綴りの人名 (הֶבֶל「息,空しさ」と「アベル」): 人名の項目を持っておく (choose_names)
    if len(out) == 1 and out[0].items and not out[0].items[0].attrib('proper'):
        name = next((a for a in found[1:] if a['morph'][1:] == 'Np' and len(a['segments']) == 1), None)
        if name is not None:
            out[0].name_item = morphology.segments(name)[0][1]
    elif len(out) == 1 and out[0].items and out[0].items[0].attrib('proper'):
        # 人名が一番多いが、連語形の分詞・名詞にも読める語 (עֹבֵד「オベド」/「仕える者」): その項目を持っておく
        common = next((a for a in found[1:] if len(a['segments']) == 1 and a['morph'][1:2] in 'VN' and
                       a['morph'][1:3] != 'Np' and a['morph'].endswith('c')), None)
        if common is not None:
            out[0].common_item = morphology.segments(common)[0][1]
    return out


# 連語形の分詞 + 名詞の「〜する人」の訳: (分詞の見出し, 後ろの名詞の見出し) → 訳 (Strong の番号)
AGENT_NOUNS = {('5647', '127'): '耕し手', ('7462', '6629'): '羊飼い'}   # עֹבֵד אֲדָמָה「土の耕し手」、רֹעֵה צֹאן「羊飼い」

# 親族の名詞 (Strong の番号): 人名と同格に並ぶ (אֶת־אָחִיו אֶת־הָבֶל「彼の弟アベルを」)
KIN_NOUNS = ('251', '1121', '1323', '802', '1', '517', '269')   # 兄弟・息子・娘・妻・父・母・姉妹
_names_seen = set()   # この文章で人名に読んだ語 (子音字)


def _is_kin(word):
    return bool(word.items) and word.items[0].pos == 'noun' and \
        (word.items[0].attrib('lemma') or '').rstrip('abcdefgh') in KIN_NOUNS


def agent_nouns(words):
    """連語形の分詞 + 名詞は「〜する人」の名詞 (עֹבֵד אֲדָמָה「土の耕し手」、רֹעֵה צֹאן「羊飼い」)"""
    for i, word in enumerate(words):
        item = word.items[0] if word.items else None
        if item is None or item.pos != 'participle' or item.attrib('state') != 'construct':
            continue
        nxt = next((w for w in words[i + 1:i + 3] if w.items and w.items[0].pos != 'article'), None)
        if nxt is None or nxt.items[0].pos != 'noun':
            continue
        key = ((item.attrib('lemma') or '').rstrip('abcdefgh'), (nxt.items[0].attrib('lemma') or '').rstrip('abcdefgh'))
        ja = AGENT_NOUNS.get(key) or (item.attrib('ja') or '').split(',')[0] + '者'
        word.items = [type(item)(dict(item.item, pos='noun', ja=ja, gloss_lang='ja'))] + word.items[1:]


def choose_names(words):
    """人名とも読める普通名詞: 親族の名詞と同格に並ぶとき (אָחִיו אֶת־הָבֶל)、または同じ文章で前に人名に読んだ語は
    人名に (創世記4章のアベル。コヘレトの言葉の הֲבֵל הֲבָלִים「空しさの空しさ」は普通名詞のまま)"""
    for i, word in enumerate(words):
        common = getattr(word, 'common_item', None)
        if common is not None and script.consonants(word.surface) not in _names_seen:
            nxt = next((w for w in words[i + 1:i + 3] if w.items and w.items[0].pos != 'article'), None)
            if nxt is not None and nxt.items[0].pos == 'noun':
                word.items = [type(word.items[0])(common)]   # 後ろに名詞: 連語形 (人名「オベド」でなく)
            continue
        name = getattr(word, 'name_item', None)
        if name is None:
            continue
        skip = lambda w: w.items and (w.items[0].pos == 'article' or w.items[0].attrib('suffix'))
        before = next((w for w in reversed(words[max(0, i - 4):i]) if not skip(w)), None)
        after = next((w for w in words[i + 1:i + 3] if not skip(w)), None)
        key = script.consonants(word.surface)
        if key in _names_seen or any(w is not None and _is_kin(w) for w in (before, after)):
            word.items = [type(word.items[0])(name)]
            _names_seen.add(key)


def _construct_alternative(found, k):
    """OSHB の解析の候補のうち、切れ目 k が連語形の名詞で、ほかの切れ目は1つ目の解析と同じもの (の項目)"""
    first = morphology.segments(found[0])
    for analysis in found[1:]:
        segments = morphology.segments(analysis)
        if len(segments) != len(first) or segments[k][1].get('state') != 'construct':
            continue
        if all(a[1]['pos'] == b[1]['pos'] for a, b in zip(first, segments)):
            return segments[k][1]
    return None


def choose_construct(words):
    """連語形とも読める名詞は、すぐ後ろ (冠詞を除く) が名詞なら連語形に (רוּחַ אֱלֹהִים「神の霊」)"""
    for i, word in enumerate(words):
        construct = getattr(word, 'construct_item', None)
        if construct is None:
            continue
        nxt = next((w for w in words[i + 1:] if w.items is not None and
                    not (w.items and w.items[0].pos == 'article')), None)
        if nxt is not None and nxt.items and nxt.items[0].pos == 'noun' and not nxt.items[0].attrib('suffix'):
            word.items = [type(word.items[0])(construct)]


def _nominal(word):
    return bool(word.items) and word.items[0].pos in ('noun', 'pronoun', 'adj', 'participle')


def attach_markers(words):
    """定冠詞 ה と目的語の標識 אֵת を後ろの名詞類の修飾語にする (訳には出さない)。אֵת の後ろは対格。
    アラム語の限定状態の語尾 -āʾ は前の名詞に付ける"""
    for i, word in enumerate(words):
        if not word.items or word.items[0].pos != 'article':
            continue
        if word.items[0].attrib('emphatic'):
            target = next((w for w in reversed(words[:i]) if _nominal(w)), None)
            if target is not None:
                target.items[0].item['definite'] = True
                target.add_modifier(word)
            continue
        target = next((w for w in words[i + 1:i + 4] if _nominal(w)), None)
        if target is None:
            continue
        if word.items[0].attrib('desc') == '目的語の標識':
            target.restrict_cases(('Acc',))
            # 並列した目的語 (אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ) はそれぞれの אֵת で
        else:
            target.items[0].item['definite'] = True
        target.add_modifier(word)


def mark_construct(words):
    """連語形の名詞の後ろの名詞・人称接尾辞を属格に。動詞の人称接尾辞は対格、前置詞の人称接尾辞は対格 (前置詞の目的語)"""
    for i, word in enumerate(words):
        if not word.items or getattr(word, 'attached_to', None) is not None:
            continue
        item = word.items[0]
        if item.attrib('suffix'):
            prev = next((w for w in reversed(words[:i]) if w.items and getattr(w, 'attached_to', None) is None), None)
            host = prev.items[0].pos if prev is not None else None
            word.restrict_cases(('Gen',) if host in ('noun', 'adj', 'participle') else ('Acc',))
            continue
        if item.pos in ('noun', 'adj', 'participle') and item.attrib('state') == 'construct':
            # すぐ後ろ (冠詞を除く) の名詞類だけ (動詞を越えない)
            nxt = next((w for w in words[i + 1:] if getattr(w, 'attached_to', None) is None), None)
            # 組んでいる相手を書いておく (解説の「連語形」の行に使う)
            if nxt is not None and nxt.items and nxt.items[0].attrib('suffix'):
                item.item['construct_with'] = ('suffix', nxt.surface, nxt.items[0].ja)
            elif nxt is not None and _nominal(nxt):
                item.item['construct_with'] = ('noun', nxt.surface, nxt.items[0].ja.split(',')[0])
            else:
                item.item['construct_with'] = ('none', '', '')
            if nxt is not None and _nominal(nxt) and not nxt.items[0].attrib('suffix'):
                for it in nxt.items:
                    if it._:
                        it._ = [('Gen',) + tuple(c[1:]) for c in it._ if c[0] in ('Nom', 'Acc')] or it._


def attach_suffix_genitives(words):
    """名詞の人称接尾辞 (属格) を名詞の属格にする (אָחִיו「彼の兄」。述語の枠の「彼の」として離さない)"""
    out = []
    for word in words:
        item = word.items[0] if word.items else None
        prev = out[-1] if out else None
        governed = len(out) >= 2 and out[-2].items and out[-2].items[0].pos == 'preposition'
        # 前置詞の目的語の名詞 (לְעַבְדָּךְ「あなたの僕に」) はそのまま (後ろの וּ が前置詞句と並列に読まれないように)
        if item is not None and item.attrib('suffix') and item._ and all(c[0] == 'Gen' for c in item._) and \
                prev is not None and prev.items and prev.items[0].pos == 'noun' and not governed and \
                getattr(word, 'attached_to', None) is None:
            prev.add_genitive(word)
            continue
        out.append(word)
    return out


def _finite(item):
    return item.pos == 'verb' and item.attrib('mood') in ('indicative', 'imperative', 'subjunctive')


def _free_nominals(words):
    """前置詞の目的語・修飾語・人称接尾辞を除いた名詞類の位置"""
    out = []
    after_preposition = False
    for i, word in enumerate(words):
        if not word.items or getattr(word, 'attached_to', None) is not None:
            continue
        item = word.items[0]
        if item.pos == 'preposition':
            after_preposition = True
            continue
        if item.pos in ('noun', 'pronoun') and not item.attrib('suffix'):
            if not after_preposition and item.attrib('state') != 'genitive':
                out.append(i)
            after_preposition = False
        elif item.pos not in ('adj', 'participle'):
            after_preposition = False
    return out


def choose_subject(words):
    """3人称の定動詞の主語を決める: 動詞の後ろ (無ければ前) の、性・数が合い、対格・属格に決まっていない最初の名詞類を
    主格に (וַיֹּאמֶר אֱלֹהִים「神は言った」。ヘブライ語の物語は 動詞-主語-目的語 の順で、目的語は אֵת で示されることが多い)。
    性の合わない名詞は主語にしない"""
    free = _free_nominals(words)
    for i, word in enumerate(words):
        if not word.items or not _finite(word.items[0]):
            continue
        if word.items[0].attrib('person') in (1, 2):
            # 1・2人称の動詞 (אֱמַר「言え」、נְחַוֵּא「私たちは告げよう」) の節の3人称の名詞は主語にならない → 目的語
            nxt = next((j for j in range(i + 1, len(words)) if _finite_word(words[j]) or words[j].items is None),
                       len(words))
            prv = next((j for j in range(i - 1, -1, -1) if _finite_word(words[j]) or words[j].items is None), -1)
            for j in free:
                if prv < j < nxt and (words[j].items[0].pos == 'noun' or words[j].items[0].attrib('interrogative')):
                    # 疑問代名詞も (מָה עָשִׂיתָ「何を したか」)
                    item = words[j].items[0]
                    accusative = [c for c in item._ or [] if c[0] == 'Acc']
                    if accusative and not any(c[0] == 'Voc' for c in item._):
                        item._ = accusative
            continue
        if word.items[0].attrib('person') != 3:
            continue
        verb = word.items[0]
        gender, number = verb.attrib('gender'), verb.attrib('number')

        def agrees(c):
            return c[0] == 'Nom' and c[1] == number and (gender is None or c[2] in (gender, None))
        nxt = next((j for j in range(i + 1, len(words)) if _finite_word(words[j])), len(words))
        prv = next((j for j in range(i - 1, -1, -1) if _finite_word(words[j])), -1)
        candidates = [j for j in free if i < j < nxt] + [j for j in reversed(free) if prv < j < i]
        for j in candidates:
            item = words[j].items[0]
            if any(agrees(c) for c in item._ or []):
                item._ = [c for c in item._ if agrees(c)]
                break


def _finite_word(word):
    return bool(word.items) and _finite(word.items[0])


COPULA = {'pos': 'verb', 'pres1sg': 'הָיָה', 'base': 'הָיָה', 'ja': 'ある,いる', 'gloss_lang': 'ja', 'voice': 'active',
          'mood': 'indicative', 'tense': 'present', 'person': 3, 'number': 'sg', 'desc': '名詞文 (繋辞なし)'}


def supply_copula(words):
    """動詞の無い節 (名詞文) に見えない繋辞を補う: 主格に読める名詞類が2つ以上あれば、最初のものの後ろに。
    節は句読点 (アトナハの切れ目を含む) で区切る"""
    out, clause = [], []
    for word in words:
        if word.items is None:
            out += _supply_copula(clause) + [word]
            clause = []
        else:
            clause.append(word)
    return out + _supply_copula(clause)


def _supply_copula(words):
    """節の、最初の定動詞より前 (定動詞が無ければ全体) に主格に読める名詞類が2つ以上あり、その定動詞が主語を取らない
    (1・2人称の) ときに補う (יְהוָה רֹעִי לֹא אֶחְסָר「主は私の羊飼い、私は乏しくない」)"""
    first = next((i for i, w in enumerate(words) if w.items and w.items[0].pos == 'verb'
                  and w.items[0].attrib('mood') != 'infinitive'), None)
    if first is not None and words[first].items[0].attrib('person') == 3:
        return words
    if first is not None:
        while first > 0 and words[first - 1].items and words[first - 1].items[0].pos == 'adv':
            first -= 1  # 動詞の前の否定・副詞 (לֹא אֶחְסָר) は動詞の側に
    head = words if first is None else words[:first]
    nominals = set(_free_nominals(head))  # 前置詞の目的語 (לְעָלְמִין「とこしえに」) は数えない
    free = [i for i, w in enumerate(head) if (i in nominals or w.items and w.items[0].pos in ('adj', 'participle'))
            and _nominal(w) and getattr(w, 'attached_to', None) is None
            and any(c[0] == 'Nom' for c in w.items[0]._ or [])]
    if len(free) < 2:
        return words
    second = head[free[1]].items[0]
    after = head[free[1] + 1] if free[1] + 1 < len(head) else None
    suffixed = after is not None and after.items and (after.items[0].attrib('suffix') or
                                                       getattr(after, 'attached_to', None) is head[free[1]])
    if second.pos == 'participle' and second.attrib('voice') != 'passive' and first is None and not suffixed and \
            second.attrib('gloss_lang', 'ja') == 'ja':
        # 主語 + 能動の分詞の名詞文は現在の動作 (הַיֶּלֶד קוֹרֵא סֵפֶר「その子供が本を読んでいる」)。
        # 分詞を定動詞 (現在・進行) にして、後ろの名詞は目的語に
        number = next((c[1] for c in second._ or [] if c[0] == 'Nom'), 'sg')
        gender = next((c[2] for c in second._ or [] if c[0] == 'Nom'), None)
        verb = dict(second.item, pos='verb', mood='indicative', tense='progressive', voice='active', person=3,
                    number=number, gender=gender, participle_predicate=True)
        head[free[1]].items = [type(second)(verb)] + head[free[1]].items[1:]
        subject = head[free[0]].items[0]
        subject._ = [c for c in subject._ if c[0] == 'Nom'] or subject._   # 分詞の前の名詞が主語
        for j in free[2:]:
            item = head[j].items[0]
            item._ = [c for c in item._ or [] if c[0] == 'Acc'] or item._   # 後ろの名詞は目的語
        head[free[1]].participle_subject = head[free[0]]
        return words
    at = free[0] + 1
    while at < len(head) and head[at].items and (head[at].items[0].attrib('suffix') or
                                                 any(c[0] == 'Gen' for c in head[at].items[0]._ or [])):
        at += 1  # 主語に掛かる属格・人称接尾辞の後ろへ
    copula = Word('(הוּא)', [dict(COPULA, surface='(הוּא)')])
    rest = [] if first is None else [Word(',', None)] + words[first:]
    return head[:at] + [copula] + head[at:] + rest


def mark_vocatives(words):
    """命令形 (2人称) の動詞の近くの固有名詞は呼びかけ「〜よ」(שְׁמַע יִשְׂרָאֵל「聞け、イスラエルよ」)"""
    for i, word in enumerate(words):
        if not word.items or word.items[0].pos != 'verb' or word.items[0].attrib('mood') != 'imperative' \
                or word.items[0].attrib('person') != 2:
            continue
        for other in words[max(0, i - 4):i + 3]:
            if not other.items or getattr(other, 'attached_to', None) is not None:
                continue
            item = other.items[0]
            # 固有名詞、またはアラム語の限定状態の名詞 (מַלְכָּא לְעָלְמִין חֱיִי「王よ、とこしえに生きよ」)
            # (アラム語の限定状態の名詞は命令形の前のものだけ。後ろは目的語が多い: אֱמַר חֶלְמָא「夢を言え」)
            position = words.index(other)
            emphatic = item.attrib('lang') == 'arc' and item.pos == 'noun' and position < i and \
                _has_emphatic(words, position)
            if item.attrib('proper') or emphatic:
                item._ = [('Voc',) + tuple(c[1:]) for c in item._ if c[0] == 'Nom'] or item._


def mark_di(words):
    """アラム語の דִּי: 名詞の後ろで、すぐ後ろが名詞なら属格「〜の」(שְׁמֵהּ דִּי־אֱלָהָא「神の名」)。
    דִּי は名詞に付けて訳に出さず、後ろの名詞を属格にする。それ以外は関係詞・接続詞「〜するところの / 〜ということ」"""
    for i, word in enumerate(words):
        if not word.items or not word.items[0].attrib('relative'):
            continue
        prev = next((w for w in reversed(words[:i]) if w.items is not None
                     and getattr(w, 'attached_to', None) is None and not w.items[0].attrib('emphatic')), None)
        nxt = next((w for w in words[i + 1:] if w.items is not None), None)
        if prev is None or nxt is None or not _nominal(prev) or not _nominal(nxt) or nxt.items[0].pos == 'adj':
            continue
        # 後ろに定動詞が続けば関係詞 (אֱלָהַיָּא דִּי שְׁמַיָּא וְאַרְקָא לָא עֲבַדוּ「天と地を造らなかった神々」)
        rest = []
        for w in words[i + 1:]:
            if w.items is None:
                break
            rest.append(w)
        if any(_finite(w.items[0]) for w in rest if w.items):
            continue
        for it in nxt.items:
            if it._:
                it._ = [('Gen',) + tuple(c[1:]) for c in it._ if c[0] in ('Nom', 'Acc')] or it._
        item = word.items[0].item
        item.update(pos='article', ja=DI_GENITIVE_NOTE, genitive=True)
        word.items = [type(word.items[0])(item)]
        nxt.add_modifier(word)


DI_GENITIVE_NOTE = ' ※属格の dî「〜の」: 前の名詞に後ろの名詞を掛ける (šəmēh dî ʾĕlāhāʾ「神の名」)。'


def _has_emphatic(words, i):
    nxt = words[i + 1] if i + 1 < len(words) else None
    return nxt is not None and bool(nxt.items) and bool(nxt.items[0].attrib('emphatic'))


def merge_kaasher(words):
    """כַּאֲשֶׁר「〜するとき」: 切り分けた前置詞 כַּ と接続詞 אֲשֶׁר (見出しは כַּאֲשֶׁר) を1語に"""
    out = []
    for word in words:
        if out and word.items and word.items[0].pos == 'conj' and word.items[0].attrib('base') == 'כַּאֲשֶׁר' and \
                out[-1].items and out[-1].items[0].pos == 'preposition':
            word.surface = out.pop().surface + word.surface
        out.append(word)
    return out


def relative_asher(words):
    """名詞の後ろの関係の小辞 אֲשֶׁר は関係代名詞 (הָאִישׁ אֲשֶׁר בָּא「来た男」)。形は変わらないので、性・数はどれにも読み、
    空所の格は共通の解析器が節の空きで決める"""
    for k, word in enumerate(words):
        item = word.items[0] if word.items else None
        if item is None or item.pos != 'conj' or script.consonants(word.surface) != 'אשר' or k == 0:
            continue
        prev = next((w for w in reversed(words[:k]) if w.items and w.items[0].pos != 'article'), None)
        if prev is None or prev.items[0].pos not in ('noun', 'pronoun'):
            continue
        word.items = [type(item)(dict(item.item, pos='pronoun', desc='関係代名詞', ja='〜するところの',
                                      _=[(c, n, g) for c in ('Nom', 'Acc') for n in ('sg', 'pl') for g in ('m', 'f')]))]


def merge_yasaf(words):
    """yāsap (hifʿil「加える」) + לְ + 不定詞は「再び〜する」(וַתֹּסֶף לָלֶדֶת「彼女は また 産んだ」。「産むことを加えた」でなく):
    yāsap の定動詞の訳語を不定詞の動詞の訳語にして、לְ と不定詞は訳の語の列から除く (目的語は yāsap の節に残る)"""
    out = []
    i = 0
    while i < len(words):
        word = words[i]
        item = word.items[0] if word.items else None
        nxt = words[i + 1:i + 3]
        if item is not None and item.pos == 'verb' and item.attrib('pres1sg') == 'יָסַף' and _finite(item) and \
                len(nxt) == 2 and nxt[0].items and nxt[0].items[0].pos == 'preposition' and \
                script.consonants(nxt[0].surface) == 'ל' and nxt[1].items and nxt[1].items[0].pos == 'verb' and \
                nxt[1].items[0].attrib('mood') == 'infinitive':
            inf = nxt[1].items[0]
            ja = ','.join('再び' + g for g in (inf.ja or '').split(',')[:2])
            word.items = [type(item)(dict(item.item, ja=ja, gloss_lang=inf.attrib('gloss_lang'),
                                          base=item.attrib('base') + ' + ' + (inf.attrib('base') or '')))] + word.items[1:]
            out.append(word)
            i += 3
            continue
        out.append(word)
        i += 1
    return out


SPEECH_VERBS = {'אָמַר'}


def split_quotations(words):
    """動詞の前に引用の名詞句を置く言う文 (הֲבֵל הֲבָלִים אָמַר קֹהֶלֶת הֲבֵל הֲבָלִים הַכֹּל הָבֶל「空しさの空しさ、と
    コヘレトは言った。空しさの空しさ、すべては空しい」): 動詞の前の名詞句は引用「〜と」、主語の後ろは別の節。
    後ろが前の句の繰り返しで始まれば、そこでも切る (後ろの名詞文 הַכֹּל הָבֶל に繋辞を補えるように)"""
    for i, word in enumerate(words):
        item = word.items[0] if word.items else None
        if item is None or item.pos != 'verb' or item.attrib('pres1sg') not in SPEECH_VERBS or not _finite(item):
            continue
        start = next((k + 1 for k in range(i - 1, -1, -1) if words[k].items is None or _finite_word(words[k])), 0)
        before = words[start:i]
        if not before or not all(w.items and w.items[0].pos in ('noun', 'adj', 'article') for w in before):
            continue
        subject = words[i + 1] if i + 1 < len(words) else None
        if subject is None or not subject.items or subject.items[0].pos not in ('noun', 'name'):
            continue
        for w in before:
            if w.items[0].pos == 'noun' and not any(c[0] == 'Gen' for c in w.items[0]._ or []):
                w.quote = True
        end = next((k for k in range(i + 2, len(words)) if words[k].items is None), len(words))
        if end <= i + 2:
            continue
        cut = [i + 2]
        repeat = [script.consonants(w.surface) for w in before]
        if [script.consonants(w.surface) for w in words[i + 2:i + 2 + len(before)]] == repeat and \
                i + 2 + len(before) < end:
            cut.append(i + 2 + len(before))
        if len(cut) > 1:
            # 繰り返しの句だけの名詞文 (הֲבֵל הֲבָלִים「空しさの空しさである」): 句の後ろに見えない繋辞、句は補語
            head = words[i + 2]
            head.items = [type(head.items[0])(dict(head.items[0].item, complement=True))] + head.items[1:]
            words.insert(cut[1], Word(',', None))
            words.insert(cut[1], Word('(הוּא)', [dict(COPULA, surface='(הוּא)', shared_subject=True)]))   # 主語は補わない
            cut = cut[:1]
        for k in reversed(cut):
            words.insert(k, Word(',', None))
        return words
    return words


def lookup_all(surfaces):
    langs = choose_languages(surfaces)
    words = [w for ix, s in enumerate(surfaces) for w in _words(s, ix, langs[ix])]
    words = merge_yasaf(merge_kaasher(words))
    relative_asher(words)
    mark_vocatives(words)
    choose_names(words)
    agent_nouns(words)
    choose_construct(words)
    attach_markers(words)
    mark_di(words)
    mark_construct(words)
    words = attach_suffix_genitives(words)
    words = split_quotations(words)
    words = supply_copula(words)  # 名詞文の繋辞を先に補う (後ろの1・2人称の動詞の節と分けるため)
    choose_subject(words)
    for i, word in enumerate(words):
        word.index = i
    return words


def sentence_language(words):
    """文の言語: 語の多いほう (アラム語なら ARAMAIC の設定)"""
    langs = [w.items[0].attrib('lang') for w in words if w.items]
    return ARAMAIC if langs.count('arc') > langs.count('heb') else HEBREW


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(sentence_language(words)):
        return common.analyze_words([w.surface for w in words], words, word_details, [])


def analyze_text(text):
    _names_seen.clear()
    for surfaces in sentences(text):
        analysis = analyze_sentence(surfaces)
        analysis.tokens = surfaces  # 切れ目に分ける前の語 (見出しの行に使う)
        yield analysis
