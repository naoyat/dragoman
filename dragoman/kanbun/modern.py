#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文の現代語訳: 書き下しと同じ要素の列 (kundoku.Elem。読む順・後ろの語が求めた形) から、現代語に組み立て直す
#
#   用言は文語の終止形から現代語の見出しに (習ふ → 習う、改む → 改める、楽し → 楽しい。古語は中古和文UniDic の語彙素:
#   罔し → 暗い)、助動詞は現代語の働きに: ず → ない、べし → ことができる (可) / べきだ (当・応・宜・須)、しむ → せる、
#   る・らる → れる・られる、欲す → たいと思う、勿かれ → てはならない、ごとし → ようだ、也 → のだ・である、乎 → か
#   句法: ずや → ではないか (詠嘆)、疑問の副詞 + ん → どうして〜だろうか (反語)、ずんば → なければ、
#   已然形 + ば (則) → ば、而 → て、ずして → ないで
#
from dragoman.kobun.modernize import Modern, Derived
from . import kundoku, readings

# 文語の終止形 (新字体) → 現代語 (UniDic の語彙素では外れるもの・漢文でよく使う意味)
MODERN = {'出づ': '出る', '破る': '破れる', '死す': '死ぬ', '施す': '施す', '懼る': '恐れる', '有り': 'ある', '在り': 'ある', '来たる': '来る',
          '欲す': '望む', '長ず': '優れる', '生ず': '生じる', '信ず': '信じる', '説ばし': 'うれしい', '曰ふ': '言う',
          '謂ふ': '言う', '云ふ': '言う', '居り': 'いる', '罔し': '道理が分からない', '殆し': '危うい', '温む': '温める',
          '誨ふ': '教える', '釈つ': '捨てる', '冀ふ': '願う', '鬻ぐ': '売る', '陥す': '突き通す', '敏す': '素早くする',
          '訥す': '口が重い', '如く': '及ぶ', '若く': '及ぶ', '然り': 'そうだ', '安んず': '安心する', '過つ': '間違える',
          '悪む': '憎む', '因る': '基づく', '彫む': 'しぼむ', '慍る': '怒る', '省みる': '反省する', '学問す': '学問する',
          '為る': 'なる', '爲る': 'なる', '可なり': 'よい', '已む': 'やめる', '訥す': 'ゆっくり話す', '敏す': 'すばやく行う'}
# 同じ終止形で活用の型の違う語: (終止形, 型) → 現代語 (苦し: ク にがし → 苦い、シク くるし → 苦しい)
MODERN_KIND = {('苦し', 'ク'): '苦い', ('苦し', 'シク'): '苦しい'}
# 用言の名詞の形 (是を過ちと謂ふ)
NOUNS = {'過つ': '過ち'}
# 名詞に読む用言 (readings.NOMINAL_VERBS) の現代語
NOMINAL_VERBS = {'過ぎたる': '過ぎたこと'}
# 最後に置き換える言い回し
PHRASES = {'何如': 'どうだろうか', '如何': 'どうしようか'}
# 代名詞・副詞などの現代語
PRONOUNS = {'之': 'これ', '我': '私', '吾': '私', '予': '私', '余': '私', '朕': '私', '汝': 'あなた', '爾': 'あなた',
            '女': 'あなた', '子': 'あなた', '其': 'それ', '其れ': 'それ', '此': 'これ', '此れ': 'これ', '是': 'これ',
            '是れ': 'これ', '斯': 'これ', '斯れ': 'これ', '彼': 'あの人', '己': '自分', '自ら': '自分', '何': '何',
            '誰': '誰', '焉': 'これ', '夫れ': 'そもそも'}
