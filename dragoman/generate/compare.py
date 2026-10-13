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

from . import latin, english, russian, sanskrit, greek, indonesian, tagalog, arabic, hebrew, persian, hindi, ainu, tibetan, \
    japanese, kobun, korean, turkish, mongolian, german

LANGS = ('la', 'grc', 'sa', 'ru', 'de', 'en', 'id', 'tl', 'ar', 'he', 'fa', 'hi', 'ur', 'tr', 'mn', 'ko', 'ain', 'bo', 'ja', 'kobun')
NAMES = {'la': 'ラテン語', 'grc': 'ギリシア語', 'sa': 'サンスクリット', 'ru': 'ロシア語', 'de': 'ドイツ語', 'en': '英語', 'id': 'インドネシア語',
         'tl': 'タガログ語', 'ar': 'アラビア語', 'he': 'ヘブライ語', 'fa': 'ペルシア語', 'hi': 'ヒンディー語',
         'ur': 'ウルドゥー語', 'tr': 'トルコ語', 'mn': 'モンゴル語', 'ko': '韓国語', 'ain': 'アイヌ語', 'bo': 'チベット語',
         'ja': '日本語', 'kobun': '古文'}
MODULES = {'la': latin, 'grc': greek, 'sa': sanskrit, 'ru': russian, 'de': german, 'en': english, 'id': indonesian, 'tl': tagalog,
           'ar': arabic, 'he': hebrew, 'fa': persian, 'hi': hindi, 'ur': hindi, 'tr': turkish, 'mn': mongolian, 'ko': korean, 'ain': ainu,
           'bo': tibetan, 'ja': japanese,
           'kobun': kobun}
# 比較の表の口 (compare_np・compare_predicate と説明の文字列) を持つ生成器の言語 (言語ごとの分岐を書かない)
GENERIC = ('ko', 'tr', 'mn', 'de')
ROLE_NAMES = {'subject': '主語', 'object': '目的語', 'recipient': '受け手', 'means': '手段', 'possessor': '所有者',
              'complement': '補語', 'place': '場所', 'source': '起点', 'prep': '前置詞句', 'address': '呼びかけ'}
CASE_NAMES = {'Nom': '主格', 'Acc': '対格', 'Gen': '属格', 'Dat': '与格', 'Abl': '奪格', 'Loc': '処格', 'Ins': '具格',
              'Voc': '呼格'}
RU_CASES = {'Nom': '主格', 'Acc': '対格', 'Gen': '生格', 'Dat': '与格', 'Ins': '造格', 'Loc': '前置格'}
LATIN_ROLE_CASES = {'subject': 'Nom', 'object': 'Acc', 'recipient': 'Dat', 'means': 'Abl', 'possessor': 'Gen',
                    'complement': 'Nom', 'place': 'Abl', 'source': 'Abl'}
WORD_ORDER = {'subject': '動詞の前', 'object': '動詞の後ろ', 'complement': '繋辞の後ろ'}
PRO_DROP = {'la': '書かない (動詞の語尾で分かる)', 'grc': '書かない (動詞の語尾で分かる)', 'sa': '書かない (動詞の語尾で分かる)',
            'ja': '書かない (文脈で分かる)', 'kobun': '書かない (文脈で分かる)', 'ru': '代名詞を補う', 'en': '代名詞を補う',
            'id': '代名詞を補う', 'tl': '代名詞を補う', 'ar': '書かない (動詞の接辞で分かる)',
            'he': '完了形・未完了形は書かない (動詞の接辞で分かる)。分詞なら代名詞を補う',
            'fa': '書かない (動詞の人称語尾で分かる)', 'hi': '書かない (文脈で分かる)', 'ur': '書かない (文脈で分かる)',
            'ain': '書かない (動詞の人称の接辞 ku=・e= … で分かる)', 'bo': '書かない (文脈で分かる)'}
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
    if lang in ('ar', 'he') and text and not text.startswith('('):   # 右から左の文字には転写を添える
        import unicodedata
        text = unicodedata.normalize('NFC', text)
        return '%s (%s)' % (text, MODULES[lang].transliterate(text).strip(' .'))
    return text


