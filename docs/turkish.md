# トルコ語（作りかけ）

トルコ語の語を形態素解析器 zeyrek（Zemberek の Python 版）で語幹と接尾辞に分け、読みを文脈で選んでから、格の接尾辞から
格の枠を決めて日本語に訳します。日本語と同じ主語-目的語-動詞の語順で、格の接尾辞が日本語の助詞にほぼ対応するので、
韓国語と同じく「語順のまま」の訳（≒）も添えます。

```
./dragoman.py tr -e "Ali'nin okuduğu kitap güzeldi."
  →  Aliが読んだ本は / 美しかった
  ≒  Aliが 読んだ 本は 美しかった。  (語順のまま)
./dragoman.py tr -e "Eve gelince yemek yedik."
  ≒  家に 来ると 食事を 食べた。  (語順のまま)
```

ğ・ı・ş・İ のある文、トルコ語らしい語（bir, ve, bu, için, değil …）が2つ以上ある文は、言語を省略してもトルコ語と推定します。

## 接尾辞と訳

| 接尾辞 | 働き | 訳 |
|---|---|---|
| （無標） | 主格・不定の目的語 | が・は（文の最初の名詞は主題）、他動詞の直前は「を」（kitap okudu「本を読んだ」） |
| -ı / -i / -u / -ü | 対格（定の目的語） | を |
| -a / -e | 与格 | に |
| -da / -de | 位格 | で（述語なら「〜にある」: Kitap masada「本は机にある」） |
| -dan / -den | 奪格 | から |
| -ın / -in | 属格（後ろの名詞に掛かる。関係節の主語にもなる） | の・が |
| -la / -le | 具格 | で・と |
| -(ı)m・-(ı)n・-(s)ı … | 所有（evim「私の家」）。不定の名詞の後ろの -ı は名詞の複合（Yugoslav lideri） | 私の・君の … |

* 用言: 時制（-dı 過去・-mış 伝聞の過去・-acak 未来・-iyor 進行・-ır 超越）、人称（-m・-n・-k …。主語を書かなければ人称から
  「私が」「我々が」を補う）、否定 -ma、可能 -abil「〜できる」、受動 -ıl、使役 -dır「〜させる」、命令・願望、条件 -sa、必要 -malı。
* 名詞・形容詞の述語（Ben öğretmenim「私は先生である」、güzeldi「美しかった」）と、動詞の無い文には見えない繋辞を補う。
  var「ある」・yok「ない」は存在、değil は否定の繋辞（büyük değil「大きくない」、evde değildim「家にいなかった」）。
* 後置詞（için「〜のために」・ile「〜と」・gibi「〜のように」・tarafından「〜によって」・sonra「〜の後で」…）は前の名詞句の
  前置詞句にする。
* 分詞（-an「〜する（人）」・-dığı「〜した（もの）」・-acağı）は後ろの名詞に掛ける関係節（Kitap okuyan çocuk「本を読む子供」、
  Ali'nin okuduğu kitap「アリが読んだ本」）。副動詞（-ıp・-arak「〜して」、-ınca「〜すると」、-ken「〜している間」、
  -madan「〜せずに」…）は節を区切る接続の語。不定詞（-mak・-ma）は「〜すること」。
* 読みの選択: zeyrek は語ごとにすべての読みを返すので、文の最後は定動詞、文中は名詞・形容詞、名詞の前の指示詞は「この」、
  形容詞の前の çok は「とても」、属格の代名詞の後ろは同じ人称の所有（benim kardeşim）、文中の大文字の語は固有名詞を先にする。

## 準備

```
pip install zeyrek                                     # 約1MB (MIT。nltk も入る)
mkdir -p ~/.local/share/dragoman-data/tr/ud
curl -sL https://kaikki.org/dictionary/Turkish/kaikki.org-dictionary-Turkish.jsonl | python3 tools/build_turkish_dic.py -
```

Wiktionary のトルコ語の抽出データ（約 440MB、CC BY-SA）を標準入力から読み、見出し語（動詞は -mak / -mek の形）ごとの品詞・
英語の語義を `~/.local/share/dragoman-data/tr/wiktionary.sqlite` に残します（4.6 万項目）。英語の語義は解析の時に日本語に直し、
基本の語の訳語は `turkish/morphology.py` の GLOSSES で決めておきます。

評価用に UD Turkish-BOUN・Kenet（CC BY-SA 4.0）の test を `~/.local/share/dragoman-data/tr/ud/` に置きます。

## 評価

```
python3 tools/ud_eval.py --lang=tr [--source=boun,kenet]
```

BOUN・Kenet の test（2,622 文）で、格の正解率 80%、主語の再現率 41%・目的語の再現率 34%、述語の検出 58%。分詞・副動詞・
不定詞の節の中の目的語（çevreyi kirleterek「環境を汚して」）は、分詞の関係節を名詞の訳に組み込むので述語として数えられず、
取りこぼしの多くを占めます。

## まだのこと

* 分詞の関係節を共通の解析器の関係節に（韓国語と同じ）。
* 固有名詞のカタカナ表記（Ali → アリ）。
* zeyrek の辞書に無い語（Unk）・新しい語の扱い。
* 文の生成（出口）と比較の表。
