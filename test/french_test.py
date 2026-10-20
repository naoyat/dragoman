#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語: 役割からの格、冠詞・縮約形・部分冠詞、接語の代名詞、動詞の組 (複合過去・受動・話法の助動詞)、
# 否定、il y a、関係節、de 句の属格、日本語訳 (french.analyzer)。名前のカタカナ。
# spaCy のフランス語モデルか辞書 (tools/build_french_dic.py) が無ければ飛ばす
#
import unittest

from dragoman.core.katakana_names import latin

try:
    from dragoman.french import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_DATA, 'spaCy のフランス語モデルかフランス語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_roles_and_articles(self):
        self.assertEqual(self.ja("Le garçon lit un livre à l'école."), '少年が / 学校[に,で] / 本を / 読む')   # lit を動詞に
        self.assertEqual(self.ja('Le livre du professeur est sur la table.'), '机の上に / 先生の本が / ある')
        self.assertEqual(self.ja('Je veux manger du pain.'), '私が / パンを / 食べたい')            # 部分冠詞
        self.assertEqual(self.ja('Nous parlons du film.'), '私たちが / 映画について / 話す')    # parler de

    def test_clitics_and_verb_groups(self):
        self.assertEqual(self.ja('Je le lui ai donné hier.'), '私が / {彼,彼女}に / {彼,それ}を / 昨日 / 与えた')
        self.assertEqual(self.ja('Elle est allée au marché avec son ami.'),
                         '{彼女,それ}が / 市場[に,で] / 彼の友達[と,で] / 行った')                # être + 移動の動詞
        self.assertEqual(self.ja('Le livre a été écrit par le professeur.'), '本が / 先生によって / 書かれた')
        self.assertEqual(self.ja('Nous voulons lire un livre.'), '私たちが / 本を / 読みたい')

    def test_negation_existential_clauses(self):
        self.assertEqual(self.ja('Il ne mange pas de pain.'), '{彼,それ}が / パンを / 食べない')
        self.assertEqual(self.ja('Il y a un chat dans le jardin.'), '庭の中に / 猫が / いる')
        self.assertEqual(self.ja('La fille qui chante est ma sœur.'), '歌う{少女,娘}は / 私の姉妹である')
        self.assertEqual(self.ja("Je sais que tu m'aimes."), '私が / 知っている / 〜ということ / 君が / 私を / 愛する,好む')

    def test_pronoun_subjects(self):
        self.assertEqual(self.ja('Je vous aime.'), '私が / あなたを / 愛する,好む')               # 主語の後ろの vous は目的語
        self.assertEqual(self.ja('Nous chanterons.'), '私たちが / 歌うだろう')
        self.assertEqual(self.ja('Ils chantent.'), '{彼ら,それら}が / 歌う')                      # spaCy の半過去を直す
        self.assertEqual(self.ja('Je les vois.'), '私が / {彼ら,それら}を / 見る')

    def test_clitic_valency(self):
        # 人を表す接語 (me・te・nous・vous) の格は動詞から: 間接他動詞・二重目的語の動詞は与格、ほかは対格
        self.assertEqual(self.ja('Nous vous parlons.'), '私たちが / あなたに / 話す')
        self.assertEqual(self.ja("Il m'a parlé."), '{彼,それ}が / 私に / 話した')            # 複合過去は本動詞で
        self.assertEqual(self.ja('Il me donne le livre.'), '{彼,それ}が / 私に / 本を / 与える')
        self.assertEqual(self.ja('Il me voit.'), '{彼,それ}が / 私を / 見る')

    def test_pronominal_and_experiencer(self):
        self.assertEqual(self.ja('Il se lève.'), '{彼,それ}が / 起きる')                   # 代名動詞 (辞書の se lever)
        self.assertEqual(self.ja("Elle s'est levée tôt."), '{彼女,それ}が / 早く / 起きた')  # 再帰 + être は複合過去
        self.assertEqual(self.ja("Je m'appelle Jean."), '私が / ジャンと / 呼ばれている')
        self.assertEqual(self.ja('Tu me manques.'), '私は / 君が / いなくて寂しい')          # manquer à
        self.assertEqual(self.ja('Tu manques à ta mère.'), '君の母は / 君が / いなくて寂しい')
        self.assertEqual(self.ja('Ce livre me plaît.'), '私は / この本が / 気に入っている')       # plaire à
        self.assertEqual(self.ja('Cette ville plaît à mon père.'), '私の父は / この町が / 気に入っている')
        self.assertEqual(self.ja('Tu me plais.'), '私は / 君が / 気に入っている')           # plais を過去分詞と読む誤り

    def test_reform_spelling(self):
        # 1990年の綴りの改革: 辞書の「post-1990 spelling of …」から。記号で区別する語 (sûr・dû) は変わらない
        self.assertEqual([morphology.reform_note(w, l) for w, l in
                          (('plaît', 'plaire'), ('connait', 'connaitre'), ('événement', 'événement'), ('sûr', 'sûr'))],
                         [('new', 'plait'), ('old', 'connaît'), ('new', 'évènement'), None])
        self.assertEqual(morphology.gloss('cout', 'noun')[0], morphology.gloss('coût', 'noun')[0])   # 新しい綴りも同じ訳

    def test_en_clitic_and_negative_pronouns(self):
        a = next(analyzer.analyze_text("Il est parti sans que personne ne s'en aperçoive."))
        self.assertEqual([c.predicate.translate()[0] for c in a.clauses][-1],
                         '{誰も それに 実感しない,気づかない}まま / {彼,それ}が / 出発した')   # s'en aperçoive (en は接語)・sans que
        self.assertEqual(self.ja('Personne ne vient.'), '誰も / 来ない')
        self.assertEqual(self.ja('Il ne voit rien.'), '{彼,それ}が / 何も / 見ない')

    def test_superlatives_and_complements(self):
        self.assertEqual(self.ja('Le bon sens est la chose du monde la mieux partagée.'),
                         '良識は / {世界の & 最もよく共有された}ものである')   # 最上級 + 分詞、繋辞の補語
        self.assertEqual(self.ja("C'est le plus grand homme du monde."), 'それは / {世界の & 最も大きい}男である')
        self.assertEqual(self.ja('Je suis fatigué.'), '私は / 疲れている')             # 形容詞になった過去分詞
        self.assertEqual(self.ja('La porte était ouverte.'), 'ドアは / 開いていた')
        self.assertEqual(self.ja('Il est aimé de tous.'), '{彼,それ}が / すべて[の,から] / 愛される,好まれる')   # 動作主があれば受動
        self.assertEqual(self.ja('Elle semble fatiguée.'), '{彼女,それ}が / 疲れたように見える')
        self.assertEqual(self.ja('Ils pensent être heureux.'), '{彼ら,それら}が / {幸せである}ことを / 考える')
        self.assertEqual(self.ja('Il est devenu riche.'), '{彼,それ}が / 金持ちになった')
        self.assertEqual(self.ja('Elle est partie.'), '{彼女,それ}が / 出発した')   # 分詞の見出し parti → partir

    def test_relatives_and_idioms(self):
        self.assertEqual(self.ja('Ceux qui travaillent réussissent.'), '働く人々が / 成功する')   # 関係節の後ろの主節の動詞
        self.assertEqual(self.ja("J'aime ceux qui lisent."), '私が / 読む人々を / 愛する,好む')
        self.assertEqual(self.ja("Ils n'ont point coutume d'en désirer plus."),
                         '{彼ら,それら}が / それを / もう / 強く望む習慣がない')                 # ne … point、avoir coutume de
        self.assertEqual(self.ja("J'ai envie de partir."), '私が / 出発したい')
        self.assertEqual(self.ja('Tu as besoin de dormir.'), '君が / 眠る必要がある')
        self.assertEqual(self.ja('Chacun pense en être si bien pourvu.'),
                         '各人が / それを / {それほど よく 備えられている}ことを / 考える')   # 不定詞の être + 分詞、si「それほど」

    def test_meme_impersonal_and_ce_que(self):
        self.assertEqual(self.ja('Même les enfants le savent.'), '子供さえ / {彼,それ}を / 知っている')   # même「〜さえ」
        self.assertEqual(self.ja("C'est le même livre."), 'それは / {同じ,真実の}本である')            # le même「同じ」
        self.assertEqual(self.ja('Il est important que tu viennes.'), '{君が 来る}ことは / 重要である,大きい')
        self.assertEqual(self.ja("Il n'est pas vraisemblable que tous se trompent."),
                         '{すべての(人,物)が 間違える}ことは / もっとも,ありそうではない')
        self.assertEqual(self.ja("Je ne sais pas ce qu'il veut."), '私が / {{彼,それ}が 欲する}ことを / 知らない')

    def test_noun_infinitives(self):
        self.assertEqual(self.ja('Il a le courage de parler.'), '{彼,それ}が / {話す}勇気を / 持つ')
        self.assertEqual(self.ja("J'ai le désir de voir la mer."), '私が / {海を 見る}強い願いを / 持つ')
        self.assertEqual(self.ja('La puissance de bien juger et distinguer le vrai est égale.'),
                         '{よく 判断する、真実を 区別する}{力,主権}は / 同じ,公平である')   # et でつないだ不定詞
        self.assertEqual(self.ja('Je veux voir la mer.'), '私が / 海を / 見たい')   # 冠詞の後ろの mer は名詞
        self.assertEqual(self.ja('Le livre de Pierre est rouge.'), 'ピエールの本は / 赤い')

    def test_naming_and_phrases(self):
        self.assertEqual(self.ja("C'est ce qu'on nomme le bon sens."), 'それは / {人々が 良識と 呼ぶ,名付ける}ことである')
        self.assertEqual(self.ja('La diversité de nos opinions ne vient pas de ce que les uns sont plus raisonnables que les autres.'),
                         '私たちの意見の多様さが / {ある人々が 他の人々より 理性的,正確である}こと[の,から] / 来ない')

    def test_que_complements(self):
        self.assertEqual(self.ja('Je sais que tu viens.'), '私が / {君が 来る}ことを / 知っている')   # 補文は入れ子
        self.assertEqual(self.ja('Cela témoigne que la puissance de bien juger est égale.'),
                         'それが / {{よく 判断する}{力,主権}が 同じ,公平である}ことを / 示す,証言する')

    def test_long_sentence(self):
        # 『方法序説』: 名詞 + de + 不定詞のカンマを挟んだ並列と d'avec「〜から」、関係節の中の関係節を越えて主節に主語、
        # 関係節の繋辞の補語 (ce qu'on nomme …)、並列の名詞の格
        self.assertEqual(self.ja("La puissance de bien juger, et distinguer le vrai d'avec le faux, qui est proprement ce "
                                 "qu'on nomme le bon sens ou la raison, est naturellement égale en tous les hommes."),
                         '{まさに,本来 {人々が 良識と={理性,理由}と 呼ぶ,名付ける}ことである}{よく 判断する、偽りから 真実を 区別する}'
                         '{力,主権}は / 生まれつき,自然に / すべての男[に,で] / 同じ,公平である')

    def test_adverbial_clauses(self):
        self.assertEqual(self.ja("Je reste à la maison parce qu'il pleut."), '{雨が降る}ので / 私が / 家[に,で] / とどまる')
        self.assertEqual(self.ja('Quand il arrive, nous mangeons.'), '{{彼,それ}が 着く}とき / 私たちが / 食べる')
        self.assertEqual(self.ja('Si tu viens, je serai content.'), '私は / {君が 来る}なら / うれしいだろう')

    def test_questions_and_imperatives(self):
        self.assertEqual(self.ja('Viens-tu avec moi ?'), '君が / 私[と,で] / 来るか')    # 倒置は主語を前に、疑問文は「か」
        self.assertEqual(self.ja('Est-ce que tu viens ?'), '君が / 来るか')               # est-ce que は疑問の印
        self.assertEqual(self.ja('A-t-il mangé ?'), '{彼,それ}が / 食べたか')
        self.assertEqual(self.ja('Mange ta soupe !'), '君のスープを / 食べろ')
        self.assertEqual(self.ja('Ne pars pas !'), '出発するな')
        self.assertEqual(self.ja('Parlons français.'), 'フランス語を / 話そう')         # 1人称の命令は「〜よう」
        self.assertEqual(self.ja("J'aime le vin français."), '私が / フランスのワインを / 愛する,好む')

    def test_verb_constructions(self):
        self.assertEqual(self.ja('Je viendrais si je pouvais.').split(' / ')[1:], ['私が', '来るだろう'])   # 条件法
        self.assertEqual(self.ja('Je viens de manger.'), '私が / 食べたところだ')                # 近い過去
        self.assertEqual(self.ja('Il me fait rire.'), '{彼,それ}が / 私を / 笑わせる')           # 使役 faire
        self.assertEqual(self.ja('En marchant, il chante.'), '歩きながら / {彼,それ}が / 歌う')  # ジェロンディフ
        self.assertEqual(self.ja('Il faut partir.'), '出発しなければならない')                   # 非人称の il
        self.assertEqual(self.ja('Il est plus grand que moi.'), '{彼,それ}は / 私より / 大きい')  # 比較
        self.assertEqual(self.ja("C'est le livre que j'ai lu."), 'それは / {私が 読んだ}本である')

    def test_subjunctive(self):
        def mood(text, surface):
            a = next(analyzer.analyze_text(text))
            return next(w.items[0].attrib('mood') for w in a.words if w.surface == surface)
        self.assertEqual(mood('Il faut que je parte.', 'parte'), 'subjunctive')   # il faut que で話法の組にまとめても接続法
        self.assertEqual(self.ja('Il fallait que je parte.'), '私が / 出発しなければならなかった')
        self.assertEqual(self.ja('Il faut que je parte.'), '私が / 出発しなければならない')
        self.assertEqual(self.ja("Il faut que je m'en aille."), '私が / 立ち去らなければならない')   # s'en aller
        self.assertEqual(mood('Je veux que tu viennes.', 'viennes'), 'subjunctive')
        self.assertEqual(mood('Je sais que tu viens.', 'viens'), 'indicative')
        self.assertEqual(mood("Bien qu'il pleuve, nous sortons.", 'pleuve'), 'subjunctive')

    def test_names(self):
        self.assertEqual(self.ja('Jean aime Marie.'), 'ジャンが / マリを / 愛する,好む')


class KatakanaTestCase(unittest.TestCase):
    def test_french_names(self):
        self.assertEqual([latin(n, 'fr') for n in ('Jean', 'Paris', 'Rousseau', 'Michel', 'Camus', 'Claude', 'Vincent')],
                         ['ジャン', 'パリ', 'ルソー', 'ミシェル', 'カミュ', 'クロード', 'ヴァンサン'])
        # 後ろに m・n が続く em・en は鼻母音にしない、語末の -nne は「ンヌ」、語末の「母音 + r・n・m・z … + e」は長音
        self.assertEqual([latin(n, 'fr') for n in ('Emmanuel', 'Anne', 'Étienne', 'Céline', 'Pierre', 'Antoine',
                                                    'Rose', 'Isabelle', 'Nicole', 'Alice')],
                         ['エマニュエル', 'アンヌ', 'エティエンヌ', 'セリーヌ', 'ピエール', 'アントワーヌ', 'ローズ',
                          'イザベル', 'ニコル', 'アリス'])


if __name__ == '__main__':
    unittest.main()