# 受動の動作主 (ā + 奪格) の言語ごとの手段 (前置詞の表とは別の規則で作る)
AGENT = {'la': 'ā + 奪格', 'grc': 'ὑπό + 属格', 'sa': '具格 (動作主)', 'ru': '造格 (動作主)', 'en': '前置詞 by',
         'id': '前置詞 oleh', 'tl': 'ng (焦点でない行為者)', 'ar': 'مِنْ قِبَلِ + 属格', 'he': 'עַל־יְדֵי',
         'ain': '書かない (受動の a= は動作主を書かない)', 'bo': '能格 (受動は無いので能動の主語に)',
         'fa': 'توسط (tavassot-e)', 'hi': 'के द्वारा (ke dvārā)', 'ur': 'کے ذریعے (ke zariye)',
         'ja': '助詞 に', 'kobun': '助詞 に'}
AR_CASES = {'n': '主格', 'a': '対格', 'g': '属格'}


def _ar_active(clause):
    """アラビア語で受動の形が無く、能動に組み替える節か (مَدَحَ المُعَلِّمُ الوَلَدَ)"""
    return clause.voice == 'passive' and not clause.copula and not _safe(arabic.passive_possible, clause) is True


# ----------------------------------------------------------------------
# 名詞句の要素

def np_form(lang, role, np, clause):
    """(形, 手段) — 名詞句の要素 role を言語 lang で"""
    text, how = _np_form(lang, role, np, clause)
    return _display(lang, text), how


# 呼びかけ (呼格の名詞句) の言語ごとの表し方。形は各言語の vocative で作る (文の頭に置き、カンマで区切る)
ADDRESS_HOW = {'ain': '名詞 (印なし)', 'bo': '名詞 (印なし)', 'fa': 'ای + 名詞', 'hi': '名詞 (呼びかけの印なし)', 'ur': '名詞 (呼びかけの印なし)','la': '呼格', 'grc': 'ὦ + 呼格 (冠詞なし)', 'sa': '呼格', 'ru': '主格 (呼格は無い)', 'en': '冠詞なし',
               'id': 'そのまま', 'tl': '標識なし', 'ar': 'يا + 主格 (冠詞・タンウィーンなし)', 'he': '冠詞付き',
               'ja': '助詞 よ', 'kobun': '助詞 よ'}


# 語を組 (文字, 転写[, ウルドゥー文字]) で作る言語: 表示の文字の列
WORD_COLUMNS = {'fa': 0, 'hi': 0, 'ur': 2}
FA_HOW = {'subject': '動詞の前 (格の印なし)', 'object': 'را (定の目的語の印)', 'recipient': '前置詞 به',
          'address': 'ای + 名詞'}
HI_HOW = {'address': '名詞 (呼びかけの印なし)'}


def _words(lang, words):
    """組の列 → 文字 (転写)"""
    if not words:
        return ''
    column = WORD_COLUMNS[lang]
    script = ' '.join(w[column] for w in words if w[column])
    roman = ' '.join(w[1] for w in words if w[1]).replace(' -', '-')
    return '%s (%s)' % (script, roman)