DETERMINERS = {'其の': 'その', '此の': 'この', '是の': 'この', '彼の': 'あの', '斯の': 'この', '夫の': 'あの'}
ADVERBS = {'亦た': 'また', '又': 'また', '復た': '再び', '則ち': '', '未だ': 'まだ', '必ず': '必ず', '皆': 'みな',
           '嘗て': '以前', '曾て': '以前', '甚だ': 'たいへん', '獨り': 'ひとり', '且つ': 'その上', '既に': 'もう',
           '已に': 'もう', '方に': 'ちょうど', '乃ち': 'そこで', '卽ち': 'すぐに', '即ち': 'すぐに', '遂に': 'とうとう',
           '終に': 'とうとう', '共に': '一緒に', '倶に': '一緒に', '尙ほ': 'それでもやはり', '徒らに': 'むだに',
           '豈に': 'どうして', '寧ろ': 'むしろ', '唯だ': 'ただ', '惟だ': 'ただ', '只だ': 'ただ', '但だ': 'ただ',
           '果たして': '思ったとおり', '敢へて': 'あえて', '能く': '', '頗る': 'たいへん', '殆ど': 'ほとんど',
           '蓋し': '思うに', '竊かに': 'ひそかに', '故に': 'だから', '何ぞ': 'どうして', '安くんぞ': 'どうして',
           '焉くんぞ': 'どうして', '惡くんぞ': 'どうして', '誰か': '誰が', '孰れか': 'どちらが', '奚ぞ': 'どうして',
           '胡ぞ': 'どうして', '曷ぞ': 'どうして', '盍ぞ': 'どうして', '縱ひ': 'たとえ', '苟くも': 'かりにも', '若し': 'もし',
           '如し': 'もし', '時に': '時々', '先づ': 'まず', '固より': 'もとより', '凡そ': 'およそ', '俄かに': '急に',
           '忽ち': 'たちまち', '暫く': 'しばらく', '再び': '再び', '三たび': '三度', '專ら': 'ひたすら', '頻りに': 'しきりに',
           '將に': '', '且に': '', '當に': '当然', '應に': 'きっと', '宜しく': 'ぜひ', '須らく': 'ぜひ', '猶ほ': 'ちょうど',
           '由ほ': 'ちょうど', '以て': 'それで', '曰はく': '言うことには', '肯へて': '進んで', '多く': '多く',
           '善く': 'うまく', '是に於いて': 'そこで', '是を以て': 'こういうわけで', '何如': 'どうか', '如何': 'どうか'}
PARTICLES = {'は': 'は', 'を': 'を', 'に': 'に', 'の': 'の', 'が': 'の', 'と': 'と', 'より': 'から', 'をして': 'に',
             'を以て': 'で', 'の爲に': 'のために', 'の為に': 'のために', 'に因りて': 'によって', 'に至るまで': 'まで',
             'に向かひて': 'に向かって', 'の如く': 'のように', 'に在りて': 'にいて'}
COMPARE = 'よりも'


def _hiragana_modern(text):
    """歴史的仮名遣いの語尾を現代仮名遣いに (習は → 習わ、思ひ → 思い)"""
    return text.replace('ゐ', 'い').replace('ゑ', 'え').replace('を', 'お')


def modern_word(pred):
    """Predicate → (現代語の見出し, Modern の種類 verb / adj / fixed)"""
    base = readings.shinjitai(pred.base)
    if (base, pred.kind) in MODERN_KIND:
        return MODERN_KIND[base, pred.kind], 'adj'
    if base in MODERN:
        word = MODERN[base]
        return word, 'adj' if word.endswith('い') and pred.adjective else 'verb'
    lemma = _unidic_lemma(base, pred)
    if lemma == base and pred.kind == 'サ変':   # 晩成す の 成す (四段の なす でなく 成する)
        lemma = None
    if lemma:
        return lemma, 'adj' if pred.adjective else 'verb'
    kind = pred.kind
    if kind in ('ク', 'シク'):
        return base[:-1] + 'い' if kind == 'ク' else base + 'い', 'adj'
    if kind == 'ナリ':
        return base[:-2] if base.endswith('なり') else base, 'fixed'
    if kind == 'ラ変':
        return base[:-1] + 'る', 'verb'
    if kind == 'サ変':
        return base[:-1] + 'する', 'verb'
    if kind == 'ザ変':
        return base[:-1] + 'じる', 'verb'
    if kind in ('上二', '下二'):
        stem = readings.shinjitai(pred.forms[1])
        stem = stem[:-1] + {'ひ': 'い', 'へ': 'え'}.get(stem[-1], stem[-1])
        return stem + 'る', 'verb'
    if kind == '四段' and base.endswith('ふ'):
        return base[:-1] + 'う', 'verb'
    return base, 'verb'


