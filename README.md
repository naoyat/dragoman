# dragoman

古典語・現代語の文を辞書引き・構文解析して、日本語の逐語訳を付けるプログラムです（日本語の古文は現代語に組み立て直します）。語ごとの辞書引きと文法の解説、
並列・係り先・前置詞句・格の枠・関係節・間接疑問の解析、日本語の動詞の活用を含む逐語訳、音読ができます。
解析の結果はノート（HTML / PDF。行間逐語訳と構造の図）に清書できます。また、解析から言語に依らない「文の枠」を取り出し、
そこから別の言語の文を作り直す試み（対応している21言語と英語・日本語の間。チベット語・アイヌ語・古文・英語は出口だけ）もあります
（下の「文の生成」）。

```
$ echo "लड़के ने किताब पढ़ी।" | python3 dragoman.py -w

लड़के ने किताब पढ़ी।  (laṛke ne kitāb paṛhī.)

1 VERB FOUND: पढ़ी

  पढ़ी (indicative 3sg)
    Nom:
      लड़के
        ने
    Acc:
      किताब

  →  少年,息子が / 本を / 読んだ,学んだ
```

## 対応している言語

| 言語 | `--lang` | 語形の解析・辞書 | 評価 (Universal Dependencies の主語・目的語の再現率) | 音読 | 詳しく |
|---|---|---|---|---|---|
| ラテン語 | `la` | 手作りの辞書 + Wiktionary、品詞タガー、マクロンの推定 | PROIEL (カエサル): 主語 47%・目的語 56% | MBROLA / espeak-ng / Piper | [docs/latin.md](docs/latin.md) |
| 古典ギリシア語 | `grc` | Wiktionary、Morpheus | 新約聖書: 主語 62%・目的語 50% | MBROLA (古典式 / 現代式) | [docs/greek.md](docs/greek.md) |
| サンスクリット | `sa` | Vidyut (連声・複合語)、Wiktionary | Vedic: 主語 41%・目的語 54% | MBROLA (in1 / in2) | [docs/sanskrit.md](docs/sanskrit.md) |
| ロシア語 | `ru` | pymorphy3、Wiktionary (訳語・強勢) | SynTagRus: 主語 68%・目的語 46% | say (Milena) | [docs/russian.md](docs/russian.md) |
| 聖書ヘブライ語・アラム語 | `he` | OSHB、HebrewLexicon (Strong・BDB) | (OSHB の解析の選択 97%) | say (Carmit) | [docs/hebrew.md](docs/hebrew.md) |
| アラビア語 (MSA) | `ar` | CAMeL Tools、Wiktionary | PADT: 主語 66%・目的語 54% | say (Majed) | [docs/arabic.md](docs/arabic.md) |
| ペルシア語 | `fa` | 自前の規則 + Wiktionary | PerDT: 主語 61%・目的語 48% | espeak-ng | [docs/persian.md](docs/persian.md) |
| ヒンディー語 | `hi` | Wiktionary の変化表 | HDTB: 主語 53%・目的語 31% | say (Lekha) | [docs/hindi.md](docs/hindi.md) |
| ウルドゥー語 | `ur` | ヒンディー語の語形に引き当てる | UDTB: 主語 40%・目的語 32% | espeak-ng | [docs/urdu.md](docs/urdu.md) |
| 古典チベット語 | `bo` | botok で語に分ける、Hill & Garrett の品詞辞書・Wiktionary・蔵英辞書。語順のまま日本語に | Hill & Garrett のコーパス: 語の区切り 87%・格助詞 87% | MMS-TTS / espeak-ng (ラサ方言の音素・声調) | [docs/tibetan.md](docs/tibetan.md) |
| インドネシア語・マレー語 | `id` / `ms` | 接辞の解析 (meN- の鼻音の交替など) + Wiktionary | UD Indonesian: 主語 67%・目的語 69% | say (Damayanti / Amira) | [docs/indonesian.md](docs/indonesian.md) |
| タガログ語 | `tl` | 焦点の接辞とアスペクトの解析 + Wiktionary。焦点の名詞を主題「は」に | UD Tagalog: 主語 53%・目的語 37% | espeak-ng (インドネシア語の音声で代用) | [docs/tagalog.md](docs/tagalog.md) |
| ドイツ語 | `de` | spaCy (de_core_news_sm。品詞・格・依存関係) + Wiktionary。動詞の組 (枠構造)・分離動詞をまとめる | UD German-GSD: 主語 90%・目的語 80% | say (Anna) | [docs/german.md](docs/german.md) |
| フランス語 | `fr` | spaCy (fr_core_news_sm) + Wiktionary。格は役割から、接語の代名詞・複合過去・部分冠詞 | UD French-GSD: 主語 79%・目的語 69% | say (Thomas) | [docs/french.md](docs/french.md) |
| トルコ語 | `tr` | zeyrek (形態素解析) + Wiktionary。格・所有・時制・人称の接尾辞、分詞の関係節、副動詞。語順のままの訳も | UD Turkish-BOUN・Kenet: 主語 40%・目的語 37% | say (Yelda) | [docs/turkish.md](docs/turkish.md) |
| モンゴル語 | `mn` | 辞書 (Wiktionary) と規則で格・時制・副動詞・分詞の接尾辞を分ける。語順のままの訳も。ラテン文字の転写も読む | UD Mongolian-GDUD (88文): 主語 73%・目的語 31% | — | [docs/mongolian.md](docs/mongolian.md) |
| フィンランド語 | `fi` | spaCy (fi_core_news_sm。15格・依存関係) + Wiktionary。否定動詞 ei・完了・話法をまとめ、目的語の属格・分格を「を」に | UD Finnish-TDT: 主語 70%・目的語 48% | say (Satu) | [docs/finnish.md](docs/finnish.md) |
| 古英語 | `ang` | Wiktionary の変化表 + 綴りの揺れの読み替え・語尾と複合語の推定。冠詞の掛け先・助動詞と本動詞・否定の縮約。生成も | ISWOC: 主語 63%・目的語 52% | espeak-ng (再建音の音素で。ドイツ語の表を土台にした古英語の音素表) | [docs/oldenglish.md](docs/oldenglish.md) |
| ハワイ語 | `haw` | Wiktionary + 手で書いた小辞の表。語順 (VSO) と小辞 (ua・i / iā・ʻo・o / a …) から役割を決める。ʻokina・長音符の無い綴りも | (自作の例文) | espeak-ng (haw の音声に ʻokina・長母音・強勢の音素で) | [docs/hawaiian.md](docs/hawaiian.md) |
| 韓国語 | `ko` | kiwipiepy (形態素解析) + Wiktionary (漢字語の漢字も)。助詞から格、語尾から時制・接続、補助用言をまとめる | UD Korean-Kaist: 主語 69%・目的語 83% | say (Yuna) | [docs/korean.md](docs/korean.md) |
| アイヌ語 | `ain` | 人称の接辞の分解 + 手作りの語彙表・Wiktionary。語順のまま日本語に | — | — | [docs/ainu.md](docs/ainu.md) |
| 古文（平安の和文） | `kobun` | MeCab + 中古和文UniDic。品詞分解して現代語に組み立て直す | — | say (Kyoko) | [docs/kobun.md](docs/kobun.md) |

