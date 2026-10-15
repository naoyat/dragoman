# 古英語（作りかけ）

古英語（アングロ・サクソン語、およそ 700〜1100年）の文を、Wiktionary の変化表で語ごとにすべての読み（名詞類の格・数・性、
動詞の法・時制・人称・数）を並べてから、冠詞を名詞に掛け、助動詞と本動詞をまとめ、共通の解析器（格の枠）で日本語に訳します。
品詞を決める解析器（spaCy など）は無いので、ラテン語・古典ギリシア語と同じく、どの読みを採るかは語の形と文の中の並びで決めます。
訳語は Wiktionary の英語の語義を日本語に直したもの（よく使う語は手で決めた訳）です。

```
./dragoman.py ang -e "Se cyning sealde þǣm biscope gold."
  →  王が / 主教に / 金を / 与えた
./dragoman.py ang -e "Hē ne mihte þone weg findan."
  →  彼が / 道を / 見つけることができなかった
./dragoman.py ang -e "Hwæt! Wē Gārdena in ġeārdagum þēodcyninga þrym ġefrūnon."
  →  さあ聞け
  →  私たちが / デーン人の / 昔の日々[で,の中で] / 王の栄光を / 聞き知った
python3 tools/samples.py --lang=ang              # サンプル (samples/oldenglish.txt) の訳
```

þ・ð・ƿ・ġ・ċ のある文、または æ と古英語らしい語（and, se, wæs, þone …）が2つ以上ある文を古英語と推定します
（ラテン語の æ (Cæsar) とは分ける）。

## 辞書

`python3 tools/build_oldenglish_dic.py` で、kaikki.org の Wiktionary の抽出データ
（`$DRAGOMAN_DATA/ang/kaikki.org-dictionary-OldEnglish.jsonl`、約 140MB、CC BY-SA）から
`$DRAGOMAN_DATA/ang/wiktionary.sqlite`（約 34MB）を作ります。

* 見出し語ごとの品詞・見出し（長音符付き）・英語の語義・名詞の性・動詞の強変化 / 弱変化と類。
* 語形の表: 見出しの変化表と、「inflection of ābīdan」のような変化形だけの項目の語義の印から集める。
  変化表の動詞の段には直説法と接続法の印が無いので、並びで分ける（人称の付いた形は直説法、人称の無い単数の形の後は接続法、
  imperative + 数は命令法、imperative + present / past で数の無いものは現在分詞・過去分詞）。
* 異綴り（alternative form of 〜、変化表の alternative）は元の語の同じ形の読みを写す（cing・cining → cyning）。
* 人称代名詞は iċ の項目の変化表に hē・hēo・wē … がまとめて載っているので表から外し、手で書いた表（oldenglish/morphology.py）で読む。

## 綴り

辞書は長音符と口蓋音の点の付いた標準化した綴り（cyning・sēo・ġiefan・ċild）で、写本の翻刻は長音符を書かず、þ と ð を区別せずに使う
（onginneð = onginneþ）。辞書を引く鍵は長音符・点を除き、ð → þ、ƿ（ウィン）→ w、⁊・&（ティロ式の and）→ and にして小文字にしたもの。
手で決めた訳語の表の鍵は長音符を残す（god「神」と gōd「良い」を分ける）。

辞書に無い綴りは、方言・時代の綴りの揺れを1か所（無ければ2か所）読み替えて引き直す（oldenglish/orthography.py）:
y・i・ie（hyran = hieran）、eo・io、ea・a・e、o・a（鼻音の前。mon = man）、ur・yr → eor（wurþan = weorþan）、重子音、
後期の語尾の弱まり（lufodan = lufodon）、弱変化の過去 -od = -ed（getimbrod = getimbred）、過去分詞の ge-（i-・y-）。

それでも無い語は推定する: 動詞の語尾（-ode・-de・-don・-aþ・-ian …）を外して不定詞（〜an・〜ian）を引く（gyrnde → ġeornan の過去）、
複合語は後ろの要素の格・数・性を使う（leorningcnihtas → leorning + cniht）、ローマ数字（dccc・xl）は数詞。大文字の語は固有名詞
（辞書に無い名前はカタカナ）。

