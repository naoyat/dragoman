#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文の書き下し: UD-Kanbun の係り受けから読む順序を決め、送り仮名・助詞・助動詞を付ける
#
#   読む順序: 語ごとに、係り先より前の語 (主語・副詞・連体修飾) はそのまま前に、後ろの目的語・補語・前置詞句
#   (obj・iobj・obl・ccomp・xcomp・expl) は係り先の前に移し、否定・助動詞・前置詞などの助字 (不・可・欲・所・於 …)
#   は係り先の後ろに回す (日本語の語順。返り点のレ点・一二点に当たる)。並列 (conj)・続く節 (parataxis)・文末の
#   助字はそのまま後ろ
#     不入虎穴 → 虎穴 入 不 → 虎穴に入らず
#   送り仮名: 後ろの語が前の用言に求める活用形 (ず → 未然形、べし → 終止形、所・者・を → 連体形、而 → 連用形 + て、
#   則 → 已然形 + ば) を、右から左へ順に決める。用言の訓と活用は readings.py
#   置き字 (而・於・矣・焉・兮) は読まない。於は場所・相手 (に)、比較・起点 (より) の助詞にする
#   再読文字 (未・將・當・應・宜・須・猶・盍) は副詞として前で読み、助動詞として後ろで読む (未だ〜ず)
#   助動詞・助詞に当たる字 (不・可・使・也・乎・之 (の)・與 (と)・自 (より) …) はひらがなで書く
#
from dataclasses import dataclass
from typing import Optional

from . import readings

NEG = ('ざら', 'ず', 'ず', 'ざる', 'ざれ', 'ざれ')
BESHI = ('べから', 'べく', 'べし', 'べき', 'べけれ', 'べし')
GOTOSHI = ('ごとく', 'ごとく', 'ごとし', 'ごとき', 'ごとけれ', 'ごとし')
SHIMU = ('しめ', 'しめ', 'しむ', 'しむる', 'しむれ', 'しめよ')
NARI = ('なら', 'なり', 'なり', 'なる', 'なれ', 'なれ')
NTOSU = ('んとせ', 'んとし', 'んとす', 'んとする', 'んとすれ', 'んとせよ')


@dataclass
class Need:
    """後ろの語が前の語に求める形: 用言の活用形 + 付ける語、体言に付ける語"""
    form: str = '終止'
    suffix: str = ''
    noun: str = ''


END = Need('終止')


@dataclass
class Elem:
    kind: str                      # pred (用言) / aux (助動詞) / noun / text / particle / drop (置き字) / punct /
                                   # boundary (節の境目: 前の用言の形。助動詞・置き字の求めは上書きしない)
    token: object = None
    text: str = ''
    pred: object = None            # readings.Predicate
    forms: tuple = ()              # 助動詞の活用形 (未然・連用・終止・連体・已然・命令)
    need: Optional[Need] = None    # 前の語に求める形
    used: Optional[Need] = None    # 書き下しで使った形 (後ろの語が求めた形。現代語訳 modern.py が使う)
    out: str = ''                  # 書き下しの文字列


def _neg(t):
    return t.form in ('不', '弗') or (t.upos == 'ADV' and t.x[1:3] == ['副詞', '否定'] and t.x[3:4] == ['無界'])