def _tuple_np(lang, role, np, clause):
    """ペルシア語・ヒンディー語・ウルドゥー語の名詞句の要素 (表示の形, 手段)"""
    passive = clause.voice == 'passive'
    if lang == 'fa':
        if role == 'prep' and np.prep is not None:
            words = persian.prepositional(np, passive)
            return _words(lang, words), words[0][0] + ' (%s)' % words[0][1] if not (passive and np.prep.lemma in
                                                                                     ('ā', 'ab', 'abs')) else AGENT['fa']
        if role == 'object':
            return _words(lang, persian._object(np)), FA_HOW['object']
        if role == 'recipient' or (role == 'means' and np.animate):
            return _words(lang, [('به', 'be')] + persian.noun_phrase(np)), FA_HOW['recipient']
        if role == 'address':
            return _words(lang, persian.vocative(np)), FA_HOW['address']
        return _words(lang, persian.noun_phrase(np)), FA_HOW.get(role, '')
    if role == 'prep' and np.prep is not None:
        words = hindi.prepositional(np, passive)
        last = words[-1]
        how = AGENT[lang] if passive and np.prep.lemma in ('ā', 'ab', 'abs') else \
            '斜格 + %s (%s)' % (last[2] if lang == 'ur' else last[0], last[1])
        return _words(lang, words), how
    if role == 'subject':
        _, ergative = _safe(lambda c: hindi.verb_words(c, np, (c.role('object') or [None])[0]), clause) \
            if not clause.copula else ([], False)
        words = hindi.noun_phrase(np, oblique=ergative) + ([('ने', 'ne', 'نے')] if ergative else [])
        return _words(lang, words), ('斜格 + %s (他動詞の完了相)' % _ur(lang, 'ने', 'نے')) if ergative else '直格'
    if role == 'object':
        if hindi._takes_ko(np):
            return _words(lang, hindi.noun_phrase(np, True) + [('को', 'ko', 'کو')]), '斜格 + %s (人の目的語)' % _ur(lang, 'को', 'کو')
        return _words(lang, hindi.noun_phrase(np)), '直格 (格の印なし)'
    if role == 'recipient' or (role == 'means' and np.animate):
        return _words(lang, hindi.noun_phrase(np, True) + [('को', 'ko', 'کو')]), '斜格 + %s' % _ur(lang, 'को', 'کو')
    if role == 'address':
        return _words(lang, hindi.noun_phrase(np)), HI_HOW['address']
    return _words(lang, hindi.noun_phrase(np, True) + [('में', 'meṃ', 'میں')]), '斜格 + %s' % _ur(lang, 'में', 'میں')


def _ur(lang, deva, urdu):
    """説明の中の後置詞を表の言語の文字で"""
    return urdu if lang == 'ur' else deva


def _ain_bo_np(lang, role, np, clause):
    """アイヌ語・チベット語の名詞句の要素 (表示の形, 手段)"""
    passive = clause.voice == 'passive'
    if lang == 'ain':
        text = ' '.join(ainu.noun_phrase(np))
        if role == 'prep' and np.prep is not None:
            if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
                return '', AGENT['ain']
            post = ainu.POSTPOSITIONS.get((np.prep.lemma, np.case), 'ta')
            return ' '.join(ainu.noun_phrase(dataclasses.replace(np, prep=None)) + [post]), '後置詞 %s' % post
        if role == 'means' and not np.animate:
            return text + ' ari', '後置詞 ari'
        return text, {'subject': '動詞の前 (格の印なし。人称は動詞の接辞)', 'object': '格の印なし',
                      'recipient': '印なし (目的語の前)', 'means': '印なし (目的語の前)'}.get(role, '')
    text = tibetan.noun_phrase(np if role != 'prep' else dataclasses.replace(np, prep=None))
    if role == 'subject':
        if passive and not clause.copula:
            return _bo(text), '絶対格 (受動は無いので能動の目的語に)'
        transitive = bool(clause.role('object')) and not clause.copula
        return (_bo(tibetan.particle(text, 'erg')), '能格 (kyis/gyis/gis/-s)') if transitive else (_bo(text), '絶対格 (印なし)')
    if role == 'prep' and np.prep is not None:
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return _bo(tibetan.particle(text, 'erg')), AGENT['bo']
        post = tibetan.POSTPOSITIONS.get((np.prep.lemma, np.case), 'na')
        return _bo(text + ' ' + post), '後置 %s' % post
    if role == 'recipient' or (role == 'means' and np.animate):
        return _bo(text + ' la'), '後置 la'
    if role == 'means':
        return _bo(tibetan.particle(text, 'erg')), '具格 (能格と同じ形)'
    return _bo(text), {'object': '絶対格 (印なし)', 'address': ADDRESS_HOW['bo']}.get(role, '')


def _bo(wylie):
    """チベット文字 (Wylie)"""
    if not wylie:
        return ''
    script = tibetan.tibetan_script(wylie)
    return '%s (%s)' % (script, wylie) if script else wylie