## 扱うもの

* 格: 主格「が」・対格「を」・属格「の」・与格「に」・具格「で」と呼格「よ」。属格はふつう名詞の前から掛かる
  （þēodcyninga þrym「王の栄光」）。名詞の具格は与格と同じ形として冠詞と一致させる（þȳ ilcan ġēare「同じ年に」）。
* 冠詞・指示詞: sē・sēo・þæt（冠詞「その」）と þes「この」は、後ろの一致する名詞（無ければ形容詞）に掛けて訳さず、名詞の格を絞る。
  冠詞の掛かる語の動詞の読みは除く（se sang「その歌」）。よく使う動詞（wesan・habban・話法の動詞など）の形には掛けない
  （þæt is「それは〜である」の is を īs「氷」と読まない）。掛からない sē は指示代名詞「その人・それ」、þā は副詞「その時」。
* 前置詞: 後ろの語の格で訳を選ぶ（on + 与格「〜で」、on + 対格「〜へ」）。fōr（faran の過去「行った」）は前置詞 for と同じ綴りなので
  両方の読みを持たせる（Hēr fōr se here「この年に軍が進んだ」）。
* 動詞の選択: すべての読みが動詞の語が無い節（句読点・and・ac・従属の接続詞で区切る）では、定動詞の読みのある語を1つ動詞に絞る。
  主格の代名詞と人称・数の合うものを先に、従属節では最後の、主節では最初の候補。
* 主語と目的語: 節ごとに、動詞の人称・数と合う語のうち、主格だけの語、無ければ動詞の前の語、無ければ動詞の後ろの最初の語を主語にし、
  残りの主格・対格の語を対格に絞る（Þā ġeseah hē hīe「その時彼は彼女（彼ら）を見た」）。2つの動詞の間の語は前の動詞に結ぶ
  （主節は動詞が2番目）。
* 助動詞と本動詞: 話法の動詞（sculan・magan・cunnan・willan・mōtan …）+ 不定詞「〜なければならない・〜できる・〜たい」、
  habban + 過去分詞は完了（過去なら過去完了）、bēon / wesan / weorþan + 過去分詞は受動（移動・変化の自動詞は完了: hē wæs ġecumen）。
  間に語があってもよい（Hē hæfde þone cyning ġesewen）。
* 否定: ne・nā・nǣfre と縮約形（nis = ne is、næs = ne wæs、nolde = ne wolde、nyste = ne wiste、næfde = ne hæfde …）、
  否定の代名詞 nān・nǣniġ。
* 関係節: 関係の小辞 þe（名詞・代名詞の後ろ）と se þe「〜する人」。
* 補文の þæt「〜ということ」: þæt þæt（補文の þæt + 冠詞）、主語の代名詞の後ろの þæt は代名詞「それを」、定動詞の前の þæt は「それ」。
  þā þā「〜した時」。
* 呼びかけ: 2人称の代名詞か命令法のある文の、文頭からコンマまでの名詞句を呼格に（Fæder ūre, þū þe eart on heofonum「天にいる私たちの父よ」）。

## 音読

`./dragoman.py ang -s -e "…"` で読む。古英語の音声は espeak-ng に無いので、音素の列（`[[…]]`。oldenglish/phonology.py）で渡す。

* 古英語の音声 ang（`python3 tools/build_oldenglish_espeak.py`。下）があればそれで、無ければドイツ語の音声で読む。
* 発音はウェストサクソン方言の古典期（およそ 1000年頃）の再建音: ċ [tʃ]・ġ [j]（点の無い綴りでは位置から推す: 前舌母音の前の語頭、
  前舌母音の後ろの語末）、sc [ʃ]、cg [dʒ]、ng [ŋg]、g は母音・l・r の後ろで [ɣ]、h は語頭以外で [x]（後舌母音の後ろ）・[ç]（前舌母音の後ろ）、
  f・s・þ は有声音に挟まれると [v]・[z]・[ð]、重子音は長く、二重母音 ea [æɑ]・eo [eo]・ie [iy]・io [io]。
