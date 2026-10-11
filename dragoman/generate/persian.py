#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からペルシア語の文を作る
#
#   語はペルシア語の辞書 (fa/wiktionary.sqlite の lemmas: 英語・日本語の訳語、動詞の現在語幹・過去語幹) から、
#   英語の訳語を仲立ちに選ぶ (基本の語は PREFERRED)。語は (ペルシア文字, 転写) の組で作り、文字と転写の2行に
#   語順: 主語 - 目的語 + را - به + 受け手 - 前置詞句 - 動詞 (SOV)。主語の代名詞は書かない (動詞の人称語尾で分かる)
#   動詞: 現在 می + 現在語幹 + 人称語尾 (می‌بیند)、過去 過去語幹 + 語尾 (دید)、未完了過去 می + 過去語幹、
#     未来 خواه + 語尾 + 過去語幹 (خواهد دید)、否定 ن / نمی、命令 ب + 現在語幹 (بخوان)、禁止 ن + 現在語幹、
#     受動 過去分詞 + شدن (ستوده شد)。繋辞 است / هستند、否定 نیست、過去 بود
#   名詞句: 名詞 (複数 ‌ها) + エザーフェ (-e / -ye。文字には書かない) + 形容詞・属格 (گل زیبا gol-e zibâ)
#   関係節: 名詞 + ی + که + 節 (پسری که معلم می‌ستاید)
#
import functools
import json
import math
import re
import unicodedata

from . import english
from .frame import NP

ZWNJ = '‌'
PRESENT_ENDINGS = {(1, 'sg'): ('م', 'am'), (2, 'sg'): ('ی', 'i'), (3, 'sg'): ('د', 'ad'),
                   (1, 'pl'): ('یم', 'im'), (2, 'pl'): ('ید', 'id'), (3, 'pl'): ('ند', 'and')}
PAST_ENDINGS = {(1, 'sg'): ('م', 'am'), (2, 'sg'): ('ی', 'i'), (3, 'sg'): ('', ''),
                (1, 'pl'): ('یم', 'im'), (2, 'pl'): ('ید', 'id'), (3, 'pl'): ('ند', 'and')}
COPULA = {(1, 'sg'): ('هستم', 'hastam'), (2, 'sg'): ('هستی', 'hasti'), (3, 'sg'): ('است', 'ast'),
          (1, 'pl'): ('هستیم', 'hastim'), (2, 'pl'): ('هستید', 'hastid'), (3, 'pl'): ('هستند', 'hastand')}
PRONOUNS = {('ego', 'sg'): ('من', 'man'), ('ego', 'pl'): ('ما', 'mâ'), ('tū', 'sg'): ('تو', 'to'),
            ('tū', 'pl'): ('شما', 'šomâ'), ('is', 'sg'): ('او', 'u'), ('is', 'pl'): ('آنها', 'ânhâ'),
            ('sē', 'sg'): ('خود', 'xod'), ('sē', 'pl'): ('خود', 'xod'), ('hic', 'sg'): ('این', 'in'),
            ('ille', 'sg'): ('آن', 'ân'), ('hic', 'pl'): ('اینها', 'inhâ'), ('ille', 'pl'): ('آنها', 'ânhâ')}
DEMONSTRATIVES = {'hic': ('این', 'in'), 'ille': ('آن', 'ân'), 'is': ('آن', 'ân'), 'iste': ('آن', 'ân')}
PREPOSITIONS = {('in', 'Abl'): ('در', 'dar'), ('in', 'Acc'): ('به', 'be'), ('ad', 'Acc'): ('به', 'be'),
                ('ex', 'Abl'): ('از', 'az'), ('ē', 'Abl'): ('از', 'az'), ('ab', 'Abl'): ('از', 'az'),
                ('ā', 'Abl'): ('از', 'az'), ('cum', 'Abl'): ('با', 'bâ'), ('dē', 'Abl'): ('درباره‌ی', 'darbâre-ye'),
                ('sine', 'Abl'): ('بی', 'bi'), ('per', 'Acc'): ('از میان', 'az miyân-e'), ('post', 'Acc'): ('پس از', 'pas az'),
                ('ante', 'Acc'): ('پیش از', 'piš az'), ('sub', 'Abl'): ('زیر', 'zir-e'), ('super', 'Acc'): ('روی', 'ru-ye'),
                ('propter', 'Acc'): ('به خاطر', 'be xâter-e'), ('apud', 'Acc'): ('نزد', 'nazd-e'),
                ('contrā', 'Acc'): ('بر ضد', 'bar zedd-e'), ('inter', 'Acc'): ('میان', 'miyân-e')}
