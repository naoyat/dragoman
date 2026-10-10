#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ノート (HTML) の清書: 行間逐語訳・弧の図のデータ・入れ子の図・訳
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.latin import latindic, analyzer  # noqa: E402
from dragoman.core import notebook  # noqa: E402


class NotebookTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        latindic.load()

    def note(self, text):
        nb = notebook.Notebook('test')
        for a in analyzer.analyze_text(text):
            nb.add(a)
        return nb

    def test_arcs(self):
        nb = self.note('Puella rosam pulchram in hortō videt.')
        arcs = {(a['from'], a['to'], a['label']) for a in nb.sentences[0]['arcs']}
        self.assertIn((5, 0, '主格'), arcs)     # videt → Puella
        self.assertIn((5, 1, '対格'), arcs)     # videt → rosam
        self.assertIn((1, 2, '修飾'), arcs)     # rosam → pulchram
        self.assertIn((5, 3, '前置詞'), arcs)   # videt → in
        self.assertIn((3, 4, '奪格'), arcs)     # in → hortō

    def test_relative_and_question(self):
        nb = self.note('Puella puerum videt quem magister laudat.')
        labels = {a['label'] for a in nb.sentences[0]['arcs']}
        self.assertIn('関係節', labels)
        nb = self.note('Magister rogāvit quis cantāret.')
        self.assertIn('間接疑問', {a['label'] for a in nb.sentences[0]['arcs']})

    def test_html(self):
        page = self.note('Puella rosam pulchram in hortō videt.').html()
        for part in ('行間逐語訳', '図A 弧', '図B 入れ子', '語の詳細', 'class="w c-Nom"', 'videō'):
            self.assertIn(part, page)

    def test_no_markup_injection(self):
        # 原文の %DATA% や <svg …> で、本文にタグを作らない (置換は一度だけ、JSON の < は \\u003c)
        import html.parser
        page = self.note('Puella %DATA% <svg/onload=alert(1)> </script> cantat.').html()

        class Tags(html.parser.HTMLParser):
            found = []

            def handle_starttag(self, tag, attrs):
                self.found.append((tag, dict(attrs)))
        parser = Tags()
        parser.feed(page)
        self.assertFalse([t for t, a in parser.found if t == 'svg' and 'onload' in a])
        self.assertEqual(page.count('<script>'), 1)
        self.assertNotIn('</script> cantat', page)

    def test_write_refuses_pdf_before_writing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'old.pdf')
            open(path, 'w').write('%PDF-1.4')
            with self.assertRaises(ValueError):
                self.note('Puella cantat.').write(path)
            self.assertEqual(open(path).read(), '%PDF-1.4')

    def test_provenance(self):
        # 再現条件: データの置き場所の下で開いたファイル、コードの版、文を除いたオプション
        import tempfile
        from unittest import mock
        from dragoman.core import provenance, paths
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'xx'))
            for name in ('xx/a.sqlite', 'xx/deep/b.bin', 'xx/deep/c.bin'):
                os.makedirs(os.path.dirname(os.path.join(tmp, name)), exist_ok=True)
                open(os.path.join(tmp, name), 'w').write('data')
            with mock.patch.object(paths, 'DATA_DIR', tmp), mock.patch.object(provenance, '_used', set()):
                provenance.start()
                for name in ('xx/a.sqlite', 'xx/deep/b.bin', 'xx/deep/c.bin'):
                    open(os.path.join(tmp, name)).read()
                open(__file__).read()   # データの置き場所の外は記録しない
                used = {path: count for path, _, _, count in provenance.used_data()}
                self.assertEqual(used, {os.path.join('xx', 'a.sqlite'): 1, os.path.join('xx', 'deep'): 2})
                rows = dict(provenance.info('la', ['la', '-D', '-e', 'Puella cantat.', '-weRōma.', '--html=n.html']))
        self.assertEqual(rows['オプション'], 'la -D -w --html=n.html')   # 解析の文は記録しない
        self.assertTrue(rows['コード'].startswith(('git ', 'dragoman ', '不明')))
        nb = self.note('Puella cantat.')
        nb.provenance = [('言語', 'la'), ('使ったデータ', [('wiktionary.sqlite', '2026-10-10', 2048, 1)])]
        page = nb.html()
        self.assertIn('再現条件', page)
        self.assertIn('wiktionary.sqlite', page)

    def test_rtl_heading(self):
        self.assertIn('dir="rtl"', notebook.heading('בָּרָא (bārā)'))


if __name__ == '__main__':
    unittest.main()
