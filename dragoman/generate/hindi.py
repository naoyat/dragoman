#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からヒンディー語・ウルドゥー語の文を作る (文法は同じ。文字だけ違う)
#
#   語はヒンディー語の辞書 (hi/wiktionary.sqlite の lemmas: 訳語・性・ウルドゥー文字の綴り・自他) から、英語・日本語の
#   訳語を仲立ちに選ぶ (基本の語は PREFERRED)。語は (デーヴァナーガリー, 転写, ウルドゥー文字) の三つ組で作り、
#   語尾は規則で両方の文字に付ける
#   語順: 主語 - 目的語 - 受け手 + को - 後置詞句 - 動詞 (SOV)。後置詞の前の名詞は斜格 (लड़कों को)
#   動詞: 現在 語幹 + ता/ते/ती + है、未完了過去 + था、過去 (完了相) 語幹 + आ/ए/ई (他動詞は主語 + ने、動詞は目的語に一致)、
#     未来 語幹 + एगा …、命令 語幹 + ओ、禁止 मत、否定 नहीं、受動 完了分詞 + जाना
#   名詞: 男性 -आ の斜格・複数 -ए、斜格複数 -ओं、女性 -ई の複数 -इयाँ、ほかの女性 -एँ。形容詞 -आ は性・数・格に一致
#   属格 का/के/की は後ろの名詞に一致 (अध्यापक की किताब)。関係節 जो / जिसे
#
import functools
import math
import re
import unicodedata

from . import english
from .frame import NP

# 語尾: 転写 → ((子音の後, 母音の後) のデーヴァナーガリー, (子音の後, 母音の後) のウルドゥー文字)
SUFFIXES = {
    'ā': (('ा', 'या'), ('ا', 'یا')), 'e': (('े', 'ए'), ('ے', 'ئے')), 'ī': (('ी', 'ई'), ('ی', 'ئی')),
    'īṃ': (('ीं', 'ईं'), ('یں', 'ئیں')), 'o': (('ो', 'ओ'), ('و', 'ؤ')), 'oṃ': (('ों', 'ओं'), ('وں', 'ؤں')),
    'eṃ': (('ें', 'एँ'), ('یں', 'ئیں')), 'iyāṃ': (('ियाँ', 'इयाँ'), ('یاں', 'ئیاں')),
    'tā': (('ता', 'ता'), ('تا', 'تا')), 'te': (('ते', 'ते'), ('تے', 'تے')), 'tī': (('ती', 'ती'), ('تی', 'تی')),
    'tīṃ': (('तीं', 'तीं'), ('تیں', 'تیں')),
    'ūṃgā': (('ूँगा', 'ऊँगा'), ('وں گا', 'ؤں گا')), 'egā': (('ेगा', 'एगा'), ('ے گا', 'ئے گا')),
    'egī': (('ेगी', 'एगी'), ('ے گی', 'ئے گی')), 'eṃge': (('ेंगे', 'एँगे'), ('یں گے', 'ئیں گے')),
    'eṃgī': (('ेंगी', 'एँगी'), ('یں گی', 'ئیں گی')), 'oge': (('ोगे', 'ओगे'), ('و گے', 'ؤ گے')),
}
# 不規則な完了相 (語幹 → m sg, m pl, f sg, f pl の三つ組)
PERFECTIVE = {'जा': [('गया', 'gayā', 'گیا'), ('गए', 'gae', 'گئے'), ('गई', 'gaī', 'گئی'), ('गईं', 'gaīṃ', 'گئیں')],
              'कर': [('किया', 'kiyā', 'کیا'), ('किए', 'kie', 'کیے'), ('की', 'kī', 'کی'), ('कीं', 'kīṃ', 'کیں')],
              'दे': [('दिया', 'diyā', 'دیا'), ('दिए', 'die', 'دیے'), ('दी', 'dī', 'دی'), ('दीं', 'dīṃ', 'دیں')],
              'ले': [('लिया', 'liyā', 'لیا'), ('लिए', 'lie', 'لیے'), ('ली', 'lī', 'لی'), ('लीं', 'līṃ', 'لیں')],
              'हो': [('हुआ', 'huā', 'ہوا'), ('हुए', 'hue', 'ہوئے'), ('हुई', 'huī', 'ہوئی'), ('हुईं', 'huīṃ', 'ہوئیں')]}