def _np_form(lang, role, np, clause):
    if lang in GENERIC:
        try:
            return MODULES[lang].compare_np(role, np, clause)
        except Exception as e:
            return '(作れない: %s)' % type(e).__name__, ''
    if lang in ('ain', 'bo'):
        try:
            return _ain_bo_np(lang, role, np, clause)
        except Exception as e:
            return '(作れない: %s)' % type(e).__name__, ''
    if lang in WORD_COLUMNS:
        return _tuple_np_safe(lang, role, np, clause)
    m = MODULES[lang]
    passive = clause.voice == 'passive'
    if role == 'address':
        how = '主格 (主格の形の呼びかけ)' if lang == 'la' and latin._nominative_address(np) else ADDRESS_HOW[lang]
        return _safe(m.noun_phrase if lang == 'id' else m.vocative, np), how
    if role == 'prep' and np.prep is not None:
        return _prep_form(lang, np, passive, clause)
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
    if lang == 'tl':
        return _tagalog_np(role, np, clause)
    if lang == 'ar':
        if role == 'subject' and _ar_active(clause):
            return _safe(arabic.noun_phrase, np, 'a'), '対格 (受動の形が無いので能動に組み替えた目的語)'
        if role == 'recipient' or (role == 'means' and np.animate):
            return _safe(arabic.noun_phrase, np, 'g', True, 'li_prep'), 'لِـ + 属格'
        if role == 'means':
            return _safe(arabic.noun_phrase, np, 'g', True, 'bi_prep'), 'بِـ + 属格'
        case = arabic.CASES.get(role)
        if case is None:
            return 'فِي ' + _safe(arabic.noun_phrase, np, 'g'), 'فِي + 属格'
        return _safe(arabic.noun_phrase, np, case), AR_CASES[case] + (' (動詞の後ろ)' if role == 'subject' and not clause.copula else '')
    if lang == 'he':
        if role == 'object':
            return 'אֶת־' + _safe(lambda x: hebrew.noun_phrase(x)[0], np), 'אֶת־ (定の目的語の印)'
        if role == 'recipient' or (role == 'means' and np.animate):
            return _safe(lambda x: hebrew.noun_phrase(x, 'לְ')[0], np), 'לְ (語に付く)'
        if role != 'subject':
            return _safe(lambda x: hebrew.noun_phrase(x, 'בְּ')[0], np), 'בְּ (語に付く)'
        return _safe(lambda x: hebrew.noun_phrase(x)[0], np), '格の変化なし (完了形なら動詞の後ろ、分詞なら前)'
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


TL_FOCUS = {'actor': '行為者焦点', 'object': '対象焦点', 'conveyance': '移動物焦点', 'locative': '場所焦点'}


def _tagalog_np(role, np, clause):
    """タガログ語: 焦点の名詞句が ang、焦点でない行為者・目的語が ng、受け手・場所が sa"""
    try:
        voice, _, topic = tagalog._focus(clause)
    except Exception:
        voice, topic = 'actor', None
    if role in ('subject', 'object'):
        if np is topic:
            marker, how = 'ang', 'ang (焦点)'
        else:
            marker, how = 'ng', 'ng (焦点でない%s)' % ('行為者' if role == 'subject' else '目的語')
    elif role == 'means' and not np.animate:
        marker, how = 'ng', 'ng'
    else:
        marker, how = 'sa', 'sa'
    return _safe(tagalog.noun_phrase, np, marker), how


def _tuple_np_safe(lang, role, np, clause):
    try:
        return _tuple_np(lang, role, np, clause)
    except Exception as e:   # 作れない要素があっても表は作る
        return '(作れない: %s)' % type(e).__name__, ''