# 前に係る助字で、係り先の後ろで読む語: 字 → (前で読む副詞 (再読文字) / None, 後ろの活用形, 前に求める形)
POST = {
    '不': (None, NEG, Need('未然', '', 'なら')), '弗': (None, NEG, Need('未然', '', 'なら')),
    '未': ('未だ', NEG, Need('未然')),
    '勿': (None, ('勿かれ',) * 6, Need('連体', 'こと', 'こと')), '毋': (None, ('毋かれ',) * 6, Need('連体', 'こと', 'こと')),
    '非': (None, ('非ざら', '非ず', '非ず', '非ざる', '非ざれ', '非ざれ'), Need('連体', 'に', 'に')),
    '可': (None, BESHI, Need('終止')),
    '欲': (None, ('欲せ', '欲し', '欲す', '欲する', '欲すれ', '欲せよ'), Need('未然', 'んと')),
    '得': (None, ('得', '得', '得', '得る', '得れ', '得よ'), Need('連体', 'を', 'を')),
    '足': (None, ('足ら', '足り', '足る', '足る', '足れ', '足れ'), Need('連体', 'に', 'に')),
    '將': ('將に', NTOSU, Need('未然')), '且': ('且に', NTOSU, Need('未然')),
    '當': ('當に', BESHI, Need('終止')), '應': ('應に', BESHI, Need('終止')), '宜': ('宜しく', BESHI, Need('終止')),
    '須': ('須らく', BESHI, Need('終止')), '猶': ('猶ほ', GOTOSHI, Need('連体', 'が', 'の')),
    '由': ('由ほ', GOTOSHI, Need('連体', 'が', 'の')), '盍': ('盍ぞ', ('ざる',) * 6, Need('未然')),
    '所': (None, ('所',) * 6, Need('連体')), '莫': (None, ('莫から', '莫く', '莫し', '莫き', '莫けれ', '莫かれ'), Need('連体')), '雖': (None, ('雖も',) * 6, Need('終止', 'と', 'と')),
    '見': (None, None, Need('未然')), '被': (None, None, Need('未然')),
}
# 禁止の 無・莫 (副詞、否定、禁止)
PROHIBIT = {'無': '無かれ'}
# 前置詞 (case): 字 → 名詞に付ける助詞 (於 は係り先で決める)
CASES = {'自': 'より', '從': 'より', '由': 'より', '與': 'と', '以': 'を以て', '爲': 'の爲に', '為': 'の為に',
         '因': 'に因りて', '向': 'に向かひて', '至': 'に至るまで', '及': 'と', '如': 'の如く', '在': 'に在りて',
         '乎': 'に', '於': 'に', '于': 'に', '諸': 'に'}
# 於 が より になる係り先 (起点・比較)
FROM_VERBS = {'出', '去', '離', '發', '生', '受', '學', '聞', '免', '逃', '辭', '歸'}
# 文末の助字: 字 → (形, 前に求める形)
FINALS = {'也': (NARI, Need('連体')), '乎': (('か',) * 6, Need('連体')), '哉': (('かな',) * 6, Need('連体')),
          '與': (('か',) * 6, Need('連体')), '歟': (('か',) * 6, Need('連体')), '邪': (('か',) * 6, Need('連体')),
          '耶': (('か',) * 6, Need('連体')), '耳': (('のみ',) * 6, Need('連体')), '爾': (('のみ',) * 6, Need('連体')),
          '已': (('のみ',) * 6, Need('連体')), '而已': (('のみ',) * 6, Need('連体'))}
SILENT = {'矣', '焉', '兮', '而', '於', '于'}
MOVED = ('obj', 'iobj', 'obl', 'ccomp', 'xcomp', 'expl')
# 目的語に に を付ける動詞 (虎穴に入る・山に登る・人に遇ふ)
NI_OBJECT = {'入', '至', '登', '及', '歸', '赴', '適', '似', '勝', '從', '隨', '遇', '逢', '會', '近', '臨', '就', '居', '處'}
# 是謂X「是を X と謂ふ」の主語
THIS = {'是', '此', '斯', '之'}
CAUSATIVES = {'使', '令', '敎', '教', '遣'}


def _subtree(t):
    out = [t]
    for c in t.children:
        out += _subtree(c)
    return out


def _single_compound(child, head):
    """隣り合った1字ずつの修飾 (虎穴・遠方・百獸) は熟語として送り仮名・助詞を付けない"""
    return child.rel in ('nmod', 'amod', 'nummod', 'compound', 'flat') and not child.children and \
        abs(child.i - head.i) == 1 and len(child.form) == 1 and child.form not in readings.DETERMINERS