AUX_PRESENT = {(1, 'sg'): ('हूँ', 'hūṃ', 'ہوں'), (2, 'sg'): ('हो', 'ho', 'ہو'), (3, 'sg'): ('है', 'hai', 'ہے'),
               (1, 'pl'): ('हैं', 'haiṃ', 'ہیں'), (2, 'pl'): ('हो', 'ho', 'ہو'), (3, 'pl'): ('हैं', 'haiṃ', 'ہیں')}
AUX_PAST = {('m', 'sg'): ('था', 'thā', 'تھا'), ('m', 'pl'): ('थे', 'the', 'تھے'), ('f', 'sg'): ('थी', 'thī', 'تھی'),
            ('f', 'pl'): ('थीं', 'thīṃ', 'تھیں')}
PRONOUNS = {('ego', 'sg'): ('मैं', 'maiṃ', 'میں', 'मुझ', 'mujh', 'مجھ'), ('ego', 'pl'): ('हम', 'ham', 'ہم', 'हम', 'ham', 'ہم'),
            ('tū', 'sg'): ('तुम', 'tum', 'تم', 'तुम', 'tum', 'تم'), ('tū', 'pl'): ('तुम', 'tum', 'تم', 'तुम', 'tum', 'تم'),
            ('is', 'sg'): ('वह', 'vah', 'وہ', 'उस', 'us', 'اس'), ('is', 'pl'): ('वे', 've', 'وہ', 'उन', 'un', 'ان'),
            ('hic', 'sg'): ('यह', 'yah', 'یہ', 'इस', 'is', 'اس'), ('hic', 'pl'): ('ये', 'ye', 'یہ', 'इन', 'in', 'ان'),
            ('ille', 'sg'): ('वह', 'vah', 'وہ', 'उस', 'us', 'اس'), ('ille', 'pl'): ('वे', 've', 'وہ', 'उन', 'un', 'ان')}
POSTPOSITIONS = {('in', 'Abl'): ('में', 'meṃ', 'میں'), ('in', 'Acc'): ('को', 'ko', 'کو'), ('ad', 'Acc'): ('को', 'ko', 'کو'),
                 ('ex', 'Abl'): ('से', 'se', 'سے'), ('ē', 'Abl'): ('से', 'se', 'سے'), ('ab', 'Abl'): ('से', 'se', 'سے'),
                 ('ā', 'Abl'): ('से', 'se', 'سے'), ('cum', 'Abl'): ('के साथ', 'ke sāth', 'کے ساتھ'),
                 ('dē', 'Abl'): ('के बारे में', 'ke bāre meṃ', 'کے بارے میں'), ('sine', 'Abl'): ('के बिना', 'ke binā', 'کے بغیر'),
                 ('post', 'Acc'): ('के बाद', 'ke bād', 'کے بعد'), ('ante', 'Acc'): ('से पहले', 'se pahle', 'سے پہلے'),
                 ('sub', 'Abl'): ('के नीचे', 'ke nīce', 'کے نیچے'), ('super', 'Acc'): ('के ऊपर', 'ke ūpar', 'کے اوپر'),
                 ('propter', 'Acc'): ('के कारण', 'ke kāraṇ', 'کی وجہ سے'), ('apud', 'Acc'): ('के पास', 'ke pās', 'کے پاس'),
                 ('per', 'Acc'): ('से होकर', 'se hokar', 'سے ہو کر'), ('inter', 'Acc'): ('के बीच', 'ke bīc', 'کے بیچ')}