CONNECTIVES = {'et': ('و', 'va'), 'que': ('و', 'va'), 'atque': ('و', 'va'), 'sed': ('اما', 'ammâ'),
               'autem': ('و', 'va'), 'enim': ('زیرا', 'zirâ'), 'nam': ('زیرا', 'zirâ'), 'igitur': ('پس', 'pas'),
               'itaque': ('پس', 'pas'), 'tum': ('سپس', 'sepas'), 'deinde': ('سپس', 'sepas'),
               'ubi': ('وقتی که', 'vaqti ke'), 'cum': ('وقتی که', 'vaqti ke'), 'postquam': ('پس از آنکه', 'pas az ân-ke'),
               'dum': ('در حالی که', 'dar hâli ke'), 'quod': ('چون', 'čun'), 'quia': ('چون', 'čun'),
               'sī': ('اگر', 'agar'), 'ut': ('تا', 'tâ'), 'nē': ('تا نه', 'tâ na')}
QUESTION_WORDS = {'quis': ('چه کسی', 'če kasi'), 'quid': ('چه', 'če'), 'cūr': ('چرا', 'čerâ'),
                  'quārē': ('چرا', 'čerâ'), 'ubi': ('کجا', 'kojâ'), 'quō': ('کجا', 'kojâ'), 'quōmodo': ('چگونه', 'čegune'),
                  'quandō': ('کی', 'key')}
# 基本の語: (英語, 品詞) → ペルシア語の見出し (辞書の項目を引く)
PREFERRED = {('girl', 'noun'): 'دختر', ('boy', 'noun'): 'پسر', ('child', 'noun'): 'کودک', ('man', 'noun'): 'مرد',
             ('woman', 'noun'): 'زن', ('king', 'noun'): 'شاه', ('queen', 'noun'): 'ملکه', ('teacher', 'noun'): 'معلم',
             ('book', 'noun'): 'کتاب', ('rose', 'noun'): 'گل', ('flower', 'noun'): 'گل', ('garden', 'noun'): 'باغ',
             ('city', 'noun'): 'شهر', ('house', 'noun'): 'خانه', ('road', 'noun'): 'راه', ('water', 'noun'): 'آب',
             ('god', 'noun'): 'خدا', ('lord', 'noun'): 'خداوند', ('father', 'noun'): 'پدر', ('mother', 'noun'): 'مادر',
             ('son', 'noun'): 'پسر', ('daughter', 'noun'): 'دختر', ('friend', 'noun'): 'دوست', ('letter', 'noun'): 'نامه',
             ('citizen', 'noun'): 'شهروند', ('sailor', 'noun'): 'ملوان', ('farmer', 'noun'): 'کشاورز',
             ('soldier', 'noun'): 'سرباز', ('enemy', 'noun'): 'دشمن', ('world', 'noun'): 'جهان', ('sin', 'noun'): 'گناه',
             ('beautiful', 'adj'): 'زیبا', ('good', 'adj'): 'خوب', ('bad', 'adj'): 'بد', ('great', 'adj'): 'بزرگ',
             ('big', 'adj'): 'بزرگ', ('large', 'adj'): 'بزرگ', ('small', 'adj'): 'کوچک', ('long', 'adj'): 'دراز',
             ('see', 'verb'): 'دیدن', ('give', 'verb'): 'دادن', ('praise', 'verb'): 'ستودن', ('sing', 'verb'): 'خواندن',
             ('come', 'verb'): 'آمدن', ('go', 'verb'): 'رفتن', ('say', 'verb'): 'گفتن', ('read', 'verb'): 'خواندن',
             ('write', 'verb'): 'نوشتن', ('walk', 'verb'): 'رفتن', ('flee', 'verb'): 'گریختن', ('capture', 'verb'): 'گرفتن',
             ('take', 'verb'): 'گرفتن', ('ask', 'verb'): 'پرسیدن', ('know', 'verb'): 'دانستن', ('fear', 'verb'): 'ترسیدن',
             ('love', 'verb'): 'دوست داشتن', ('call', 'verb'): 'خواندن', ('hear', 'verb'): 'شنیدن', ('sleep', 'verb'): 'خوابیدن',
             ('pity', 'verb'): 'بخشودن', ('remove', 'verb'): 'برداشتن', ('fight', 'verb'): 'جنگیدن', ('die', 'verb'): 'مردن'}


