# ハワイ語（作りかけ）

ハワイ語の文を、語順（動詞 - 主語 - 目的語）と小辞から語の役割（格）を決め、共通の解析器（格の枠）で日本語に訳します。
語形はほとんど変わらないので、ラテン語のように語ごとの読みを並べて選ぶのでなく、タガログ語と同じく節の頭から順に読みます。
訳語は Wiktionary の英語の語義を日本語に直したもの（よく使う語は手で決めた訳）です。

```
./dragoman.py haw -e "Ua ʻai ke keiki i ka poi."
  →  子供が / ポイを / 食べた
./dragoman.py haw -e "He kumu ʻo ia."
  →  彼は / 先生である
./dragoman.py haw -e "Ua ʻai ʻia ka iʻa e ka pōpoki."
  →  魚が / 猫によって / 食べられた
python3 tools/samples.py --lang=haw              # サンプル (samples/hawaiian.txt) の訳
```

ʻokina（ʻ）のある文、または長音符とハワイ語の字（a e i o u h k l m n p w）だけの文をハワイ語と推定します。

## 少ない音素での「やりくり」

子音は8つ（p k ʔ h m n l w）、母音は5つ（a e i o u）。その分を次のもので補っている:

* 母音の長さと声門閉鎖音（ʻokina）も音素: pau「終わり」/ paʻu「煤」、kau「置く」/ kāu「あなたの」/ kaʻu「私の」
* 二重母音（ai・ae・ao・au・ei・eu・oi・ou・iu と長いもの）
* 音節は（子音）＋母音だけなので語が長くなり、重ね（wikiwiki「とても速い」）をよく使う
* 文法の仕事は小辞が受け持つ（冠詞 ke / ka・目的語の i / iā・時制と相の ua・e … ana・ke … nei・否定 ʻaʻole、所有の a 類・o 類）
* 借用語は音を寄せる（Merry Christmas → Mele Kalikimaka）

## 辞書

`python3 tools/build_hawaiian_dic.py` で、kaikki.org の Wiktionary の抽出データ
（`$DRAGOMAN_DATA/haw/kaikki.org-dictionary-Hawaiian.jsonl`、約 6MB、CC BY-SA）から `$DRAGOMAN_DATA/haw/wiktionary.sqlite` を作る。
見出し語約 4,000（品詞・英語の語義）と、複数形（kānaka ← kanaka・wāhine ← wahine）・異綴り（wau = au）。語数は少ないので、
よく使う語は手で書いた訳語の表（hawaiian/morphology.py）で補う。

## 綴り

今の綴りは ʻokina（ʻ U+02BB）と長音符（kahakō: ā ē ī ō ū）を書く。19世紀の新聞・聖書は両方を書かないので、辞書を引く鍵は ʻokina と
長音符を除いた小文字（hawaiian/orthography.py）。ʻokina の代わりの ' ‘ ` ’ は ʻ に揃える。

* 機能語の表は ʻokina・長音符付きの綴りで持ち、本文に印があればその綴り、無ければ鍵の同じ候補をすべて（kau → kaʻu「私の」/ kāu「君の」、
  ia → ia「彼」/ iā「〜を」/ ʻia「〜される」）引いて文脈で選ぶ。決められないもの（所有の kau）は両方の訳 {私の,君の} を出す。
* 辞書の語は鍵で引いて、綴りの合うもの、語義の多いものを先に。

## 扱うもの

* 動詞: 時制・相の小辞の後ろ（ua 完了「〜した」、e … ana 未完了・未来「〜するだろう」、ke … nei 進行「〜している」、e + 動詞は命令）、
  否定 ʻaʻole（+ i で過去「〜しなかった」）の後ろ、無ければ節の頭の動詞の読みのある語（Nani ka wahine「その女は美しい」: 状態の動詞）。
  動詞の後ろの ʻia は受け身、mai・aku・iho・aʻe（方向）は訳さない。mai + 動詞は禁止「〜するな」
