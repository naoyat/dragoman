#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文の語の切り分け・品詞・係り受け: UD-Kanbun (安岡孝一、MIT。pip install udkanbun)。
# 句点・読点で区切った句ごとに Token の列を返す
#
#   學而時習之 → [Token(i=1, form='學', lemma='學', simplified='学', upos='VERB', xpos='v,動詞,行為,動作', head=1,
#                        deprel='root', gloss='study'), Token(i=2, form='而', … deprel='cc'), …]
#
import functools
from dataclasses import dataclass, field


@dataclass
class Token:
    i: int
    form: str
    lemma: str
    simplified: str     # 見出しの簡体字 (學 → 学。新字体を探す手掛かり)
    upos: str
    xpos: str           # 品詞の細分類 (v,動詞,行為,動作 / v,副詞,否定,無界 / p,助詞,句末 …)
    feats: str
    head: int           # 句の中の係り先の番号 (句の根は自分自身)
    deprel: str
    gloss: str          # 英語の語義 (UD-Kanbun の辞書の Gloss)
    children: list = field(default_factory=list, repr=False)

    @property
    def x(self):
        """品詞の細分類の欄 (['v', '動詞', '行為', '動作'])"""
        return self.xpos.split(',')

    @property
    def rel(self):
        """依存関係の主な部分 (obl:tmod → obl)"""
        return self.deprel.split(':')[0]


def available():
    try:
        import udkanbun   # noqa: F401
        return True
    except ImportError:
        return False


@functools.lru_cache(maxsize=1)
def _pipeline():
    import udkanbun
    return udkanbun.load()


@functools.lru_cache(maxsize=256)
def _entry(text):
    """UD-Kanbun の解析 (係り受けを repair で直したもの。句の Token と返り点はこれから)"""
    entry = _pipeline()(text)
    repair(entry)
    return entry


NEGATIVE = '副詞,否定'
NOMINAL_DEPS = ('nummod', 'obl:tmod', 'nmod', 'amod', 'obl')
TIME_SUBJECTS = {'歲月', '歳月', '光陰', '日月', '時日', '少年'}   # 主語になる時の名詞 (歲月は人を待たず・少年老い易し)
EASY = {'易', '難'}


def _sentences(entry):
    tokens = list(entry[1:])
    out = []
    for t in tokens:
        if t.id == 1:
            out.append([])
        out[-1].append(t)
    return out


