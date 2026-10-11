#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 解析の結果 (格の枠) から文を作る: ラテン語に戻す (手作りの辞書だけで) と、英語にする (英語の訳語の表があれば)
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths  # noqa: E402
from dragoman.latin import latindic, analyzer  # noqa: E402
from dragoman.generate import frame, english, latin, russian, sanskrit, greek, indonesian, tagalog, arabic, hebrew, persian, hindi, ainu, tibetan, japanese, kobun  # noqa: E402
from dragoman.generate.frame import Lex  # noqa: E402

_saved = None


def setUpModule():
    global _saved
    latindic.load()
    _saved = (latindic.LatinDic.use_wiktionary, analyzer.USE_TAGGER)
    latindic.LatinDic.use_wiktionary = False
    analyzer.USE_TAGGER = False


def tearDownModule():
    latindic.LatinDic.use_wiktionary, analyzer.USE_TAGGER = _saved


def clauses(text):
    analyses = list(analyzer.analyze_text(text))
    assert len(analyses) == 1, analyses
    return frame.frames(analyses[0])


class FrameTestCase(unittest.TestCase):
    def test_roles(self):
        c, = clauses('Puella rosam pulchram in hortō videt.')
        self.assertEqual((c.verb.lemma, c.tense, c.person, c.number), ('videō', 'present', 3, 'sg'))
        self.assertEqual([(r, np.head.lemma) for r, np in c.args],
                         [('subject', 'puella'), ('object', 'rosa'), ('prep', 'hortus')])
        rose = c.role('object')[0]
        self.assertEqual([m.lemma for m in rose.modifiers], ['pulcher'])
        self.assertEqual(c.role('prep')[0].prep.lemma, 'in')

    def test_infinitive_kind(self):
        c, = clauses('Mārcus puerōs in hortō lūdere dīcit.')
        inner, = c.infinitives
        self.assertEqual((inner.verb.lemma, inner.infinitive_kind), ('lūdō', 'saying'))

    def test_pronoun_lemma(self):
        c, = clauses('Haec puella illum puerum videt.')
        self.assertEqual([m.lemma for m in c.role('object')[0].modifiers], ['ille'])


class LatinRegenerationTestCase(unittest.TestCase):
    """解析 → 文の枠 → ラテン語 で元の文に戻る"""

    def again(self, text):
        return latin.sentence(clauses(text))

    def test_same_sentence(self):
        for text in ('Puella rosam pulchram in hortō videt.',
                     'Agricola nautam nōn amat.',
                     'Puerī et puellae cantant.',
                     'Rosae līliaque flōrent.',
                     'Et puer et puella cantant.',
                     'Fīlia agricolae rosās pulchrās amat.',
                     'Haec puella illum puerum videt.',
                     'Puer ā magistrō laudātur.'):
            self.assertEqual(self.again(text), text)

    def test_word_order(self):
        # 受け手 (与格) は目的語の前に置く
        self.assertEqual(self.again('Magister librōs puerīs dat.'), 'Magister puerīs librōs dat.')

    def test_accusative_subject_of_infinitive(self):
        self.assertEqual(self.again('Magister puerōs in hortō lūdere dīcit.'),
                         'Magister puerōs in hortō lūdere dīcit.')

    def test_complement_agreement(self):
        self.assertEqual(self.again('Puellae pulchrae erant.'), 'Puellae pulchrae erant.')


class PeriphrasticTestCase(unittest.TestCase):
    def test_deponent_perfect(self):
        # 繋辞 + 形式受動態動詞の完了分詞 (prōgressus est) → 完了の能動、ふつうの動詞の分詞 → 受動
        from dragoman.generate.frame import Clause, NP
        participle = NP(Lex('prōgressus', 'participle', '', verb='prōgredior', ptense='past'))
        clause = Clause(Lex('sum', 'verb'), copula=True, args=[('complement', participle)])
        again = frame.periphrastic(clause)
        self.assertEqual((again.verb.lemma, again.tense, again.voice, again.copula, again.args),
                         ('prōgredior', 'perfect', 'active', False, []))
        participle = NP(Lex('occīsus', 'participle', '', verb='occīdō', ptense='past'))
        clause = Clause(Lex('sum', 'verb'), tense='imperfect', copula=True, args=[('complement', participle)])
        self.assertEqual((frame.periphrastic(clause).tense, frame.periphrastic(clause).voice),
                         ('past-perfect', 'passive'))


class QuestionTestCase(unittest.TestCase):
    """間接疑問: 解析で支配する動詞の格の枠 'Q' に入れ、文の枠では questions に"""

    def test_analysis_and_frame(self):
        analysis, = analyzer.analyze_text('Magister rogāvit quis cantāret.')
        self.assertEqual(len(analysis.clauses), 1)
        question, = analysis.clauses[0].predicate.case_slot['Q']
        self.assertEqual((question.word.surface, question.predicate.surface), ('quis', 'cantāret'))
        self.assertEqual(question.translate()[0][-3:], '}かを')
        main, = frame.frames(analysis)
        self.assertEqual([q.question_word for q in main.questions], ['quis'])
        self.assertEqual(latin.sentence([main]), 'Magister quis cantāret rogāvit.')

    def test_relative_is_not_a_question(self):
        # 先行詞 (性・数の一致する名詞) のすぐ後ろの quem は関係代名詞
        analysis, = analyzer.analyze_text('Puer magistrum quem puella amet videt.')
        self.assertFalse(any('Q' in c.predicate.case_slot for c in analysis.clauses))

    def test_not_a_question(self):
        # 支配する動詞が問う・知る類でなければ入れない (ubi + 接続法の時の節)
        analysis, = analyzer.analyze_text('Puer cantat ubi puella dormiat.')
        self.assertFalse(any('Q' in c.predicate.case_slot for c in analysis.clauses))


class RelativeTestCase(unittest.TestCase):
    """関係節: 先行詞の名詞に付き、関係代名詞の格を空所の役割として持つ"""

    def test_analysis(self):
        analysis, = analyzer.analyze_text('Puella puerum videt quem magister laudat.')
        self.assertEqual(len(analysis.clauses), 1)
        relative, = analysis.relatives
        self.assertEqual((relative.antecedent.surface, relative.pronoun.surface, relative.gap),
                         ('puerum', 'quem', 'Acc'))
        self.assertIn('{教師,先生が 称賛する,ほめる}少年を', analysis.clauses[0].predicate.translate()[0])

    def test_subject_gap(self):
        # 主格・対格のどちらにも読める quae は、先行詞との一致と節の空きで主格 (主語を補わない)
        analysis, = analyzer.analyze_text('Puella cantat quae in hortō sedet.')
        self.assertEqual(analysis.relatives[0].gap, 'Nom')
        self.assertTrue(analysis.clauses[0].predicate.translate()[0].startswith('{{庭}'))

    def test_relative_before_antecedent(self):
        # 先行詞より前の関係節 (相関の形): 後ろの節の指示代名詞が先行詞。日本語は「{…する}人」
        analysis, = analyzer.analyze_text('Quem puella amat, eum magister laudat.')
        relative, = analysis.relatives
        self.assertEqual((relative.antecedent.surface, relative.gap), ('eum', 'Acc'))
        self.assertIn('{少女が 愛する}人を', analysis.clauses[0].predicate.translate()[0])

    def test_connecting_relative(self):
        # 文頭の関係代名詞 + 従属の接続詞 (Quod cum …「それを … したとき」) は前の文を指す。関係節にしない
        analysis, = analyzer.analyze_text('Quod cum puella vīdisset, eum magister laudāvit.')
        self.assertEqual(analysis.relatives, [])

    def test_comparative_quam(self):
        analysis, = analyzer.analyze_text('Nēmō clārior erat quam Hector.')
        self.assertEqual(analysis.relatives, [])

    def test_latin(self):
        # 関係節は先行詞のすぐ後ろに戻す (関係節が主節の動詞の前に入った文の解析はまだできない)
        self.assertEqual(latin.sentence(clauses('Puella puerum videt quem magister laudat.')),
                         'Puella puerum quem magister laudat videt.')
        self.assertEqual(latin.sentence(clauses('Puella cantat quae in hortō sedet.')),
                         'Puella quae in hortō sedet cantat.')


