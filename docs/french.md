# フランス語（作りかけ）

フランス語の文を、spaCy のフランス語モデル（fr_core_news_sm）で品詞・原形・性・数・人称・時制と依存関係を付けてから、
動詞の組（複合過去・受動・話法の助動詞）をまとめ、共通の解析器（格の枠）で日本語に訳します。名詞に格の形は無いので、
格は文の中の役割（前置詞の目的語・主語・目的語）から付けます。訳語は Wiktionary の英語の語義を日本語に直したものです。

```
./dragoman.py fr -e "Le garçon lit un livre à l'école."
  →  少年が / 学校[に,で] / 本を / 読む
./dragoman.py fr -e "Je le lui ai donné hier."
  →  私が / {彼,彼女}に / {彼,それ}を / 昨日 / 与えた
./dragoman.py fr -e "La fille qui chante est ma sœur."
  →  歌う{少女,娘}は / 私の姉妹である
python3 tools/samples.py --lang=fr              # サンプル (samples/french.txt) の訳
./dragoman.py fr samples/french.txt                # 解析の詳細 (-w で語ごとの辞書引きを省く)
```

ラテン文字の文は、フランス語らしい語（le, la, les, est, que, pas …）が2つ以上（ドイツ語・トルコ語らしい語より多く）あるか、
アクセント記号（é・è・ê・à …）・エリジオン（l'・qu'）があればフランス語と推定します。

## 扱うもの

* 語の切り出し: エリジオン（l'école → l' école、qu'il → qu' il）、倒置（dit-il → dit il、a-t-il → a il）。
  aujourd'hui・quelqu'un は1語。
* 格: 前置詞の後ろは前置詞の目的語。それ以外は動詞の前なら主語「が」、後ろなら目的語「を」（être・devenir などの後ろは補語）。
  読点・接続詞・関係代名詞で節を区切る。代名詞は形で格が分かる（je 主格、me 対格・与格、le 対格、lui 与格、moi 前置詞の後ろ）。
  接語が2つ並ぶとき（me le・le lui）は le・la・les が対格、ほかが与格。3人称の代名詞は人にも物にも取れる訳
  （il「{彼,それ}が」、le「{彼,それ}を」、l'「{彼,彼女,それ}を」、lui「{彼,彼女}に」）。主語の代名詞の後ろの nous・vous は目的語、
  文頭・節の頭なら主語。動詞の人称は直前の主語の代名詞から（spaCy の読み誤りを直す）。
* 冠詞（le・un・des）は名詞に掛けて訳さない。所有形容詞・指示形容詞（mon・ce・tout …）は「私の」「この」「すべての」。
  前置詞と冠詞の縮約形（au・aux・du・des）は前置詞。動詞のすぐ後ろの du・des は部分冠詞（manger du pain「パンを食べる」）。
  de を取る動詞（parler de「〜について」、venir de「〜から」…）の後ろは前置詞のまま。
* 名詞 + de + 名詞は属格（la maison de mon père「私の父の家」）。
* 動詞の組を助動詞の位置の1語にまとめる: avoir + 過去分詞 → 複合過去「〜した」（avait + 過去分詞 → 大過去）、
  être + 過去分詞 → 移動・変化の動詞（aller・venir・partir …）なら複合過去、ほかは受動（par + 名詞は「〜によって」）、
  話法の助動詞 + 不定詞（pouvoir「〜できる」・vouloir「〜したい」・devoir「〜なければならない」）、aller + 不定詞 → 近い未来。
  不定詞の目的語は不定詞の後ろ（言語の設定 `infinitive_objects_follow`: Nous voulons lire un livre「本を読みたい」）。
* 否定 ne … pas（ne の無い pas も）、ne … jamais「決して」・ne … rien「何も」、il y a + 名詞「〜がある」。
* 関係代名詞 qui・que は共通の解析器の関係節に。que・si・quand … の従属節。
* spaCy の小さいモデルの読み誤りを辞書の語形の表で直す: 主語・関係代名詞 qui の後ろの動詞の形（Le garçon lit … の lit を
  前置詞と、qui chante の chante を形容詞と読む）、動詞の前の接語の代名詞（le lui を冠詞と名詞と読む）、文頭の命令形、
  主語・目的語の位置の形容詞の形（a trouvé preneur）。