CONNECTIVES = {'et': ('और', 'aur', 'اور'), 'que': ('और', 'aur', 'اور'), 'sed': ('लेकिन', 'lekin', 'لیکن'),
               'autem': ('और', 'aur', 'اور'), 'enim': ('क्योंकि', 'kyoṃki', 'کیونکہ'), 'igitur': ('इसलिए', 'islie', 'اس لیے'),
               'itaque': ('इसलिए', 'islie', 'اس لیے'), 'tum': ('फिर', 'phir', 'پھر'), 'deinde': ('फिर', 'phir', 'پھر'),
               'ubi': ('जब', 'jab', 'جب'), 'cum': ('जब', 'jab', 'جب'), 'postquam': ('जब', 'jab', 'جب'),
               'sī': ('अगर', 'agar', 'اگر'), 'quod': ('क्योंकि', 'kyoṃki', 'کیونکہ'), 'ut': ('ताकि', 'tāki', 'تاکہ')}
PREFERRED = {('girl', 'noun'): 'लड़की', ('boy', 'noun'): 'लड़का', ('child', 'noun'): 'बच्चा', ('man', 'noun'): 'आदमी',
             ('woman', 'noun'): 'औरत', ('king', 'noun'): 'राजा', ('queen', 'noun'): 'रानी', ('teacher', 'noun'): 'अध्यापक',
             ('book', 'noun'): 'किताब', ('rose', 'noun'): 'गुलाब', ('flower', 'noun'): 'फूल', ('garden', 'noun'): 'बाग़',
             ('city', 'noun'): 'शहर', ('house', 'noun'): 'घर', ('road', 'noun'): 'सड़क', ('water', 'noun'): 'पानी',
             ('god', 'noun'): 'भगवान', ('father', 'noun'): 'पिता', ('mother', 'noun'): 'माँ', ('son', 'noun'): 'बेटा',
             ('daughter', 'noun'): 'बेटी', ('friend', 'noun'): 'दोस्त', ('letter', 'noun'): 'चिट्ठी', ('sailor', 'noun'): 'नाविक',
             ('farmer', 'noun'): 'किसान', ('soldier', 'noun'): 'सिपाही', ('citizen', 'noun'): 'नागरिक', ('enemy', 'noun'): 'दुश्मन',
             ('world', 'noun'): 'दुनिया', ('sky', 'noun'): 'आसमान', ('heaven', 'noun'): 'स्वर्ग', ('sin', 'noun'): 'पाप',
             ('beautiful', 'adj'): 'सुंदर', ('good', 'adj'): 'अच्छा', ('bad', 'adj'): 'बुरा', ('great', 'adj'): 'बड़ा',
             ('big', 'adj'): 'बड़ा', ('large', 'adj'): 'बड़ा', ('small', 'adj'): 'छोटा', ('long', 'adj'): 'लंबा', ('wide', 'adj'): 'चौड़ा', ('broad', 'adj'): 'चौड़ा',
             ('spacious', 'adj'): 'चौड़ा',
             ('see', 'verb'): 'देखना', ('give', 'verb'): 'देना', ('praise', 'verb'): 'सराहना', ('sing', 'verb'): 'गाना',
             ('come', 'verb'): 'आना', ('go', 'verb'): 'जाना', ('say', 'verb'): 'कहना', ('read', 'verb'): 'पढ़ना',
             ('write', 'verb'): 'लिखना', ('walk', 'verb'): 'चलना', ('flee', 'verb'): 'भागना', ('capture', 'verb'): 'पकड़ना',
             ('take', 'verb'): 'लेना', ('ask', 'verb'): 'पूछना', ('know', 'verb'): 'जानना', ('fear', 'verb'): 'डरना',
             ('call', 'verb'): 'बुलाना', ('hear', 'verb'): 'सुनना', ('sleep', 'verb'): 'सोना', ('die', 'verb'): 'मरना',
             ('fight', 'verb'): 'लड़ना', ('leave', 'verb'): 'निकलना',
             ('depart', 'verb'): 'निकलना', ('love', 'verb'): 'प्यार करना', ('pity', 'verb'): 'दया करना'}
INTRANSITIVE = {'आना', 'जाना', 'चलना', 'भागना', 'डरना', 'सोना', 'मरना', 'लड़ना', 'गाना', 'होना', 'रहना'}


def _db():
    from dragoman.hindi import dictionary
    return dictionary._connect()


def available():
    return _db() is not None