def _bare_advcl(t):
    """接続の助字の無い前の節で 連用形 + て でつなぐもの (parse.repair が advcl:te にする 國破 山河在)"""
    return t.deprel == 'advcl:te'


class Reader:
    def __init__(self, phrase):
        self.phrase = phrase
        self.by_i = {t.i: t for t in phrase}

    def head_of(self, t):
        return self.by_i.get(t.head) if t.head != t.i else None

    # --------------------------------------------------------------
    # 読む順序

    def order(self):
        roots = [t for t in self.phrase if t.head == t.i or t.head not in self.by_i]
        out = []
        for r in roots:
            out += self.linear(r)
        return out

    def linear(self, t):
        left = [c for c in t.children if c.i < t.i]
        right = [c for c in t.children if c.i > t.i]
        pre, post, moved, after = [], [], [], []
        for c in left:
            if self._is_post(c):
                post.append(c)
            else:
                pre.append(c)
        for c in right:
            if c.rel in MOVED and c.upos != 'PUNCT' and not self._stays(c, t):
                moved.append(c)
            else:
                after.append(c)
        out = []
        for c in pre:
            out += self._child(c, t, pre=True)
        for c in moved:
            out += self._child(c, t)
        out += self._head(t)
        for c in reversed(post):
            out += self._post(c, t)
        for c in after:
            if c.rel == 'conj' and t.upos in ('NOUN', 'PRON', 'PROPN') and c.upos in ('NOUN', 'PRON', 'PROPN'):
                out.append(Elem('particle', None, text='と'))   # 盾と矛と
                out += [e for e in self._child(c, t) if not (e.token is not None and e.token.rel == 'cc')]
                out.append(Elem('particle', None, text='と'))
                continue
            if c.rel in ('conj', 'parataxis') and c.upos != 'PUNCT':
                out.append(Elem('boundary', need=Need('連用') if c.rel == 'conj' else END))
            out += self._child(c, t)
        return out

    def _is_post(self, c):
        if c.rel == 'case' or (c.rel == 'mark' and c.form in POST):
            return True
        if c.rel == 'cop':
            return True
        if c.rel in ('advmod', 'aux') and (c.form in POST or _neg(c) or
                                           (c.form in PROHIBIT and c.x[2:3] == ['否定'])):
            return c.form != '能'
        return False

    def _stays(self, c, head):
        """後ろの補語を前に移さない係り先 (曰 の後ろの引用)"""
        return head.form in ('曰', '云') and c.rel in ('ccomp', 'parataxis', 'obj')

    # --------------------------------------------------------------
    # 語ごとの要素

    def _child(self, c, head, pre=False):
        if c.upos == 'PUNCT':
            return [Elem('punct', c, text=c.form)]
        elems = self.linear(c)
        if pre and _single_compound(c, head):
            return [Elem('text', c, text=''.join(e.token.form for e in elems if e.token))] if \
                all(e.kind in ('noun', 'pred', 'text') for e in elems) else elems
        if pre and _bare_advcl(c):   # 而 の無い前の節 (國破山河在) は 連用形 + て でつなぐ
            elems.append(Elem('drop', None, need=Need('連用', 'て')))
            return elems
        particle = self._particle(c, head)
        if particle is not None:
            if particle and elems and elems[-1].kind == 'noun' and elems[-1].token is c and c.upos == 'PRON':
                elems[-1].text = c.form   # 助詞の前の代名詞は送り仮名を付けない (是を・其を)
            elems.append(Elem('particle', c, text=particle, need=Need('連用' if particle == 'と' else '連体')))
        return elems

    def _particle(self, c, head):
        """係り先との関係から付ける助詞 (None は付けない。前置詞・之 などが付けるもの)"""
        rel = c.rel
        if any(k.rel == 'case' for k in c.children):
            return None
        if rel in ('nsubj', 'csubj'):
            if head.form in ('曰', '云', '言') or _bare_advcl(head):
                return None   # 國破れて
            if head.form == '謂' and c.form in THIS:
                return 'を'
            if head.form in ('有', '無') and any(k.rel == 'obj' for k in head.children):
                return 'に'   # 楚人に盾と矛とを鬻ぐ者有り
            if any(k.form in ('所', '者') and k.rel == 'mark' for k in head.children) or head.rel in ('advcl', 'acl', 'ccomp', 'xcomp',
                                                                                   'csubj', 'obj'):
                return 'の'
            return 'は'
        if rel == 'obj':
            if head.form in ('有', '無', '莫', '在', '多', '少'):
                return None
            if head.form in CAUSATIVES and self._causative(head):
                return 'をして'
            if head.form in ('如', '若'):
                return None    # 係り先が求める (に如かず・の如し)
            if head.form in ('非',):
                return None
            if head.form in ('以',):
                return None
            if head.form in ('欲',) and c.upos == 'VERB':
                return None
            if head.form == '謂' and any(k.rel == 'nsubj' and k.form in THIS for k in head.children):
                return 'と'
            if head.form in NI_OBJECT:
                return 'に'
            return 'を'
        if rel == 'iobj':
            return 'に'
        if rel in ('nmod', 'det') and c.upos == 'PRON' and c.form not in readings.DETERMINERS:
            return 'が' if c.form in ('吾', '我', '予', '余', '汝', '爾') else 'の'   # 吾が身・子の矛
        if rel == 'nmod' and not _single_compound(c, head) and not any(k.form == '之' for k in c.children):
            return 'の'
        if rel == 'obl':
            if c.form in readings.ADVERBS and not c.children:
                return None
            return 'に'
        if rel in ('ccomp', 'xcomp'):
            if head.form in CAUSATIVES or head.form in ('欲', '如', '若', '非', '可', '能', '得', '足', '曰', '云'):
                return None
            return 'を'
        return None

    def _causative(self, head):
        return any(k.rel in ('xcomp', 'ccomp') for k in head.children)

    def _negated(self, t):
        return any(_neg(k) for k in t.children)

    def _head(self, t):
        f = t.form
        if t.upos == 'PUNCT':
            return [Elem('punct', t, text=f)]
        if f in ('曰',):
            return [Elem('text', t, text='曰はく')]
        if f in SILENT and t.rel in ('cc', 'discourse', 'case', 'mark', 'fixed') or \
                f in SILENT and t.rel == 'advmod' and f not in readings.ADVERBS:
            return [Elem('drop', t, need=Need('連用', 'て') if f == '而' else None)]
        if t.rel == 'discourse' or (t.upos == 'PART' and f in FINALS):
            if f in FINALS:
                forms, need = FINALS[f]
                return [Elem('aux', t, forms=forms, need=need)]
            return [Elem('drop', t)]
        if f == '之' and t.rel == 'case':
            return [Elem('particle', t, text='の', need=Need('連体'))]
        if f == '者':
            return [Elem('noun', t, text='者', need=Need('連体'))]
        if f in CAUSATIVES and t.upos == 'VERB' and self._causative(t):
            return [Elem('aux', t, forms=SHIMU, need=Need('未然'))]
        if t.rel == 'aux' and f in ('能', '敢', '肯'):
            return [Elem('text', t, text=readings.ADVERBS.get(f, {'肯': '肯へて'}.get(f, f)))]
        if f in ('如', '若') and any(k.form in ('何', '奈') for k in t.children):
            return [Elem('text', t, text=f)]   # 何如・如何 (いかん)
        if f in ('如', '若') and t.upos == 'VERB':
            if self._negated(t):
                return [Elem('pred', t, pred=readings.predicate('如く'), need=Need('連体', 'に', 'に'))]
            return [Elem('aux', t, forms=GOTOSHI, need=Need('連体', 'が', 'の'))]
        if f == '非' and t.upos in ('VERB', 'AUX'):
            return [Elem('aux', t, forms=POST['非'][1], need=Need('連体', 'に', 'に'))]
        if f == '以' and t.upos == 'VERB':
            return [Elem('text', t, text='以て', need=Need('連体', 'を', 'を'))]
        if f == '欲' and t.upos in ('VERB', 'AUX') and any(k.rel in ('xcomp', 'ccomp') or k.upos == 'VERB'
                                                          for k in t.children if k.i > t.i):
            return [Elem('aux', t, forms=POST['欲'][1], need=Need('未然', 'んと'))]
        if t.rel == 'fixed':
            return [Elem('text', t, text=f)]
        if t.upos in ('ADV',) or (t.rel == 'advmod' and t.upos != 'VERB') or \
                (t.rel == 'obl' and f in readings.ADVERBS and t.upos == 'NOUN' and not t.children):
            return [Elem('text', t, text=readings.ADVERBS.get(f, f), need=Need('已然', 'ば') if f == '則' else None)]
        if t.rel == 'det' and f in readings.DETERMINERS:
            return [Elem('text', t, text=readings.DETERMINERS[f])]
        if t.upos == 'PRON':
            return [Elem('noun', t, text=readings.PRONOUNS.get(f, f) if t.rel in ('nsubj',) else f)]
        if t.upos == 'DET' or t.rel == 'det':
            return [Elem('text', t, text=readings.DETERMINERS.get(f, f))]
        if t.upos == 'VERB' and t.rel in ('obj', 'nsubj') and not t.children and t.x[2:3] != ['描写']:
            return [Elem('noun', t, text=f)]   # 名詞として読む用言 (死を知る・生を楽しむ)
        if t.upos in ('VERB', 'ADJ') or (t.upos == 'AUX' and t.rel not in ('aux', 'cop')):
            p = readings.verb(f, t.simplified, t.gloss)
            if f in readings.WITH_OBJECT and any(k.rel == 'obj' for k in t.children):
                p = readings.predicate(readings.WITH_OBJECT[f])
            fixed = ''.join(k.form for k in t.children if k.rel == 'fixed' and k.i > t.i)
            return [Elem('pred', t, pred=p, text=fixed)]
        if t.upos == 'NOUN' and t.rel in ('root', 'conj', 'parataxis') and t.x[2:3] == ['描写'] and f in readings.VERBS:
            return [Elem('pred', t, pred=readings.verb(f, t.simplified, t.gloss))]
        return [Elem('noun', t, text=f)]

    def _post(self, c, head):
        """係り先の後ろで読む助字 (と、前で読む再読文字の副詞は linear が前に入れる)"""
        f = c.form
        if c.rel == 'case':
            text = CASES.get(f, '')
            if f in ('於', '于', '乎'):
                gov = self.head_of(head)
                if gov is not None and (gov.form in FROM_VERBS or gov.x[2:3] == ['描写'] and
                                        readings.verb(gov.form, gov.simplified, gov.gloss).adjective):
                    text = 'より'
            if f == '之':
                text = 'の'
            return [Elem('particle', c, text=text, need=Need('連体'))]
        if c.rel == 'cop':
            if f in ('爲', '為'):
                return [Elem('pred', c, pred=readings.predicate(f + 'る'), need=Need('終止', 'と', 'と'))]
            return [Elem('aux', c, forms=NARI, need=Need('連体'))]
        if f in PROHIBIT and c.x[2:3] == ['否定']:
            return [Elem('aux', c, forms=(PROHIBIT[f],) * 6, need=Need('連体', 'こと', 'こと'))]
        if _neg(c) and f not in POST:
            return [Elem('aux', c, forms=NEG, need=Need('未然', '', 'なら'))]
        pre_reading, forms, need = POST[f]
        out = [Elem('aux', c, forms=forms if f not in ('見', '被') else None, need=need)]
        for k in reversed([k for k in c.children if k.i < c.i and self._is_post(k)]):
            out += self._post(k, c)   # 不可 → べからず
        return out