def _unidic_lemma(base, pred):
    """中古和文UniDic の語彙素 (罔し → 暗い、謂ふ → 言う)。1語にならない・現代語でない形は使わない"""
    from dragoman.kobun import mecab
    if not mecab.available():
        return None
    tokens = mecab.parse(base)
    if len(tokens) != 1 or tokens[0].pos not in ('動詞', '形容詞'):
        return None
    lemma = tokens[0].lemma
    if lemma.endswith(('する', 'りる', 'でる')) and pred.kind != 'サ変' or lemma.endswith('する') and len(lemma) > 3:
        return None
    if (tokens[0].pos == '形容詞') != pred.adjective or not lemma or lemma == base:
        return lemma if lemma == base and lemma[-1] in 'うくぐすつぬぶむる' else None
    return lemma


def _plain(m):
    return m.text()


def _conditional(m):
    """仮定・確定の 〜ば (学べば・思わなければ・暗ければ)"""
    if m.kind == 'adj':
        return m.prefix + m.last[:-1] + 'ければ'
    if m.kind == 'verb':
        v = m.last
        if isinstance(v, Derived) or v.endswith(('る',)) and Modern.masu_stem(v) == v[:-1]:
            return m.prefix + v[:-1] + 'れば'
        row = {'う': 'え', 'く': 'け', 'ぐ': 'げ', 'す': 'せ', 'つ': 'て', 'ぬ': 'ね', 'ぶ': 'べ', 'む': 'め', 'る': 'れ'}
        return m.prefix + v[:-1] + row.get(v[-1], v[-1]) + 'ば'
    return m.text() + 'ならば'


def _connect(m, used, nxt):
    """述語の後ろの形 (書き下しで後ろの語が求めた形 used) に合わせた現代語"""
    suffix = used.suffix if used else ''
    form = used.form if used else '終止'
    if nxt is not None and nxt.kind == 'particle' and nxt.text == 'と':
        return NOUNS.get(m.base, m.text())
    if suffix in ('て',):
        return m.final('te')
    if suffix == 'して':
        return m.prefix + 'ないで' if m.last == 'ない' else m.final('te')
    if suffix == 'ば':
        return _conditional(m)
    if suffix == 'んば':
        return _conditional(m)
    if suffix == 'ん':
        return (m.prefix + Modern.volitional(m.last) if m.kind == 'verb' else m.text() + 'だろう') + 'か'
    if form == '連用' and not suffix:
        if m.kind == 'adj':   # 形容詞の連用中止 (老いやすく、学は成りにくい)
            return m.final('adverbial')
        if nxt is not None and nxt.kind == 'punct':
            return m.text()
        return m.final('te')
    if suffix in ('と',):
        return m.text() + ('だ' if m.kind == 'fixed' and not m.text().endswith('だ') else '') + 'と'
    if suffix in ('を', 'に', 'が', 'の'):
        return m.text() + 'こと' + {'が': 'が', 'の': 'の'}.get(suffix, suffix)
    if form == '連体' and m.kind == 'fixed':
        return m.text() + 'な'
    if m.kind == 'fixed' and not m.applied and (nxt is None or nxt.kind == 'punct'):
        return m.text() + 'だ'
    return m.text()