def _db():
    from dragoman.persian import dictionary
    return dictionary._connect()


def available():
    return _db() is not None


@functools.lru_cache(maxsize=1)
def _rows():
    """見出し → 項目 (品詞, 転写, 現在語幹, 過去語幹, 訳語, 訳語の言語, 語義の数)"""
    out = {}
    for word, pos, roman, present, past, ja, lang, senses in _db().execute(
            'SELECT word, pos, roman, present, past, ja, gloss_lang, senses FROM lemmas'):
        roman = re.split(r' or |,', roman or '')[0].strip()   # 別形の並び (darâz or derâz) は最初の形
        out.setdefault((word, pos), (word, pos, roman, present, past, ja or '', lang, senses or 1))
    return out


@functools.lru_cache(maxsize=1)
def _index():
    """訳語 (英語・日本語) → [(語義の中の順位, 見出し, 品詞)]"""
    index = {}
    for (word, pos), row in _rows().items():
        for j, gloss in enumerate(g.strip().lower() for g in row[5].split(',')):
            if gloss:
                index.setdefault(gloss, []).append((j, word, pos))
    return index


def to_persian(lex, pos):
    """語 → 辞書の項目 (見つからなければ None)"""
    pos = {'participle': 'verb', 'name': 'noun'}.get(pos, pos)
    if lex.lang == 'fa':   # 元がペルシア語なら元の語 (選び直さない)
        row = _rows().get((lex.lemma, pos)) or next((r for (w, p), r in _rows().items() if w == lex.lemma), None)
        if row:
            return row
    sources = english.candidates(lex) or [e for e in (lex.en or '').split(',') if e]
    if (lex.lang or 'la') == 'la':   # 手作りの辞書の日本語に和英で合う英語を先に (transfer と同じ)
        from .transfer import _with_japanese
        sources = _with_japanese(list(sources)[:6], [j.strip() for j in (lex.ja or '').split(',') if j.strip()])
    for en in sources[:1]:
        key = PREFERRED.get((en.lower(), pos)) or PREFERRED.get((en.lower().split(' ')[-1], pos))
        if key and (key, pos) in _rows():
            return _rows()[(key, pos)]
    wanted = [j.strip() for j in (lex.ja or '').split(',') if j.strip()]
    best = None
    for i, en in enumerate(wanted[:1] + [s.lower() for s in sources[:6]]):
        for j, word, p in _index().get(en, []):
            if p != pos or j > 4:
                continue
            row = _rows()[(word, p)]
            score = 3 * max(0, i - 1) + j - math.log(1 + row[7]) - (2 if i == 0 else 0)
            if j == 0 and i <= 1:   # コーパスでの出現数 (筆頭の語義が合うときだけ。transfer と同じ)
                from .transfer import _count
                score -= math.log(1 + _count('fa', word))
            if pos == 'verb' and not row[3]:
                score += 5   # 語幹の分からない動詞は後回し
            if best is None or score < best[0]:
                best = (score, row)
    return best[1] if best else None


# ----------------------------------------------------------------------
# 名詞句 (語は (文字, 転写) の組)

def _ezafe(word):
    """エザーフェを付けた形: 転写に -e (母音の後は -ye)。文字は ه・ا・و で終われば ی を足す (خانه‌ی)"""
    script, roman = word
    if roman.endswith(('â', 'u', 'o', 'i', 'e', 'a')):
        if script.endswith('ه'):
            return script + ZWNJ + 'ی', roman + '-ye'
        if script.endswith(('ا', 'و')):
            return script + 'ی', roman + '-ye'
        return script, roman + '-ye'
    return script, roman + '-e'


