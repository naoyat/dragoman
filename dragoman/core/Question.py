#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 間接疑問: 疑問詞で始まり、動詞が接続法の節を、問う・知る・教える・言うなどの動詞の目的語として持つ
#
#   Quid fierī vellet docuit.         {何が なる ことを 望んでいた}かを 教えた
#   Rogāvit cūr puer flēret.          {なぜ 少年が 泣いていた}かを 尋ねた
#
# 解析では、述語ごとの節にいったん分けたあとで、隣の節の動詞がこの種類なら、その節の格の枠 ('Q') に入れる
# (不定詞句 InfinitiveClause と同じく入れ子にする)
#
from .LatinObject import LatinObject

# 間接疑問を目的語に取る動詞 (直説法現在1人称単数)
QUESTION_VERBS = {'rogō', 'interrogō', 'quaerō', 'requīrō', 'exquīrō', 'scīscitor', 'percontor', 'cōnsulō',
                  'sciō', 'nesciō', 'ignōrō', 'cognōscō', 'intellegō', 'sentiō', 'videō', 'audiō', 'animadvertō',
                  'doceō', 'ēdoceō', 'dīcō', 'nārrō', 'nūntiō', 'ostendō', 'dēmōnstrō', 'mōnstrō', 'expōnō',
                  'explicō', 'referō', 'prōnūntiō', 'indicō', 'aperiō', 'mīror', 'dubitō', 'cōgitō', 'meminī',
                  'recordor', 'considerō', 'cōnsīderō', 'dēlīberō', 'exspectō', 'experior', 'temptō', 'probō',
                  'cūrō', 'videor',
                  # ギリシア語
                  'ἐρωτάω', 'ἔρομαι', 'πυνθάνομαι', 'οἶδα', 'γιγνώσκω', 'ἐπίσταμαι', 'ἀγνοέω', 'μανθάνω', 'ὁράω',
                  'ἀκούω', 'λέγω', 'φράζω', 'δηλόω', 'διδάσκω', 'θαυμάζω', 'σκοπέω', 'ἀπορέω', 'βουλεύω', 'εἶπον',
                  'αἰσθάνομαι', 'ἐννοέω', 'σκέπτομαι', 'ζητέω', 'ἐξετάζω',
                  # 英語 (原形)
                  'ask', 'know', 'wonder', 'tell', 'see', 'understand', 'remember', 'forget', 'decide', 'explain',
                  'show', 'learn', 'find', 'guess', 'imagine', 'say', 'care', 'doubt', 'check', 'discover', 'notice',
                  'hear', 'think', 'realize', 'realise', 'consider', 'figure out', 'find out'}
# 疑問の副詞・形容詞 (疑問代名詞 quis / quid は辞書の desc で見分ける)
INTERROGATIVES = {'cūr', 'quārē', 'quōmodo', 'quemadmodum', 'unde', 'quō', 'quā', 'quotiēns', 'quandō',
                  'utrum', 'num', 'nōnne', 'quantus', 'quālis', 'quot', 'uter', 'ubi', 'quam',
                  # ギリシア語 (直接の形と間接の形 ὅπως・ὅπου …、εἰ「〜かどうか」)
                  'πῶς', 'ποῦ', 'πότε', 'πόθεν', 'ποῖ', 'πόσος', 'ποῖος', 'πότερον', 'ὅπως', 'ὅπου', 'ὁπότε', 'ὁπόθεν',
                  'ὅποι', 'ὁπόσος', 'ὁποῖος', 'ὁπότερον', 'εἰ',
                  # 英語 (疑問代名詞 who・what は desc で)
                  'where', 'when', 'why', 'how', 'whether'}


def is_interrogative(word):
    """疑問代名詞 (quis, quid …) か、疑問の副詞 (cūr, quōmodo …) の語"""
    items = getattr(word, 'items', None) or []
    if any(item.attrib('not_interrogative') for item in items):
        return False   # 解析器が接続詞と決めたもの (英語の副詞節の when)
    if any(item.pos == 'pronoun' and item.attrib('desc') == '疑問代名詞' for item in items):
        return True
    if any(item.attrib('base') == 'ὅστις' for item in items):
        return True   # ギリシア語の不定関係代名詞は間接疑問の疑問詞にも (ἤρετο ὅστις εἴη)。先行詞があれば関係節
    if not items:
        return False
    surface = getattr(word, 'surface', '').lower()
    if surface in INTERROGATIVES:
        return True
    from . import language
    own = language.current().interrogatives if language.current() is not None else ()
    base = (items[0].attrib('base') or '').lower()
    return bool(own) and (surface in own or base in own or base.split(' ')[0] in own)


def interrogative_gloss(word):
    """言語の設定の疑問詞の、間接疑問での訳 (無ければ None。'' は「〜かどうか」)"""
    from . import language
    own = language.current().interrogatives if language.current() is not None else {}
    items = getattr(word, 'items', None) or []
    surface = getattr(word, 'surface', '').lower()
    base = (items[0].attrib('base') or '').lower() if items else ''
    key = next((k for k in (surface, base, base.split(' ')[0]) if k in own), None)
    return None if key is None else own[key]


def is_question_verb(pres1sg):
    """間接疑問を取る動詞 (知る・問う …) の見出しか (共通の表と言語の設定の表)"""
    from . import language
    return pres1sg in QUESTION_VERBS or language.current() is not None and pres1sg in language.current().question_verbs


class QuestionClause(LatinObject):
    def __init__(self, predicate, governor, word):
        self.predicate = predicate      # 間接疑問の節の述語 (接続法の動詞の Predicate)
        self.governor = governor        # 支配する動詞 (Predicate)
        self.word = word                # 疑問詞 (Word)
        self.surface = predicate.surface
        self.surface_len = len(self.surface)
        self.case_slot = predicate.case_slot

    def translate(self):
        inner, _ = self.predicate.translate()
        whether = getattr(self.word, 'surface', '').lower() in ('whether', 'if', 'εἰ') or \
            getattr(self.word, 'whether', False)
        inner = ' '.join(part for part in inner.split(' / ') if part.strip())
        return ('{' + inner + ('}かどうかを' if whether else '}かを'), False)