def _prep_form(lang, np, passive, clause=None):
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
        elif lang == 'ar' and _ar_active(clause):
            return (_safe(arabic.noun_phrase, dataclasses.replace(np, prep=None), 'n'),
                    '主格 (受動の形が無いので能動に組み替えた主語)')
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
    if lang == 'tl':
        before, marker = tagalog.PREPOSITIONS.get(key, ('', 'sa'))
        return _safe(tagalog.prepositional, np, passive), ' + '.join(x for x in (before, marker) if x)
    if lang == 'ar':
        prep = arabic.PREPOSITIONS.get(key, 'فِي')
        return _safe(arabic.prepositional, np, passive), '%s + 属格' % prep
    if lang == 'he':
        prep, attached = hebrew.PREPOSITIONS.get(key, ('בְּ', True))
        return _safe(hebrew.prepositional, np, passive), prep + (' (語に付く)' if attached else '')
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
    'tl': '接辞で焦点 (行為者 -um-/mag-・対象 -in・移動物 i-)、重複と -in- でアスペクト',
    'ar': '完了形・未完了形 (人称・性・数の接辞)、法 (直説法・要求法)、否定 لَمْ・لا・لَنْ',
    'he': '完了形・未完了形 (人称・性・数の接辞)、現在は分詞 (性・数)、態は動詞の型 (binyan)',
    'fa': 'می + 現在語幹 + 人称語尾 / 過去語幹 + 人称語尾、否定 ن、未来 خواه、受動 + شدن',
    'hi': '語幹 + 相 (習慣 ता・完了 आ) + 助動詞 है/था (性・数に一致)、否定 नहीं、受動 + जाना',
    'ur': '語幹 + 相 (習慣 تا・完了 ا) + 助動詞 ہے/تھا (性・数に一致)、否定 نہیں、受動 + جانا',
    'ain': '時制は無い。人称の接辞 (ku=・e=・ci=)、否定 somo、未来・意図 kusu ne、受動 a=',
    'bo': '時制の語幹 (現在・過去・未来・命令) + 終止の助詞 (ngo・do・no …)、否定 mi (現在)・ma (過去)',
    'ja': '活用 + 助動詞 (た・ない・れる)', 'kobun': '活用 + 助動詞 (けり・ず・む・る)'}


# 繋辞の文 (Puella pulchra est.) の述語 = 繋辞 + 補語。言語ごとの表し方
COPULA_HOW = {
    'la': 'sum + 補語 (主語に性・数・格で一致)', 'grc': 'εἰμί (前接語) + 補語 (主語に一致)',
    'sa': '繋辞を書かない (名詞文。補語は主語に一致)', 'ru': '現在は繋辞を書かない (過去は был。補語は主語に一致)',
    'en': 'be + 補語', 'id': '繋辞を書かない (名詞なら adalah も)', 'tl': '述語が先 (繋辞を書かない)',
    'ar': '繋辞を書かない (名詞文。過去は كانَ、否定は لَيْسَ。その後の補語は対格)',
    'he': '繋辞を書かない (名詞文。過去は הָיָה)',
    'fa': '補語 + است (否定 نیست、過去 بود)', 'hi': '補語 + है (過去 था。性・数に一致)',
    'ur': '補語 + ہے (過去 تھا。性・数に一致)',
    'ain': '名詞 + ne (形容詞は状態の動詞でそのまま述語: pirka)', 'bo': '補語 + yin (否定 min)',
    'ja': '形容詞はそのまま述語 (名詞なら である)', 'kobun': '形容詞はそのまま述語 (名詞なら なり)'}


def predicate_form(lang, clause):
    """述語の形。語形 (一致・補語) を決めるため主語と補語は残して節を作り、主語の形を外す
    (主語の無い節では、主語を補う言語の代名詞が付く。split_supplied で外す)"""
    # 補語の無い繋辞 (存在・所在の文 Puella in hortō est.) は前置詞句なども残す (外すと there is … の文になる)
    keep_all = clause.copula and not clause.role('complement')
    kept = [(role, np) for role, np in clause.args if keep_all or role in ('subject', 'complement')]
    reduced = dataclasses.replace(clause, args=kept, adverbs=[], infinitives=[], questions=[], adjuncts=[],
                                  connectives=[], subordinator='')
    if lang == 'ar' and _ar_active(clause):   # 能動に組み替えた主語 (元の動作主) を残して外す
        clause = arabic.to_active(clause)
        kept = [(role, np) for role, np in clause.args if role == 'subject']
        reduced = dataclasses.replace(reduced, voice='active', args=kept, person=clause.person, number=clause.number)
    if lang in GENERIC:
        try:
            text, how = MODULES[lang].compare_predicate(clause, reduced)
            return _display(lang, text), how
        except Exception as e:
            return '(作れない: %s)' % type(e).__name__, ''
    if lang in ('ain', 'bo'):
        how = COPULA_HOW[lang] if clause.copula and clause.role('complement') else PREDICATE_HOW[lang]
        try:
            return _ain_bo_predicate(lang, clause, reduced), how
        except Exception as e:
            return '(作れない: %s)' % type(e).__name__, how
    if lang in WORD_COLUMNS:
        how = COPULA_HOW[lang] if clause.copula and clause.role('complement') else PREDICATE_HOW[lang]
        try:
            return _words(lang, _tuple_predicate(lang, clause, reduced)), how
        except Exception as e:
            return '(作れない: %s)' % type(e).__name__, how
    m = MODULES[lang]
    if lang == 'ja':
        text = _safe(japanese.predicate, reduced)
    elif lang == 'kobun':
        text = _safe(kobun.predicate, reduced)
    elif lang in ('en', 'la', 'ru', 'sa'):
        text = _safe(m.realize, reduced, False)
    elif lang == 'id':
        text = _safe(indonesian.realize, reduced)
    elif lang == 'tl' and not clause.copula:   # 選んだ焦点は文ごとに変わるので形に添える (nakita (対象焦点))
        voice, root, _ = tagalog._focus(clause)
        text = _safe(tagalog.verb_form, clause, voice, root) or _safe(tagalog.realize, reduced)
        text = ('hindi ' if clause.negated else '') + text + ' (%s)' % TL_FOCUS.get(voice, voice)
    else:
        text = _safe(m.realize, reduced)
    text = text.split('\n')[0].strip(' .।')
    if lang not in ('ja', 'kobun') and not (lang == 'tl' and not clause.copula):
        for role, np in kept:
            if role != 'complement':
                text = _without(text, _np_form(lang, role, np, clause)[0])
    how = COPULA_HOW[lang] if clause.copula and clause.role('complement') else PREDICATE_HOW[lang]
    return _display(lang, text), how