def _plural(word, animate):
    script, roman = word
    return script + ZWNJ + 'ها', roman + '-hâ'


def _noun(np):
    head = np.head
    if head.pos == 'pronoun' and (head.lemma, np.number) in PRONOUNS:
        return PRONOUNS[(head.lemma, np.number)], True
    if head.proper:   # Wiktionary の名前 (Rōma → رم)。無ければ英語の名前
        from .names import localized
        found = localized(head, 'fa')
        if found:
            from dragoman.persian import script
            row = _rows().get((found[0], 'name')) or _rows().get((found[0], 'noun'))
            return (found[0], row[2] if row and row[2] else script.rough_translit(found[0])), True
        name = english.word(head)
        return (name, name), True
    row = to_persian(head, 'adj' if head.pos in ('adj', 'participle') and not english.substantive(head) else 'noun')
    if row is None:
        return ('[%s]' % english.word(head), '[%s]' % english.word(head)), True
    word = (row[0], row[2])
    if np.number == 'pl':
        word = _plural(word, np.animate)
    return word, False


def adjective(lex):
    row = to_persian(lex, 'adj')
    return (row[0], row[2]) if row else ('[%s]' % english.word(lex),) * 2


def noun_phrase(np, relative_ok=True):
    """名詞句 → [(文字, 転写)]"""
    if np.members:
        out = []
        for k, m in enumerate(np.members):
            if k:
                out.append(('و', 'va'))
            out += noun_phrase(m)
        return out
    if np.head is None:
        return []
    word, bare = _noun(np)
    attributes = []
    demonstrative = None
    for m in np.modifiers:
        if isinstance(m, NP):
            attributes += [w for k, x in enumerate(m.members) for w in ([('و', 'va')] if k else []) + [adjective(x.head)]]
        elif m.pos == 'pronoun' and m.lemma in DEMONSTRATIVES:
            demonstrative = DEMONSTRATIVES[m.lemma]
        else:
            attributes.append(adjective(m))
    for g in np.genitives:
        attributes += noun_phrase(g)
    out = [demonstrative] if demonstrative else []
    if attributes and not bare:
        out.append(_ezafe(word))
        for k, w in enumerate(attributes):
            # 形容詞が続くときは、最後以外もエザーフェでつなぐ (گل سرخ زیبا: gol-e sorx-e zibâ)
            nxt_is_attr = k + 1 < len(attributes) and attributes[k + 1][0] != 'و'
            out.append(_ezafe(w) if nxt_is_attr and w[0] != 'و' else w)
    else:
        out.append(word)
    for r in np.relatives if relative_ok else []:
        script, roman = out[-1]
        out[-1] = (script + 'ی', roman + 'i')   # 関係節の先行詞の ی (پسری که …)
        out += [('که', 'ke')] + realize(r, gap=r.gap)
    return out


def _object(np):
    """目的語 + را (定まった目的語の印。ラテン語には冠詞が無いので定として)。関係節は را の後ろ (پسری را که …)"""
    words = noun_phrase(np, relative_ok=False) + [('را', 'râ')]
    for r in np.relatives:
        words[-2] = (words[-2][0] + 'ی', words[-2][1] + 'i')
        words += [('که', 'ke')] + realize(r, gap=r.gap)
    return words


def prepositional(np, passive=False):
    import dataclasses
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
        return [('توسط', 'tavassot-e')] + noun_phrase(inner)   # 受動の動作主
    prep = PREPOSITIONS.get((np.prep.lemma, np.case), ('در', 'dar'))
    return [prep] + noun_phrase(inner)


# ----------------------------------------------------------------------
# 動詞

# 辞書に転写の無い現在語幹
PRESENT_ROMAN = {'آ': 'â', 'آی': 'ây'}


def _stems(row):
    present = json.loads(row[3])[0] if row[3] else None
    if present and not present[1]:
        present = [present[0], PRESENT_ROMAN.get(present[0], '')]
    past = json.loads(row[4]) if row[4] else None
    if past is None and row[0].endswith('ن'):
        past = (row[0][:-1], row[2][:-2] if row[2].endswith('an') else row[2])
    return (tuple(present) if present else past), tuple(past) if past else (row[0], row[2])


