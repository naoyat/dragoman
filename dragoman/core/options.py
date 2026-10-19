#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# コマンドのオプションの定義 (一か所に): 名前・値の有無・説明
#
#   ここに書いた定義から、getopt の書式 (getopt_spec)、値を取るオプションの一覧 (value_names。入口 main.py が値を
#   言語の符号・入力ファイルと取り違えないように)、説明の文 (help_text) を作る。
#   共通のオプションは COMMON、ラテン語のコマンド (latin/main.py) だけのものは LATIN、
#   ほかの言語だけのものは LANGUAGE (<言語>/command.py の Command(options=...) がここから取る)
#
from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    long: str           # 長い名前 (no-word-detail)
    short: str = ''     # 短い名前の1字 (w)
    value: str = ''     # 値の名前 (FILE・BACKEND)。空なら値を取らない
    help: str = ''      # 説明 (改行で続ける)

    @property
    def names(self):
        """コマンド行での名前 (-w, --no-word-detail)"""
        return (('-' + self.short,) if self.short else ()) + ('--' + self.long,)


COMMON = (
    Option('no-word-detail', 'w', help='語ごとの辞書引きの結果を表示しない'),
    Option('descendants', 'D', help='ほかの言語に入った語 (子孫語) も表示する'),
    Option('etymology', 'E', help='語源も表示する'),
    Option('speech', 's', help='音読する'),
    Option('tts', 't', 'BACKEND', '音読の方式 (mbrola / espeak / piper / say)'),
    Option('romanize', 'r', help='語ごとの辞書引きの結果に、語の転写を添える'),
    Option('kana', 'k', help='文のカタカナ読み (発音に忠実に。語の区切りは空白) を見出しの下に添える'),
    Option('kana-only', help='カタカナ読みだけを出す (解析結果は出さない)'),
    Option('kana-long', value='STYLE', help='カタカナ読みの長音「ー」: phonemic (音素として長い母音だけ) / phonetic\n'
                                            '(実際に長く発音される母音にも)。既定は言語ごと (フランス語は phonetic)'),
    Option('kana-wa', value='KANA', help='カタカナ読みの [wa]: ワ (既定) / ウァ (西洋古典学の慣習: ミネルウァ)'),
    Option('kana-si', value='KANA', help='カタカナ読みの [si]・[zi]: スィ (既定。[ʃi] の「シ」と分ける) / シ (慣用)'),
    Option('no-explain', help='初学者向けの解説 (動詞の型・語根など) を出さない'),
    Option('english-glosses', help='英語の訳語 (Wiktionary などの語義) を日本語に置き換えない'),
    Option('sentence-per-line', help='改行も文の区切りにする (歌詞・詩など、行末に句点の無い行。\n'
                                     '行末がカンマなら次の行に続ける)'),
    Option('html', value='FILE', help='解析結果をノート (HTML) に清書する (行間逐語訳・弧の図・入れ子の図・訳・語の詳細)'),
    Option('pdf', value='FILE', help='ノートを PDF に (Google Chrome のヘッドレス印刷)'),
    Option('marks', help='ノートに確かさの印 (辞書に無い・推測した語形・構造の外・候補が複数・格が決まらない …)'),
    Option('legend', help='ノートの冒頭に印の凡例と見本 (--marks も)'),
    Option('provenance', help='ノートに再現条件 (コードの版・オプション・使ったデータ)'),
    Option('compare', value='LANGS', help='ノートに要素ごとの比較の表: 文の枠の要素を各言語がどう表すか\n'
                                          '(言語の符号をカンマで: la,grc,ja。all で全部: la grc sa ru en id tl ar he fa hi ur ain bo ja kobun)'),
    Option('gaps', help='解析の穴の一覧だけを出す (辞書に無い語・推測した語形・構造の外の語・述語の見つからない文の数)。\n'
                        '本文は出さない: 語は理由ごとに重複を除いて並べ替える (文中の順・前後の語は出さない)'),
    Option('help', 'h', help='説明を表示する'),
)

