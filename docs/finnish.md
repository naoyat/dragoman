# フィンランド語（作りかけ）

フィンランド語の文を、spaCy のフィンランド語モデル（fi_core_news_sm）で品詞・原形・格（15格）・数・人称・時制・所有の接尾辞と
依存関係を付けてから、否定動詞・助動詞を本動詞にまとめ、共通の解析器（格の枠）で日本語に訳します。訳語は Wiktionary の英語の
語義を日本語に直したものです。

```
./dragoman.py fi -e "Minulla on kaksi kissaa."
  →  私には / {二}猫が / いる
./dragoman.py fi -e "Olen lukenut tämän kirjan."
  →  私が / {この}本を / 読んだ
./dragoman.py fi -e "Voin puhua suomea."
  →  私が / フィンランド語を / 話すことができる
python3 tools/samples.py --lang=fi              # サンプル (samples/finnish.txt) の訳
./dragoman.py fi samples/finnish.txt               # 解析の詳細 (-w で語ごとの辞書引きを省く)
```

フィンランド語らしい語（ja, on, ei, että, minulla …）が2つ以上ある文は、言語を省略してもフィンランド語と推定します。

## 格と訳

| 格 | 語尾 | 訳 |
|---|---|---|
| 主格 | — | が |
| 属格 | -n | の（名詞の前から掛かる）。目的語なら「を」（全体の目的語: luin kirjan「本を読んだ」） |
| 分格 | -a / -ä / -ta | 目的語なら「を」（部分・継続の目的語: luen kirjaa「本を読んでいる」）、存在の文の主語なら「が」 |
| 内格 | -ssa / -ssä | で（〜の中で） |
| 出格 | -sta / -stä | から（〜の中から） |
| 入格 | -Vn・-seen | へ（〜の中へ） |
| 所格 | -lla / -llä | で（〜の上で）。olla と組んで所有「〜には〜がある」 |
| 離格 | -lta / -ltä | から |
| 向格 | -lle | に |
| 様格 | -na / -nä | として |
| 変格 | -ksi | に（なる） |
| 欠格・共格・具格 | -tta・-ine・-n | なしで・と共に・で |

* 目的語（依存関係の obj）の属格・分格・主格は対格「を」に読み替える。語ごとの表には元の格を「内格「〜の中で」」のように添える。
* 否定動詞 ei（人称で en・et・ei・emme・ette・eivät と変わる）+ 本動詞は否定（ei tullut「来なかった」）。olla + 過去分詞は完了
  （olen lukenut「読んだ」）。voida「〜できる」・täytyä「〜ねばならない」・haluta「〜したい」+ 不定詞は話法。
* 所有の接尾辞（siskoni「私の姉妹」）は「私の」、関係代名詞 joka は共通の解析器の関係節。

## 準備

```
pip install spacy && python3 -m spacy download fi_core_news_sm      # 約14MB (CC BY-SA 4.0。UD Finnish-TDT で学習)
mkdir -p ~/.local/share/dragoman-data/fi/ud
curl -sL https://kaikki.org/dictionary/Finnish/kaikki.org-dictionary-Finnish.jsonl | python3 tools/build_finnish_dic.py -
```

Wiktionary のフィンランド語の抽出データは約 4.6GB（変化形の項目が多い）あるので、標準入力から読んで見出し語の品詞・英語の語義
だけを `~/.local/share/dragoman-data/fi/wiktionary.sqlite` に残します（26 万項目・約 20MB）（語形変化は spaCy が原形に戻すので、語形の表は作らない）。

評価用に UD Finnish-TDT（CC BY-SA 4.0）の test を `~/.local/share/dragoman-data/fi/ud/` に置きます。spaCy のモデルは
TDT の train で学習されているので、test で測る数字は spaCy の解析の精度に近くなります。

## 評価

```
python3 tools/ud_eval.py --lang=fi
```

UD Finnish-TDT の test（1,555 文）で、主語の再現率 70%・目的語の再現率 48%、述語の検出 92%。目的語の格（属格・分格）を対格に
読み替えるので、格の正解率は測らない。取りこぼしの多くは、目的語が遠くの動詞に掛かる文と、spaCy が目的語の属格を
名詞に掛かる属格と読む文（Poika luki kirjan koulussa の kirjan）。

## まだのこと

* 分格の目的語の継続の読み（luen kirjaa「読んでいる」）を訳に。
* 受動（非人称の受動: kirja luetaan「本が読まれる・人は本を読む」）・条件法・可能法の訳。
* 語順の自由な文（目的語が文頭）。
* 出口（`generate/finnish.py`）: 15格・動詞の人称と時制・否定動詞は辞書の変化表から（辞書は変化形の表も残す。
  所有の接尾辞の形・条件法・可能法は除いて約 520MB）、目的語の属格・分格、所有の構文、関係節 joka。比較の表にも。
  所有の接尾辞（minun kirjani、ystävälleen）は規則で付ける。辞書に無い名前の格語尾（Liisaa・Matin・Greteliä）も規則で。
* 辞書に無い名前はカタカナ（Matti → マッティ、Liisa → リーサ。重子音は ッ）。