@functools.lru_cache(maxsize=1)
def _rows():
    out = {}
    for word, pos, roman, gender, urdu, ja, senses, trans in _db().execute(
            'SELECT word, pos, roman, gender, urdu, ja, senses, transitivity FROM lemmas'):
        out.setdefault((word, pos), (word, pos, roman or word, gender or 'm', urdu or '', ja or '', senses or 1,
                                     trans or ''))
    return out


@functools.lru_cache(maxsize=1)
def _index():
    index = {}
    for (word, pos), row in _rows().items():
        for j, gloss in enumerate(g.strip().lower() for g in row[5].split(',')):
            if gloss:
                index.setdefault(gloss, []).append((j, word, pos))
    return index


def to_hindi(lex, pos):
    pos = {'participle': 'verb', 'name': 'noun'}.get(pos, pos)
    if lex.lang in ('hi', 'ur'):   # 元がヒンディー語・ウルドゥー語なら元の語 (選び直さない)
        row = _rows().get((lex.lemma, pos)) or next((r for (w, p), r in _rows().items() if w == lex.lemma), None)
        if row:
            return row
    sources = english.candidates(lex) or [e for e in (lex.en or '').split(',') if e]
    if (lex.lang or 'la') == 'la':   # 手作りの辞書の日本語に和英で合う英語を先に (transfer と同じ)
        from .transfer import _with_japanese
        sources = _with_japanese(list(sources)[:6], [j.strip() for j in (lex.ja or '').split(',') if j.strip()])
    for en in sources[:1]:
        key = PREFERRED.get((en.lower(), pos)) or PREFERRED.get((en.lower().split(' ')[-1], pos))
        if key:
            return _rows().get((key, pos)) or (key, pos, _roman(key), 'm', '', '', 1, '')
    wanted = [j.strip() for j in (lex.ja or '').split(',') if j.strip()]
    best = None
    for i, en in enumerate(wanted[:1] + [s.lower() for s in sources[:6]]):
        for j, word, p in _index().get(en, []):
            if p != pos or j > 4:
                continue
            row = _rows()[(word, p)]
            score = 3 * max(0, i - 1) + j - math.log(1 + row[6]) - (2 if i == 0 else 0)
            if j == 0 and i <= 1:   # コーパスでの出現数 (筆頭の語義が合うときだけ)
                from .transfer import _count
                score -= math.log(1 + _count('hi', word))
            if best is None or score < best[0]:
                best = (score, row)
    return best[1] if best else None


def _roman(word):
    from dragoman.hindi import script
    return script.translit(word) if hasattr(script, 'translit') else word


# ----------------------------------------------------------------------
# 語形 (三つ組)

def _word(row):
    return (row[0], row[2], row[4] or row[0])


def _strip_final(word, deva, roman, urdu):
    """語末の母音を除いた語幹 (लड़का → लड़क、laṛkā → laṛk、لڑکا → لڑک)"""
    d, r, u = word
    if r.endswith(roman):
        r = r[:-len(roman)]
    if d.endswith(deva):
        d = d[:-len(deva)]
    for ending in urdu:
        if u.endswith(ending):
            u = u[:-len(ending)]
            break
    return d, r, u


def attach(stem, suffix):
    """語幹 + 語尾 (母音で終わる語幹の後ろは独立の母音字: गाया・گایا)"""
    d, r, u = stem
    after_vowel = bool(r) and r[-1] in 'aāiīuūeo'
    deva, urdu = SUFFIXES[suffix]
    return d + deva[after_vowel], r + suffix, u + urdu[after_vowel]


def noun_form(row, number, oblique):
    word = _word(row)
    gender = row[3] or 'm'
    r = word[1]
    if gender == 'm' and r.endswith('ā') and row[0] not in ('राजा', 'पिता'):
        stem = _strip_final(word, 'ा', 'ā', ('ا', 'ہ'))
        if number == 'pl':
            return attach(stem, 'oṃ' if oblique else 'e')
        return attach(stem, 'e') if oblique else word
    if number == 'pl':
        if oblique:
            if gender == 'f' and r.endswith('ī'):
                return attach(_strip_final(word, 'ी', 'ī', ('ی',)), 'iyāṃ')[0].replace('ियाँ', 'ियों'), \
                    r[:-1] + 'iyoṃ', word[2][:-1] + 'یوں'
            return attach(word, 'oṃ')
        if gender == 'f':
            if r.endswith('ī'):
                return attach(_strip_final(word, 'ी', 'ī', ('ی',)), 'iyāṃ')
            return attach(word, 'eṃ')
    return word