def _passive(prev):
    """受身の る / らる: 四段・ナ変・ラ変の後は る"""
    if prev is not None and prev.pred is not None and prev.pred.kind in ('四段', 'ナ変', 'ラ変'):
        return ('れ', 'れ', 'る', 'るる', 'るれ', 'れよ')
    return ('られ', 'られ', 'らる', 'らるる', 'らるれ', 'られよ')


TOPIC_WA = False   # 書き下しの主語に「は」を付ける (--wa)。既定は教科書に合わせて付けない (者 の後ろは付ける)


def _topic_dropped(elems, i, kept=False):
    """主語の「は」を書き下しで省くか (現代語訳には残す)。kept: 「は」を残す決まった言い回し (readings.WA_KEPT) の句"""
    e = elems[i]
    if TOPIC_WA or kept or e.kind != 'particle' or e.text != 'は':
        return False
    before = elems[i - 1] if i > 0 else None
    return not (before is not None and before.token is not None and before.token.form == '者')


def render(elems, final=END, text=''):
    """要素の列 → 書き下しの文字列 (右から左へ、後ろの語が求める形を前の用言に付ける)。text: 句の白文"""
    kept = any(k in text for k in readings.WA_KEPT)
    out = []
    need = final
    strong = False   # 助動詞・置き字・則 の求め (節の境目で上書きしない)
    for i in range(len(elems) - 1, -1, -1):
        e = elems[i]
        prev = next((p for p in reversed(elems[:i]) if p.kind != 'boundary' and (p.kind != 'drop' or p.need)), None)
        if e.kind == 'punct':
            out.append(e.text)
            need = final if i == len(elems) - 1 else END
            continue
        if e.kind == 'boundary':
            if not strong:
                need = e.need
            continue
        if e.kind == 'drop':
            if e.need is not None:
                need = e.need
                if e.token is not None and e.token.form == '而' and prev is not None and prev.kind == 'aux' and \
                        prev.forms == NEG:
                    need = Need('連用', 'して')   # ずして
                strong = True
            continue
        strong = e.kind in ('aux', 'text') and e.need is not None
        current = need or END
        e.used = current
        if e.kind == 'aux':
            forms = e.forms if e.forms is not None else _passive(prev)
            if e.token is not None and e.token.form in ('乎', '哉', '與', '邪', '耶', '歟') and prev is not None and \
                    prev.kind == 'aux' and prev.forms == NEG:
                out.append('や' + current.suffix)
                need = Need('終止')
                continue
            name = current.form if current.form in readings.FORMS else '終止'
            out.append(forms[readings.FORMS.index(name)] + current.suffix)
            need = e.need
            if need is not None and need.form == '終止' and prev is not None and prev.pred is not None and \
                    (prev.pred.kind == 'ラ変' or prev.pred.adjective):
                need = Need('連体', need.suffix, need.noun)   # べし の前のラ変・形容詞は連体形 (有るべし・楽しかるべし)
            continue
        if e.kind == 'pred':
            aux = bool(current.suffix in ('', 'ん', 'んと') and _aux_follows(elems, i))
            name = current.form if current.form in readings.FORMS else '終止'
            text = e.pred.form(name, aux=aux) + e.text + current.suffix
            out.append(text)
            need = e.need
            continue
        if e.kind == 'particle':
            out.append('' if _topic_dropped(elems, i, kept) else e.text)
            need = e.need or Need('連体')
            continue
        # noun / text
        out.append(e.text + (current.noun if need is not None else ''))
        need = e.need or (Need('連体') if e.kind == 'noun' or e.token is not None and e.token.upos == 'NOUN' else None)   # 名詞の前の用言は連体形 (然る後)
    for e, text in zip(_rendered(elems), reversed(out)):
        e.out = text
    return ''.join(reversed(out))