def _join(*parts):
    """(文字, 転写) を一語に。می・نمی の後ろは ZWNJ"""
    script = ''
    roman = ''
    for k, (s, r) in enumerate(parts):
        if k and script.endswith('می') and s:
            script += ZWNJ
        script += s
        roman += r
    return script, roman


def _ending(stem, ending):
    """母音で終わる現在語幹の後ろは y を挟む (می‌آید・می‌گوید)"""
    if ending[1] and stem[1] and stem[1][-1] in 'âuoie':
        return 'ی' + ending[0], 'y' + ending[1]
    return ending


def _neg(stem, negated, mark='ن', roman='na'):
    if not negated:
        return ('', '')
    if stem[0].startswith('آ'):
        return 'نی', roman[:-1] + 'iy'   # نیامد (na + âmad)
    if stem[0].startswith('ا'):
        return 'نی', roman[:-1] + 'iy'
    return mark, roman


def _stem_after_prefix(stem):
    if stem[0].startswith('آ'):
        return 'ا' + stem[0][1:], stem[1]
    return stem


def verb_words(clause, person, number):
    """動詞の語の列 [(文字, 転写)]"""
    row = to_persian(clause.verb, 'verb')
    if row is None or not row[4]:
        word = english.word(clause.verb)
        return [('[%s]' % word, '[%s]' % word)]
    compound = row[0].split(' ')
    head = []
    if len(compound) > 1:   # 複合動詞 (دوست داشتن): 前の語はそのまま、後ろの動詞を活用
        head = [(compound[0], row[2].split(' ')[0])]
        main = _rows().get((compound[-1], 'verb'))
        if main:
            row = main
    present, past = _stems(row)
    key = (person, number)
    neg = clause.negated
    if clause.voice == 'passive':   # 過去分詞 + شدن
        participle = (past[0] + 'ه', past[1] + 'e')
        shod = _rows().get(('شدن', 'verb'))
        inner = verb_words_for(shod, clause.tense, key, neg, clause.mood) if shod else [('شد', 'šod')]
        return head + [participle] + inner
    return head + verb_words_for(row, clause.tense, key, neg, clause.mood)


def verb_words_for(row, tense, key, neg, mood):
    present, past = _stems(row)
    if mood == 'imperative':   # 命令 ب + 現在語幹 (+ ید)、禁止 ن + 現在語幹
        tail = ('ید', 'id') if key[1] == 'pl' else ('', '')
        if neg:
            return [_join(_neg(present, True), _stem_after_prefix(present), _ending(present, tail))]
        prefix = ('بی', 'biy') if present[0].startswith(('آ', 'ا')) else ('ب', 'be')
        return [_join(prefix, _stem_after_prefix(present), _ending(present, tail))]
    if tense in ('perfect', 'past-perfect'):
        return [_join(_neg(past, neg), _stem_after_prefix(past) if neg else past, PAST_ENDINGS[key])]
    if tense == 'imperfect':
        return [_join(('نمی', 'nemi') if neg else ('می', 'mi'), ('', '-'), past, PAST_ENDINGS[key])]
    if tense in ('future', 'future-perfect'):
        aux = _join(('نخواه', 'naxâh') if neg else ('خواه', 'xâh'), PRESENT_ENDINGS[key])
        return [aux, past]
    if row[0] in ('داشتن', 'بودن'):   # 現在で می を付けない動詞
        return [_join(_neg(present, neg), present, _ending(present, PRESENT_ENDINGS[key]))]
    return [_join(('نمی', 'nemi') if neg else ('می', 'mi'), ('', '-'), present, _ending(present, PRESENT_ENDINGS[key]))]


def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun':
        lemma = subject.head.lemma
        return ({'ego': 1, 'tū': 2}.get(lemma, 3), 'pl' if subject.number == 'pl' or subject.members else 'sg')
    if subject is not None:
        return 3, 'pl' if (subject.number == 'pl' or subject.members) else 'sg'
    return clause.person, clause.number


# ----------------------------------------------------------------------
# 節