def repair(entry):
    """UD-Kanbun の係り受けのよくある誤りを直す (返り点もこれに合わせて付く)。
    (1) 名詞の主語を述語と読んだもの: 「X 不 V …」で X が根、V が X の補文 (ccomp) で、X に前から名詞の修飾
        (百聞・春眠) だけが係るとき、V を根に、X をその主語 (名詞) に。V の目的語が数詞だけを伴う動詞なら名詞に
        (一見): 百聞不如一見 → 百聞は一見に如かず、春眠不覺曉 → 春眠 曉を覺えず
    (2) 二つの節の主語を前の動詞の目的語と読んだもの: 「N1 V1 N2 V2」で V2 が V1 に並ぶ節か V1 が V2 の主語の節、
        N2 が V1 の目的語で、V2 に主語も目的語も無いとき、N2 を V2 の主語に、V1 を V2 に係る節に:
        國破山河在 → 國破れて山河在り
    (3) 句読点も與も無く並ぶ1字の名詞 (山河) は熟語に
    (4) 助動詞 (可・能) の係る 已 (句末の のみ と読んだもの) は動詞に: 學不可以已 → 學は以て已むべからず
    (5) 文頭の時の名詞 (歲月・光陰) が述語に主語の無い文の時の補語 (obl:tmod) なら主語に: 歲月不待人 → 歲月は人を待たず
    (6) 文頭の子の無い動詞が副詞の前で述語の連用修飾 (advmod) なら主語に (名詞に読む): 過猶不及 → 過ぎたるは猶ほ…
    (7) 如 の補文の形容詞の動詞 (描写) に、すぐ前の名詞の主語だけが係るとき、名詞の句 (目的語) に:
        地利不如人和 → 人の和に如かず
    (8) 易・難 のすぐ後ろの用言を 易・難 の目的語と読んだものは、易・難 をその用言に係る連用修飾に (V易し・V難し):
        少年易老 → 少年老い易し。その用言の前の、子の補文だけを持つ1字の動詞は主語に: 學難成 → 學成り難し
    (9) すぐ後ろの用言に係る1字の形容詞の動詞 (advmod) で、二つで熟語のサ変 (readings.SAHEN) になるものは熟語に:
        大器晩成 → 大器は晩成す"""
    for sent in _sentences(entry):
        kids = {t.id: [] for t in sent}
        for t in sent:
            if t.head is not t:
                kids[t.head.id].append(t)
        for v1 in sent:
            if v1.deprel != 'root' or v1.upos != 'VERB':
                continue
            right = [k for k in kids[v1.id] if k.id > v1.id and k.deprel != 'punct']
            left = [k for k in kids[v1.id] if k.id < v1.id]
            # (1)
            if len(right) == 1 and right[0].deprel == 'ccomp' and left and \
                    all(k.deprel in NOMINAL_DEPS for k in left):
                v2 = right[0]
                if any(k.id < v2.id and NEGATIVE in k.xpos for k in kids[v2.id]):
                    v2.head, v2.deprel = 0, 'root'
                    for k in kids[v1.id]:
                        if k is not v2 and k.deprel == 'punct':
                            k.head = v2.id
                    v1.head, v1.deprel, v1.upos = v2.id, 'nsubj', 'NOUN'
                    for k in left:
                        if k.deprel == 'obl:tmod':
                            k.deprel = 'nmod'
                    for o in kids[v2.id]:
                        if o.deprel in ('obj', 'ccomp') and o.upos == 'VERB' and kids[o.id] and \
                                all(k.upos == 'NUM' and k.id < o.id for k in kids[o.id]):
                            o.upos, o.deprel = 'NOUN', 'obj'
                            for k in kids[o.id]:
                                k.deprel = 'nummod'
                    break
            # (2) 根 V1 に主語 N1 と目的語 N2 があり、N2 のすぐ後ろの V2 が V1 に並ぶ節 (parataxis) か、V1 が V2 の
            #     主語の節 (csubj) で、V2 に主語も目的語も無いとき
            pairs = [(v1, k) for k in right if k.deprel == 'parataxis'] + \
                    [(k, v1) for k in left if k.deprel == 'csubj']
            for a, b in pairs:
                objs = [k for k in kids[a.id] if k.deprel == 'obj' and a.id < k.id < b.id]
                if len(objs) != 1 or not any(k.deprel == 'nsubj' and k.id < a.id for k in kids[a.id]) or \
                        any(k.deprel in ('nsubj', 'obj') for k in kids[b.id]):
                    continue
                o = objs[0]
                if max([o.id] + [k.id for k in kids[o.id]]) != b.id - 1:
                    continue
                if b.head is a:
                    b.head, b.deprel = 0, 'root'
                    for k in kids[a.id]:
                        if k.deprel == 'punct':
                            k.head = b.id
                o.head, o.deprel = b.id, 'nsubj'
                a.head, a.deprel = b.id, 'advcl:te'   # 連用形 + て でつなぐ (kundoku._bare_advcl)
                break
        # (3) 句読点の無い1字の名詞の並び (山河・父母) は熟語に: 並列 (conj) を compound に
        for t in sent:
            h = t.head
            if t.deprel == 'conj' and h is not t and h.id == t.id - 1 and t.upos == h.upos == 'NOUN' and \
                    len(t.form) == len(h.form) == 1 and not any(k.deprel == 'cc' for k in kids[t.id]):
                t.head, t.deprel, h.head, h.deprel = (h.head.id if h.head is not h else 0), h.deprel, t.id, 'compound'
        kids = {t.id: [] for t in sent}
        for t in sent:
            if t.head is not t:
                kids[t.head.id].append(t)
        # (4)
        for t in sent:
            if t.form == '已' and t.upos == 'PART' and any(k.deprel == 'aux' for k in kids[t.id]):
                t.upos, t.xpos = 'VERB', 'v,動詞,行為,動作'
        root = next((t for t in sent if t.deprel == 'root'), None)
        if root is not None and not any(k.deprel.startswith('nsubj') or k.deprel == 'csubj' for k in kids[root.id]):
            first = sent[0]
            # (5)
            if first.deprel == 'compound' and first.head.deprel == 'obl:tmod' and first.head.head is root and \
                    first.form + first.head.form in TIME_SUBJECTS:
                first.head.deprel = 'nsubj'
            # (6)
            elif first.upos == 'VERB' and first.deprel == 'advmod' and first.head is root and not kids[first.id] and \
                    len(sent) > 1 and sent[1].upos == 'ADV':
                first.deprel = 'nsubj'
        # (8)
        for x in sent:
            if x.form not in EASY or x.upos != 'VERB':
                continue
            v = next((k for k in kids[x.id] if k.id == x.id + 1 and k.deprel in ('obj', 'ccomp')), None)
            if v is not None:
                v.head, v.deprel = (0 if x.head is x else x.head.id), x.deprel
                if v.deprel == 'root':
                    for k in kids[x.id]:
                        if k is not v:
                            k.head = v.id
                x.head, x.deprel = v.id, 'advmod'
                if v.upos == 'NOUN':
                    v.upos, v.xpos = 'VERB', 'v,動詞,変化,生物'
            elif not (x.deprel == 'advmod' and x.head.id == x.id + 1):
                continue
            v = sent[x.id]   # 易・難 の係る用言
            subj = sent[x.id - 2] if x.id >= 2 else None
            if subj is not None and subj.upos == 'VERB' and len(subj.form) == 1 and v.head is subj and \
                    v.deprel == 'ccomp' and all(k is v or k.deprel == 'punct' for k in sent if k.head is subj and k is not subj):
                v.head, v.deprel = (0 if subj.head is subj else subj.head.id), subj.deprel
                for k in sent:
                    if k.head is subj and k is not subj and k is not v:
                        k.head = v.id
                subj.head, subj.deprel, subj.upos = v.id, 'nsubj', 'NOUN'
        kids = {t.id: [] for t in sent}
        for t in sent:
            if t.head is not t:
                kids[t.head.id].append(t)
        root = next((t for t in sent if t.deprel == 'root'), None)
        # (5) の続き: 修飾語の付いた名詞 (少年)
        if root is not None and not any(k.deprel.startswith('nsubj') for k in kids[root.id]):
            for t in sent:
                if t.deprel == 'obl:tmod' and t.head is root and \
                        ''.join(k.form for k in kids[t.id] if k.id < t.id) + t.form in TIME_SUBJECTS:
                    t.deprel = 'nsubj'
        # (9)
        from .readings import SAHEN
        for t in sent:
            if t.deprel == 'advmod' and t.upos == 'VERB' and t.head.id == t.id + 1 and t.form + t.head.form in SAHEN:
                t.deprel = 'compound'
        # (7)
        for t in sent:
            if t.deprel == 'ccomp' and t.upos == 'VERB' and t.head.form == '如' and '描写' in t.xpos and \
                    len(kids[t.id]) == 1 and kids[t.id][0].deprel == 'nsubj' and kids[t.id][0].id == t.id - 1 and \
                    kids[t.id][0].upos == 'NOUN':
                t.upos, t.deprel = 'NOUN', 'obj'
                kids[t.id][0].deprel = 'nmod'


def _misc(misc, key):
    for part in misc.split('|'):
        if part.startswith(key + '='):
            return part[len(key) + 1:]
    return ''


def phrases(text):
    """文 (白文。句読点があればそこで区切る) → [[Token]] (句ごと。句読点の Token も含む)"""
    entry = _entry(text)
    out, current = [], []
    for t in entry[1:]:
        if t.id == 1 and current:
            out.append(current)
            current = []
        lemma, _, simplified = t.lemma.partition('/')
        current.append(Token(i=t.id, form=t.form, lemma=lemma, simplified=simplified or lemma, upos=t.upos,
                             xpos=t.xpos, feats=t.feats, head=t.head.id if t.head is not t else t.id,
                             deprel=t.deprel, gloss=_misc(t.misc, 'Gloss')))
    if current:
        out.append(current)
    for phrase in out:
        by_i = {t.i: t for t in phrase}
        for t in phrase:
            if t.head != t.i and t.head in by_i:
                by_i[t.head].children.append(t)
    return out


def kaeriten(text):
    """UD-Kanbun の返り点付きの白文 (學而時習㆑之、不㆓亦說㆒乎。)"""
    return ''.join(_entry(text).kaeriten().split())