def _rendered(elems):
    """render が文字列を出した要素 (右から左の順に出したものを左から並べる)"""
    return [e for e in elems if e.kind not in ('boundary', 'drop')]


def _aux_follows(elems, i):
    """用言の後ろに助動詞が続く (形容詞はカリ活用にする)"""
    for e in elems[i + 1:]:
        if e.kind in ('boundary', 'drop'):
            continue
        return e.kind == 'aux' and e.token is not None and e.token.form not in FINALS and e.forms != ('所',) * 6
    return False


def _root(phrase):
    return next((t for t in phrase if t.rel == 'root'), None)


def _final_need(phrase, following):
    """句の終わりの用言の形: 疑問・反語の副詞があれば 未然形 + ん (焉くんぞ死を知らん)、不A不B の前の句は ずんば"""
    root = _root(phrase)
    if root is None:
        return END
    if any(k.rel == 'advmod' and k.form in readings.QUESTION_ADVERBS for k in root.children) and \
            not any(k.form in FINALS for k in root.children):
        return Need('未然', 'ん')
    nxt = _root(following) if following else None
    if nxt is not None and any(_neg(k) for k in root.children) and any(_neg(k) for k in nxt.children) and \
            not any(k.rel in ('cc', 'mark', 'nsubj') for k in nxt.children + root.children):
        return Need('連用', 'んば')   # 虎穴に入らずんば、虎子を得ず
    return END