def adjective(lex, gender, number, oblique):
    row = to_hindi(lex, 'adj')
    if row is None:
        w = '[%s]' % english.word(lex)
        return w, w, w
    word = _word(row)
    if not word[1].endswith('ā'):
        return word   # 変化しない形容詞 (सुंदर)
    stem = _strip_final(word, 'ा', 'ā', ('ا', 'ہ'))
    if gender == 'f':
        return attach(stem, 'ī')
    if number == 'pl' or oblique:
        return attach(stem, 'e')
    return word


def _gender(np):
    if np.head is None:
        return 'm'
    if np.head.pos == 'pronoun' or np.head.proper:
        return 'f' if np.gender == 'f' else 'm'
    row = to_hindi(np.head, 'noun')
    return (row[3] if row else 'm') or 'm'


def noun_phrase(np, oblique=False):
    """名詞句 → [三つ組]。oblique: 後置詞の前 (斜格)"""
    if np.members:
        out = []
        for k, m in enumerate(np.members):
            if k:
                out.append(('और', 'aur', 'اور'))
            out += noun_phrase(m, oblique)
        return out
    head = np.head
    if head is None:
        return []
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.pos == 'pronoun' and (head.lemma, number) in PRONOUNS:
        p = PRONOUNS[(head.lemma, number)]
        return [p[3:] if oblique else p[:3]]
    if head.proper:
        from .names import localized
        found = localized(head, 'hi')
        name = english.word(head)
        return [(found[0], name, found[0]) if found else (name, name, name)]
    row = to_hindi(head, 'noun')
    if row is None:
        w = '[%s]' % english.word(head)
        return [(w, w, w)]
    gender = row[3] or 'm'
    out = []
    for g in np.genitives:   # 属格は前に: अध्यापक की किताब (का/के/की は後ろの名詞に一致)
        out += noun_phrase(g, True)
        out.append({('m', False): ('का', 'kā', 'کا')}.get((gender, number == 'sg' and not oblique),
                                                          ('की', 'kī', 'کی') if gender == 'f' else ('के', 'ke', 'کے')))
    for m in np.modifiers:
        if isinstance(m, NP):
            for k, x in enumerate(m.members):
                if k:
                    out.append(('और', 'aur', 'اور'))
                out.append(adjective(x.head, gender, number, oblique))
        elif m.pos == 'pronoun' and m.lemma in ('hic', 'ille', 'is'):
            p = PRONOUNS[('hic' if m.lemma == 'hic' else 'ille', number)]
            out.append(p[3:] if oblique else p[:3])
        else:
            out.append(adjective(m, gender, number, oblique))
    out.append(noun_form(row, number, oblique))
    return out


# ----------------------------------------------------------------------
# 動詞

def _verb_row(clause):
    row = to_hindi(clause.verb, 'verb')
    if row is None:
        return None, []
    parts = row[0].split(' ')
    if len(parts) > 1:   # 複合動詞 (प्यार करना): 前の語はそのまま
        roman, urdu = row[2].split(' '), (row[4] or row[0]).split(' ')
        head = [(parts[0], roman[0] if roman else parts[0], urdu[0] if urdu else parts[0])]
        main = _rows().get((parts[-1], 'verb')) or (parts[-1], 'verb', roman[-1], 'm', urdu[-1], '', 1, '')
        return main, head
    return row, []


def _stem(row):
    return _strip_final(_word(row), 'ना', 'nā', ('نا',))


