#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠の要素ごとに、各言語がどの手段で表すかを並べる (言語の理解のため)
#
#   同じ枠の要素 (述語・主語・目的語・受け手・場所の句 …) を各言語の生成器で作り、その手段を添える:
#     「庭で」 in + 奪格 (la)、ἐν + 与格 (grc)、в + 前置格 (ru)、処格 (sa、前置詞なし)、in (en)、di (id)、で (ja)、にて (古文)
#     書かれていない主語: 動詞の語尾で分かる言語は書かず (la・grc・sa・ja・古文)、英語・ロシア語・インドネシア語は代名詞を補う
#
#   rows(clause, langs) → [(要素の名前, {言語: (形, 手段)})]
#
import dataclasses

from . import latin, english, russian, sanskrit, greek, indonesian, japanese, kobun

LANGS = ('la', 'grc', 'sa', 'ru', 'en', 'id', 'ja', 'kobun')
NAMES = {'la': 'ラテン語', 'grc': 'ギリシア語', 'sa': 'サンスクリット', 'ru': 'ロシア語', 'en': '英語', 'id': 'インドネシア語',
         'ja': '日本語', 'kobun': '古文'}
MODULES = {'la': latin, 'grc': greek, 'sa': sanskrit, 'ru': russian, 'en': english, 'id': indonesian, 'ja': japanese,
           'kobun': kobun}
ROLE_NAMES = {'subject': '主語', 'object': '目的語', 'recipient': '受け手', 'means': '手段', 'possessor': '所有者',
              'complement': '補語', 'place': '場所', 'source': '起点', 'prep': '前置詞句'}
CASE_NAMES = {'Nom': '主格', 'Acc': '対格', 'Gen': '属格', 'Dat': '与格', 'Abl': '奪格', 'Loc': '処格', 'Ins': '具格',
              'Voc': '呼格'}
RU_CASES = {'Nom': '主格', 'Acc': '対格', 'Gen': '生格', 'Dat': '与格', 'Ins': '造格', 'Loc': '前置格'}
LATIN_ROLE_CASES = {'subject': 'Nom', 'object': 'Acc', 'recipient': 'Dat', 'means': 'Abl', 'possessor': 'Gen',
                    'complement': 'Nom', 'place': 'Abl', 'source': 'Abl'}
WORD_ORDER = {'subject': '動詞の前', 'object': '動詞の後ろ', 'complement': '繋辞の後ろ'}
PRO_DROP = {'la': '書かない (動詞の語尾で分かる)', 'grc': '書かない (動詞の語尾で分かる)', 'sa': '書かない (動詞の語尾で分かる)',
            'ja': '書かない (文脈で分かる)', 'kobun': '書かない (文脈で分かる)', 'ru': '代名詞を補う', 'en': '代名詞を補う',
            'id': '代名詞を補う'}
TENSES = {'present': '現在', 'imperfect': '未完了過去', 'perfect': '完了', 'past-perfect': '過去完了', 'future': '未来'}


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:   # 作れない要素があっても表は作る
        return '(作れない: %s)' % type(e).__name__


def _display(lang, text):
    """表示の形: サンスクリットは SLP1 → IAST、ギリシア語は文中の重アクセント"""
    if lang == 'sa':
        from dragoman.sanskrit import script
        return ' '.join(w if w.startswith(('[', '*', '(')) else script.iast(w) for w in text.split(' '))
    if lang == 'grc':
        return greek._grave(text + ' x')[:-2]   # 句の後ろにも語が続くものとして (τὸ καλὸν ῥόδον)
    return text


# 受動の動作主 (ā + 奪格) の言語ごとの手段 (前置詞の表とは別の規則で作る)
AGENT = {'la': 'ā + 奪格', 'grc': 'ὑπό + 属格', 'sa': '具格 (動作主)', 'ru': '造格 (動作主)', 'en': '前置詞 by',
         'id': '前置詞 oleh', 'ja': '助詞 に', 'kobun': '助詞 に'}


# ----------------------------------------------------------------------
# 名詞句の要素