class ConnectiveTestCase(unittest.TestCase):
    """文をつなぐ語・従属節の接続詞"""

    def test_frame(self):
        main, = clauses('Puella autem cantat.')
        self.assertEqual(main.connectives, ['autem'])
        sub, main = clauses('Ubi puella cantat, puer dormit.')
        self.assertEqual((sub.subordinator, sub.after_main, main.subordinator), ('ubi', False, ''))
        main, = clauses('Puer ad hortum venit ubi puella cantat.')
        garden = main.role('prep')[0]   # 名詞のすぐ後ろの ubi は関係節「〜するところの」
        self.assertEqual([(r.gap, r.relative.surface) for r in garden.relatives], [('place', 'ubi')])

    def test_latin(self):
        # 後置の語 (autem, igitur) は節の2語目に
        for text in ('Puella autem cantat.', 'Agricola igitur nautam amat.', 'Ubi puella cantat, puer dormit.'):
            self.assertEqual(latin.sentence(clauses(text)), text)

    def test_sanskrit_correlative(self):
        from dragoman.generate import connectives
        sub, main = clauses('Ubi puella cantat, puer dormit.')
        self.assertEqual(connectives.join([sub, main], ['A', 'B'], 'sa'), 'yadA A tadA B')   # yadā … tadā …
        self.assertEqual(connectives.join([sub, main], ['A', 'B'], 'en'), 'when A, B')


class EnglishMorphologyTestCase(unittest.TestCase):
    def test_verbs(self):
        self.assertEqual(english.third_singular('carry'), 'carries')
        self.assertEqual(english.third_singular('be fond of'), 'is fond of')
        self.assertEqual(english.past('see'), 'saw')
        self.assertEqual(english.past('love'), 'loved')
        self.assertEqual(english.past_participle('give'), 'given')
        self.assertEqual(english.present_participle('run'), 'running')
        self.assertEqual(english.present_participle('make'), 'making')

    def test_nouns(self):
        self.assertEqual(english.plural('rose'), 'roses')
        self.assertEqual(english.plural('city'), 'cities')
        self.assertEqual(english.plural('child'), 'children')


@unittest.skipUnless(os.path.exists(paths.data('la-en.tsv')), 'la-en.tsv が無い (tools/build_latin_english.py)')
class EnglishTestCase(unittest.TestCase):
    def english(self, text):
        return english.sentence(clauses(text))

    def test_sentences(self):
        self.assertEqual(self.english('Puella rosam pulchram in hortō videt.'),
                         'The girl sees the beautiful rose in the garden.')
        self.assertEqual(self.english('Agricola nautam nōn amat.'), 'The farmer does not love the sailor.')
        self.assertEqual(self.english('Puer ā magistrō laudātur.'), 'The boy is praised by the teacher.')
        self.assertEqual(self.english('Puellae in silvā ambulābant.'), 'The girls were walking in the forest.')

    def test_connectives(self):
        self.assertEqual(self.english('Ubi puella cantat, puer dormit.'), 'When the girl sings, the boy sleeps.')
        self.assertEqual(self.english('Puer ad hortum venit ubi puella cantat.'),
                         'The boy comes to the garden where the girl sings.')
        self.assertEqual(self.english('Puella puerum videt quem magister laudat.'),
                         'The girl sees the boy whom the teacher praises.')
        self.assertEqual(self.english('Quem puella amat, eum magister laudat.'),
                         'The teacher praises him whom the girl loves.')

    def test_indirect_question(self):
        self.assertEqual(self.english('Magister rogāvit quis cantāret.'), 'The teacher asked who was singing.')
        self.assertEqual(self.english('Rēx rogat quid puer videat.'), 'The king asks what the boy sees.')
        self.assertEqual(self.english('Puella nescit quis cantet.'), 'The girl does not know who sings.')

    def test_homographs(self):
        # 同綴の語は解析の日本語の訳語で (volō「飛ぶ」/「望む」)、決まらなければ語形と基本形で (appellō)
        self.assertEqual(english.gloss(Lex('volō', 'verb', '飛ぶ')), 'fly')
        self.assertEqual(english.gloss(Lex('volō', 'verb', '願う,欲しい')), 'wish')
        self.assertEqual(english.gloss(Lex('appellō', 'verb', '?', surface='appellābātur')), 'address as')
        self.assertEqual(english.gloss(Lex('appellō', 'participle', '?', surface='appulsa')),
                         'drive or move to')

    def test_gloss_follows_japanese(self):
        # Wiktionary の最初の訳語 (traverse) ではなく、解析の日本語「歩く」に合う walk
        self.assertEqual(english.gloss(Lex('ambulō', 'verb', '歩く')), 'walk')



@unittest.skipUnless(russian.available() and english.gloss(Lex('puella', 'noun', '少女')),
                     'pymorphy3 か ru/en-index.tsv・la-en.tsv が無い')
class RussianTestCase(unittest.TestCase):
    def russian(self, text):
        return russian.sentence(clauses(text))

    def test_cases_and_agreement(self):
        self.assertEqual(self.russian('Puella rosam pulchram in hortō videt.'), 'Девочка видит красивую розу в саду.')
        self.assertEqual(self.russian('Puellae pulchrae erant.'), 'Девочки были красивые.')

    def test_aspect_and_passive(self):
        # 完了の受動 → был + 完了体の短語尾受動分詞、動作主は造格
        self.assertEqual(self.russian('Puer ā magistrō nōn laudātus est.'), 'Мальчик не был похвален учителем.')

    def test_possessive_dative(self):
        self.assertEqual(self.russian('Mihi est liber.'), 'У меня есть книга.')


@unittest.skipUnless(sanskrit.available() and english.gloss(Lex('puella', 'noun', '少女')),
                     'vidyut か sa/en-index.tsv・la-en.tsv が無い')