def perfective(row, gender, number):
    stem = _stem(row)
    if stem[0] in PERFECTIVE:
        return PERFECTIVE[stem[0]][(gender == 'f') * 2 + (number == 'pl')]
    if gender == 'f':
        return attach(stem, 'īṃ' if number == 'pl' else 'ī')
    return attach(stem, 'e' if number == 'pl' else 'ā')


def _agreement(np, clause):
    """(人称, 性, 数)"""
    if np is None:
        return clause.person, 'm', clause.number
    if np.head is not None and np.head.pos == 'pronoun' and np.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[np.head.lemma], 'f' if np.gender == 'f' else 'm', np.number
    return 3, _gender(np), 'pl' if (np.number == 'pl' or np.members) else 'sg'


def verb_words(clause, subject, obj):
    row, head = _verb_row(clause)
    if row is None:
        w = '[%s]' % english.word(clause.verb)
        return [(w, w, w)], False
    person, gender, number = _agreement(subject, clause)
    neg = [('नहीं', 'nahīṃ', 'نہیں')] if clause.negated else []
    if clause.mood == 'imperative':
        if clause.negated:
            return [('मत', 'mat', 'مت')] + head + [attach(_stem(row), 'o')], False
        return head + [attach(_stem(row), 'o')], False
    if clause.voice == 'passive':   # 完了分詞 + जाना
        jana = _rows().get(('जाना', 'verb')) or ('जाना', 'verb', 'jānā', 'm', 'جانا', '', 1, '')
        participle = perfective(row, gender, number)
        return neg + head + [participle, perfective(jana, gender, number)] + \
            ([AUX_PRESENT[(person, number)]] if clause.tense == 'present' else []), False
    tense = clause.tense
    if tense in ('perfect', 'past-perfect'):
        transitive = (row[0] not in INTRANSITIVE and (obj is not None or row[7] == 'transitive')) and not head or \
            (head and row[0] in ('करना',))
        if transitive:   # 他動詞の完了相: 主語 + ने、動詞は (को の無い) 目的語に一致
            g, n = (_gender(obj), 'pl' if obj.number == 'pl' else 'sg') if obj is not None and not _takes_ko(obj) \
                else ('m', 'sg')
            return neg + head + [perfective(row, g, n)], True
        return neg + head + [perfective(row, gender, number)], False
    if tense in ('future', 'future-perfect'):
        suffix = {(1, 'sg'): 'ūṃgā', (2, 'sg'): 'oge', (3, 'sg'): 'egā', (1, 'pl'): 'eṃge', (2, 'pl'): 'oge',
                  (3, 'pl'): 'eṃge'}[(person, number)]
        word = attach(_stem(row), suffix)
        if gender == 'f':
            word = (word[0][:-2] + 'गी' if word[0].endswith('गा') or word[0].endswith('गे') else word[0],
                    word[1][:-2] + 'gī', word[2][:-2] + 'گی' if word[2].endswith(('گا', 'گے')) else word[2])
        return neg + head + [word], False
    # 女性複数の鼻音は助動詞だけに (गाती हैं・गाती थीं)。否定で助動詞を落とすときは分詞に (नहीं गातीं)
    female_plural = 'tīṃ' if clause.negated and tense == 'present' else 'tī'
    habitual = attach(_stem(row), ('tī' if gender == 'f' else 'tā') if number == 'sg' else
                      (female_plural if gender == 'f' else 'te'))
    aux = AUX_PAST[(gender, number)] if tense == 'imperfect' else AUX_PRESENT[(person, number)]
    if clause.negated and tense == 'present':
        return neg + head + [habitual], False   # 否定の現在は है を落とす (नहीं गाती)
    return neg + head + [habitual, aux], False


def _takes_ko(np):
    """को の付く目的語 (人・代名詞)"""
    return np is not None and (np.animate or (np.head is not None and np.head.pos == 'pronoun'))


# ----------------------------------------------------------------------
# 節

