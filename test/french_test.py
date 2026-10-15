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
                         '〜することなく / 誰も / それに / 実感しない,気づかない')   # s'en aperçoive (en は接語)・sans que
        self.assertEqual(self.ja('Personne ne vient.'), '誰も / 来ない')
        self.assertEqual(self.ja('Il ne voit rien.'), '{彼,それ}が / 何も / 見ない')

    def test_questions_and_imperatives(self):
        self.assertEqual(self.ja('Viens-tu avec moi ?'), '君が / 私[と,で] / 来る')      # 倒置は主語を前に
        self.assertEqual(self.ja('Est-ce que tu viens ?'), '君が / 来る')               # est-ce que は疑問の印
        self.assertEqual(self.ja('A-t-il mangé ?'), '{彼,それ}が / 食べた')
        self.assertEqual(self.ja('Mange ta soupe !'), '君のスープを / 食べろ')
        self.assertEqual(self.ja('Ne pars pas !'), '出発するな')
        self.assertEqual(self.ja('Parlons français.'), 'フランス語を / 話そう')         # 1人称の命令は「〜よう」
        self.assertEqual(self.ja("J'aime le vin français."), '私が / フランスのワインを / 愛する,好む')

    def test_names(self):
        self.assertEqual(self.ja('Jean aime Marie.'), 'ジャンが / マリを / 愛する,好む')


class KatakanaTestCase(unittest.TestCase):
    def test_french_names(self):
        self.assertEqual([latin(n, 'fr') for n in ('Jean', 'Paris', 'Rousseau', 'Michel', 'Camus', 'Claude', 'Vincent')],
                         ['ジャン', 'パリ', 'ルソー', 'ミシェル', 'カミュ', 'クロード', 'ヴァンサン'])


if __name__ == '__main__':
    unittest.main()
