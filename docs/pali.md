# パーリ語

サンスクリットと同じく、辞書引きだけをパーリ語用に書き、解析・訳は共通の解析器を使います。
語形・連声の分解・訳語は [Digital Pāḷi Dictionary](https://github.com/digitalpalidictionary/dpd-db)（DPD。
CC BY-NC-SA 4.0）から取ります。見出し約9万語、語形約118万の表を、`tools/build_pali_dic.py` で解析に使う列だけの
SQLite（約190MB）にします。ローマ字（PTS 式: ṃ・ḷ。SuttaCentral の ṁ も）のほか、シンハラ文字・タイ文字・ビルマ文字・
デーヴァナーガリーでも入力できます（文字の変換は Vidyut の lipi）。

```
pip install vidyut
mkdir -p ~/.local/share/dragoman-data/pi && cd ~/.local/share/dragoman-data/pi
gh release download -R digitalpalidictionary/dpd-db -p dpd.db.tar.xz   # 約170MB (展開すると約2.3GB)
tar -xJf dpd.db.tar.xz
cd - && python3 tools/build_pali_dic.py        # → ~/.local/share/dragoman-data/pi/pali.sqlite
./dragoman.py pi samples/dhammapada.pi.txt     # 法句経 第1章 (-w で語ごとの辞書引きを省く、-E 語源)
```

```
Na hi verena verāni, sammantīdha kudācanaṃ; Averena ca sammanti, esa dhammo sanantano.
  カナ: ナ ヒ ヴェーレーナ ヴェーラーニ サンマンティーダ クダーチャナン アヴェーレーナ チャ サンマンティ エーサ ダンモー サナンタノー
  →  なぜなら,実に / 怨みが / 怨みで / ここで,この世で / いつか,かつて / 止まない
  →  そして / {永久の & これ}法が / 怨みの無いことで / 止む
Buddhaṃ saraṇaṃ gacchāmi.
  →  私が / 仏=帰依処を / 行く
Sabbe sattā bhavantu sukhitattā.
  →  すべての衆生は / 幸せである
```

* 語形は DPD の語形の表（dhammā → dhamma の男性・複数・主格 …）で引き、見出しの品詞から名詞・形容詞・代名詞・
  分詞（過去分詞・現在分詞・未来受動分詞。元の動詞は「pp of bhamati」から）・定動詞（現在・アオリスト・未来・願望法・
  命令法 …）・絶対分詞（gantvā → 行って）・不定詞・不変化詞にします。
* 表に無い語は DPD の分解（sammantīdha → sammanti + idha、tesūpasammati → tesu + upasammati）で分けます。
  語末の ṃ が m になって母音とつながった語（dukkhamanveti → dukkhaṃ + anveti）は、表にあっても分けます。
  ti の前の n は ṃ に戻します（katan ti → kataṃ ti）。複合語の前の要素は語幹として引きます。
* 訳語は、手作りの表（代名詞・不変化詞・仏典の語: bhikkhu → 比丘、nibbāna → 涅槃、vera → 怨み、satta → 衆生）→
  サンスクリットの仏典の訳語（`sanskrit/buddhist.py`。DPD のサンスクリットの対応語で引く: dhamma → dharma → 法、
  buddha → 仏）→ DPD の英語の語義（英語 → 日本語の表で）の順です。英語の語義は、日本語に訳せる候補
  （meaning_1・meaning_2）を先にします（sammati: is calmed → ceases → 止む）。アオリストなどの見出しは現在形の動詞の語義で
  （akkocchi「aor of akkosati」）。
* 読みの順: 表の語 → 代名詞 → 仏典の訳語のある名詞 → 頻度（DPD の初期経典での出現数）。反射態・願望法だけの読み
  （veraṃ を vāti「吹く」の反射態・願望法）、固有名詞（小文字の manomayā を独覚の名前に）は後ろに回します。
  仏典の訳語のある名詞と同じ語幹の形容詞の読み（buddha「目覚めた」）は除きます。
* 定動詞の選び方・形容詞と名詞の一致・後置の ca・vā はサンスクリットと同じ（`sanskrit/analyzer.py`）。
* `-E`（語源）: DPD のサンスクリットの対応語・語根・成り立ち（dhamma: dharma [dhṛ]、√dhar、√dhar + ma）。

## 文字

* 入力の文字は自動で見分け、見出しに添えます（ローマ字の入力なら添えない）。`--script=sinhala|thai|myanmar|devanagari` で
  見出しに添える文字を選べます。
* 変換は ISO 15919 を経ます（子音の ḷ・長い e o を区別するので）。ビルマ文字の ss は合字 ဿ、タイ文字は点（phinthu ฺ）と
  niggahīta ํ の書き方です。
* 言語の推定: シンハラ文字・ビルマ文字、点や niggahīta のあるタイ文字はパーリ語。ローマ字は ṃ・ṅ・ñ・ṭ・ḍ・ṇ・ḷ があり、
  ś・ṣ・ṛ・ḥ が無く、サンスクリットに少ない重子音（mm・ss・kkh・ṭṭh …）があればパーリ語です。

## カタカナ読み

`--kana` は発音から（`pali/katakana.py`）: namo tassa bhagavato arahato sammāsambuddhassa →
ナモー タッサ バガヴァトー アラハトー サンマーサンブッダッサ、buddhaṃ saraṇaṃ gacchāmi → ブッダン サラナン ガッチャーミ。

* ā ī ū は「ー」。e・o は長いが、子音の連なりの前では短い（metta → メッタ、sotthi → ソッティ）。
* ṃ は「ン」、鼻音 + 子音も「ン」（pañca → パンチャ、paññā → パンニャー）。有気音の h は書かない、v は「ヴ」、ḷ は「ル」の行。

## 見本

* `samples/dhammapada.pi.txt`: 法句経 第1章 双要品（第1〜20偈）。原文は SuttaCentral の bilara-data（Mahāsaṅgīti 版。
  原典はパブリックドメイン、SuttaCentral の素材は CC0）。入力の277語はすべて DPD で引けます。

## まだできないこと

* 名詞文（manopubbaṅgamā dhammā「諸法は意を先とする」）の述語、半偈（;）をまたぐ節の係り（ce の条件節）。
* 命令法・願望法の訳し分け（bhavantu「〜であれ」）、分詞の述語（evaṃ me sutaṃ「このように私は聞いた」）。
* 英語の語義の訳せない語（manopubbaṅgama「led by mind」など複合語の説明的な語義）。
* 文字の図の字の名前（今は Unicode の名前: mahaapraana bayanna）。音読。