評価は関係節の中の主語・目的語も数えます（UD では関係代名詞が関係節の主語・目的語。2026-10-12 から）。
2026-10-13 に評価ツールの不具合（複合語の行の範囲を次の文の語にも当てていた）を直して測り直しました
（書かれたとおりの語を渡す言語: アラビア語・ペルシア語・ウルドゥー語・インドネシア語・タガログ語・ドイツ語・フランス語）。
ラテン語以外は作りかけです。日本語の訳語の無い語は、英語の語義（Wiktionary・CAMeL Tools）を英語 → 日本語の表で
置き換えます（下の「訳語」）。それでも訳せない語は英語のまま出ます。

## セットアップ

Python 3.11 以降。日本語の動詞の活用に MeCab（辞書は UniDic）を使います。ノートの PDF には Google Chrome（または Chromium）を使います。

```
pip install -r requirements.txt     # または pip install -e .  (dragoman コマンドができる。任意の依存は .[russian] など)
```

これだけでラテン語（手作りの辞書、約1,500語）が読めます。ほかの言語と追加の辞書・コーパスは、言語ごとの文書の
手順でデータを用意します。データは `~/.local/share/dragoman-data/`（環境変数 `DRAGOMAN_DATA` で変更可。旧名の
`LATIN_DATA` と `~/.local/share/latin-data` も読む）に置き、リポジトリには入れません。

