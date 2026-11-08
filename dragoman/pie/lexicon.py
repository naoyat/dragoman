#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 印欧祖語 (シュライヒャーの表記) の手作りの辞書: シュライヒャーの寓話 (1868) の語
#
#   LEMMAS: シュライヒャーの見出し (語幹・語根) → 訳語・今の再建形 (喉音のある表記)・ラテン語・ギリシア語・サンスクリットの同源の語
#   FORMS:  本文の語形 → 読みのリスト (見出し, 品詞, 格・数・性 / 動詞の時制・人称 …)
#
# シュライヒャーの表記は19世紀の再建 (喉音が無い、母音は a・i・u の体系、v は今の *w、j は *y、k の口蓋音を区別しない)。
# 今の再建形は見出しの形 (名詞は単数主格、動詞は語根) で、語形ごとの今の形は載せない (説によって違うところが多い)
#

# 見出し → (訳語, 今の再建形, [(言語, 同源の語), ...])
LEMMAS = {
    'avi': ('羊', '*h₂ówis', [('la', 'ovis'), ('grc', 'ὄϊς'), ('sa', 'ávi-')]),
    'akva': ('馬', '*h₁éḱwos', [('la', 'equus'), ('grc', 'ἵππος'), ('sa', 'áśva-')]),
    'ka': ('と', '*-kʷe', [('la', '-que'), ('grc', 'τε'), ('sa', 'ca')]),
    'ja': ('(関係代名詞)', '*yós', [('grc', 'ὅς'), ('sa', 'yá-')]),
    'varnā': ('羊毛', '*wĺ̥h₂neh₂', [('la', 'lāna'), ('grc', 'λῆνος'), ('sa', 'ūrṇā')]),
    'na': ('〜ない', '*ne', [('la', 'ne-'), ('sa', 'na')]),
    'as': ('ある', '*h₁es-', [('la', 'est'), ('grc', 'ἐστί'), ('sa', 'asti')]),
    'dark': ('見る', '*derḱ-', [('grc', 'δέρκομαι'), ('sa', 'dadarśa')]),
    'ta': ('それ', '*só, *tód', [('grc', 'τό'), ('sa', 'tad')]),
    'vāgha': ('車', '*weǵʰ-', [('la', 'vehō'), ('grc', 'ὄχος'), ('sa', 'vahati')]),
    'vagh': ('引く', '*weǵʰ-', [('la', 'vehō'), ('grc', 'ὄχος'), ('sa', 'vahati')]),
    'garu': ('重い', '*gʷréh₂us', [('la', 'gravis'), ('grc', 'βαρύς'), ('sa', 'guru-')]),
    'bhāra': ('荷', '*bʰóros', [('grc', 'φόρος'), ('sa', 'bhāra-')]),
    'bhar': ('運ぶ', '*bʰer-', [('la', 'ferō'), ('grc', 'φέρω'), ('sa', 'bharati')]),
    'magha': ('大きい', '*méǵh₂s', [('la', 'magnus'), ('grc', 'μέγας'), ('sa', 'mahā-')]),
    'manu': ('人', '*mánus', [('sa', 'manu-')]),
    'āku': ('速く', '*h₁ōḱús', [('la', 'ōcior'), ('grc', 'ὠκύς'), ('sa', 'āśu-')]),
    'vak': ('言う', '*wekʷ-', [('la', 'vōx'), ('grc', 'ἔπος'), ('sa', 'vavāca')]),
    'kard': ('心', '*ḱḗr', [('la', 'cor'), ('grc', 'καρδία'), ('sa', 'hṛd-')]),
    'agh': ('痛む', '*h₂eǵʰ-', [('la', 'angō'), ('grc', 'ἄχος'), ('sa', 'aghá-')]),
    'ma': ('私', '*me', [('la', 'mihi'), ('grc', 'μοι'), ('sa', 'me')]),
    'vid': ('見る', '*weyd-', [('la', 'videō'), ('grc', 'οἶδα'), ('sa', 'veda')]),
    'ag': ('駆る', '*h₂eǵ-', [('la', 'agō'), ('grc', 'ἄγω'), ('sa', 'ajati')]),
    'kru': ('聞く', '*ḱlew-', [('la', 'clueō'), ('grc', 'κλῦθι'), ('sa', 'śrudhi')]),
    'vas': ('私たち', '*wos', [('la', 'vōs'), ('sa', 'vas')]),
    'pati': ('主人', '*pótis', [('la', 'potis'), ('grc', 'πόσις'), ('sa', 'pati-')]),
    'kar': ('作る', '*kʷer-', [('sa', 'kṛṇoti')]),
    'sva': ('自分', '*swé', [('la', 'sē'), ('grc', 'ἕ'), ('sa', 'sva-')]),
    'gharma': ('暖かい', '*gʷʰermós', [('la', 'formus'), ('grc', 'θερμός'), ('sa', 'gharmá-')]),
    'vastra': ('衣服', '*wéstrom', [('la', 'vestis'), ('sa', 'vastra-')]),
    'agra': ('野', '*h₂éǵros', [('la', 'ager'), ('grc', 'ἀγρός'), ('sa', 'ájra-')]),
    'bhug': ('逃げる', '*bʰewg-', [('la', 'fugiō'), ('grc', 'φεύγω')]),
}