def realize(clause, gap=None):
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    subject = (clause.role('subject') or [None])[0]
    obj = (clause.role('object') or [None])[0]
    out = []
    if clause.copula:
        if subject is not None and gap != 'subject':
            out += noun_phrase(subject)
        person, gender, number = _agreement(subject, clause)
        from .frame import adjective_members
        for np in clause.role('complement'):
            members = adjective_members(np) or ([np] if np.head is not None and np.head.pos in ('adj', 'participle')
                                                and not np.members else None)
            if members:
                out += [w for k, m in enumerate(members)
                        for w in ([('और', 'aur', 'اور')] if k else []) + [adjective(m.head, gender, number, False)]]
            else:
                out += noun_phrase(np)
        for role, np in clause.args:
            if role == 'prep':
                out += prepositional(np)
        if clause.negated:
            out.append(('नहीं', 'nahīṃ', 'نہیں'))
        past = clause.tense in ('perfect', 'imperfect', 'past-perfect')
        out.append(AUX_PAST[(gender, number)] if past else AUX_PRESENT[(person, number)])
        return out
    words, ergative = verb_words(clause, subject, obj)
    if subject is not None and gap != 'subject':
        out += noun_phrase(subject, oblique=ergative)
        if ergative:
            out.append(('ने', 'ne', 'نے'))
    elif subject is None and gap is None and clause.mood != 'imperative' and clause.person in (1, 2):
        pronoun = PRONOUNS[({1: 'ego', 2: 'tū'}[clause.person], clause.number)]
        out.append(pronoun[3:] if ergative else pronoun[:3])
        if ergative:
            out.append(('ने', 'ne', 'نے'))
    for np in clause.role('object'):
        if gap == 'object':
            continue
        if _takes_ko(np):
            out += noun_phrase(np, True) + [('को', 'ko', 'کو')]
        else:
            out += noun_phrase(np)
    for np in clause.role('recipient'):
        out += noun_phrase(np, True) + [('को', 'ko', 'کو')]
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            out += prepositional(np, clause.voice == 'passive')
        elif role == 'means':
            out += noun_phrase(np, True) + [('को', 'ko', 'کو') if np.animate else ('से', 'se', 'سے')]
        else:
            out += noun_phrase(np, True) + [('में', 'meṃ', 'میں')]
    return out + words


def prepositional(np, passive=False):
    import dataclasses
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
        return noun_phrase(inner, True) + [('के द्वारा', 'ke dvārā', 'کے ذریعے')]   # 受動の動作主
    post = POSTPOSITIONS.get((np.prep.lemma, np.case), ('में', 'meṃ', 'میں'))
    return noun_phrase(inner, True) + [post]


def relative(np, r):
    """関係節: 先行詞の後ろに जो (主語) / जिसे (目的語) + 節"""
    pronoun = ('जिसे', 'jise', 'جسے') if r.gap == 'object' else ('जो', 'jo', 'جو')
    return [pronoun] + realize(r, gap=r.gap)


def sentence_words(clauses):
    from .frame import split_address
    out = []
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        if k:
            out.append(('،', ',', '،'))
        for group in groups:
            for np in group:
                out += noun_phrase(np) + [(',', ',', '،')]
        keys = rest.connectives + ([rest.subordinator] if rest.subordinator else [])
        out += [CONNECTIVES[key] for key in keys if key in CONNECTIVES]
        words = realize(rest)
        # 関係節は節の後ろに (लड़की उस लड़के को देखती है जिसे अध्यापक सराहता है)
        for np in [x for _, x in rest.args if x.relatives]:
            for r in np.relatives:
                words += [(',', ',', '،')] + relative(np, r)
        out += words
    return out


def _render(words, column, stop):
    text = ' '.join(w[column] for w in words if w[column]).replace(' ,', ',').replace(' ،', '،')
    return unicodedata.normalize('NFC', re.sub(r'\s+', ' ', text).strip()) + stop


def sentence(clauses):
    """デーヴァナーガリー (と転写の行)"""
    if not clauses:
        return ''
    words = sentence_words(clauses)
    return '%s\n            %s' % (_render(words, 0, '।'), _render(words, 1, '.'))


def sentence_urdu(clauses):
    """ウルドゥー文字 (と転写の行)"""
    if not clauses:
        return ''
    words = sentence_words(clauses)
    return '%s\n            %s' % (_render(words, 2, '۔'), _render(words, 1, '.'))