def _apply(m, aux, following):
    """助動詞 1つを現代語の Modern に重ねる"""
    forms = aux.forms
    f = aux.token.form if aux.token is not None else ''
    if forms == kundoku.NEG:
        if following and following[0].kind == 'aux' and following[0].token is not None and \
                following[0].token.form in ('乎', '哉', '與', '邪', '耶', '歟'):
            if m.rhetorical:   # 豈に〜ずや: どうして〜ないことがあろうか (反語)
                m.negative()
                m.attach('ことがあろう', 'fixed')
            else:
                m.attach('ではない', 'adj')
            return 'zuya'
        m.negative()
    elif forms == kundoku.BESHI:
        if f == '可' or f not in ('當', '應', '宜', '須'):
            if following and following[0].forms == kundoku.NEG:
                m.attach_potential()
            else:
                m.attach_potential()
        else:
            m.attach('べきだ', 'fixed')
    elif forms == kundoku.SHIMU:
        if m.kind == 'verb':
            stem = Modern.neg_stem(m.last)
            m.last = Derived(stem + ('せる' if stem[-1:] in 'かがさたなばまらわ' else 'させる'))
    elif forms is None:   # 受身
        if m.kind == 'verb':
            stem = Modern.neg_stem(m.last)
            m.last = Derived(stem + ('れる' if stem[-1:] in 'かがさたなばまらわ' else 'られる'))
    elif f == '欲':
        if m.kind == 'verb':
            m.prefix += Modern.masu_stem(m.last)
            m.last, m.kind = 'たいと思う', 'verb'
    elif f in ('勿', '毋', '無') and forms and forms[0].endswith('かれ'):
        if m.kind == 'verb':
            m.prefix += Modern.te(m.last)
            m.last, m.kind = 'はならない', 'fixed'
    elif f in ('莫', '無'):
        m.attach('ものはない', 'fixed')
    elif f == '非':
        m.attach('のではない' if m.kind != 'fixed' else 'ではない', 'adj')
    elif forms == kundoku.GOTOSHI:
        m.attach(('の' if m.kind == 'fixed' else '') + 'ようだ', 'fixed')
    elif forms == kundoku.NTOSU:
        if m.kind == 'verb':
            m.prefix += Modern.volitional(m.last)
            m.last, m.kind = 'とする', 'verb'
    elif f in ('易', '難'):   # 老い易し → 老いやすい、成り難し → 成りにくい
        if m.kind == 'verb':
            m.prefix += Modern.masu_stem(m.last)
            m.last, m.kind = 'やすい' if f == '易' else 'にくい', 'adj'
    elif f == '所':
        m.attach('こと', 'fixed')
    elif f == '雖':
        m.attach('といっても', 'fixed')
    elif f == '得':
        m.attach_potential()
    elif f == '足':
        m.attach('のに十分だ', 'fixed')
    elif forms == kundoku.NARI:
        m.attach('のだ' if m.kind != 'fixed' else 'である', 'fixed')
    elif forms and forms[0] in ('か',):
        m.attach('か', 'fixed')
    elif forms and forms[0] == 'かな':
        m.attach('なあ', 'fixed')
    elif forms and forms[0] == 'のみ':
        m.attach('だけだ', 'fixed')
    elif f == '盍':
        m.negative()
        m.attach('のか', 'fixed')
    return None


def _noun_text(e):
    text = e.text
    if e.token is not None and e.token.upos == 'PRON':
        return PRONOUNS.get(text, PRONOUNS.get(e.token.form, readings.shinjitai(text)))
    return NOMINAL_VERBS.get(text, readings.shinjitai(text))