class SanskritTestCase(unittest.TestCase):
    def sanskrit(self, text):
        return sanskrit.sentence(clauses(text)).split('\n')[0]

    def test_cases(self):
        # 優先表の語だけの文 (英梵辞典の表の有無で変わらない)。形容詞は名詞の性に一致 (sundaram pustakam)
        self.assertEqual(self.sanskrit('Puella librum pulchrum in hortō videt.'),
                         'bālikā sundaram pustakam udyāne paśyati ।')
        self.assertEqual(self.sanskrit('Puer ā magistrō laudātur.'), 'bālakaḥ adhyāpakena praśasyate ।')

    def test_government(self):
        # bhī「恐れる」は奪格を取る
        self.assertEqual(self.sanskrit('Agricola nautam nōn timet.'), 'kṛṣakaḥ nāvikāt na bibheti ।')

    def test_possessive(self):
        self.assertEqual(self.sanskrit('Mihi est liber.'), 'mama pustakam asti ।')

    def test_participles(self):
        # 分詞はもとの動詞の語根から: 現在 → śānac / śatṛ、完了 → kta、形式受動態 → ktavatu、動形容詞 → tavya
        def form(lemma, verb, ptense, linga='m', case='Nom'):
            return sanskrit.participle_from_lex(Lex(lemma, 'participle', '', verb=verb, ptense=ptense),
                                                linga, case, 'sg')
        self.assertEqual(form('fugiēns', 'fugiō', 'present', case='Acc'), 'palAyamAnam')
        self.assertEqual(form('laudāta', 'laudō', 'past', 'f'), 'praSastA')
        self.assertEqual(form('locūtus', 'loquor', 'past'), 'uditavAn')
        self.assertEqual(form('cantandus', 'cantō', 'future', 'n'), 'gAtavyam')



from dragoman.generate import from_japanese  # noqa: E402


@unittest.skipUnless(from_japanese.available(), 'MeCab が無い')
class JapaneseInputTestCase(unittest.TestCase):
    """日本語の文 → 文の枠 → ラテン語"""

    def latin(self, text):
        return latin.sentence(from_japanese.parse(text))

    def test_simple(self):
        self.assertEqual(self.latin('少女が庭で美しい薔薇を見た。'), 'Puella rosam pulchram in hortō vīdit.')
        self.assertEqual(self.latin('農夫は水夫を愛さない。'), 'Agricola nautam nōn amat.')

    def test_passive_agent(self):
        self.assertEqual(self.latin('少年は先生に褒められた。'), 'Puer ā magistrō laudātus est.')

    def test_relative_clause(self):
        # 連体修飾節: 空所は節の中で欠けている格 (褒める は他動詞で が があるので目的語)
        self.assertEqual(self.latin('先生が褒める少年は本を読んでいた。'), 'Puer quem magister laudat librum legēbat.')

    def test_complement_clauses(self):
        self.assertEqual(self.latin('私は少女が歌うのを見た。'), 'Puellam cantāre vīdī.')
        self.assertEqual(self.latin('少年は少女が来ると言った。'), 'Puer puellam venīre dīxit.')
        self.assertEqual(self.latin('あなたは誰が来たか知らない。'), 'Quis vēnerit nōn scīs.')

    def test_subordinate_clauses(self):
        self.assertEqual(self.latin('少年が庭で寝ているとき、少女は歌った。'),
                         'Ubi puer in hortō dormiēbat, puella cantāvit.')


    def test_long_sentence(self):
        # 関係節が2つある長い文 (GiNZA があれば係り受けで、無ければ後ろの一番近い述語へ)
        self.assertEqual(self.latin('先生が褒めた少年は、庭で美しい薔薇を見ている少女に本を与えた。'),
                         'Puer quem magister laudāvit puellae quae rosam pulchram in hortō videt librum dedit.')

    def test_mecab_backend(self):
        self.assertEqual(latin.sentence(from_japanese.parse('少女が庭で美しい薔薇を見た。', backend='mecab')),
                         'Puella rosam pulchram in hortō vīdit.')

    def test_round_trip(self):
        # 日本語 → 文の枠 → 日本語 (語はラテン語の見出しの訳語に置き換わる: 先生 → 教師)
        from dragoman.generate import japanese
        for text in ('私は少女が歌うのを見た。', '少年は少女が来ると言った。', 'あなたは誰が来たか知らない。'):
            self.assertEqual(japanese.sentence(from_japanese.parse(text)), text)
        self.assertEqual(japanese.sentence(from_japanese.parse('少年は先生に褒められた。')), '少年は教師に称賛された。')


class JapaneseOutputTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → 日本語"""

    def japanese(self, text):
        from dragoman.generate import japanese
        return japanese.sentence(clauses(text))

    def test_relative_and_passive(self):
        self.assertEqual(self.japanese('Puella puerum videt quem magister laudat.'),
                         '少女は教師が称賛する少年を見る。')
        self.assertEqual(self.japanese('Puer ā magistrō laudātur.'), '少年は教師に称賛される。')



class OtherSourceTestCase(unittest.TestCase):
    """ロシア語・サンスクリット・古典ギリシア語 → 文の枠 → 元の言語・ラテン語"""

    def frames_of(self, module, text):
        analysis, = module.analyze_text(text)
        return frame.frames(analysis)

    @unittest.skipUnless(russian.available(), 'pymorphy3 か ru/en-index.tsv が無い')
    def test_russian(self):
        from dragoman.russian import analyzer as ru
        cs = self.frames_of(ru, 'Мальчик, которого хвалит учитель, читал книгу.')
        self.assertEqual(russian.sentence(cs), 'Мальчик, которого учитель хвалит, читал книгу.')
        self.assertEqual(latin.sentence(cs), 'Puer quem magister laudat librum legēbat.')
        cs = self.frames_of(ru, 'Если ты придёшь, я буду рад.')
        self.assertEqual(russian.sentence(cs), 'Если ты придёшь, я буду рад.')   # 完了体の未来

    @unittest.skipUnless(sanskrit.available(), 'vidyut か sa/en-index.tsv が無い')
    def test_sanskrit(self):
        from dragoman.sanskrit import analyzer as sa
        cs = self.frames_of(sa, 'नृपः अश्वान् अददात्')
        self.assertEqual(sanskrit.sentence(cs).split('\n')[0], 'nṛpaḥ aśvān adadāt ।')   # 元の類 (dā 第3類)
        cs = self.frames_of(sa, 'बालकः पुस्तकं पठति')
        self.assertEqual(latin.sentence(cs), 'Puer librum legit.')

    @unittest.skipUnless(greek.available(), 'grc/wiktionary.sqlite か grc/en-index.tsv が無い')
    def test_greek(self):
        from dragoman.greek import analyzer as gr
        cs = self.frames_of(gr, 'ὁ διδάσκαλος τοῖς παισὶ βιβλίον ἔδωκεν.')
        self.assertEqual(greek.sentence(cs), 'ὁ διδάσκαλος τοῖς παισὶ βιβλίον ἔδωκε.')
        cs = self.frames_of(gr, 'οἱ πολῖται ἔχαιρον.')   # 1単と同形の3複
        self.assertEqual(latin.sentence(cs), 'Cīvēs gaudēbant.')
        cs = self.frames_of(gr, 'οἱ στρατιῶται οὐκ ἐμάχοντο.')
        self.assertEqual(greek.sentence(cs), 'οἱ στρατιῶται οὐκ ἐμάχοντο.')

    @unittest.skipUnless(greek.available(), 'grc/wiktionary.sqlite か grc/en-index.tsv が無い')
    def test_greek_relative(self):
        from dragoman.greek import analyzer as gr
        cs = self.frames_of(gr, 'ὁ ἀνὴρ ὃν εἶδες σοφός ἐστιν.')
        self.assertEqual(greek.sentence(cs), 'ὁ ἀνὴρ ὃν εἶδες σοφός ἐστι.')   # 前接語 ἐστι
        self.assertEqual(latin.sentence(cs), 'Vir quem vīdistī catus est.')
        cs = self.frames_of(gr, 'ἡ πόλις ἐν ᾗ οἰκοῦμεν μεγάλη ἐστίν.')
        self.assertEqual(latin.sentence(cs), 'Urbs in quā habitāmus magna est.')   # 前置詞の空所
        cs = self.frames_of(gr, 'ἃ λέγει ὁ διδάσκαλος, ταῦτα γράφομεν.')   # 先行詞より前の関係節
        self.assertEqual(latin.sentence(cs), 'Haec quae magister dīcit scrībimus.')

    @unittest.skipUnless(greek.available(), 'grc/wiktionary.sqlite か grc/en-index.tsv が無い')
    def test_greek_indirect_question(self):
        from dragoman.greek import analyzer as gr
        cs = self.frames_of(gr, 'οὐκ οἶδα τίς ἦλθεν.')   # οἶδα: 形は完了、意味は現在
        self.assertEqual(greek.sentence(cs), 'οὐκ οἶδα τίς ἦλθε.')
        self.assertEqual(latin.sentence(cs), 'Quis ierit nōn sciō.')
        cs = self.frames_of(gr, 'ὁ διδάσκαλος ἤρετο τί ὁ παῖς γράφοι.')   # 希求法 → 接続法
        self.assertEqual(greek.sentence(cs), 'ὁ διδάσκαλος ἤρετο τί ὁ παῖς γράφοι.')
        self.assertEqual(latin.sentence(cs), 'Magister puer quid scrībat interrogāvit.')
        cs = self.frames_of(gr, 'ἐρωτῶ πῶς ὁ βασιλεὺς ἀπέθανεν.')
        self.assertEqual(english.sentence(cs), 'I ask how the king died.')
        cs = self.frames_of(gr, 'ἤρετο εἰ ὁ παῖς ἔλθοι.')
        self.assertEqual(latin.sentence(cs), 'Num puer ierit interrogāvit.')

    def test_greek_enclitic_accent(self):
        self.assertEqual(greek._grave('ὁ ἄνθρωπος ἐστί'), 'ὁ ἄνθρωπός ἐστι')
        self.assertEqual(greek._grave('τὸ δῶρον ἐστί'), 'τὸ δῶρόν ἐστι')
        self.assertEqual(greek._grave('ὁ λόγος ἐστί'), 'ὁ λόγος ἐστί')


@unittest.skipUnless(greek.available(), 'grc/wiktionary.sqlite か grc/en-index.tsv が無い')
class GreekTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → 古典ギリシア語"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def greek(self, text):
        analysis, = analyzer.analyze_text(text)
        return greek.sentence(frame.frames(analysis))

    def test_article_and_accent(self):
        self.assertEqual(self.greek('Puella rosam pulchram in hortō videt.'), 'ἡ κόρη τὸ καλὸν ῥόδον ἐν τῷ κήπῳ ὁρᾷ.')

    def test_aorist_and_augment(self):
        self.assertEqual(self.greek('Magister puerōs in hortum dūxit.'), 'ὁ διδάσκαλος τοὺς παῖδας εἰς τὸν κῆπον ἤγαγε.')
        self.assertEqual(self.greek('Rēgīna puellīs rosās dedit.'), 'ἡ βασίλεια ταῖς κόραις τὰ ῥόδα ἔδωκε.')

    def test_passive_agent(self):
        self.assertEqual(self.greek('Puer ā magistrō laudātus est.'), 'ὁ παῖς ὑπὸ τοῦ διδασκάλου ἐπῃνέθη.')

    def test_relative(self):
        self.assertEqual(self.greek('Puella puerum videt quem magister laudat.'),
                         'ἡ κόρη τὸν παῖδα ὃν ὁ διδάσκαλος ἐπαινεῖ ὁρᾷ.')

    def test_genitive_absolute(self):
        self.assertEqual(self.greek('Urbe captā, cīvēs fūgērunt.'), 'τῆς πόλεως ληφθείσης οἱ πολῖται ἔφυγον.')

    def test_indirect_question(self):
        self.assertEqual(self.greek('Magister rogāvit quis cantāret.'), 'ὁ διδάσκαλος ἠρώτησε τίς ᾖδε.')

    def test_neuter_plural_subject(self):
        self.assertEqual(self.greek('Rosae sunt pulchrae.'), 'τὰ ῥόδα καλά ἐστι.')

    def test_negated_copula(self):
        self.assertEqual(self.greek('Nauta nōn est malus.'), 'ὁ ναύτης κακὸς οὐκ ἔστι.')


@unittest.skipUnless(indonesian.available(), 'id/en-index.tsv が無い')
class IndonesianTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → インドネシア語"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def indonesian(self, text):
        analysis, = analyzer.analyze_text(text)
        return indonesian.sentence(frame.frames(analysis))

    def test_svo_and_prepositions(self):
        self.assertEqual(self.indonesian('Puella rosam pulchram in hortō videt.'), 'Gadis melihat mawar cantik di taman.')
        self.assertEqual(self.indonesian('Rēgīna puellīs rosās dedit.'),
                         'Ratu telah memberi mawar-mawar kepada gadis-gadis.')   # 重複で複数、受け手 kepada

    def test_passive_and_relative(self):
        self.assertEqual(self.indonesian('Puer ā magistrō laudātus est.'), 'Anak laki-laki telah dipuji oleh guru.')
        self.assertEqual(self.indonesian('Puella puerum videt quem magister laudat.'),
                         'Gadis melihat anak laki-laki yang dipuji oleh guru.')

    def test_copula(self):
        self.assertEqual(self.indonesian('Nauta nōn est malus.'), 'Pelaut tidak buruk.')
        self.assertEqual(self.indonesian('Puella est rēgīna.'), 'Gadis adalah ratu.')

    def test_question_and_absolute(self):
        self.assertEqual(self.indonesian('Magister rogāvit quis cantāret.'), 'Guru telah bertanya siapa yang bernyanyi.')
        self.assertEqual(self.indonesian('Urbe captā, cīvēs fūgērunt.'), 'Setelah kota direbut, warga-warga telah berlari.')

    def test_affixes(self):
        self.assertEqual([indonesian.men(r) for r in ('tulis', 'pakai', 'kirim', 'sapu', 'baca', 'dengar', 'ambil', 'cat')],
                         ['menulis', 'memakai', 'mengirim', 'menyapu', 'membaca', 'mendengar', 'mengambil', 'mengecat'])
        self.assertEqual(indonesian.passive('memiliki'), 'dimiliki')
        self.assertEqual(indonesian.intransitive('nyanyi'), 'bernyanyi')
        self.assertEqual(indonesian.active('beri'), 'memberi')   # ber- で始まるが語根


@unittest.skipUnless(tagalog.available(), 'tl/wiktionary.sqlite か tl/en-index.tsv が無い')
class TagalogTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → タガログ語"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def tagalog(self, text):
        analysis, = analyzer.analyze_text(text)
        return tagalog.sentence(frame.frames(analysis))

    def test_focus(self):
        # 目的語があれば対象焦点 (目的語が ang、行為者が ng)、物が移る動詞は移動物焦点、受動は主語を ang に
        self.assertEqual(self.tagalog('Puella rosam pulchram in hortō videt.'),
                         'Nakikita ng dalaga ang magandang rosas sa hardin.')
        self.assertEqual(self.tagalog('Rēgīna puellīs rosās dedit.'), 'Ibinigay ng reyna ang mga rosas sa mga dalaga.')
        self.assertEqual(self.tagalog('Puer ā magistrō laudātus est.'), 'Pinuri ng guro ang batang lalaki.')

    def test_relative_and_question(self):
        self.assertEqual(self.tagalog('Puella puerum videt quem magister laudat.'),
                         'Nakikita ng dalaga ang batang lalaking pinupuri ng guro.')
        self.assertEqual(self.tagalog('Magister rogāvit quis cantāret.'), 'Nagtanong ang guro kung sino ang umaawit.')

    def test_copula_negation_absolute(self):
        self.assertEqual(self.tagalog('Nauta nōn est malus.'), 'Hindi masama ang mandaragat.')
        self.assertEqual(self.tagalog('Puella est rēgīna.'), 'Reyna ang dalaga.')
        self.assertEqual(self.tagalog('Rosam nōn vīdit.'), 'Hindi niya nakita ang rosas.')   # 代名詞は hindi の後ろ
        self.assertEqual(self.tagalog('Urbe captā, cīvēs fūgērunt.'), 'Nang sinakop ang lungsod, tumakas ang mga mamamayan.')

    def test_aspect_forms(self):
        forms = [tagalog.conjugate(tagalog.lemma_for(r, v), r, a) for r, v, a in (
            ('kain', 'actor', 'progressive'), ('kain', 'object', 'completive'), ('bigay', 'conveyance', 'completive'),
            ('awit', 'actor', 'contemplative'), ('galak', 'actor', 'progressive'), ('matay', 'actor', 'completive'))]
        self.assertEqual(forms, ['kumakain', 'kinain', 'ibinigay', 'aawit', 'nagagalak', 'namatay'])


@unittest.skipUnless(arabic.available(), 'CAMeL Tools の形態素の辞書 (ar/camel) が無い')
class ArabicTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → アラビア語 (CAMeL Tools の生成器)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def arabic(self, text):
        analysis, = analyzer.analyze_text(text)
        return arabic.sentence(frame.frames(analysis)).split('\n')[0]

    def assertEqual(self, first, second, msg=None):   # 記号 (シャッダ・母音記号) の並びの違いは問わない
        import unicodedata
        super().assertEqual(unicodedata.normalize('NFC', first), unicodedata.normalize('NFC', second), msg)

    def test_verbal_sentence(self):
        # 動詞が先、女性の主語に一致、格 (主格・対格・属格)、定冠詞、形容詞の一致
        self.assertEqual(self.arabic('Puella rosam pulchram in hortō videt.'), 'تَرَى البِنْتُ الوَرْدَ الجَمِيلَ فِي الحَدِيقَةِ.')
        self.assertEqual(self.arabic('Rēgīna puellīs rosās dedit.'), 'أَعْطَت المَلِكَةُ الوَرْداتِ لِلبَناتِ.')

    def test_passive_without_form(self):
        self.assertEqual(self.arabic('Puer ā magistrō laudātus est.'), 'مَدَحَ المُعَلِّمُ الوَلَدَ.')   # 受動の形が無ければ能動に

    def test_nominal_and_negation(self):
        self.assertEqual(self.arabic('Puella est rēgīna.'), 'البِنْتُ مَلِكَةٌ.')
        self.assertEqual(self.arabic('Nauta nōn est malus.'), 'لَيْسَ البَحّارُ سَيِّئاً.')   # لَيْسَ + 対格
        self.assertEqual(self.arabic('Rosam nōn vīdit.'), 'لَمْ يَرَ الوَرْدَ.')   # لَمْ + 要求法

    def test_relative(self):
        self.assertEqual(self.arabic('Puella puerum videt quem magister laudat.'),
                         'تَرَى البِنْتُ الوَلَدَ الَّذِي يَمْدَحه المُعَلِّمُ.')   # 目的語の空所は代名詞の接尾辞


@unittest.skipUnless(hebrew.available(), 'ヘブライ語の辞書 (he/hebrew.sqlite) が無い')
class HebrewTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → 聖書ヘブライ語 (OSHB の語形)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def hebrew(self, text):
        analysis, = analyzer.analyze_text(text)
        return hebrew.sentence(frame.frames(analysis)).split('\n')[0]

    def assertEqual(self, first, second, msg=None):   # 点 (母音記号・ダゲシュ) の並びの違いは問わない
        import unicodedata
        super().assertEqual(unicodedata.normalize('NFC', first), unicodedata.normalize('NFC', second), msg)

    def test_participle_and_perfect(self):
        # 現在は分詞 (主語が先)、過去は完了形 (動詞が先)、אֶת־、冠詞と前置詞の縮約 (בַּגָּן)、形容詞の一致
        self.assertEqual(self.hebrew('Puella rosam pulchram in hortō videt.'), 'הַנַּעֲרָה רֹאָה אֶת־הַחֲבַצֶּלֶת הַיָּפֶה בַּגָּן.')
        self.assertEqual(self.hebrew('Rēgīna puellīs rosās dedit.'), 'נָתְנָה הַמַּלְכָּה אֶת־הַחֲבַצֶּלֶת לַנְּעָרוֹת.')

    def test_agreement(self):
        self.assertEqual(self.hebrew('Puella cantat.'), 'הַנַּעֲרָה שָׁרָה.')   # 女性単数の分詞を男性単数から
        self.assertEqual(self.hebrew('Puellae cantant.'), 'הַנְּעָרוֹת שָׁרוֹת.')
        self.assertEqual(self.hebrew('Urbe captā, cīvēs fūgērunt.'),   # עִיר は形は男性でも女性
                         'אַחֲרֵי אֲשֶׁר נִלְכְּדָה הָעִיר, בָּרָחוּ הָעַמִּים.')

    def test_passive_nominal_negation(self):
        self.assertEqual(self.hebrew('Puer ā magistrō laudātus est.'), 'הֻלַּל הַנַּעַר עַל־יְדֵי הַמּוֹרֶה.')   # プアル
        self.assertEqual(self.hebrew('Puella est rēgīna.'), 'הַנַּעֲרָה מַלְכָּה.')
        self.assertEqual(self.hebrew('Nauta nōn est malus.'), 'הַמַּלָּח לֹא רָע.')
        self.assertEqual(self.hebrew('Rosam nōn vīdit.'), 'לֹא רָאָה אֶת־הַחֲבַצֶּלֶת.')

    def test_relative(self):
        self.assertEqual(self.hebrew('Puella puerum videt quem magister laudat.'),
                         'הַנַּעֲרָה רֹאָה אֶת־הַנַּעַר אֲשֶׁר הַמּוֹרֶה מְהַלֵּל.')   # 分詞が型 (ピエル) から


class ImperativeTestCase(unittest.TestCase):
    """命令法・禁止 (nōlī + 不定詞)・与格を取る動詞 (miserēre nōbīs)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    @staticmethod
    def prohibition():
        timeo = frame.Clause(verb=frame.Lex('timeō', 'verb', '恐れる'), mood='infinitive')
        return frame.Clause(verb=frame.Lex('nōlō', 'verb', '望まない'), mood='imperative', person=2,
                            infinitives=[timeo])

    def test_imperative(self):
        clause, = clauses('Venī!')
        self.assertEqual(japanese.sentence([clause]), '来い。')
        self.assertEqual(kobun.sentence([clause]), '来よ。')   # 古文の命令形
        self.assertEqual(tagalog.sentence([clause]), 'Dumating ka.')   # 命令の2人称単数は ka

    def test_prohibition(self):
        clause = frame.prohibition(self.prohibition())   # Nōlī timēre → 否定の命令法の timeō
        self.assertEqual((clause.verb.lemma, clause.mood, clause.negated), ('timeō', 'imperative', True))
        self.assertEqual(japanese.sentence([self.prohibition()]), '恐れるな。')
        self.assertEqual(kobun.sentence([self.prohibition()]), 'な恐れそ。')   # な + 連用形 + そ

    def test_dative_as_object(self):
        us = frame.NP(frame.Lex('ego', 'pronoun', '私'), case='Dat', number='pl')
        clause = frame.Clause(verb=frame.Lex('misereor', 'verb', '憐れむ'), mood='imperative', person=2,
                              args=[('recipient', us)])
        self.assertEqual(japanese.sentence([clause]), '私たちを憐れめ。')
        self.assertEqual(english.sentence([clause]), 'Have mercy on us.')
        self.assertEqual(latin.sentence([clause]).split(' ')[0], 'Nōbīs')   # ラテン語は与格のまま

    @unittest.skipUnless(arabic.available(), 'CAMeL Tools の形態素の辞書が無い')
    def test_arabic(self):
        self.assertEqual(arabic.imperative('تَكْتُبْ'), 'اُكْتُبْ')
        self.assertEqual(arabic.imperative('تَرْحَمْ'), 'اِرْحَمْ')
        self.assertEqual(arabic.imperative('تُكْرِمْ'), 'أَكْرِمْ')   # 第4型
        self.assertEqual(arabic.imperative('تُعَلِّمْ'), 'عَلِّمْ')
        us = frame.NP(frame.Lex('ego', 'pronoun', '私'), number='pl')
        self.assertEqual(arabic.with_pronoun('li_prep', us), 'لَنا')
        self.assertEqual(arabic.with_pronoun('بَعْدَ', us), 'بَعْدَنا')

    @unittest.skipUnless(hebrew.available(), 'ヘブライ語の辞書が無い')
    def test_hebrew(self):
        clause, = clauses('Venī!')
        self.assertEqual(hebrew.sentence([clause]).split('\n')[0], 'בֹּא.')
        him = frame.NP(frame.Lex('is', 'pronoun', '彼'))
        self.assertEqual(hebrew.pronoun_with_preposition('עִם־', him), 'עִמּוֹ')
        self.assertEqual(hebrew.noun_phrase(frame.NP(frame.Lex('ego', 'pronoun', '私')), 'לְ')[0], 'לִי')