* 名詞句: 冠詞（ke / ka「その」、nā 複数、he「ある」）は名詞に掛けて訳さない。指示詞 kēia「この」・所有の語 kaʻu / koʻu「私の」（a 類・o 類）は
  名詞の前、状態の動詞（nui「大きい」）と nei・lā は名詞の後ろ。名詞の後ろの o / a + 名詞句は所有「〜の」（ka hale nui o ke aliʻi
  「首長の大きい家」）。ma luna o「〜の上に」・i loko o「〜の中に」などの場所の名詞
* 役割: 動詞の後ろの印の無い最初の名詞句・代名詞は主語「が」、ʻo + 名詞句は主語（主題「は」）、i / iā + 名詞句は目的語「を」（移動・所在の
  動詞の後ろでは「〜へ・〜に」）、ma・mai・me・no・na は前置詞「〜で・〜から・〜と・〜のために」、受け身の e + 名詞句は動作主「〜によって」
* 動詞の無い文: He kumu ʻo ia「彼は先生である」（he の名詞が述語、ʻo の句が主語）、ʻO Kimo koʻu inoa「私の名前はキモだ」（文頭の ʻo の句が
  述語）には見えない繋辞を補う。Aia ka puke ma luna o ka papa「本はテーブルの上にある」の aia は「ある・いる」
* 関係節: 名詞 + i（過去）/ e … ana（進行・未来）+ 動詞は名詞に掛ける連体節（ka wahine i hīmeni「歌った女」、
  ka wahine e hīmeni ana「歌っている女」）。動詞の後ろの ai は目的語・場所の空所（ke kanaka i ʻike ai au「私が見た人」）
* 名詞句を前に出した文: 節の頭の名詞句 + i / e + 動詞は、その名詞句が主語（ʻElua kanaka i hele mai「2人が来た」）。
  hele mai「来る」・hele aku「行く」（方向の小辞）。mai ka hale mai「家から」の後ろの mai は訳さない
* 所有の文: He kaʻa koʻu「私には車がある」（he + 名詞 + 所有の語）、Naʻu kēia puke「この本は私のものだ」（na / no の所有の語の述語）、
  Loaʻa iaʻu ke kaʻa「私に車がある」（loaʻa + i / iā は「〜に」、iaʻu は目的語の形の代名詞）
* 疑問: wai「誰」（名前 inoa を尋ねるときは「何」）・aha「何」・hea「どこ」（i hea「どこへ」・ma hea「どこで」）・pehea「どう」・
  no ke aha「なぜ」・ʻehia「いくつ」。名詞の付かない kēia「これ」
* 数詞: ʻekahi … ʻumi は名詞の前（ʻelua ʻīlio「2匹の犬」）
* 辞書に無い語: 使役の hoʻo- を外して「〜させる」、重ね（wikiwiki → wiki）、大文字の語は名前（カタカナ）

## 音読

`./dragoman.py haw -s -e "…"` で読む。espeak-ng のハワイ語の音声（haw）は文字のまま渡すと ʻokina を読まない（ʻoe → [oe]）ので、
音素の列（`[[…]]`。hawaiian/phonology.py）で渡す。

* ʻokina は声門閉鎖音 [ʔ]、長音符は長母音。w は i・e の後ろで [v]、ほかは [w]（ʻawa [ʔava]・iwi [ivi]）。二重母音は1音節。
* 強勢: 最後の音節が長母音・二重母音ならそこ、それ以外は終わりから2番目（wahine [waˈhine]）。その前の長母音に頭子音の無い音節が続くとき
  は長母音の方（ʻāina [ˈʔaːina]）。ほかの長母音には副強勢。
* ʻokina・長音符の無い本文は、解析で選んだ読みの辞書の綴りで読む（ai → ʻai、ia oe → iā ʻoe）。

## 評価

Universal Dependencies にハワイ語のツリーバンクは無いので、自作の例文（samples/hawaiian.txt、test/hawaiian_test.py）で確かめる。

## まだ扱わないもの

* 語数の少なさ（Wiktionary 約 4,000語）: パブリックドメインの辞書（Andrews『A Dictionary of the Hawaiian Language』1865年）で補えるか
* 補文（ʻōlelo mai ʻo ia, ua hele …「彼は…と言った」）、条件・理由の節の中の語順、数詞の助数詞（「二つの人」→「2人の」）
* 生成（ほかの言語からハワイ語へ）