def translate(elems):
    """書き下しの要素の列 (kundoku.render の後) → 現代語訳"""
    out = []
    rhetorical = any(e.kind == 'text' and e.text in ('豈に', '何ぞ', '安くんぞ', '焉くんぞ') for e in elems)
    elems = [e for e in elems if not (e.kind == 'boundary' and e.need is not kundoku.END)]
    n = len(elems)
    i = 0
    while i < n:
        e = elems[i]
        if e.kind == 'drop':
            i += 1
            continue
        if e.kind == 'boundary':   # 続く節 (parataxis): 読点で区切る
            if out and not out[-1].endswith('、'):
                out.append('、')
            i += 1
            continue
        if e.kind == 'punct':
            out.append(e.text)
            i += 1
            continue
        if e.kind == 'particle':
            text = PARTICLES.get(e.text, e.text)
            if e.text == 'より' and _comparative(elems, i):
                text = COMPARE
            if out and out[-1].endswith(('は', 'を', 'に', 'の', 'と', 'が')) and text and out[-1][-1:] == text[:1]:
                text = ''
            if i > 0 and elems[i - 1].kind in ('pred', 'aux') and text in ('を', 'に', 'が', 'は'):
                text = 'こと' + text   # 新しいことを知る
            out.append(text)
            i += 1
            continue
        if e.kind == 'text' and not (i + 1 < n and elems[i + 1].kind == 'aux' and e.token is not None and
                                     e.token.upos == 'NOUN'):
            text = ADVERBS.get(e.text, DETERMINERS.get(e.text, readings.shinjitai(e.text)))
            if e.text == '曰はく':
                if out and out[-1] and not out[-1].endswith(('は', 'が', 'を', 'に')):
                    out[-1] += 'が'
            if e.text == '能く':
                _mark_potential(elems, i)
            if e.text == '以て' and e.token is not None and e.token.rel != 'fixed' and out and out[-1].endswith('を'):
                out[-1] = out[-1][:-1] + 'で'   # 子の矛を以て → あなたの矛で
                text = ''
            out.append(text)
            i += 1
            continue
        # 述語のまとまり: 用言 (または体言) + 後ろに続く助動詞
        if e.kind == 'pred':
            word, kind = modern_word(e.pred)
            m = Modern(word, kind)
            m.base = readings.shinjitai(e.pred.base)
            if getattr(e, 'potential', False):
                m.attach_potential()
        elif e.kind == 'aux':
            m = Modern('', 'fixed')
            i -= 1
        else:   # noun / text の体言
            word = _noun_text(e) if e.kind == 'noun' else readings.shinjitai(e.text)
            if e.token is not None and e.token.form == '子' and _subject_of_say(elems, i):
                word = '先生'
            joiner = e.used.noun if e.used else ''
            if not (i + 1 < n and elems[i + 1].kind == 'aux'):
                joiner = {'なら': '', 'に': 'に', 'と': 'と', 'の': 'の', 'が': 'が', 'を': 'を', 'こと': ''}.get(joiner, '')
                if not joiner and e.kind == 'noun' and i + 1 < n and elems[i + 1].kind == 'pred':
                    joiner = 'が'   # 朋有り → 友がある
                out.append(word + joiner)
                i += 1
                continue
            m = Modern(word, 'fixed')
        m.applied = False
        m.rhetorical = rhetorical
        if not hasattr(m, 'base'):
            m.base = ''
        j = i + 1
        skip_neg = False
        last = e
        while j < n and elems[j].kind == 'aux':
            aux = elems[j]
            if skip_neg and aux.forms == kundoku.NEG:
                j += 1
                continue
            r = _apply(m, aux, elems[j + 1:])
            m.applied = True
            last = aux
            if r == 'zuya':
                j += 2   # ず + や: ではないか
                m.attach('か', 'fixed')
                last = elems[j - 1]
                continue
            j += 1
        nxt = elems[j] if j < n else None
        out.append(_connect(m, last.used, nxt))
        i = j
    text = ''.join(out).replace('、、', '、').replace('、。', '。')
    for a, b in PHRASES.items():
        text = text.replace(a, b)
    return text


def _comparative(elems, i):
    """より の後ろが形容詞 (比較: 藍よりも青い)"""
    for e in elems[i + 1:]:
        if e.kind == 'pred':
            return e.pred.adjective
        if e.kind in ('noun', 'punct'):
            return False
    return False


def _mark_potential(elems, i):
    for e in elems[i + 1:]:
        if e.kind == 'pred':
            e.potential = True
            return
        if e.kind == 'punct':
            return


def _subject_of_say(elems, i):
    return i + 1 < len(elems) and elems[i + 1].kind == 'text' and elems[i + 1].text == '曰はく'
