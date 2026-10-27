# ポルトガル語（作りかけ）

ブラジル（pt-br）とポルトガル（pt-pt）のポルトガル語の文を、spaCy のポルトガル語モデル（pt_core_news_sm）で品詞・原形・
性・数・人称・時制と依存関係を付けてから、動詞の組（複合完了・受動・進行・近い未来・話法の動詞）をまとめ、共通の解析器
（格の枠）で日本語に訳します。名詞に格の形は無いので、格は依存関係（主語・目的語・間接目的語・前置詞の目的語）から付けます。
訳語は Wiktionary の英語の語義を日本語に直したものです（基本の語は morphology.GLOSSES で決めておく）。

```
./dragoman.py pt -e "O menino leu o livro da professora na escola."
  →  少年が / 学校[で,に] / 先生の本を / 読んだ
./dragoman.py pt -e "Você me deu o livro?"
  →  あなたが / 私に / 本を / 与えたか
./dragoman.py pt -e "Estou lendo um livro."        (ブラジル。ポルトガルの Estou a ler um livro. も同じ)
  →  私が / 本を / 読んでいる
./dragoman.py pt -k -e "Obrigado pela noite."      カナ: オブリガドゥ ペラ ノイチ
./dragoman.py pt -k --variety=pt -e "Obrigado pela noite."   カナ: オブリガドゥ ペラ ノイト (音読もポルトガルの声)
```

ラテン文字の文は、ã・õ・-ção・lh・nh があるか、ポルトガル語らしい語（não, você, um, com, para, o, de, que …）が2つ以上
（フランス語らしい語より多く）あればポルトガル語と推定します。

## 必要なもの

```
pip install https://github.com/explosion/spacy-models/releases/download/pt_core_news_sm-3.8.0/pt_core_news_sm-3.8.0-py3-none-any.whl
curl -L -o ~/.local/share/dragoman-data/pt/kaikki.org-dictionary-Portuguese.jsonl \
  https://kaikki.org/dictionary/Portuguese/kaikki.org-dictionary-Portuguese.jsonl     # 約 610MB
python3 tools/build_portuguese_dic.py
```

* pt_core_news_sm（約 13MB）: UD Portuguese Bosque と WikiNER で学習（CC BY-SA 4.0）
* 辞書: kaikki.org の Wiktionary の抽出（CC BY-SA）。見出し約 6.5 万・語形約 62 万。ブラジルとポルトガルの綴りの違い
  （fato / facto）は「Brazilian spelling of …」の語義から語形の表に

## 扱うもの

* 語の切り出し: 動詞の後ろのハイフンの接語（deu-me → deu -me、dá-lhes）と、動詞の中に入る接語（dar-te-ei → darei -te、
  vê-lo-ei → verei -lo）。複合語（guarda-chuva）はそのまま
* 前置詞と冠詞の縮約形（do・na・pelo・ao …）は前置詞。前置詞と代名詞の縮約形は前置詞 + 代名詞（nele・disso）、名詞の後ろの
  dele・dela は所有「彼の」（o livro dele「彼の本」）
* 格: 依存関係から（主語 → 主格、目的語 → 対格、間接目的語 → 与格、前置詞の後ろ → 前置詞の目的語、繋辞の補語）。
  名詞 + de + 名詞は属格（o livro da professora「先生の本」）。1・2人称の動詞の後ろの名詞は目的語
* 接語の代名詞: 動詞の前（ブラジルに多い: me deu）も後ろ（ポルトガルに多い: deu-me）も。動詞の前の接語は後ろの動詞の節に
  （O homem que veio | me viu）。人の接語（me・te・nos・vos）は目的語の名詞があるか与格を取る動詞（dizer・dar …）なら与格
  「〜に」、ほかは対格。lhe は与格
* 動詞の組: ter / haver + 過去分詞（完了・過去完了）、ser + 過去分詞（受動。por は動作主「〜によって」）、estar + 現在分詞
  （ブラジル）・estar a + 不定詞（ポルトガル）の進行「〜している」、ir + 不定詞（近い未来）、話法の動詞 + 不定詞（poder・querer・
  dever・ter que / de …）。spaCy の時制が語形の表に無ければ表から（sei を過去と読む誤り）
* você・vocês は3人称の動詞を取る「あなた（たち）」。há + 名詞・主語の無い tem + 名詞は「〜がある」
* 副詞節（quando・se・porque・embora・enquanto・ainda que・depois que …。いくつかの語の接続詞は1語に）、補文の que
  （言う・思う動詞は「〜と」、ほかは「〜ことを」）、関係節（que・quem・onde）、間接疑問（onde・quando・como・se …）
* 否定（não・nunca・jamais）

## カタカナ（`portuguese/katakana.py`）

espeak-ng の発音（IPA）から、共通の規則（core/kana.py）で。既定はブラジル（`--kana-pt=br`、espeak-ng の pt-br）、
`--kana-pt=pt` か `--variety=pt` でポルトガル（pt）。

| | ブラジル | ポルトガル |
|---|---|---|
| 語末の -e | イ（noite → ノイチ） | 書かない（ノイト） |
| t・d + i | チ・ジ（cidade → スィダジ） | ティ・ディ / ト・ド（スィダド） |
| 語頭・rr の r | ハ行（Rio → ヒウ、carro → カフ） | ラ行（リウ・カル） |
| 語末の l | ウ（Brasil → ブラズィウ） | ル（ブラズィル） |
| 語末・子音の前の s | ス（vocês → ヴォセス） | シュ（ヴセシュ） |

鼻母音は「ン」（bem → ベイン）、鼻音の二重母音は「ン」を最後に1つ（coração → コラサウン、mãe → マイン）、子音の前の em・en は
鼻母音（gente → ジェンチ）。長さは書かない（母音に長短の区別が無い）。1語では文字の名前に読まれる冠詞 o・接続詞 e は
弱い形（ウ・イ）。