def realize(clause, gap=None):
    """節 → [(文字, 転写)]"""
    from .frame import lexical_negation, periphrastic, dative_as_object
    clause = lexical_negation(periphrastic(clause))
    person, number = _person(clause)
    out = []
    for p in clause.adjuncts:
        if p.kind == 'absolute' and p.subject is not None:
            out += [('پس از آنکه', 'pas az ân-ke')] + realize(_absolute_clause(p)) + [('،', ',')]
    for np in clause.role('subject'):
        if gap == 'subject' or (np.head is not None and np.head.pos == 'pronoun'):
            continue   # 代名詞の主語は書かない (動詞の人称語尾で分かる)
        out += noun_phrase(np)
    if clause.copula:
        complements = clause.role('complement')
        from .frame import adjective_members
        for np in complements:
            members = adjective_members(np)
            if members:   # 形容詞の並列 (دراز و پهن)
                out += [w for k, m in enumerate(members) for w in ([('و', 'va')] if k else []) + [adjective(m.head)]]
            elif np.head is not None and np.head.pos in ('adj', 'participle') and not np.members:
                out.append(adjective(np.head))   # 名詞 (malum「りんご」) として引かない
            else:
                out += noun_phrase(np)
        past = clause.tense in ('perfect', 'imperfect', 'past-perfect')
        if past:
            bud = ('بود', 'bud')
            out.append(_join(('ن', 'na') if clause.negated else ('', ''), bud, PAST_ENDINGS[(person, number)]))
        elif clause.negated:
            out.append(('نیست', 'nist') if (person, number) == (3, 'sg') else
                       ('نیست' + COPULA[(person, number)][0][3:], 'nist' + COPULA[(person, number)][1][4:]))
        else:
            out.append(COPULA[(person, number)] if complements else ('هست', 'hast'))
        for role, np in clause.args:
            if role == 'prep':
                out[-1:-1] = prepositional(np)
        return out
    for np in clause.role('object'):
        if gap != 'object':
            out += _object(np)
    for np in clause.role('recipient'):
        if gap != 'recipient':
            out += [('به', 'be')] + noun_phrase(np)
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            out += prepositional(np, clause.voice == 'passive')
        elif role == 'means':   # 与格と奪格の同形: 人なら受け手 به、ほかは手段 با
            out += [('به', 'be') if np.animate else ('با', 'bâ')] + noun_phrase(np)
        else:
            out += [('در', 'dar')] + noun_phrase(np)
    for inner in clause.infinitives:
        out += [('که', 'ke')] + realize(inner)
    for inner in clause.questions:
        word = QUESTION_WORDS.get(inner.question_word)
        out += ([word] if word else [('که', 'ke')]) + realize(inner)
    out += verb_words(clause, person, number)
    return out


def _absolute_clause(p):
    """独立奪格 (Urbe captā) → 節 (受動の完了)"""
    from .frame import Clause, Lex
    verb = Lex(p.verb.verb, 'verb', p.verb.verb_ja, lang=p.verb.lang)
    passive = p.verb.ptense == 'past' and not p.verb.verb.endswith('r')
    return Clause(verb=verb, tense='perfect', voice='passive' if passive else 'active', args=[('subject', p.subject)])


def wrap(words, clause):
    keys = clause.connectives + ([clause.subordinator] if clause.subordinator else [])
    return [CONNECTIVES[k] for k in keys if k in CONNECTIVES] + words


def vocative(np):
    return [('ای', 'ey')] + noun_phrase(np)


def transliterate(text):
    return text


def sentence(clauses):
    """ペルシア文字 (と転写の行)"""
    if not clauses:
        return ''
    from .frame import split_address
    parts = []
    for c in clauses:
        groups, rest = split_address(c)
        words = [w for group in groups for np in group for w in vocative(np) + [('،', ',')]]
        parts.append(words + wrap(realize(rest), c))
    words = [w for k, part in enumerate(parts) for w in ([('،', ',')] if k else []) + part]
    script = ' '.join(s for s, _ in words if s).replace(' ،', '،')
    roman = ' '.join(r for _, r in words if r).replace(' ,', ',').replace(' -', '-')
    script = unicodedata.normalize('NFC', script) + '.'
    roman = re.sub(r'\s+', ' ', roman).strip() + '.'
    return '%s\n            %s' % (script, roman)