英語 → 日本語の訳語の表は、日本語版 Wiktionary の抽出（[kaikki.org の ja-extract](https://kaikki.org/dictionary/rawdata.html)、
`ja-extract.jsonl.gz`）と [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html)（`JMdict_e.gz`、EDRDG、CC BY-SA 4.0。任意）を
データの置き場所に置いて作ります:

```
curl -L -o ~/.local/share/dragoman-data/JMdict_e.gz http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz
python3 tools/build_en_ja.py        # → ~/.local/share/dragoman-data/en-ja.sqlite (Wiktionary 約3.6万 + JMdict 約3.8万)
```

## 使い方

```
./dragoman.py [LANG] [オプション] [ファイル...]   # ファイル (無ければ標準入力) を解析 (python3 dragoman.py / python3 -m dragoman でも)
./dragoman.py hi -e "लड़के ने किताब पढ़ी।"        # 引数の文を解析 (-e は何度でも)
./dragoman.py he --help                          # 言語ごとのオプション
./dragoman.py la                                 # ラテン語の対話モード (変化表・マクロンの推定)
./dragoman.py --languages                        # 対応している言語の一覧
```

言語は最初の引数（`grc` など。`--lang=grc` でも）で指定します。知らない符号なら言語の一覧を出して終わります。
`auto` は省略したときと同じく文字から推定します（推定した言語は標準エラー出力に「推定した言語: ru (ロシア語)」と出す）。
言語を省略すると文字から推定します（ラテン文字 → ラテン語、ギリシア文字 → 古典ギリシア語、キリル文字 → ロシア語（ө・ү があればモンゴル語）、
ヘブライ文字 → ヘブライ語、アラビア文字はウルドゥー語の字（ٹ ڈ ڑ ں ے ھ）があればウルドゥー語、ペルシア語の字の多さで
ペルシア語かアラビア語、デーヴァナーガリーはヒンディー語らしい語の有無でヒンディー語かサンスクリット、チベット文字 →
古典チベット語、インドネシア語らしい語のあるラテン文字はインドネシア語かマレー語、タガログ語らしい語（ang, ng, mga, ay …）
があればタガログ語、ğ・ı・ş・İ かトルコ語らしい語（bir, ve, bu, için …）があればトルコ語、フィンランド語らしい語（ja, on, ei, että …）があればフィンランド語、フランス語らしい語（le, la, est, que, pas …）かアクセント記号・エリジオン（é・è・l'）があればフランス語、ドイツ語らしい語（der, die, das, und, ist …）かウムラウト・ß があればドイツ語、ハングル → 韓国語、かな交じりの日本語は古文）。

| 共通のオプション | |
|---|---|
| `-w`, `--no-word-detail` | 語ごとの辞書引きの結果を表示しない |
| `-D`, `--descendants` | ほかの言語に入った語（子孫語）も表示する |
| `-E`, `--etymology` | 語源も表示する |
| `-s`, `--speech` | 音読する（`-t BACKEND` で方式: mbrola / espeak / piper / say） |
| `-r`, `--romanize` | 語ごとの辞書引きの結果に転写を添える |
| `--no-explain` | 初学者向けの解説（動詞の型・語根・連語形など）を出さない |
| `--english-glosses` | 英語の訳語を日本語に置き換えない |
| `--sentence-per-line` | 改行も文の区切りにする（歌詞・詩など、行末に句点の無い行。行末がカンマなら次の行に続ける） |
| `--html=FILE` | 解析結果をノート（HTML）に清書する（下の「ノート」） |
| `--pdf=FILE` | ノートを PDF にする（Google Chrome / Chromium のヘッドレス印刷） |
| `--marks` / `--legend` / `--provenance` | ノートに確かさの印 / 印の凡例 / 再現条件を載せる |
| `--gaps` | 解析の穴の一覧だけを出す（辞書に無い語・推測した語形・構造の外の語・述語の見つからない文の数）。本文は出さず、語は理由ごとに重複を除いて並べ替える。手元だけで読むテキスト（歌詞など）の穴を、本文を渡さずに伝えるため |
| `--compare=LANGS` | ノートに要素ごとの比較の表（言語の符号をカンマで: `la,grc,ja`。`all` で全部: la grc sa ru de fi en id tl ar he fa hi ur tr mn ko ain bo ja kobun） |

言語ごとの例文とその訳は `python3 tools/samples.py --lang=xx` で、解析の精度は `python3 tools/ud_eval.py --lang=xx` で
見られます（評価用のツリーバンクは言語ごとの文書を参照）。

## ノート (HTML / PDF)

`--html=FILE` / `--pdf=FILE` で、解析結果を読みやすい形に清書します（どの言語でも。`-D`・`-E`・`-r` の情報も入ります）。

```
./dragoman.py la -D -E --html=note.html -e "Puella rosam pulchram in hortō videt."
./dragoman.py he -r --pdf=note.pdf FILE
```

文ごとに次のものを並べます。HTML ではページの上のチェックボックスで表示する部分を選べ、印刷にも効きます。

* 訳: 節ごとの逐語訳（原文の直下に）
* 行間逐語訳: 語ごとに 原文 / 転写 / 見出し語 / 文法 / 訳語 を縦に揃える。語の色は端末と同じ（主格 青、対格 黒、属格 緑、
  奪格 黄、与格 赤紫、動詞 赤）
* 図A 弧: 語を原文の順に並べ、述語から主語・目的語・前置詞句へ、名詞から修飾語・属格へ、先行詞から関係節へ弧を張る
  （関係節・間接疑問・独立奪格は点線、関係節の空所も）。離れた語の係り先が一目で分かる
* 図B 入れ子: 述語 → 格の枠 → 語 の構造（端末の字下げの表示と同じ）を箱の入れ子で
* 語の詳細: 読みの候補ごとの見出し語・品詞・文法・訳語と、解説・子孫語（`-D`）・語源（`-E`）

次のものは、オプションで指定したときだけ載せます。

* `--marks` 確かさの印: 読み手が確かめたほうがよい所（橙: 辞書に無い・推測した語形・構造に入らなかった語）と、参考
  （灰: 品詞の違う読みの候補が複数・格が決まらない・主語は動詞の語尾から）に札と点線の下線を付ける
* `--legend` 印の凡例と見本の文を冒頭に（`--marks` も入る）。PDF では凡例の後で改ページし、`--provenance` があれば
  再現条件はそのページの下部に
* `--provenance` 再現条件を末尾に: コードの版（git のコミット）・オプション・ライブラリの版と、実際に使ったデータのファイル
  （更新日・大きさ）。同じ文の結果が変わったときに、実装の変更か辞書の更新かを切り分けられる

* `--compare=LANGS` 要素ごとの比較: 文の枠の要素（述語・主語・目的語・前置詞句 …）を、選んだ言語がそれぞれどう表すかの表
  （要素が行・言語が列。格・前置詞・語順・助詞、書かれていない主語を補うか）。述語の表し方は冒頭に1回。
  端末では `python3 tools/generate.py --compare` でも

HTML のチェックボックスは画面で一時的に隠すためのもので（ブラウザで印刷するときにも効く）、`--pdf` には効きません。
PDF に載せるものはオプションで選びます。

右から左の文字（ヘブライ語・アラビア語など）は逐語訳を右から並べ、図A を左右反転します。PDF は HTML を Chrome で
印刷したもの（A4）。古文のように独自の表示の言語は、表示をそのまま載せます。

## カタカナ読み

`--kana` で、見出しの下に文のカタカナ読み（発音に忠実に。語の区切りは空白）を添えます。`--kana-only` ならカタカナ読みだけを
出します。対応している言語はラテン語・古典ギリシア語・サンスクリット・古英語・ハワイ語・フランス語（ほかの言語は順に移す。
docs/katakana.md）。

```
./dragoman.py fr --kana-only -e "Emmanuel Macron parle avec Juliette."
  カナ: エマニュエル マクロン パルル アヴェック ジュリエット
./dragoman.py la --kana-only -e "Gallia est omnis divisa in partes tres."
  カナ: ガリア エスト オムニス ディーウィーサ イン パルテース トレース
```

読みは解析で選んだ語の綴りから作るので、長音符・マクロンの無い入力でも長母音を補います（ラテン語の格の決まった dīvīsa、
ハワイ語の ia → iā）。`--kana-long=phonetic` で実際に長く発音される母音にも「ー」（既定は音素として長い母音だけ。フランス語は
phonetic）、`--kana-wa=ウァ` で [wa] を「ウァ」（西洋古典学の慣習: ミネルウァ。既定は「ワ」）。

## macOS の右クリックのメニューから (サービス)

どのアプリでも、テキストを選んで右クリックのメニュー（「サービス」の下）の「dragoman で解析」から、解析結果のノート（HTML）を
ブラウザで開けます。言語は文字から推定します（短い選択では取り違えることがある）。

```
python3 tools/macos/install_service.py     # ~/Library/Services/dragoman で解析.workflow を作る
```

クイックアクション（Automator）が `tools/macos/dragoman-service.sh` を呼び、選択したテキストを `$TMPDIR/dragoman-service/` に書いて
`dragoman.py --html` で清書します。サービスはログインシェルの PATH を引き継がないので、`install_service.py` を実行した Python
（conda の環境など）をそのまま書き込みます（`--python=PATH` で変えられる）。キーボードショートカットはシステム設定の
「キーボード → キーボードショートカット → サービス」で割り当てます。

## 訳語

訳語は、各言語の辞書の日本語の訳語（日本語版 Wiktionary、その訳語の表を逆に引いたもの、手で決めた基本語）を使い、
無ければ英語の語義を英語 → 日本語の表（`core/en_ja.py`）で置き換えます。英語の語義は品詞ごとに引き、訳せた最初の語義の
一番の訳語を使います（go,travel → 行く。動詞は日本語の活用に通すため辞書形のものだけ）。元の英語は項目の `ja_en` に残します。
表は日本語版 Wiktionary の英語の項目を先に使い、無い語を JMdict（よく使う語の印・頻度の順位の高い見出し語から）で補い、
順位では決めにくい基本語（minister → 大臣 など）は手で決めます。UD の各言語の先頭 300 文で、名詞・動詞・形容詞の訳語に
英語が残る割合は、ロシア語 49% → 6%、アラビア語 70% → 7%、古典ギリシア語 84% → 21%、ヒンディー語 68% → 24%、
サンスクリット 89% → 31% になりました。残りの多くは固有名詞・民族名（Corinthian）、説明的な語義（comparative degree of …）、
辞書に無い語です。

## 文の生成 (文の枠)

実用の翻訳ではなく、言語の理解のための試みです。解析の結果（述語と格の枠）から、言語に依らない「文の枠」
（`dragoman/generate/frame.py`。述語・時制・法・態・人称と、主語・目的語・受け手・前置詞句などの役割ごとの名詞句、
関係節・間接疑問・不定詞句・独立奪格・分詞句、節のつなぎ）を取り出し、そこから文を作り直します。

| | 入口（文 → 文の枠） | 出口（文の枠 → 文） |
|---|---|---|
| ラテン語 | 解析器 | 辞書（手作りの辞書・Wiktionary）を逆に引いて語形を作る |
| 古典ギリシア語 | 解析器 | Wiktionary の語形を逆に引く。冠詞、アオリスト、属格独立、前接語のアクセント、後置のつなぎ（δέ・γάρ） |
| ロシア語 | 解析器 | pymorphy3。完了体の未来、存在・所有の文（у меня есть） |
| サンスクリット | 解析器 | Vidyut。分詞・動形容詞、処格独立、iti の直接話法、双数 |
| インドネシア語 | 解析器 | 語根と派生形 (meN-・di-・ber-。辞書の対応か鼻音の交替の規則)、yang の関係節、重複の複数、時は telah・akan |
| タガログ語 | 解析器 | 焦点 (目的語があれば対象焦点、物が移る動詞は移動物焦点) と ang / ng / sa、アスペクト (重複と -in-)、繋ぎ、関係節 |
| アラビア語 (MSA) | 解析器 | CAMeL Tools の生成器で格・数・性・定冠詞を指定。動詞 - 主語 - 目的語、لَمْ + 要求法、名詞文と لَيْسَ、関係節 الَّذِي と代名詞の接尾辞 |
| ペルシア語 | 解析器 | 辞書の現在語幹・過去語幹から。主語 - 目的語 + را - 動詞 (SOV)、می・ن、خواه + 過去語幹、命令 ب、受動 + شدن、エザーフェ、関係節 ی که |
| ヒンディー語・ウルドゥー語 | 解析器 | 同じ文法で文字だけ違う (辞書のウルドゥー文字の綴り + 規則の語尾)。SOV、後置詞と斜格、他動詞の完了相の ने と目的語への一致、習慣相 + है/था、未来 -एगा、命令 -ओ・禁止 मत、受動 + जाना、関係節 जो/जिसे |
| アイヌ語 | 解析器 | 解析側の手作りの語彙表 (日本語の訳語) と Wiktionary。SOV、人称の接辞 ku=・e=・ci=・en=、状態の動詞 (pirka)、否定 somo・禁止 iteki、繋辞 ne、後置詞 ta・un・orowa、受動 a=、ラテン文字とカタカナ |
| 古典チベット語 | 解析器 | 辞書の英語の訳語と時制の語幹の表から。チベット文字 (pyewts で Wylie から) と Wylie の2行。SOV、能格 kyis/gyis/gis/-s・属格・終止の助詞 (ngo/do/no …) の形、否定 mi/ma、繋辞 yin/yod、関係節は名詞化 + 属格、受動は能動に |
| 聖書ヘブライ語 | 解析器 | OSHB に現れた語形 (無ければ binyan の型から)。動詞 - 主語 (分詞なら主語が先)、אֶת־、冠詞と前置詞の縮約、現在は分詞、אֲשֶׁר の関係節 |
| ドイツ語 | 解析器 | Wiktionary の変化表 (名詞の格・動詞の人称と時制)。定冠詞と形容詞の弱変化、主文の動詞は2番目、分離動詞 (ruft … an)、完了・受動・未来、関係節 (der / die / das …) は動詞を最後に |
| フランス語 | 解析器 | Wiktionary の変化表 (名詞の複数・形容詞の性数・動詞の人称と時制)。冠詞と縮約 (au・du)・エリジオン、前後に置く形容詞、接語の代名詞 (je t'aime)、複合過去 (avoir / être)・半過去・受動、ne … pas、il y a、関係節 qui / que |
| フィンランド語 | 解析器 | Wiktionary の変化表 (15格・動詞の人称と時制)。目的語の属格・分格 (否定・継続の動詞)、否定動詞 ei、所有 (Minulla on …)、関係節 joka |
| トルコ語 | 解析器 | 規則: 母音調和の格の接尾辞・有声化 (kitabı)・母音の脱落 (şehri)、時制と人称 (-dı・-iyor・-acak)、否定 -ma、受動、分詞の関係節 (-an・-dığı) |
| モンゴル語 | 解析器 | 規則: 4通りの母音調和の格の接尾辞と動詞の語尾、つなぎの母音、否定 -гүй、繋辞は書かない (過去 байсан・否定 биш)、分詞の関係節 |
| 韓国語 | 解析器 | 規則: 한다体の活用 (過去の母音の縮約・ㅂ/ㄷ/르 不規則)、助詞の交替 (이/가・을/를)、連体形の関係節、名前はハングルに (마르쿠스) |
| 英語 | — | 規則と語形の表 |
| 日本語 | MeCab + UniDic と規則（長い文は GiNZA の係り受け） | 動詞の活用 (core/japanese.py)、連体修飾節、〜か・〜とき |
| 古文 | — | 現代語の訳語を古語の活用 (四段・上二段・下二段・変格) に直す、けり・ず・む・る/らる・なり、已然形 + ば、係り結びの間接疑問 |

閉じた語類（代名詞・前置詞・つなぎの語・時制）はラテン語の形を中立の形に使い、名詞・動詞などの語は元の言語のまま持って、
作るときに英語の訳語を仲立ちに置き換えます（`transfer.py`。元と同じ言語に戻すときは置き換えず、元の語形・定・不定・性・
タガログ語の焦点を保つ）。名前の表に無い固有名詞は綴りを各言語の文字に写します（`name_script.py`。慣用の綴りとは限らない）。

`--compare`（ノートと `tools/generate.py`）の比較の表は、要素ごとに各言語の形と手段を並べ、選んだ語の辞書の語義の幅も
添えます（pirka「良い・適当な・気持ちのいい」、me tog「花・天然痘」。訳語は一対一に対応しない）。

```
python3 tools/generate.py "Puella rosam pulchram in hortō videt."            # ラテン語 → 文の枠 → 全部の出口の言語
python3 tools/generate.py --to=grc,ja latin/texts/fabulae_faciles/perseus.txt
python3 tools/generate.py --from=grc "ἡ κόρη τὸ καλὸν ῥόδον ἐν τῷ κήπῳ βλέπει."   # --from=ru / sa / grc / fa / hi / ur / ar / he / id / tl / de / fi / tr / mn / ko / ja
python3 tools/generate.py --from=ja "少女が庭で美しい薔薇を見た。"
python3 tools/generate.py --gaps FILE   # 言語ごとに訳語の見つからない語の一覧だけ (生成文・元の文は出さない)
```

元の言語に戻した文が元の文と同じ語になれば ✓ を付けます。Fabulae Faciles（Ritchie、Project Gutenberg）でラテン語に戻る文は、
ペルセウス 80/109、ヘラクレス 266/394、アルゴナウタイ 114/206、ウリクセス 110/200。

語の置き換えの表はデータの置き場所に作ります（いずれも手元だけで使う）:

```
python3 tools/build_latin_english.py               # la-en.tsv (ラテン語 → 英語。kaikki-Latin.jsonl.gz から)
python3 tools/build_english_index.py --lang=ru     # ru/en-index.tsv (英語 → ロシア語。sa・grc・id・tl・ang (古英語) も)
python3 tools/build_sanskrit_apte.py               # sa/en-index-apte.tsv (Apte の英梵辞典。任意)
python3 tools/build_ja_transitivity.py             # ja-transitivity.tsv (日本語の動詞の自他。日本語の入口で)
python3 tools/build_ja_en.py                       # ja-en.tsv (和英。JMdict から。手作りの辞書の日本語に合う英語を先に)
python3 tools/build_name_index.py --lang=all       # <lang>/names.tsv (固有名詞: Jesus → Иисус・Ἰησοῦς・يَسُوع …)
python3 tools/build_lemma_counts.py --lang=all     # <lang>/lemma-counts.tsv (UD の見出し語の出現数。よく使う語を先に)
```

訳語は、元の語の英語の訳語 (Wiktionary) を仲立ちに選びます。手作りの辞書の一番の日本語の訳語と和英で合う英語を先にし
(tollō「取り去る」→ remove。lift up より)、候補の語の筆頭の語義・コーパスでの出現数 (εἰρήνη を ἡσυχία より) で並べます。
固有名詞は Wiktionary の英語の名前を経て各言語の名前に (Iēsus → Jesus → Иисус)。

日本語の入口の長い文には GiNZA（`pip install ginza ja-ginza`）を使います（無ければ MeCab と規則だけで）。

## ラテン文字への転写

ラテン文字以外の言語では、`-r` / `--romanize` で語ごとの辞書引きの結果に転写を添えます（`tools/samples.py -r` は文にも）。

| 言語 | 転写 | 例 |
|---|---|---|
| 古典ギリシア語 | 学術的な転写の簡略版 | ἐν ἀρχῇ ἦν ὁ λόγος → en archêi ên ho lógos |
| ロシア語 | Wiktionary の強勢を付けた学術転写 | Девочка → Dévočka |
| ヘブライ語 | 母音記号からの転写 | וַיֹּאמֶר → wayyōʾmer |
| アラビア語 | 解析で補った母音記号からの転写（見出しの行には常に添える） | ذهب الولد → ḏahaba al-waladu |
| ペルシア語 | Wiktionary のイラン式の転写に、解析で推定したエザーフェを補う | کتاب علی → ketâb-e ali |
| ヒンディー語 | 辞書の語は Wiktionary の転写、それ以外はデーヴァナーガリーから規則で | लड़का → laṛkā |
| ウルドゥー語 | 引き当てたヒンディー語の語形から（短母音を書かないウルドゥー文字からは作れない） | لڑکا → laṛkā |
| サンスクリット | 語の表示がもとから IAST（デーヴァナーガリーは文の行に） | — |
| 古典チベット語 | ワイリー式（EWTS） | བུ་མོ → bu mo |

### 転写からの入力

逆向きに、転写で書いた文も読めます（言語は指定する。ラテン文字だけの文はラテン語と推定されるので）。
転写から綴りが一意に戻らない所は候補を作り、辞書にある綴りを選びます。

| 言語 | 受け付ける転写 | 例 |
|---|---|---|
| ロシア語 | 学術転写・ISO 9・英語式（zh・kh・ts・shch・ya）。e → е / э、ts → ц / тс、' → ь / ъ は辞書で | `ru -e "Ja ljubljú tebjá."` → Я люблю тебя. |
| 古典ギリシア語 | 学術転写（ē ō・ê ô・h・ēi → ῃ）と Beta Code。長音の印の無い文では ε/η・ο/ω を辞書で | `grc -e "en archêi ên ho lógos"`・`e)n a)rxh=\| h)=n o( lo/gos` |
| ヒンディー語 | IAST・ISO 15919（ē ō・ṁ・m̐・r̥・ṛ = ड़）・Wiktionary 式（mẽ・hū̃）。内在の a は書いても書かなくても。子音の連続（結合文字か a の脱落か）と子音の前の鼻音は辞書で | `hi -e "laṛkā kitāb paṛhtā hai."` → लड़का किताब पढ़ता है। |
| 古典チベット語 | Wylie（pyewts でチベット文字に） | `bo -e "bu mos me tog mthong ngo /"` |
| アイヌ語 | カタカナ（小書きの ㇰ・ㇼ・ㇷ゚ などを含む）→ ラテン文字。小書きの仮名があれば言語の推定もアイヌ語に | `ain -e "マッカチ ピㇼカ。"` → matkaci pirka. |

アイヌ語の見出しの下にはカタカナを添えます（ainu-utils があれば）。

文の生成の出口では、アラビア語・ヘブライ語・ペルシア語・
ヒンディー語・ウルドゥー語・チベット語は文字の行に転写の行を、アイヌ語はラテン文字の行にカタカナの行を添えます。

## テスト

```
python3 -m unittest discover -s test -p '*_test.py'
```

* 追加データが無い環境でも動きます（データが必要なテストはスキップ）。
* `test/golden_test.py` は、テキストの解析結果を正解ファイルと比べる回帰テストです（手作りの辞書だけで、
  タガーを使わずに解析）。意図して解析結果を変えたときは `UPDATE_GOLDEN=1 python3 test/golden_test.py`
  で更新し、差分を確認してからコミットします。
* `test/corpus_test.py` は、全テキストを解析から表示まで例外なく通せるかを確かめます。
* `test/generate_golden_test.py` は、`samples/samples.txt` を全言語で生成した結果を言語ごとの正解ファイル
  （`test/golden/generate/`）と比べる回帰テストです。更新は `UPDATE_GOLDEN=1 python3 test/generate_golden_test.py`。

## 構成

```
dragoman.py              入口 (python3 -m dragoman と同じ。--lang=la|grc|sa|ru|he|ar|fa|hi|ur。省略すると文字から言語を推定)
dragoman/                パッケージ
  main.py                入口の本体 (言語の推定と振り分け)
  core/                  言語に依存しない共通部分
    cli.py                 コマンドの骨組み (共通のオプション・見出しの行・音読・表示。言語ごとの違いは <言語>/command.py)
    options.py             オプションの定義 (名前・値・説明。getopt の書式・値を取るオプション・説明の表示はここから)
    paths.py               データの置き場所
    analyzer.py            解析の骨組み (並列・係り先・前置詞句・独立奪格・分詞句・不定詞句・述語の検出、関係節・間接疑問)
                           → SentenceAnalysis
    language.py            言語ごとの設定 (接続詞・繋辞・否定・格の助詞・独立奪格の格、辞書を引く関数など)
    render.py              解析結果の表示
    notebook.py            ノート (HTML / PDF): 行間逐語訳・弧の図・入れ子の図・訳・語の詳細
    Word.py Item.py AndOr.py PrepClause.py Predicate.py   解析の要素と訳
    Absolute.py Participle.py Infinitive.py               独立奪格・分詞句・不定詞句
    Relative.py Question.py                               関係節・間接疑問
    japanese.py verb_flags.py                             日本語の動詞の活用
    wiktionary_import.py keys.py                          Wiktionary (kaikki.org) の項目の取り込み、照合用のキー
    descendants.py etymology.py languages.py              子孫語・語源の表示 (言語名の日本語表記)
    speech.py                                             音声合成 (MBROLA / espeak-ng / Piper / say)
  latin/                   ラテン語
    analyzer.py profile.py 辞書引き・品詞タガーによる前処理と、ラテン語の設定
    latindic.py words.py   辞書 (手作りの辞書の読み込みと検索)
    data/                  手作りの辞書 (*.def。パッケージに同梱)
    latin_noun.py latin_adj.py latin_verb_reg.py ...      変化形の生成
    wiktionary.py morpheus.py ldt.py rftagger.py          補助辞書と品詞タガー
    orthography.py katakana.py                            綴りの流儀の吸収、固有名詞のカタカナ表記
    macronizer.py hidden_quantity.py catalog.py           マクロンの推定、テキストの目録
    latin_phonology.py latin_prosody.py                   発音と韻律
  greek/                   古典ギリシア語 (表記の正規化、Wiktionary の取り込み、辞書、冠詞の処理、格の読み替え、
                           発音と韻律)
  sanskrit/                サンスクリット (文字の変換、Vidyut による語形の解析と連声を戻す辞書引き、複合語、Wiktionary の訳語、
                           発音と韻律)
  russian/                 ロシア語 (pymorphy3 による語形の解析、前置詞の格、繋辞の補い、Wiktionary の訳語と強勢)
  hebrew/                  聖書ヘブライ語 (OSHB の語形の解析、接頭辞・人称接尾辞の切り分け、格の代わりの手がかり、転写)
  arabic/                  アラビア語 (CAMeL Tools による語形の解析と読みの選択、接語の切り分け、連語・inna・名詞文、
                           格の語尾を補った形と転写)
  persian/                 ペルシア語 (規則による語形の解析: 動詞の語幹・接頭辞・人称語尾、複数・接語。エザーフェの推定、
                           را、複数語の動詞)
  hindi/                   ヒンディー語 (Wiktionary の変化表による語形の辞書、schwa の脱落を含む転写、動詞の並び、後置詞と能格)
  urdu/                    ウルドゥー語 (ウルドゥー文字の語をヒンディー語の語形に引き当てる綴りの骨組み。解析は hindi/)
  tibetan/                 古典チベット語 (ワイリー式の転写、botok による語の区切りと補正、格助詞と能格、動詞の語幹の時制、
                           語順のままの日本語訳)
  indonesian/              インドネシア語 (接辞・接語・重複の解析、語順からの格の枠、受動、関係節、見えない繋辞)
  malay/                   マレー語 (解析は indonesian/。マレー語の辞書の項目を先に)
  tagalog/                 タガログ語 (焦点の接辞・アスペクトの重複の解析、ang / ng / sa と焦点からの格、繋ぎ、関係節)
  german/                  ドイツ語 (spaCy の格・依存関係による語の項目、冠詞の掛け先、動詞の組 (完了・受動・未来・話法の助動詞)、
                           分離動詞、前置詞の格による訳の選択、es gibt)
  french/                  フランス語 (spaCy の語の項目と読み誤りの補正、役割からの格、接語の代名詞、動詞の組 (複合過去・受動・
                           話法の助動詞)、縮約形・部分冠詞・de 句の属格、il y a)
  turkish/                 トルコ語 (zeyrek の解析の文脈による選択、格・所有・時制・人称、繋辞の補い、分詞の関係節、副動詞、
                           語順のままの訳)
  mongolian/               モンゴル語 (辞書と規則による格・時制・副動詞・分詞の切り分け、不定の目的語、繋辞の補い、関係節、
                           語順のままの訳、ラテン文字の転写からの入力)
  finnish/                 フィンランド語 (spaCy の15格・依存関係による語の項目、目的語の格の読み替え、否定動詞・完了・話法のまとめ)
  oldenglish/              古英語 (Wiktionary の変化表のすべての読み、綴りの鍵と揺れ、冠詞の掛け先、節ごとの動詞・主語の選択、
                           助動詞と本動詞、否定の縮約、関係の þe、呼びかけ)
  hawaiian/                ハワイ語 (ʻokina・長音符の鍵と揺れ、節の頭からの読み (時制と相の小辞・目的語の i / iā・ʻo の句・所有の o / a)、
                           動詞の無い文、音読の音素)
  korean/                  韓国語 (kiwipiepy による形態素の切り分け、助詞からの格・主題、語尾の時制・接続、補助用言、
                           連体形と関係節、二重主語、改訂ローマ字の簡略版)
  ainu/                    アイヌ語 (古いローマ字表記の正規化、人称の接辞の分解、後置詞・助詞から語順のままの日本語訳)
  kobun/                   古文 (中古和文UniDic による品詞分解、助動詞の連なりからの現代語への組み立て直し、係り結び)
  generate/                文の生成 (frame.py 文の枠、transfer.py 英語を仲立ちにした語の置き換え、
                           latin.py greek.py russian.py sanskrit.py english.py indonesian.py tagalog.py arabic.py hebrew.py persian.py
                           hindi.py urdu.py ainu.py tibetan.py
                           japanese.py kobun.py
                           文の枠 → 各言語、
                           from_japanese.py ja_lexicon.py 日本語の文 → 文の枠、connectives.py 節のつなぎ、
                           reverse.py 辞書の語形の逆引き)
tools/                   マクロン推定・音読のコマンド、データの作成・取り込み、評価、文の生成 (generate.py)
latin/                   ラテン語のデータ (テキスト。手作りの辞書は dragoman/latin/data/)
  texts/                 テキストと目録 (catalog.json)。src/ は大文字で長母音を書いた原稿 (make で .txt に)
  scripts/               原稿の変換 (trans.sed: 大文字 → 長母音)
samples/                 解析・翻訳のサンプル (tools/samples.py で表示)
test/                    テスト
```

## 開発の経緯

2013年に、初級ラテン語のリーディングの授業に参加しながら書いたプログラム（latin）を、2026年に Python 3 へ
移行して改修し、解析の骨組みを言語に依存しない形（`core/`）にして、古典ギリシア語・サンスクリット・ロシア語・ヘブライ語・
アラビア語・ペルシア語・ヒンディー語・ウルドゥー語・古典チベット語・インドネシア語・マレー語・タガログ語・アイヌ語・古文・
韓国語・ドイツ語・トルコ語・モンゴル語・フィンランド語・フランス語へ広げ、文の生成（文の枠）とノートの清書を加えたものです。
名前の dragoman は、オスマン帝国などで通訳・翻訳を務めた人々の呼び名（アラビア語 tarjumān から）。
2013年からの開発履歴は、権利関係が不明なテキストを含むため、非公開のリポジトリに保管しています。

## Author

naoya_t (@naoya_t)
http://github.com/naoyat | http://x.com/naoya_t | http://naoyat.hatenablog.jp/

2026年の改修は Claude Opus 5.5（Anthropic）と共同で行いました。

## License

(c) 2013-2026 naoya_t, MIT License（`LICENSE.md`）

追加データ（リポジトリには含まない）はそれぞれのライセンスに従います:
Wiktionary（CC BY-SA）、Latin Macronizer（GPL-3.0）、RFTagger（教育・研究・評価目的なら無償）、
MBROLA（AGPL-3.0）と la1 音声（MBROLA でのみ使用可・販売不可）、Piper の音声（モデルごと）、
Vidyut（MIT）、Morpheus（Perseus）、JMdict（EDRDG、CC BY-SA 4.0）、GiNZA・ja_ginza（MIT）と SudachiDict（Apache-2.0）、
Apte の英梵辞典の電子版（Cologne Digital Sanskrit Dictionaries、CC BY-NC-SA 3.0）、OSHB（本文はパブリックドメイン、解析は CC BY 4.0）、
CAMeL Tools の形態素辞書・曖昧性解消のモデル（GPL v2）、中古和文UniDic（国立国語研究所、CC BY-NC-SA 4.0）、Universal Dependencies の各ツリーバンク（評価用。ツリーバンクごと）。