def np_form(lang, role, np, clause):
    """(形, 手段) — 名詞句の要素 role を言語 lang で"""
    text, how = _np_form(lang, role, np, clause)
    return _display(lang, text), how


def _np_form(lang, role, np, clause):
    m = MODULES[lang]
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        return _prep_form(lang, np, passive)
    if lang == 'la':
        case = LATIN_ROLE_CASES.get(role, 'Nom')
        return _safe(latin.noun_phrase, np, case), CASE_NAMES[case]
    if lang in ('grc', 'sa', 'ru'):
        case = m.ROLE_CASES.get(role, 'Nom')
        text = _safe(m.noun_phrase, np, case)
        names = RU_CASES if lang == 'ru' else CASE_NAMES
        how = names.get(case, case)
        if lang == 'grc' and np.head is not None and np.head.pos == 'noun' and not np.head.proper:
            how += ' + 冠詞'
        return text, how
    if lang == 'en':
        text = _safe(english.noun_phrase, np, role != 'subject')
        prep = english.ROLE_PREPS.get(role)
        if prep and role not in ('subject', 'object'):
            return prep + ' ' + text, '前置詞 %s' % prep
        return text, WORD_ORDER.get(role, '')
    if lang == 'id':
        text = _safe(indonesian.noun_phrase, np)
        prep = 'kepada' if role == 'recipient' or (role == 'means' and np.animate) else \
            indonesian.ROLE_PREPOSITIONS.get(role)
        if prep:
            return prep + ' ' + text, '前置詞 %s' % prep
        return text, WORD_ORDER.get(role, '')
    if lang in ('ja', 'kobun'):
        text = _safe(m.noun_phrase, np)
        if role == 'subject':
            particle = 'は' if lang == 'ja' or not clause.subordinator else 'の'
        else:
            particle = m.ROLE_PARTICLES.get(role, 'で' if lang == 'ja' else 'にて')
            if role == 'means' and np.animate:
                particle = 'に'
        return text + particle, ('助詞 %s' % particle) if particle else ''
    return '', ''


def _prep_form(lang, np, passive):
    key = (np.prep.lemma, np.case)
    if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
        text, _ = _prep_form(lang, np, False) if lang in ('ja', 'kobun') else (None, None)
        m = MODULES[lang]
        if lang == 'la':
            text = _safe(latin.noun_phrase, np)
        elif lang == 'en':
            text = _safe(english.noun_phrase, np, True, True)
        elif lang in ('ja', 'kobun'):
            text = _safe(m.noun_phrase, dataclasses.replace(np, prep=None)) + 'に'
        else:
            text = _safe(m.prepositional, np, True)
        return text, AGENT[lang]
    if lang == 'la':
        return _safe(latin.noun_phrase, np), '%s + %s' % (np.prep.lemma, CASE_NAMES.get(np.case, np.case))
    if lang == 'en':
        text = _safe(english.noun_phrase, np, True, passive)
        return text, '前置詞 %s' % text.split(' ')[0]
    if lang == 'grc':
        prep, case = greek.PREPOSITIONS.get(key, ('ἐν', 'Dat'))
        if passive and np.prep.lemma in ('ā', 'ab'):
            prep, case = 'ὑπό', 'Gen'
        return _safe(greek.prepositional, np, passive), '%s + %s' % (prep, CASE_NAMES.get(case, case))
    if lang == 'ru':
        prep, case = russian.PREPOSITIONS.get(key, ('в', 'Loc'))
        return _safe(russian.prepositional, np, passive), '%s + %s' % (prep, RU_CASES.get(case, case))
    if lang == 'sa':
        case, post = sanskrit.PREPOSITIONS.get(key, ('Loc', None))
        how = CASE_NAMES.get(case, case) + (' + %s' % post if post else ' (前置詞なし)')
        return _safe(sanskrit.prepositional, np, passive), how
    if lang == 'id':
        text = _safe(indonesian.prepositional, np, passive)
        return text, '前置詞 %s' % text.rsplit(' ', 1)[0].split(' ')[0]
    if lang in ('ja', 'kobun'):
        m = MODULES[lang]
        particle = 'に' if passive and np.prep.lemma in ('ā', 'ab') else m.PREPOSITIONS.get(key, 'で')
        return _safe(m.noun_phrase, dataclasses.replace(np, prep=None)) + particle, '助詞 %s' % particle
    return '', ''