## 音読（`-s`）

macOS の say のブラジルの声 Luciana（`--variety=pt` でポルトガルの声 Joana）、無ければ espeak-ng（pt-br / pt）。

## 文の生成 (出口)

ほかの言語の文の枠からポルトガル語（ブラジル）の文を作ります（`generate/portuguese.py`）。比較の表（`tools/generate.py --compare`）
にも出ます。ポルトガル語の文からも作れます（`--from=pt`。下の「入口」）。

```
python3 tools/generate.py --to=pt "Puella rosam pulchram in hortō videt."
  ポルトガル語: A menina vê a rosa bonita no jardim.
python3 tools/generate.py --to=pt "Ego tē amō. Mihi est liber. Puellā cantante puer dormit."
  ポルトガル語: Eu te amo.  /  Eu tenho um livro.  /  Enquanto a menina canta, o menino dorme.
```

* 語は英語を仲立ちにした置き換え（`transfer.py`。英語の索引 `pt/en-index.tsv` は辞書から `tools/build_english_index.py --lang=pt`、
  よく使う語の目安は UD の出現数 `tools/build_lemma_counts.py --lang=pt`、教科書の基本の語は transfer.PREFERRED で決めておく:
  agricultor を lavrador より）。名詞の性と、名詞・形容詞・動詞の語形は辞書の語形の表から（表に何度も載る形を先に: saber の
  sei を方言の sabo より）。無ければ規則（複数 -s・-ões・-ns・-is、女性 -a、-ar・-er・-ir の活用）。
* 名詞句: 定冠詞 o / a / os / as（所有詞の前にも: o meu livro）、不定冠詞 um / uma、前に置く形容詞（bom・grande・outro …）と後ろに
  置く形容詞（性・数の一致。並列は bom e corajoso）、指示詞 este・esse・aquele（中性は isto・isso）、de + 属格、名詞に掛かる分詞は
  que + 節（o inimigo que foge）。前置詞と冠詞・代名詞の縮約（no・do・ao・pelo・dele・nela・comigo）。
* 語順: 主語 - não - 接語の代名詞 - 動詞 - 目的語 - a + 受け手 - 前置詞句。主語の代名詞は書き（ブラジルの話し言葉）、2人称は você
  （動詞は3人称）。接語は動詞の前（Eu te amo）、不定詞の後ろの3人称の接語は -lo（posso lê-lo）。
* 時制: 現在、完了は完全過去（viu）、未完了過去（via）、過去完了 tinha + 過去分詞、単純未来（verá）、受動 ser + 過去分詞。
  否定の代名詞は動詞の後ろでも não（não vi ninguém）。望む・命じる・感情の補文と para que・embora などの後ろは接続法現在。
* 繋辞: ser（形容詞は主語に一致）、場所は estar（O menino está no jardim）、存在の文は há、所有の与格は ter（Eu tenho um livro）。
* 独立奪格は enquanto + 節（現在）・depois que + 節（過去）、述語的な分詞は動名詞（colhendo as flores）、過去の受動は一致した
  過去分詞（movida pelas palavras）。知覚の動詞 + 不定詞（Eu vejo a menina cantar）。

## 文の生成 (入口: `--from=pt`)

ポルトガル語の文を解析して文の枠にし、ほかの言語の文を作ります。元のポルトガル語に戻した文が入力と同じ語になれば ✓。

```
python3 tools/generate.py --from=pt "O menino deu o livro à menina."
  ラテン語: Puer puellae librum dedit.
  中国語:   男孩给了女孩书。
python3 tools/generate.py --from=pt "Há um livro na mesa."
  日本語:   テーブルに本がある。
  中国語:   桌子上有一本书。
```

* 冠詞（o・a / um・uma）は名詞句の定・不定に。前置詞と縮約形（no・do・ao・pelo）はラテン語の前置詞 + 格に写し、元の前置詞も
  持つ（ポルトガル語に戻すとき no を em + o に）。a + 人（à menina）は与格の受け手、受動の por + 動作主は ā + 奪格。
* 主語の代名詞から人称、você・vocês は2人称（ほかの言語では「あなた」、ポルトガル語に戻すと3人称の動詞）。
* 存在の há + 名詞は繋辞 + 主語（不定）。不定の主語の存在の文は、日本語では場所を先に「〜に …がある」、中国語は 〜上有 …。
* spaCy の読み誤りの手当て: 小文字の普通名詞を固有名詞と読む（rosa）、原形の誤り（rosa → roso: 辞書で引けた語形を見出しに）、
  文中の enquanto・quando・embora を副詞と読む（従属接続詞に）。

## 評価（`tools/ud_eval.py --lang=pt`）

UD Portuguese-GSD（CC BY-SA 4.0。`$DRAGOMAN_DATA/pt/ud/`）の test 1200 文で（2026-10-27）。spaCy のモデルは Bosque で学習して
いるので、Bosque（`--source=bosque`）は既定では使わない。

| 項目 | |
|---|---|
| 形容詞→名詞 | 再現率 78.0%・適合率 80.1% |
| 属格→名詞 | 再現率 59.4%・適合率 85.9% |
| 述語の検出 | 88.3% |
| 主語 | 74.3% |
| 目的語 | 65.3% |

há + 名詞は訳で「〜がある」の主語なので主語として測る。

## まだできないこと

* spaCy が動詞を形容詞と読む文（o menino dorme の dorme）は直していない
* 接続法未来・人称不定詞は語形の表にあるが、訳し分けはまだ
* ブラジルの口語の主語の a gente「私たち」、tu + 3人称の動詞