def read(phrases):
    """[[Token]] (句ごと) → [要素の列] (句ごと。render で書き下しの形を決めたもの)"""
    out = []
    for n, phrase in enumerate(phrases):
        r = Reader(phrase)
        elems = _with_pre(r, r.order())
        render(elems, _final_need(phrase, phrases[n + 1] if n + 1 < len(phrases) else None),
               ''.join(t.form for t in phrase if t.upos != 'PUNCT'))
        out.append(elems)
    return out


def kakikudashi(phrases):
    """[[Token]] (句ごと) → 書き下し文"""
    return ''.join(''.join(e.out for e in _rendered(elems)) for elems in read(phrases))


def _with_pre(reader, elems):
    """再読文字の前の読み (未だ・將に) と 可以 の 以て を、係り先の部分 (部分木の読む順で最初の語) の前に入れる"""
    inserts = {}
    for t in reader.phrase:
        head = reader.head_of(t)
        if head is None:
            continue
        reading = None
        if t.form in POST and POST[t.form][0] and t.rel in ('advmod', 'aux'):
            reading = POST[t.form][0]
        fixed = [k for k in t.children if k.rel == 'fixed' and k.form == '以']
        place = None
        if reading:
            place = _first_in_order(elems, head, t)
            inserts.setdefault(place, []).append((reading, t))
        if t.form == '可' and fixed:   # 以て は 以 の字の要素に (振り仮名・送り仮名が 以 に付くように)
            inserts.setdefault(_first_in_order(elems, head, t) if place is None else place, []).append(('以て', fixed[0]))
    if not inserts:
        return elems
    out = []
    for idx, e in enumerate(elems):
        for reading, t in inserts.get(idx, ()):
            out.append(Elem('text', t, text=reading))
        out.append(e)
    return out


def _first_in_order(elems, head, skip):
    """係り先の部分木の語のうち、読む順で最初の要素の位置 (再読文字自身と、主語より後ろ)"""
    members = set(id(s) for s in _subtree(head)) - set(id(s) for s in _subtree(skip))
    for k in head.children:
        if k.rel in ('nsubj', 'csubj') or (k.i < skip.i and k.rel not in ('fixed',)):
            members -= set(id(s) for s in _subtree(k))
    for idx, e in enumerate(elems):
        if e.token is not None and id(e.token) in members:
            return idx
    return 0