def _n(lemma, case, number, gender, pos='noun', **extra):
    return dict(lemma=lemma, pos=pos, cng=[(case, number, gender)], **extra)


def _v(lemma, tense, person, number, mood='indicative', voice='active', **extra):
    return dict(lemma=lemma, pos='verb', tense=tense, mood=mood, voice=voice, person=person, number=number, **extra)


def _p(lemma, tense, case, number, gender, voice='active'):
    return dict(lemma=lemma, pos='participle', tense=tense, voice=voice, cng=[(case, number, gender)])


# 本文の語形 (小文字) → 読みのリスト
FORMS = {
    'avis': [_n('avi', 'Nom', 'sg', 'f')],
    'avai': [_n('avi', 'Voc', 'sg', 'f')],
    'avisāms': [_n('avi', 'Gen', 'pl', 'f')],
    'avibhjams': [_n('avi', 'Dat', 'pl', 'f')],
    'akvāsas': [_n('akva', 'Nom', 'pl', 'm')],
    'akvams': [_n('akva', 'Acc', 'pl', 'm')],
    'akvabhjams': [_n('akva', 'Dat', 'pl', 'm')],
    'ka': [dict(lemma='ka', pos='conj')],
    'jasmin': [_n('ja', 'Loc', 'sg', 'f', pos='pronoun', desc='関係代名詞')],
    'varnā': [_n('varnā', 'Nom', 'sg', 'f')],
    'varnām': [_n('varnā', 'Acc', 'sg', 'f')],
    'na': [dict(lemma='na', pos='adv')],
    'ast': [_v('as', 'imperfect', 3, 'sg', exist=True)],   # 存在の「ある」(繋辞にしない: 羊毛が無かった)
    'asti': [_v('as', 'present', 3, 'sg')],
    'dadarka': [_v('dark', 'perfect', 3, 'sg')],
    'tam': [_n('ta', 'Acc', 'sg', 'm', pos='pronoun')],
    'tat': [_n('ta', 'Acc', 'sg', 'n', pos='pronoun')],
    'vāgham': [_n('vāgha', 'Acc', 'sg', 'm')],
    'garum': [_n('garu', 'Acc', 'sg', 'm', pos='adj')],
    'vaghantam': [_p('vagh', 'present', 'Acc', 'sg', 'm')],
    'bhāram': [_n('bhāra', 'Acc', 'sg', 'm')],
    'magham': [_n('magha', 'Acc', 'sg', 'm', pos='adj')],
    'manum': [_n('manu', 'Acc', 'sg', 'm')],
    'manus': [_n('manu', 'Nom', 'sg', 'm')],
    'āku': [dict(lemma='āku', pos='adv')],
    'bharantam': [_p('bhar', 'present', 'Acc', 'sg', 'm')],
    'vavakat': [_v('vak', 'perfect', 3, 'sg')],
    'vavakant': [_v('vak', 'perfect', 3, 'pl')],
    'kard': [_n('kard', 'Nom', 'sg', 'n')],
    'aghnutai': [_v('agh', 'present', 3, 'sg', voice='middle')],
    'mai': [_n('ma', 'Dat', 'sg', 'm', pos='pronoun')],
    'vidanti': [_p('vid', 'present', 'Dat', 'sg', 'm')],
    'agantam': [_p('ag', 'present', 'Acc', 'sg', 'm')],
    'krudhi': [_v('kru', 'present', 2, 'sg', mood='imperative')],
    'vividvant': [_p('vid', 'perfect', 'Dat', 'pl', 'm')],
    'svas': [_n('vas', 'Dat', 'pl', 'm', pos='pronoun')],
    'patis': [_n('pati', 'Nom', 'sg', 'm')],
    'karnauti': [_v('kar', 'present', 3, 'sg')],
    'svabhjam': [_n('sva', 'Dat', 'sg', 'm', pos='pronoun')],
    'gharmam': [_n('gharma', 'Acc', 'sg', 'n', pos='adj')],
    'vastram': [_n('vastra', 'Acc', 'sg', 'n')],
    'kukruvants': [_p('kru', 'perfect', 'Nom', 'sg', 'f')],
    'agram': [_n('agra', 'Acc', 'sg', 'm')],
    'bhugat': [_v('bhug', 'aorist', 3, 'sg')],
}

# 動詞の前に離して書いた加音 ā (過去の印: ā ast「あった」、ā vavakat「言った」)
AUGMENT = 'ā'