* 強勢は最初の音節。接頭辞 ġe-（子音の前）と be-・bi-・for-・ā-（解析で選んだ見出し語から接頭辞を外した語が動詞の見出しにあるとき:
  forlǣtan ← lǣtan。beran・biscop は違う）の付いた語はその次。
* 母音の長さ: 翻刻の本文には長音符が無いので、解析で選んだ読みの辞書の綴り（長音符付き）で読む（forlet → forlēt、god「神」/ gōd「良い」）。
  手で書いた表の機能語（hē・þā・þǣm・sī …）は長音符付きの綴りの表（morphology.LONG_SPELLINGS）から。

### 古英語の音声 ang

espeak-ng の音素はテキストの定義（ソースの `phsource/`）からコンパイルしたデータで、言語の表はほかの表を引き継げる。
`tools/build_oldenglish_espeak.py` は、インストールしてある espeak-ng のデータの写し（`$DRAGOMAN_DATA/ang/espeak-ng-data`）に、
次の古英語の表 ang と音声 ang を足してコンパイルし直す（インストールしてあるデータには触れない）。

* ドイツ語の表（基本の表の θ・ð・w・ɣ も持つ）を引き継ぎ、b・d・g・v・z を語末で無声にしない定義に（基本の表の定義を呼ぶ）。
* [æ]（&）・[æː]（&:）を足す（espeak-ng の母音のフォルマント vowel/& を使う）。
* 音声の言語の設定は en（de・nl の設定は音素表とは別に語末の有声音を無声にする: gōd [goːt]）。

ソースは espeak-ng と同じ版のもの（コンパイルしたデータの形式が版ごとに違う。https://github.com/espeak-ng/espeak-ng 、GPL-3.0）を
`$DRAGOMAN_DATA/espeak-src/espeak-ng-<版>/`（ほかの言語の表を作るときも共用） に展開しておく（使うのは `phsource/` だけ）。表の定義はこのツールが書き出すので、
リポジトリに espeak-ng の定義は入れない。作ったデータは espeak-ng-data 由来（GPL-3.0）。

```
espeak-ng --path=$HOME/.local/share/dragoman-data/ang -v ang "[[hw'&t w'e: g'A:Rdena]]"
```

## 評価

ISWOC Treebank（古英語の部分: アポロニウス物語・アングロサクソン年代記・オロシウス・ウェスト・サクソン福音書・エルフリックの聖人伝。
CC BY-NC-SA 3.0。`$DRAGOMAN_DATA/ang/iswoc/*.conll`、リポジトリには入れない）で測る。PROIEL 形式の CoNLL を UD の形に読み替える
（sub → nsubj、名詞に掛かる atr は amod / det / nmod、and に掛かる主語・目的語は並んだ述語の一番近いものに、助動詞にまとめた本動詞も
同じ述語として数える）。

```
python3 tools/ud_eval.py --lang=ang [--source=apt,chrona,or,wscp,æls]
```

2536文: 網羅率 95%、格 71%、述語の検出 85%、主語 63%、目的語 52%。

## まだ扱わないもの

* 語順の違い（主節の動詞2番目・従属節の動詞が最後）を節ごとに使い分けること（今は全体で「2つの動詞の間の語は前の動詞に」）。
* 強変化・弱変化の形容詞の区別、形容詞の比較級、与格の独立構文。
* 接続法の主文（祈願「〜ますように」: sī þīn nama ġehālgod）。
* 生成（ほかの言語から古英語への訳）。
* 短母音の音色（いまはドイツ語の音素の [ɪ ʊ ɔ]）、二重母音を1つの音素として（いまは母音2つ）。
* 見出しが辞書に無い語（Gār-Dene、語尾から推定した動詞）の長音符。
