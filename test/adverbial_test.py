#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 副詞節 (従属接続詞の節を主節の従属節に。core/Adverbial.py、言語の設定の subordinators) を言語をまたいで
#
import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def translate(module, text):
    analyzer = importlib.import_module('dragoman.%s.analyzer' % module)
    if module == 'latin':
        from dragoman.latin import latindic
        latindic.load()
    analysis = next(iter(analyzer.analyze_text(text)))
    return ' // '.join(c.predicate.translate()[0] for c in analysis.clauses)


def available(module):
    try:
        command = importlib.import_module('dragoman.%s.command' % module).COMMAND
    except Exception:
        return False
    return command.available() is None


class AdverbialTestCase(unittest.TestCase):
    def check(self, module, text, suffix, main_start=None):
        if module != 'latin' and not available(module):
            self.skipTest('%s のデータが無い' % module)
        tr = translate(module, text)
        self.assertNotIn(' // ', tr, tr)   # 1つの文に (副詞節は主節の中)
        self.assertTrue(tr.startswith('{'), tr)
        self.assertIn('}' + suffix + ' / ', tr)
        if main_start:
            self.assertIn('}%s / %s' % (suffix, main_start), tr)

    def test_latin(self):
        self.check('latin', 'Cum vēnit, eum vīdī.', 'とき')
        self.check('latin', 'Sī vēnit, eum vīdī.', 'なら')
        self.check('latin', 'Perseus ubi haec audīvit, ex īnsulā discessit.', 'とき', 'ペルセウスが')   # 前に出た主語
        self.check('latin', 'Caesar, cum id nūntiātum esset, mātūrat ab urbe proficīscī.', 'とき', 'カエサルが')
        self.assertIn('友人', translate('latin', 'Cum amīcīs vēnit.'))   # 奪格の前の cum は前置詞

    def test_latin_question_without_clear_verb(self):
        self.assertTrue(translate('latin', 'Ubi habitās?').endswith('住むか'))   # habitās (分詞の読みもある)

    def test_greek(self):
        self.check('greek', 'ὅτε ἦλθεν, εἶδον αὐτόν.', 'とき')
        self.check('greek', 'εἰ ἦλθεν, εἶδον αὐτόν.', 'なら')   # 文の頭の εἰ は条件 (「〜かどうか」でなく)

    def test_sanskrit(self):
        self.check('sanskrit', 'यदा सः आगच्छत् तदा अहं तम् अपश्यम्।', 'とき', '私が')   # 相関の tadā は訳さない

    def test_hindi(self):
        self.check('hindi', 'जब वह आया, मैंने उसे देखा।', 'とき')
        self.check('hindi', 'अगर वह आया तो मैं खुश हूँ।', 'なら', '私は')
        self.check('hindi', 'हालाँकि वह आया, मैंने उसे देखा।', 'けれども')

    def test_persian(self):
        self.check('persian', 'وقتی آمد او را دیدم.', 'とき')   # 従属接続詞の後ろの آمد は動詞
        self.check('persian', 'اگرچه او آمد، من او را ندیدم.', 'けれども')

    def test_indonesian(self):
        self.check('indonesian', 'Ketika dia datang, saya melihatnya.', 'とき')

    def test_finnish(self):
        self.check('finnish', 'Kun hän tuli, näin hänet.', 'とき')

    def test_hebrew(self):
        self.check('hebrew', 'כַּאֲשֶׁר בָּא רָאִיתִי אֹתוֹ.', 'とき')   # כַּ + אֲשֶׁר を1語に
        self.assertIn('}とき / ', translate('hebrew', 'וַיְהִי כַּאֲשֶׁר שָׁמַע הָאִישׁ וַיֵּלֶךְ.').split(' // ')[0])

    def test_arabic(self):
        self.check('arabic', 'عندما جاء رأيته.', 'とき')   # عِنْد + ما でなく عِنْدَما
        self.check('arabic', 'إذا جاء الولد فرحت.', 'なら')   # 帰結の fa は訳さない

    def test_old_english(self):
        self.check('oldenglish', 'Siþþan he com, ic hine geseah.', '後で')   # 後ろが与格でない siþþan は接続詞
        self.check('oldenglish', 'Gif he cymþ, ic hine geseo.', 'なら')
        self.assertIn('以来', translate('oldenglish', 'Siþþan þæm dæge he com.'))

    def test_korean(self):   # 連結語尾 (節の後ろ) と 連体形 + 때・후
        self.assertIn('{雨が 降る}なら / ', translate('korean', '비가 오면 나는 집에 있다.'))
        self.assertIn('{雨が 降る}けれども / ', translate('korean', '비가 오지만 나는 간다.'))
        self.assertIn('{彼が 来た}とき / ', translate('korean', '그가 왔을 때 나는 그를 보았다.'))
        self.assertIn('{ご飯を 食べた}後で / ', translate('korean', '밥을 먹은 후에 나는 잤다.'))
        self.assertIn('{母が 作った}食べ物を', translate('korean', '어머니가 만든 음식을 먹었다.'))   # 関係節はそのまま

    def test_turkish(self):   # 副動詞の語尾
        self.check('turkish', 'Eve gelince yemek yedim.', 'と')
        self.check('turkish', 'Okula giderken onu gördüm.', '間に')
        self.assertTrue(translate('turkish', 'Eve gelip yemek yedim.').startswith('{家に 来て} / '))   # て形

    def test_mongolian(self):
        self.check('mongolian', 'Бороо орвол би гэртээ байна.', 'なら')
        self.assertIn('来て} / ', translate('mongolian', 'Би гэртээ ирээд хоол идсэн.'))

    def test_russian(self):
        self.check('russian', 'Когда он пришёл, я увидел его.', 'とき')
        self.check('russian', 'Я остался дома, потому что шёл дождь.', 'ので')


if __name__ == '__main__':
    unittest.main()