# ラテン語のコマンド (latin/main.py) が受け付ける共通のオプション (-r・--no-explain などはラテン語では使わない。
# --sentence-per-line は入口 main.py が処理する) と、ラテン語だけのもの
LATIN_COMMON = ('no-word-detail', 'descendants', 'etymology', 'speech', 'tts', 'html', 'pdf', 'marks', 'legend',
                'provenance', 'compare', 'gaps', 'help', 'kana', 'kana-only', 'kana-long', 'kana-wa', 'kana-si')
LATIN = tuple(o for o in COMMON if o.long in LATIN_COMMON) + (
    Option('no-translation', 'q', help='訳 (日本語) を表示しない'),
    Option('capital-to-macron', 'm', help='[対話モード] 大文字の母音を長母音として読む (A → ā)'),
    Option('auto-macron', 'a', help='マクロンの無い入力にマクロンを推定して付ける'),
    Option('accent', value='ACCENT', help='[mbrola] 音読のアクセント: pitch (既定) / stress'),
    Option('no-wiktionary', help='手作りの辞書だけを使う (Wiktionary 由来の補助辞書を引かない)'),
)

# 言語ごとのコマンド (<言語>/command.py) だけのもの。入口 main.py が解析器を読み込まずに集められるよう、ここに置く
LANGUAGE = {
    'he': (   # ヘブライ語
        Option('divine-name', value='MODE', help='音読での神の名 יְהוָה の読み方: adonai (既定。ヒリクの形はエロヒム) /\n'
                                                 'hashem「ハシェム」/ literal (字面のまま)'),
        Option('binyan', value='ROOT', help='語根 (כתב / ktb / 語形でも) の態の型の表を出す\n'
                                            '(聖書に現れた形と、規則から作った形 *)'),
    ),
    'sa': (   # サンスクリット
        Option('compound-labels', value='STYLE',
               help='複合語の種類の名前: sa (tatpuruṣa など。既定) / ja (依主釈など) / en (determinative など)'),
        Option('voice', 'v', 'VOICE', '音読の MBROLA の音声 (in1 / in2)'),
        Option('buddhist', help='仏典の語彙 (漢訳語: rūpa → 色、prajñā → 般若) を使う\n'
                                '(既定は文章に bodhisattva, śāriputra, prajñāpāramitā などがあれば使う)'),
        Option('no-buddhist', help='仏典の語彙を使わない'),
    ),
    'grc': (   # 古典ギリシア語
        Option('pron', value='PRON', help='音読の発音: attic (古典期アッティカ式。既定) / modern (現代ギリシア語式)'),
    ),
    'bo': (   # 古典チベット語
        Option('pron', value='PRON', help='発音: lhasa (ラサ方言。既定) / chant (読誦式: 語末の母音を変えず -l -n を読む)'),
    ),
}


def getopt_spec(options):
    """getopt の書式: (短い名前の文字列, 長い名前のリスト)"""
    short = ''.join(o.short + (':' if o.value else '') for o in options if o.short)
    long = [o.long + ('=' if o.value else '') for o in options]
    return short, long


def value_names(options):
    """値を取るオプションのコマンド行での名前 ({'-t', '--tts', '--html', …})"""
    return {name for o in options if o.value for name in o.names}


def help_text(options, width=24):
    """説明の文: 名前 (と値) と説明を揃えて1行ずつ"""
    lines = []
    for o in options:
        names = ', '.join(o.names) + ('=' + o.value if o.value else '')
        text = o.help.split('\n')
        head = '  ' + names
        if len(head) + 1 > width:
            lines.append(head)
            head = ''
        lines.append(head.ljust(width) + ' ' + text[0])
        lines.extend(' ' * (width + 1) + rest for rest in text[1:])
    return '\n'.join(lines)
