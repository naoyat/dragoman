#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# REPL のコマンド (.conjug / .decl) と、入口 (dragoman.py) のテスト
#
import os
import re
import sys
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


def repl(*lines):
    result = subprocess.run([sys.executable, 'dragoman.py', '--lang=la'], cwd=ROOT,
                            input='\n'.join(lines) + '\n',
                            capture_output=True, text=True)
    return ANSI_ESCAPE.sub('', result.stdout)


class DeclTestCase(unittest.TestCase):
    def test_noun(self):
        out = repl('.decl rēx')
        self.assertIn('rēx (noun, m), 王,指導者', out)
        self.assertIn('    Acc: rēgem', out)
        self.assertIn('    Dat: rēgibus', out)

    def test_multiple_forms(self):
        # 同じ欄に入る複数の形がすべて表示される
        out = repl('.decl fīlius')
        self.assertIn('    Gen: fīlī, fīliī', out)


class ConjugTestCase(unittest.TestCase):
    def test_sum(self):
        out = repl('.conjug sum')
        self.assertIn('          3: est', out)
        self.assertIn('    present: esse', out)



class DragomanCommandTestCase(unittest.TestCase):
    def test_lang_option(self):
        for command in (['dragoman.py'], ['-m', 'dragoman']):
            result = subprocess.run([sys.executable] + command + ['--lang=la', '-w'], cwd=ROOT,
                                    input='Rōma magna est.\n', capture_output=True, text=True)
            self.assertIn('→', ANSI_ESCAPE.sub('', result.stdout))

    def test_detected_language(self):
        # --lang が無ければ文字から推定する (ラテン文字はラテン語)
        result = subprocess.run([sys.executable, 'dragoman.py', '-w'], cwd=ROOT,
                                input='Rōma magna est.\n', capture_output=True, text=True)
        self.assertIn('→', ANSI_ESCAPE.sub('', result.stdout))

    def test_unknown_lang(self):
        for args in (['--lang=xx'], ['xx']):
            result = subprocess.run([sys.executable, 'dragoman.py'] + args, cwd=ROOT, input='',
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('grc', result.stderr)  # 対応している言語の一覧を出す

    def test_without_optional_dependency(self):
        # 任意の依存 (サンスクリットの Vidyut) が無くても、ほかの言語は動く (オプションの定義を集めるのに解析器を読まない)
        code = ("import sys, runpy; sys.modules['vidyut'] = None; "
                "sys.argv = ['dragoman.py', 'la', '-w', '-e', 'Puella cantat.']; "
                "runpy.run_path('dragoman.py', run_name='__main__')")
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('歌う', ANSI_ESCAPE.sub('', result.stdout))

    def test_positional_lang_and_text_option(self):
        # ./dragoman.py LANG -e TEXT (言語を最初の引数で、文を -e で)
        result = subprocess.run([sys.executable, 'dragoman.py', 'la', '-w', '-e', 'Rōma magna est.'], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertIn('→', ANSI_ESCAPE.sub('', result.stdout))
        result = subprocess.run([sys.executable, 'dragoman.py', '-w', '-e', 'Rōma magna est.', '-e', 'Mārcus currit.'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(ANSI_ESCAPE.sub('', result.stdout).count('→'), 2)
        # auto は文字から推定する (ロシア語)
        result = subprocess.run([sys.executable, 'dragoman.py', 'auto', '-w', '-e', 'Мальчик читает книгу.'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertIn('本', ANSI_ESCAPE.sub('', result.stdout))
        self.assertIn('推定した言語: ru', result.stderr)

    def test_language_list(self):
        result = subprocess.run([sys.executable, 'dragoman.py', '--languages'], cwd=ROOT, capture_output=True,
                                text=True)
        for code in ('la', 'grc', 'sa', 'ru', 'he', 'ar', 'fa', 'hi', 'ur', 'kobun'):
            self.assertIn('  %s ' % code, result.stdout)

    def test_detect(self):
        sys.path.insert(0, ROOT)
        from dragoman.main import detect
        cases = {'Gallia est omnis dīvīsa.': 'la', 'ἐν ἀρχῇ ἦν ὁ λόγος.': 'grc', 'Мальчик читает книгу.': 'ru',
                 'בְּרֵאשִׁית בָּרָא אֱלֹהִים': 'he', 'ذهب الولد إلى المدرسة.': 'ar', 'من به مدرسه می‌روم.': 'fa',
                 'लड़के ने किताब पढ़ी।': 'hi', 'रामो वनं गच्छति ।': 'sa', 'لڑکے نے کتاب پڑھی۔': 'ur',
                 '今は昔、竹取の翁といふものありけり。': 'kobun'}
        for text, lang in cases.items():
            self.assertEqual(detect(text), lang, text)

    def test_language_help(self):
        result = subprocess.run([sys.executable, 'dragoman.py', '--lang=he', '--help'], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertIn('--divine-name', result.stdout)
        self.assertIn('--no-word-detail', result.stdout)


class ArgumentTestCase(unittest.TestCase):
    """引数の解析: オプションの値を言語の符号・入力ファイルと取り違えない"""

    def setUp(self):
        sys.path.insert(0, ROOT)
        from dragoman import main
        self.main = main

    def test_option_values(self):
        self.assertEqual(self.main.parse_args(['-t', 'say', '-e', 'Rōma magna est.']),
                         (None, ['-t', 'say'], ['Rōma magna est.']))   # say は言語でない
        self.assertEqual(self.main.parse_args(['grc', '--pron', 'modern', 'FILE']), ('grc', ['--pron', 'modern', 'FILE'], []))

    def test_short_option_clusters(self):
        # まとめた短いオプション: 最後の字が値を取れば次が値 (-wt say)、続きがあればそれが値 (-wtsay)、e は文 (-we TEXT)
        parse = self.main.parse_args
        self.assertEqual(parse(['-wt', 'say', '-e', 'Rōma magna est.']), (None, ['-wt', 'say'], ['Rōma magna est.']))
        self.assertEqual(parse(['-wtsay', '-e', 'Rōma.']), (None, ['-wtsay'], ['Rōma.']))
        self.assertEqual(parse(['-we', 'Rōma magna est.']), (None, ['-w'], ['Rōma magna est.']))
        self.assertEqual(parse(['-weRōma.']), (None, ['-w'], ['Rōma.']))
        self.assertEqual(parse(['bo', '-rv', 'voice', 'FILE']), ('bo', ['-rv', 'voice', 'FILE'], []))
        self.assertEqual(self.main.input_files(['-wt', __file__]), [])   # 値はファイルでも入力にしない
        self.assertEqual(self.main.input_files(['-wtsay', __file__]), [__file__])

    def test_input_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            note, text = os.path.join(tmp, 'note.html'), os.path.join(tmp, 'in.txt')
            for path in (note, text):
                open(path, 'w').write('Puella cantat.\n')
            args = ['--html', note, text]
            self.assertEqual(self.main.input_files(args), [text])   # 既存の書き出し先は入力でない
            self.assertEqual(self.main._without(args, [text]), ['--html', note])

    def test_value_options_from_definitions(self):
        # 値を取るオプションの一覧は定義 (core/options.py・各言語の Command.options) から作る
        from dragoman.core import options
        self.assertTrue({'-t', '--tts', '--html', '--pdf', '--accent', '--pron', '--binyan', '--divine-name',
                         '--compound-labels', '--voice', '-v'} <= self.main.value_options())
        self.assertNotIn('-w', self.main.value_options())
        self.assertEqual(options.getopt_spec([options.Option('tts', 't', 'BACKEND'), options.Option('speech', 's')]),
                         ('t:s', ['tts=', 'speech']))

    def test_help_lists_options(self):
        # 説明の表示も定義から: 共通のオプションと言語ごとのオプション
        for code in self.main.LANGUAGES:
            if code == 'la':
                continue
            from dragoman.core import cli
            text = cli.help_text(self.main.command_for(code))
            self.assertIn('--no-word-detail', text)
            for o in self.main.command_for(code).options:
                self.assertIn('--' + o.long, text)
        result = subprocess.run([sys.executable, 'dragoman.py', 'la', '--help'], cwd=ROOT, capture_output=True, text=True)
        for name in ('--auto-macron', '--no-wiktionary', '--html=FILE', '--legend'):
            self.assertIn(name, result.stdout)

    def test_latin_temporary_file_removed(self):
        # -e の文を渡す一時ファイルは、終わったら (例外でも) 消す
        from unittest import mock
        from dragoman.latin import main as latin_main
        passed = []

        def fake(args):
            passed.append(args[-1])
            self.assertTrue(os.path.exists(args[-1]))
            raise RuntimeError('stop')
        with mock.patch.object(latin_main, 'main', fake):
            with self.assertRaises(RuntimeError):
                self.main.main(['la', '-e', 'Sēcrētum.'])
        self.assertFalse(os.path.exists(passed[0]))

    def test_html_to_pdf_path_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'old.pdf')
            open(path, 'w').write('%PDF-1.4')
            for lang in ('la', 'grc'):
                result = subprocess.run([sys.executable, 'dragoman.py', lang, '--html=' + path, '-e', 'Puella cantat.'],
                                        cwd=ROOT, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(open(path).read(), '%PDF-1.4')   # 既存の PDF はそのまま


if __name__ == '__main__':
    unittest.main()