def _ain_bo_predicate(lang, clause, reduced):
    """アイヌ語・チベット語の述語 (繋辞の文は主語を除いた節の残り)"""
    subject = (clause.role('subject') or [None])[0]
    if lang == 'ain':
        if clause.copula:
            words = ainu.realize(reduced)
            head = ainu.noun_phrase(subject) if subject is not None else []
            return ' '.join(words[len(head):] if words[:len(head)] == head else words)
        return ' '.join(ainu.verb_words(clause, subject, (clause.role('object') or [None])[0]))
    if clause.copula:
        text = tibetan.realize(reduced)
        head = tibetan.noun_phrase(subject) if subject is not None else ''
        return _bo(text[len(head):].strip() if head and text.startswith(head) else text)
    verb = tibetan.verb_word(clause)
    return _bo(verb if clause.mood == 'imperative' else tibetan.particle(verb, 'fin'))


def _tuple_predicate(lang, clause, reduced):
    """ペルシア語・ヒンディー語・ウルドゥー語の述語の語の列 (繋辞の文は主語を除いた節の残り)"""
    subject = (clause.role('subject') or [None])[0]
    if clause.copula:
        words = (persian.realize if lang == 'fa' else hindi.realize)(reduced)
        if subject is not None:
            head = persian.noun_phrase(subject) if lang == 'fa' else hindi.noun_phrase(subject)
            if words[:len(head)] == head:
                words = words[len(head):]
        return words
    if lang == 'fa':
        person, number = persian._person(clause)
        return persian.verb_words(clause, person, number)
    words, _ = hindi.verb_words(clause, subject, (clause.role('object') or [None])[0])
    return words


def _without(text, part):
    """文から名詞句の形を外す (文頭の大文字も)。見つからなければそのまま"""
    if not part or part.startswith('('):
        return text
    for variant in (part, part[:1].upper() + part[1:]):
        k = text.find(variant)
        if k >= 0 and (k == 0 or text[k - 1] == ' ') and text[k + len(variant):k + len(variant) + 1] in ('', ' ', ','):
            return ' '.join((text[:k] + text[k + len(variant):]).split())
    return text


def split_supplied(lang, text):
    """述語の形の頭の、補った主語の代名詞 (he saw → (he, saw))。無ければ ('', text)"""
    head, _, rest = text.partition(' ')
    if lang in SUPPLIED and head.lower() in SUPPLIED[lang] and rest:
        return head, rest
    return '', text