* 人名はフランス語の読みのカタカナ（Jean → ジャン、Camus → カミュ、Claude → クロード。英語の名前 John の訳にしない）、
  地名は辞書の訳（Londres → ロンドン）。

## 文の生成 (出口)

ほかの言語の文の枠からフランス語の文を作ります（`generate/french.py`）。比較の表（`tools/generate.py --compare`）にも出ます。

```
python3 tools/generate.py --to=fr "Puella rosam in hortō vīdit."
  フランス語: La fille a vu la rose dans le jardin.
python3 tools/generate.py --to=fr "Ego tē amō. Agricola est. Via longa et lāta est."
  フランス語: Je t'aime.  /  Il y a un agriculteur.  /  La route est longue et large.
python3 tools/generate.py --from=fr "Je le lui ai donné hier."      # 入口から: ラテン語 Eī eum here dedī.
```

* 語は英語を仲立ちにした置き換え（解析器の訳語の表 GLOSSES の語を先に: soldat を drille より）。名詞の性と、名詞・形容詞・動詞の
  語形は辞書の語形の表から（無ければ規則: 複数 -s・-x・-aux、女性 -e、-er 動詞の活用）。
* 名詞句: 定冠詞 le / la / l' / les（元の言語の不定冠詞なら un / une / des）、前に置く形容詞（beau・petit・grand …）と後ろに置く
  形容詞（性・数の一致）、所有形容詞・指示形容詞（mon / ma / mes、ce / cet / cette / ces）、de + 属格、エリジオン（l'école・d'ami）、
  前置詞と冠詞の縮約（au・aux・du・des）。町の名前は à（à Rome）。
* 語順: 主語 - ne - 接語の代名詞（me・te・le・la・lui・leur …。me le・le lui の順）- 動詞 - pas - 過去分詞 - 目的語 - à + 受け手 -
  前置詞句。関係節は qui（主語の空所）・que（目的語の空所）。
* 時制: 現在、完了は複合過去（avoir + 過去分詞。移動・変化の動詞は être + 過去分詞で主語に一致: Elle est allée）、未完了は半過去、
  大過去、単純未来。受動は être + 過去分詞（par + 動作主）。否定 ne … pas。存在の文は il y a + 不定冠詞。
* 入口 (--from=fr) から: 冠詞の定・不定を枠に渡し、元の前置詞（à l'école）は元の言語に戻すときそのまま使う。

## 準備

```
pip install spacy && python3 -m spacy download fr_core_news_sm      # 約16MB (LGPL-LR。UD French-Sequoia・WikiNER で学習)
mkdir -p ~/.local/share/dragoman-data/fr/ud
curl -sL https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl | python3 tools/build_french_dic.py -
```

Wiktionary のフランス語の抽出データ（CC BY-SA）は約 580MB あるので、標準入力から読んで必要なものだけを sqlite に残します
（元のファイルは置かなくてよい。`~/.local/share/dragoman-data/fr/wiktionary.sqlite`、約 90MB。見出し語 8.6 万・語形 60 万）。
見出し語ごとの品詞・英語の語義・名詞の性と、語形の表（動詞は単純時制の形だけ。複合時制は avoir / être + 過去分詞で作る）です。

評価用に UD French-GSD（CC BY-SA 4.0）の `fr_gsd-ud-test.conllu` を `~/.local/share/dragoman-data/fr/ud/` に置きます
（spaCy のモデルの学習に使ったのは Sequoia なので、GSD とは重ならない）。

## 評価

```
python3 tools/ud_eval.py --lang=fr
```

UD French-GSD のテスト（416 文）で、述語の検出 93%、主語の再現率 79%、目的語の再現率 69%、代名詞の格 92%（2026-10-15）。
il y a + 名詞は訳では「〜がある」の主語なので、主語として数える。

## まだのこと

* pour・sans + 不定詞「〜するために」「〜せずに」を不定詞の節の接続詞に（今は行き場の無い語句になる）。
* 倒置の主語（a expliqué Véronique、Que dit l'Eglise ?）、疑問文の est-ce que。
* 代名動詞（se lever「起きる」、s'appeler「〜という名前である」）を見出しに。
* 出口: 否定の文の部分冠詞（ne mange pas de pain）、主語の倒置・疑問文、接続法（bien que・pour que の後ろ）。