# ----------------------------------------------------------------------
# 述語

PREDICATE_HOW = {
    'la': '語尾 (人称・数・時制・法・態)', 'grc': '語尾 (時制の語幹・加音)', 'sa': '語尾 (時制・人称・数)',
    'ru': '語尾 + 体 (完了体・不完了体)', 'en': '語形 + 助動詞', 'id': '語形は変えない (接辞は態、telah・akan で時)',
    'ja': '活用 + 助動詞 (た・ない・れる)', 'kobun': '活用 + 助動詞 (けり・ず・む・る)'}


def predicate_form(lang, clause):
    """述語だけの形: 名詞句を外した節を作る (主語を補う言語では代名詞も付く)"""
    bare = dataclasses.replace(clause, args=[], adverbs=[], infinitives=[], questions=[], adjuncts=[],
                               connectives=[], subordinator='')
    m = MODULES[lang]
    if lang == 'ja':
        text = _safe(japanese.predicate, bare)
    elif lang == 'kobun':
        text = _safe(kobun.predicate, bare)
    elif lang in ('en', 'la', 'ru', 'sa'):
        text = _safe(m.realize, bare, False)
    elif lang == 'id':
        text = _safe(indonesian.realize, bare)
    else:
        text = _safe(m.realize, bare)
    text = text.split('\n')[0].strip(' .।')
    return _display(lang, text), PREDICATE_HOW[lang]


def split_supplied(lang, text):
    """述語の形の頭の、補った主語の代名詞 (he saw → (he, saw))。無ければ ('', text)"""
    head, _, rest = text.partition(' ')
    if lang in SUPPLIED and head.lower() in SUPPLIED[lang] and rest:
        return head, rest
    return '', text


SUPPLIED = {'en': {'he', 'she', 'it', 'they', 'i', 'you', 'we'}, 'ru': {'он', 'она', 'оно', 'они', 'я', 'ты', 'мы', 'вы'},
            'id': {'dia', 'mereka', 'saya', 'kamu', 'kami', 'kalian'}}


# ----------------------------------------------------------------------

def rows(clause, langs=LANGS):
    """[(要素の名前, {言語: (形, 手段)})]"""
    tense = TENSES.get(clause.tense, clause.tense)
    voice = '受動' if clause.voice == 'passive' else ''
    predicates, supplied = {}, {}
    for lang in langs:
        text, how = predicate_form(lang, clause)
        supplied[lang], text = split_supplied(lang, text)   # 補った代名詞は主語の行へ (主語が書かれていれば外すだけ)
        predicates[lang] = (text, how)
    out = [('述語 (%s)' % ' '.join(x for x in (tense, voice, '否定' if clause.negated else '') if x), predicates)]
    if not clause.role('subject') and clause.mood not in ('infinitive', 'imperative') and not clause.copula:
        out.append(('主語 (書かれていない)', {lang: (supplied[lang], PRO_DROP.get(lang, '')) for lang in langs}))
    for role, np in clause.args:
        name = ROLE_NAMES.get(role, role)
        if role == 'prep' and np.prep is not None:
            name = '前置詞句 (%s + %s)' % (np.prep.lemma, CASE_NAMES.get(np.case, np.case))
        out.append((name, {lang: np_form(lang, role, np, clause) for lang in langs}))
    return out


def text_table(clauses, langs=LANGS):
    """端末に出す表 (要素ごとに、言語ごとの 形  [手段])"""
    lines = []
    for k, clause in enumerate(clauses):
        if len(clauses) > 1:
            lines.append('  節 %d' % (k + 1))
        for name, cells in rows(clause, langs):
            lines.append('    ' + name)
            width = max(len(NAMES[lang]) for lang in langs)
            for lang in langs:
                form, how = cells[lang]
                label = NAMES[lang] + '　' * (width - len(NAMES[lang]))
                lines.append('      %s  %s%s' % (label, form or '—', ('  [%s]' % how) if how else ''))
    return '\n'.join(lines)