SUPPLIED = {'en': {'he', 'she', 'it', 'they', 'i', 'you', 'we'}, 'ru': {'он', 'она', 'оно', 'они', 'я', 'ты', 'мы', 'вы'},
            'tl': {'siya', 'sila', 'ako', 'ikaw', 'kami', 'kayo', 'niya', 'nila', 'ko', 'mo'},
            'id': {'dia', 'mereka', 'saya', 'kamu', 'kami', 'kalian'},
            'he': {'הוּא', 'הִיא', 'הֵם', 'הֵן', 'אֲנִי', 'אֲנַחְנוּ', 'אַתָּה', 'אַתֶּם'}}


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
    copular = clause.copula and bool(clause.role('complement'))
    # 述語の語の語義の幅 (繋辞の文は補語の形容詞)
    complement = (clause.role('complement') or [None])[0] if copular else None
    if complement is not None and complement.head is not None and not complement.members:
        predicates = _with_senses(predicates, complement.head, complement.head.pos)
    elif not clause.copula:
        predicates = _with_senses(predicates, clause.verb, 'verb')
    head = ' '.join(x for x in (tense, voice, '否定' if clause.negated else '') if x)
    out = [('述語 (%s)' % (head if not copular else '繋辞 + 補語、' + head), predicates)]
    if not clause.role('subject') and clause.mood not in ('infinitive', 'imperative') and not clause.copula:
        if 'tl' in langs:   # タガログ語の補う代名詞は焦点で形が決まる (対象焦点なら ng の形 niya)
            voice = _safe(lambda c: tagalog._focus(c)[0], clause)
            key = ({1: 'ego', 2: 'tū'}.get(clause.person, 'is'), clause.number)
            forms = tagalog.PRONOUNS.get(key, ('siya', 'niya', 'kaniya'))
            supplied['tl'] = forms[0] if voice == 'actor' else forms[1]
        out.append(('主語 (書かれていない)', {lang: (supplied[lang], PRO_DROP.get(lang) or
                                                    getattr(MODULES[lang], 'PRO_DROP_HOW', '')) for lang in langs}))
    for role, np in clause.args:
        if copular and role == 'complement':   # 補語は述語の行に (繋辞と合わせて。語形は主語に一致)
            continue
        name = ROLE_NAMES.get(role, role) + (' (同格)' if role == 'address' and np.apposed else '')
        if role == 'prep' and np.prep is not None:
            name = '前置詞句 (%s + %s)' % (np.prep.lemma, CASE_NAMES.get(np.case, np.case))
        cells = {lang: np_form(lang, role, np, clause) for lang in langs}
        if np.head is not None and not np.members and role != 'address':
            cells = _with_senses(cells, np.head, 'noun' if np.head.pos not in ('adj', 'participle') else 'adj')
        out.append((name, cells))
    return out


SENSES_SEPARATOR = '／'


def _with_senses(cells, lex, pos):
    """手段の欄に、選んだ語の辞書の語義の幅を添える (pirka「良い・きれいだ …」。訳語は一対一に対応しない)"""
    from .senses import note
    out = {}
    for lang, (form, how) in cells.items():
        extra = note(lang, lex, pos) if form and not form.startswith('(') else ''
        out[lang] = (form, (how + SENSES_SEPARATOR + extra) if how and extra else (how or extra))
    return out


def parse_langs(value):
    """--compare の値 (la,grc,ja / all) → 言語の符号の列。知らない符号は ValueError"""
    if value.strip() in ('all', ''):   # データの要る言語 (アラビア語・ヘブライ語・ペルシア語・ヒンディー語・ウルドゥー語) は、あるものだけ
        return [lang for lang in LANGS if not hasattr(MODULES[lang], 'available') or
                lang not in ('ar', 'he', 'fa', 'hi', 'ur', 'ain', 'bo') + GENERIC or
                MODULES[lang].available()]
    langs = [v.strip() for v in value.split(',') if v.strip()]
    unknown = [lang for lang in langs if lang not in LANGS]
    if unknown:
        raise ValueError('--compare の知らない言語: %s (使える言語: %s、all で全部)' % (', '.join(unknown), ' '.join(LANGS)))
    return langs


def prepare(langs):
    """比べる言語の生成に要るもの (ラテン語の辞書は、ほかの言語のコマンドでは読み込んでいない)"""
    from dragoman.latin import latindic
    if not latindic.LatinDic.dic:
        latindic.load()


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