class LeftoverTestCase(unittest.TestCase):
    """前置詞なしの方向の対格・形容詞の並列の補語・ギリシア語の命令のアスペクト"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def test_bare_direction(self):
        clause, = clauses('Puer domum rediit.')   # domum「家へ」(目的語でなく方向)
        role, np = next((r, np) for r, np in clause.args if np.head.lemma == 'domus')
        self.assertEqual((role, np.prep.lemma, np.bare_direction), ('prep', 'in', True))
        self.assertEqual(latin.sentence([clause]), 'Puer domum rediit.')   # ラテン語には前置詞を書かない
        self.assertIn('to the house', english.sentence([clause]))

    def test_adjective_complements(self):
        clause, = clauses('Via longa et lāta est.')
        self.assertEqual(japanese.sentence([clause]), '道は長くて広い。')
        self.assertEqual(kobun.sentence([clause]), '道は長く広し。')
        clause, = clauses('Via longa et lāta nōn erat.')
        self.assertEqual(japanese.sentence([clause]), '道は長くも広くもなかった。')

    @unittest.skipUnless(greek.available(), 'ギリシア語の表が無い')
    def test_greek_imperative_aspect(self):
        clause, = clauses('Venī!')
        self.assertEqual(greek.sentence([clause]), 'ἐλθέ.')   # 肯定の命令はアオリスト

    @unittest.skipUnless(hebrew.available(), 'ヘブライ語の辞書が無い')
    def test_hebrew_conjunction(self):
        self.assertEqual(hebrew.with_and('רְחָבָה'), 'וּרְחָבָה')   # シェヴァの前は וּ
        self.assertEqual(hebrew.with_and('הַמַּלְכָּה'), 'וְהַמַּלְכָּה')
        from dragoman.hebrew import script
        self.assertEqual(script.translit('וּרְחָבָה'), 'ûrəḥāvâ')


@unittest.skipUnless(persian.available(), 'ペルシア語の辞書 (fa/wiktionary.sqlite) が無い')
class PersianTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → ペルシア語 (SOV、را、エザーフェ、می・ن、受動 شدن)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def persian(self, text):
        analysis, = analyzer.analyze_text(text)
        return persian.sentence(frame.frames(analysis)).split('\n')[1].strip()   # 転写の行

    def test_sentences(self):
        self.assertEqual(self.persian('Puella rosam pulchram in hortō videt.'), 'doxtar gol-e zibâ râ dar bâġ mi-binad.')
        self.assertEqual(self.persian('Rēgīna puellīs rosās dedit.'), 'malake gol-hâ râ be doxtar-hâ dâd.')
        self.assertEqual(self.persian('Puer ā magistrō laudātus est.'), "pesar tavassot-e mo'allem setude šod.")
        self.assertEqual(self.persian('Nauta nōn est malus.'), 'malavân bad nist.')
        self.assertEqual(self.persian('Rosam nōn vīdit.'), 'gol râ nadid.')

    def test_relative_and_imperative(self):
        self.assertEqual(self.persian('Puella puerum videt quem magister laudat.'),
                         "doxtar pesari râ ke mo'allem mi-setâyad mi-binad.")   # را は関係節の前
        self.assertEqual(self.persian('Venī!'), 'biyâ.')


@unittest.skipUnless(hindi.available(), 'ヒンディー語の辞書 (hi/wiktionary.sqlite) が無い')
class HindiTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → ヒンディー語・ウルドゥー語 (SOV、後置詞と斜格、ने、性の一致)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def hindi(self, text, urdu=False):
        analysis, = analyzer.analyze_text(text)
        clauses = frame.frames(analysis)
        return (hindi.sentence_urdu(clauses) if urdu else hindi.sentence(clauses)).split('\n')

    def test_sentences(self):
        self.assertEqual(self.hindi('Puella cantat.')[0], 'लड़की गाती है।')
        self.assertEqual(self.hindi('Puellae cantābant.')[1].strip(), 'laṛkiyāṃ gātī thīṃ.')
        self.assertEqual(self.hindi('Rēgīna puellīs rosās dedit.')[1].strip(), 'rānī ne gulāb laṛkiyoṃ ko die.')   # ने
        self.assertEqual(self.hindi('Puer ā magistrō laudātus est.')[1].strip(), 'laṛkā adhyāpak ke dvārā sarāhā gayā.')
        self.assertEqual(self.hindi('Venī!')[1].strip(), 'āo.')   # 命令 -ओ

    def test_urdu(self):
        self.assertEqual(self.hindi('Puella cantat.', urdu=True)[0], 'لڑکی گاتی ہے۔')


@unittest.skipUnless(ainu.available(), 'アイヌ語の辞書が無い')
class AinuTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → アイヌ語 (SOV、状態の動詞、somo、後置詞)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def ainu(self, text):
        clause, = clauses(text)
        return ainu.sentence([clause]).split('\n')[0]

    def test_sentences(self):
        self.assertEqual(self.ainu('Puella cantat.'), 'Matkaci sinotcaki.')
        self.assertEqual(self.ainu('Puella bona est.'), 'Matkaci pirka.')   # 形容詞は状態の動詞で述語
        self.assertTrue(self.ainu('Puer domum rediit.').startswith('Hekaci cise un '))   # 方向 un
        self.assertIn(' somo ', self.ainu('Nauta nōn est malus.'))


@unittest.skipUnless(tibetan.available(), 'チベット語の辞書 (bo/tibetan.sqlite) が無い')
class TibetanTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → 古典チベット語 (Wylie。能格・終止の助詞の形、時制の語幹、名詞化の関係節)"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def tibetan(self, text):
        clause, = clauses(text)
        return tibetan.sentence([clause]).split('\n')[-1].strip()   # Wylie の行

    def test_particles(self):
        self.assertEqual(tibetan.particle('bu mo', 'erg'), 'bu mos')
        self.assertEqual(tibetan.particle('dge rgan', 'erg'), 'dge rgan gyis')
        self.assertEqual(tibetan.particle('mthong', 'fin'), 'mthong ngo')
        self.assertEqual(tibetan.particle('bstod', 'nom'), 'bstod pa')
        if tibetan.tibetan_script('bu') is not None:   # pyewts があればチベット文字の行も
            self.assertEqual(tibetan.tibetan_script("dge rgan gyis bstod pa'i bu"), 'དགེ་རྒན་གྱིས་བསྟོད་པའི་བུ')

    def test_sentences(self):
        self.assertEqual(self.tibetan('Puella est rēgīna.'), 'bu mo rgyal mo yin no /')
        self.assertEqual(self.tibetan('Puer ā magistrō laudātus est.'), 'dge rgan gyis bu bstod do /')   # 能動に


class KobunTestCase(unittest.TestCase):
    """ラテン語 → 文の枠 → 古文"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def kobun(self, text):
        analysis, = analyzer.analyze_text(text)
        return kobun.sentence(frame.frames(analysis))

    def test_verbs(self):
        forms = {v: kobun.classical_verb(v).form('終止') for v in
                 ('見る', '褒める', '与える', '歌う', '起きる', '見える', '植える', '出る', '死ぬ', 'ある', '愛する', '感じる')}
        self.assertEqual(forms, {'見る': '見る', '褒める': '褒む', '与える': '与ふ', '歌う': '歌ふ', '起きる': '起く',
                                 '見える': '見ゆ', '植える': '植う', '出る': '出づ', '死ぬ': '死ぬ', 'ある': 'あり',
                                 '愛する': '愛す', '感じる': '感ず'})
        self.assertEqual(kobun.classical_verb('褒める').form('連体'), '褒むる')

    def test_sentences(self):
        self.assertEqual(self.kobun('Puella rosam pulchram in hortō videt.'), '乙女は麗しきバラを庭にて見る。')
        self.assertEqual(self.kobun('Rēgīna puellīs rosās dedit.'), '女王は乙女どもにバラを与へけり。')
        self.assertEqual(self.kobun('Puer ā magistrō laudātus est.'), '童は師に褒められけり。')   # 受身 らる + けり
        self.assertEqual(self.kobun('Puella puerum videt quem magister laudat.'), '乙女は師の褒むる童を見る。')

    def test_lexicon(self):
        from dragoman.generate.kobun_lexicon import VERBS
        self.assertEqual([m for m in VERBS if kobun.classical_verb(m) is None], [])   # 表の動詞はすべて古語に活用できる
        self.assertEqual(kobun.classical_verb('探す').form('終止'), '求む')
        self.assertEqual(kobun.classical_verb('見つける').form('連用'), '見出で')
        self.assertEqual(kobun.adjective('素晴らしい', '連体'), 'めでたき')
        self.assertEqual(kobun.adjective('素晴らしい', '連用+aux'), 'めでたかり')
        self.assertEqual(kobun.adjective('すべての', '連体'), 'よろづの')
        self.assertEqual([kobun._past_attributive(w) for w in ('祝福された', '歌われた', '疲れた', '織った')],
                         ['祝福せられたる', '歌はれたる', '疲れたる', '織りたる'])

    def test_round_trip_through_modern(self):
        """現代語 → 文の枠 → 古文 → (古文の現代語訳) → 現代語"""
        from dragoman.kobun import mecab, analyzer as kobun_analyzer
        if not mecab.available() or from_japanese._tagger is None:
            self.skipTest('MeCab か中古和文UniDic が無い')

        def round_trip(text):
            old = kobun.sentence(from_japanese.parse(text))
            return old, ''.join(a.modern for a in kobun_analyzer.analyze_text(old))
        self.assertEqual(round_trip('王は大きな都に住んでいた。'), ('王は大きなる都に住みたりけり。', '王は大きな都に住んでいた。'))
        self.assertEqual(round_trip('子供が泣いているのを母が聞いた。')[1], '母は子が泣くのを聞いた。')   # 準体法の の
        self.assertEqual(round_trip('先生が少年を褒めた。')[1], '先生は子供を褒めた。')
        self.assertEqual(round_trip('私は彼が何を書いたか知らない。')[1], '私はあの人が何を書いたか知らない。')
        self.assertEqual(round_trip('雨が降ったので、子供たちは家にいた。'),
                         ('雨の降りければ、子どもは家にをりけり。', '雨が降ったので、子どもは家にいた。'))   # 雨 + 落ちる → 降る
        self.assertEqual(round_trip('女王は少女たちに花を与えた。')[1], '女王は少女たちに花を与えた。')   # 乙女ども → 少女たち

    def test_copula_and_negation(self):
        self.assertEqual(self.kobun('Nauta nōn est malus.'), '舟人は悪しからず。')
        self.assertEqual(self.kobun('Puella est rēgīna.'), '乙女は女王なり。')

    def test_question_and_absolute(self):
        self.assertEqual(self.kobun('Magister rogāvit quis cantāret.'), '師は誰か歌ひけると問ひけり。')   # 係り結び
        self.assertEqual(self.kobun('Urbe captā, cīvēs fūgērunt.'), '都の捕へられて、民どもは逃げけり。')


