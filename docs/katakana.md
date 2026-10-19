# カタカナ表記（設計の叩き台）

dragoman のカタカナは、**発音に忠実**なことを目指す（学習者が発音の手がかりにする表記）。日本語として見慣れた慣用表記や、
歌いながら一目で読めること（カラオケのルビ）は目的にしない。そちらは別の仕組みで作り、発音に忠実なカタカナが要るときは
dragoman に頼めるよう、外から呼びやすい口を用意する。

## 今の作り（2026-10）

| 作り方 | 言語 | 場所 |
|---|---|---|
| 音素の列 → カナ | ラテン語 | `latin/katakana.py`（`latin_phonology` の音素から。長母音「ー」、重子音「ッ」「ン」） |
| 文字 → カナ（専用の規則） | トルコ語・モンゴル語・ロシア語・韓国語 | `core/katakana_names.py` の `turkish`・`mongolian`・`russian`・`korean` |
| 文字 → 綴りの手直し → カナ | フランス語・ドイツ語・フィンランド語 | `core/katakana_names.py` の `latin(name, lang)` と `_french`・`_german` |
| 前処理して `latin()` に | 古英語・ハワイ語 | 各言語の `analyzer._katakana` など |

同じ問題（長母音・重子音・鼻音・語末の読まない字）を言語ごとに別々に直している（例: フランス語の Emmanuel・Céline、2026-10-19）。

一方で、発音（音素・IPA）を作る仕組みはすでにいくつかの言語にある: ラテン語（`latin_phonology`）・ギリシア語（`greek/phonology`）・
サンスクリット（`sanskrit/phonology`）・チベット語（`tibetan/phonology`）・古英語（`oldenglish/phonology`）・ハワイ語
（`hawaiian/phonology` の音節）。

## 設計

1. **綴り → 音素**（言語ごと）: 手持ちの発音の仕組みを使い、無い言語（フランス語・ドイツ語・ロシア語 …）は espeak-ng の IPA
   （`espeak-ng -v fr --ipa`）を使う。音素は IPA の記号に揃え、音節の切れ目・長さ・強勢を持たせる。
2. **音素 → カナ**（共通）: IPA の音素の列からカナを作る1つの規則。言語ごとの違いは表（音素 → カナの段・行）と少しの設定に。
3. **外から呼ぶ口**: `katakana(word, lang, **options)` と、コマンド（例: `./dragoman.py --katakana fr "Emmanuel Macron"`）。

辞書の慣用表記（Wikidata の日本語ラベルなど）は使わない（発音に忠実なことを優先する）。

## 方針（2026-10-19 に決めたもの）

* [v] はヴ行（ヴァンサン・ヴィクトル）。
* 長音「ー」は設定で選ぶ: 音素として長い母音だけ（ラテン語の ā、フィンランド語の aa、ハワイ語の ā）か、実際に長く発音される
  母音（強勢のある開音節・語末の「母音 + 子音 + 読まない e」: Céline → セリーヌ）にも付けるか。
* あいまい母音 [ə] は綴りに近い母音（about → アバウト、petit → プティ）。言語ごとに既定の段を決める。
* 日本語に無い子音は近いカナに寄せ、区別は捨てる（th → ス・ズ、l と r → ラ行）。
* [wa] は設定で選ぶ。既定はどの言語も「ワ」（Hawaiʻi → ハワイイ、Minerva → ミネルワ）、`wa='ウァ'` で西洋古典学の慣習の
  「ウァ」（ミネルウァ・ウァレリア）。
* （今の作りから引き継ぐもの）重子音は閉鎖音・s・f で「ッ」、n・m で「ン」（ラテン語・フィンランド語・イタリア語）。
  音節末の子音は「ウ段」（t・d は「ト・ド」、h は「フ」）、声門閉鎖音は表記しない（ハワイ語の ʻokina は区切り）。

## 移す順番（案）

1. （済 2026-10-19）音素 → カナの共通の規則 `core/kana.py`（`kana(phonemes, long='phonemic' | 'phonetic')`）。ラテン語
   （`latin/katakana.py`）はその音素の記号を IPA に読み替えて使う。辞書の固有名詞 9,330 語で前の結果と比べ、違いは36語:
   複数語の名前を語ごとに読む（Forum Aurēliī → フォルムアウレーリイー。前はフォルマウレーリイー）、ck の重子音（Eckius →
   エッキウス）、qu + 二重母音（Aquae → アクァエ）、s + j の拗音（Sjaellandia → シャエランディア）
2. （済 2026-10-19）発音の仕組みのある言語を、共通の規則につなぐ。言語ごとの `katakana(word, **options)`:
   * ギリシア語 `greek/katakana.py`: アッティカ方言の再建音（長さは辞書から）。Σωκράτης → ソークラテース、φιλοσοφία →
     ピロソピアー。二重母音 αι・οι は「アイ」「オイ」、有気音は無気音と同じ
   * サンスクリット `sanskrit/katakana.py`: kṛṣṇa → クリシュナ、śiva → シヴァ、buddha → ブッダ。音節の ṛ は「リ」、そり舌音は
     t・d・n・ʃ に
   * 古英語 `oldenglish/phonology.katakana`: Æþelstān → エゼルスターン、Bēowulf → ベーオウルフ。æ はエ段
   * ハワイ語 `hawaiian/phonology.katakana`: Kalākaua → カラーカウア（前の綴りの規則ではカラカウア）。ʻokina は書かない
3. espeak-ng の IPA を使う言語（フランス語・ドイツ語・ロシア語 …）を移し、今の専用の規則の結果と比べる
   （名前の試験の表: `test/katakana_names_test.py`・`test/french_test.py`）。
   * （済 2026-10-19）フランス語 `french/katakana.py`: espeak-ng の IPA から。読まない字・鼻母音は espeak-ng に任せ、
     日本語の耳に合わせる所だけ手を入れる: ɛ̃ はアン（ヴァンサン）、子音 + w + a は「オワ」（フランソワ）、長さは実際の発音
     （既定 long='phonetic'。語末の o・ø・ɑ、r・z・ʒ・v の前: ルソー・ピエール）、語末の [n]・[m] は「ヌ」「ム」（綴りの -nne は
     「ンヌ」: アンヌ。ほかは前を長く: セリーヌ）、語末の閉鎖音の前の「ッ」（ジュリエット）。共通の規則には IPA の文字列の
     分け方（`split_ipa`）・鼻母音の「ン」・`final_sokuon` の設定を足した
4. 外から呼ぶ口（関数・コマンド）。
   * （済 2026-10-19）コマンド: `./dragoman.py LANG --kana`（見出しの下にカタカナ読み）・`--kana-only`（読みだけ）、
     `--kana-long=phonemic|phonetic`・`--kana-wa=ワ|ウァ`。語の区切りは空白。言語のコマンドの `katakana(analysis, kana_options)`
     が、解析で選んだ読みの綴り（ラテン語の格の決まったマクロン付きの形、古英語・ハワイ語の辞書の綴り）から語ごとに作る。
     ラテン語の入口（latin/main.py）にも同じ選択肢
   * 関数: 言語ごとの `katakana(word, **options)`（latin/katakana.py・greek/katakana.py・sanskrit/katakana.py・
     french/katakana.py・oldenglish/phonology.py・hawaiian/phonology.py）と、共通の `core.kana.kana(phonemes or ipa, …)`
