# ドイツ語（作りかけ）

ドイツ語の文を、spaCy のドイツ語モデル（de_core_news_sm）で品詞・原形・格・性・数・人称・時制と依存関係を付けてから、
動詞の組（枠構造）と分離動詞をまとめ、共通の解析器（格の枠）で日本語に訳します。格は冠詞・形容詞・名詞の形から spaCy が
文脈で決めたものを使い、訳語は Wiktionary の英語の語義を日本語に直したものです。

```
./dragoman.py de -e "Ich habe meiner Mutter einen Brief geschrieben."
  →  私が / {私の}母に / 手紙を / 書いた
./dragoman.py de -e "Das Haus, das ich gekauft habe, ist sehr schön."
  →  とても / {私が 買った}家は / 美しい
./dragoman.py de -e "Er ruft seine Mutter an."
  →  彼が / {彼の}母を / 電話する
```

ラテン文字の文は、ドイツ語らしい語（der, die, das, und, ist, nicht …）が2つ以上あるか、ウムラウト・ß があればドイツ語と推定します。

## 扱うもの

* 格: 主格「が」・対格「を」・与格「に」・属格「の」（後ろから前の名詞に掛かる: das Buch des Lehrers「先生の本」）。
  冠詞（der / ein）は名詞に掛けて訳さない。所有冠詞・指示詞は「私の」「この」…
* 前置詞は後ろの名詞の格で訳を選ぶ（in + 与格「〜で」、in + 対格「〜へ」）。前置詞と冠詞の融合形（im・ins・zum・zur・am・vom・
  beim …）も前置詞。
* 動詞の組を定動詞の位置の1語にまとめる:
  haben / sein + 過去分詞 → 現在完了「〜した」（hatte / war + 過去分詞 → 過去完了）、werden + 過去分詞 → 受動「〜される」
  （von + 与格は「〜によって」）、sein + 過去分詞（sein を取らない動詞）→ 状態受動、werden + 不定詞 → 未来、
  話法の助動詞 + 不定詞（können「〜できる」・müssen「〜なければならない」・wollen / möchten「〜したい」・sollen「〜べきだ」・
  dürfen「〜してもよい」・lassen「〜させる」）。過去分詞の完了の助動詞（haben / sein）は辞書から。
* 分離動詞の前つづり（ruft … an）は動詞に付けて見出しを引き直す（anrufen「電話する」）。
* 否定 nicht・kein（kein + 名詞は述語の否定）、es gibt + 対格「〜がある」。
* 副文（dass・weil・wenn・ob … + 動詞が最後）と関係節（関係代名詞 der / die / das …。共通の解析器の関係節）。
* 述語の形容詞（Das Haus ist schön「家は美しい」）と副詞として使う形容詞（schnell → 速く）。
* spaCy の小さいモデルが副詞と読み誤る動詞の定形（dass du mich liebst の liebst）は、辞書の語形の表で動詞に戻す。

## 古い綴り（グリム童話など）

19世紀の綴り（1901年の正書法統一より前）や 1996年の改革より前の綴りは、今の綴りに直してから spaCy と辞書に渡します
（`german/orthography.py`。語ごとの表の注に「古い綴り roth → rot」）:

| 古い綴り | 今の綴り | 規則 |
|---|---|---|
| roth・Thüre・Athem・Hochmuth・übermüthig | rot・Türe・Atem・Hochmut・übermütig | th → t |
| todt・tödten | tot・töten | dt → t |
| gieng・fieng | ging・fing | ie → i（小文字の語だけ） |
| erschrack | erschrak | ck → k |
| daß・wußte・haßte | dass・wusste・hasste | ß → ss（辞書の「Formerly standard spelling of …」も） |
| Waare | Ware | aa → a |
| hätt・wär・Stund | hätte・wäre・Stunde | 語末の e の脱落 |
| wills・wars | will es・war es | es の縮約 |

規則は直した形が辞書にあるときだけ採ります。th・dt・aa・ey は今の綴りに出ない並びなので辞書に形がある語にも当て、ie・ck・ß は
今の綴りにもある並び（die・rief・saß・großen）なので辞書に無い語にだけ当てます。固有名詞（Amiens）・略語はそのまま。

縮小形（-lein・-chen・-elein・-elchen）は元の名詞の訳を使います（Spieglein → Spiegel「鏡」、Töchterlein → Tochter「娘」、
Häuslein → Haus「家」、Gäbelchen → Gabel「フォーク」。ウムラウトを戻して探す）。

グリム童話は Wikisource（ドイツ語版）の翻刻を使えます。ページごとの翻刻（`Seite:…`）を `action=raw` で取り、
`tools/import_wikisource.py` でつないでテキストにします（テキストは `$DRAGOMAN_DATA/de/texts/` に置き、リポジトリには入れない）:

```
python3 tools/import_wikisource.py ~/.local/share/dragoman-data/de/texts/sneewittchen-1857.txt PAGE264.wiki … PAGE273.wiki
./dragoman.py de -w ~/.local/share/dragoman-data/de/texts/sneewittchen-1857.txt
```

## 準備

```
pip install spacy && python3 -m spacy download de_core_news_sm      # 約13MB (MIT)
mkdir -p ~/.local/share/dragoman-data/de/ud
curl -sL https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl | python3 tools/build_german_dic.py -
```

Wiktionary のドイツ語の抽出データ（CC BY-SA）は約 1.1GB あるので、標準入力から読んで必要なものだけを sqlite に残します
（元のファイルは置かなくてよい。`~/.local/share/dragoman-data/de/wiktionary.sqlite`、約 370MB。見出し語 9.4 万・語形 350 万）。
見出し語ごとの品詞・英語の語義・名詞の性・完了の助動詞と、語形 → 見出し語・印（格・数・人称・時制）の表です。

評価用に UD German-GSD（CC BY-SA 4.0）の `de_gsd-ud-test.conllu` を `~/.local/share/dragoman-data/de/ud/` に置きます。

## 評価

```
python3 tools/ud_eval.py --lang=de
```

UD German-GSD のテスト（977 文）で、格の正解率 91%、主語の再現率 90%、目的語の再現率 80%、述語の検出 96%（2026-10-13 に評価ツールの複合語の行の読み違いを直して測り直した数字）。

## まだのこと

* 語順の倒置（目的語が文頭: Den Mann sieht die Frau）は spaCy の格に任せている。格の決まらない女性・中性・複数の名詞句
  （die Frau sieht das Kind）は語順で主語を先にしたい。
* zu 不定詞句（um … zu「〜するために」）、再帰動詞（sich freuen「喜ぶ」）の訳。
* 出口（`generate/german.py`）: 名詞・動詞の語形は辞書の変化表から、定冠詞と形容詞の弱変化、主文の動詞は2番目、分離動詞、
  完了・受動・未来、関係節は動詞を最後に。比較の表にも。