def compare_rows(clause, langs=('la', 'ja')):
    from dragoman.generate import compare
    return compare.rows(clause, langs)


class CompareTestCase(unittest.TestCase):
    """文の枠の要素ごとに、各言語の形と手段を並べる"""

    @classmethod
    def setUpClass(cls):
        latindic.load()

    def rows(self, text, langs=('la', 'en', 'ja', 'kobun')):
        from dragoman.generate import compare
        analysis, = analyzer.analyze_text(text)
        return dict(compare.rows(frame.frames(analysis)[0], langs))

    def test_prepositional_phrase(self):
        rows = self.rows('Rosam in hortō vīdit.')
        place = rows['前置詞句 (in + 奪格)']
        self.assertEqual(place['la'], ('in hortō', 'in + 奪格'))
        self.assertEqual(place['en'], ('in the garden', '前置詞 in'))
        self.assertEqual(place['ja'], ('庭で', '助詞 で'))
        self.assertEqual(place['kobun'], ('庭にて', '助詞 にて'))

    def test_dropped_subject(self):
        rows = self.rows('Rosam in hortō vīdit.')
        dropped = rows['主語 (書かれていない)']
        self.assertEqual(dropped['la'][0], '')            # ラテン語は書かない
        self.assertEqual(dropped['en'], ('he', '代名詞を補う'))   # 英語は補う
        self.assertEqual(rows['述語 (完了)']['en'][0], 'saw')   # 補った代名詞は述語の行に入れない

    @unittest.skipUnless(greek.available() and russian.available(), 'ギリシア語かロシア語の表が無い')
    def test_cases_and_agent(self):
        rows = self.rows('Puer ā magistrō laudātus est.', ('la', 'grc', 'ru', 'ja'))
        agent = rows['前置詞句 (ā + 奪格)']
        self.assertEqual(agent['grc'][1], 'ὑπό + 属格')
        self.assertEqual(agent['ru'][1], '造格 (動作主)')
        self.assertEqual(rows['主語']['grc'][1], '主格 + 冠詞')

    def test_address(self):
        # 呼びかけ (呼格) は文の頭に。2人称の動詞の名詞の「主語」(主格の形 Agnus Deī) も呼びかけ
        rows = self.rows('Domine, venī!')
        self.assertEqual(rows['呼びかけ']['la'], ('domine', '呼格'))
        self.assertEqual(rows['呼びかけ']['ja'][1], '助詞 よ')
        self.assertEqual(rows['呼びかけ']['en'][1], '冠詞なし')
        self.assertFalse(rows['呼びかけ']['en'][0].startswith(('the ', 'O ')))
        analysis, = analyzer.analyze_text('Fīlius rēgis, venī!')   # 主格の形 (呼格なら fīlī)
        clause = frame.frames(analysis)[0]
        self.assertEqual([r for r, _ in clause.args], ['address'])
        self.assertEqual(english.sentence([clause]), 'Son of the king, come.')
        self.assertEqual(japanese.sentence([clause]), '王の息子よ、来い。')
        self.assertEqual(latin.sentence([clause]), 'Fīlius rēgis, venī.')

    def test_vocative_apposition(self):
        # 属格と同形の Iēsū を、呼格だけの Christe と同格の呼格に (属格として掛けない)
        analysis, = analyzer.analyze_text('Iēsū Christe, venī!')
        clause = frame.frames(analysis)[0]
        self.assertEqual([(r, np.case, np.apposed) for r, np in clause.args],
                         [('address', 'Voc', False), ('address', 'Voc', True)])
        self.assertEqual(japanese.sentence([clause]), 'イエス・キリストよ、来い。')
        self.assertEqual(latin.sentence([clause]), 'Iēsū Christe, venī.')
        self.assertIn('呼びかけ (同格)', dict(compare_rows(clause)))
        analysis, = analyzer.analyze_text('Servum dominī vīdit.')   # 格の合わない属格はそのまま
        self.assertEqual(frame.frames(analysis)[0].role('object')[0].genitives[0].head.lemma, 'dominus')

    @unittest.skipUnless(ainu.available() and tibetan.available(), 'アイヌ語かチベット語の辞書が無い')
    def test_ainu_tibetan(self):
        rows = self.rows('Puella bona est.', ('ain', 'bo'))
        self.assertEqual(rows['述語 (繋辞 + 補語、現在)']['ain'][0], 'pirka')   # 状態の動詞がそのまま述語
        self.assertTrue(rows['述語 (繋辞 + 補語、現在)']['bo'][0].endswith('(bzang po yin no)'))
        rows = self.rows('Puer ā magistrō laudātus est.', ('ain', 'bo'))
        self.assertTrue(rows['前置詞句 (ā + 奪格)']['bo'][0].endswith('(dge rgan gyis)'))   # 能動に組み替えた主語は能格

    @unittest.skipUnless(russian.available(), 'ロシア語の表が無い')
    def test_predicate_agrees_with_subject(self):
        # 述語の形は主語を残して作る (一致)。表では主語の形を外す
        rows = self.rows('Puella rosam vīdit.', ('ru', 'en', 'ja'))
        self.assertEqual(rows['述語 (完了)']['ru'][0], 'увидела')
        self.assertEqual(rows['述語 (完了)']['en'][0], 'saw')

    def test_copula_predicate(self):
        # 繋辞の文の述語は 繋辞 + 補語 (補語の形も主語に一致)。補語の行は述語の行にまとめる
        rows = self.rows('Puella pulchra est.')
        predicate = rows['述語 (繋辞 + 補語、現在)']
        self.assertEqual(predicate['la'][0], 'pulchra est')
        self.assertEqual(predicate['en'][0], 'is beautiful')
        self.assertEqual(predicate['ja'][0], '美しい')
        self.assertEqual(predicate['kobun'][0], '麗し')
        self.assertNotIn('補語', rows)
        rows = self.rows('Puella in hortō est.', ('en', 'tl'))   # 所在の文は前置詞句を残して作る
        self.assertEqual(rows['述語 (現在)']['en'][0], 'is')

    @unittest.skipUnless(arabic.available() and hebrew.available(), 'アラビア語かヘブライ語の辞書が無い')
    def test_arabic_hebrew(self):
        rows = self.rows('Puer ā magistrō laudātus est.', ('ar', 'he'))
        self.assertEqual(rows['述語 (完了 受動)']['he'][0], 'הֻלַּל (hullal)')
        self.assertTrue(rows['主語']['ar'][1].startswith('対格'))   # 受動の形が無いので能動に組み替え (通常の生成と同じ)
        self.assertTrue(rows['前置詞句 (ā + 奪格)']['ar'][1].startswith('主格'))
        rows = self.rows('Rosam in hortō vīdit.', ('ar', 'he'))
        self.assertEqual(rows['前置詞句 (in + 奪格)']['he'], ('בַּגָּן (baggān)', 'בְּ (語に付く)'))


if __name__ == '__main__':
    unittest.main()
