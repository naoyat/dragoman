# ベトナム語（作りかけ）

ベトナム語の文を語に切り分け、Stanza（UD Vietnamese-VTB で学習したモデル）で品詞と依存関係を付けてから、ベトナム語の構文
（量詞・所有・相の副詞・否定・助動詞・受動・文末の疑問の助詞・関係節）をまとめ、共通の解析器（格の枠）で日本語に訳します。
中国語（`chinese/`）と同じ作りです。訳語は Wiktionary の英語の語義を日本語に直したもの（基本の語は morphology.GLOSSES で
決めておく）。

```
echo "Tôi đã đọc quyển sách mà anh cho tôi." | ./dragoman.py vi
  →  私が / 彼が私にくれた本を / 読んだ
echo "Con mèo của tôi đang ngủ trên bàn." | ./dragoman.py vi     →  私の猫が / 机の上で / 寝ている
echo "Tôi có hai người bạn." | ./dragoman.py vi                  →  私には / 二人の友人が / いる
echo "Bạn ăn cơm chưa?" | ./dragoman.py vi                       →  あなたが / ご飯を / 食べたか
echo "Nếu trời mưa thì tôi sẽ ở nhà." | ./dragoman.py vi         →  {雨が降る}なら / 私が / 家に / いるだろう,住むだろう
./dragoman.py vi --kana samples/vietnamese.txt     # カナ: トイ ダー ドック クイエン サイック …
python3 tools/samples.py --lang=vi                 # サンプル (samples/vietnamese.txt) の訳
```

ă・đ・ơ・ư と声調記号付きの字（ạ ả ấ … ỹ）が2つ以上あるか、ベトナム語らしい語（tôi, của, không, người …）が2つ以上ある
ラテン文字の文はベトナム語と推定します（フランス語の â・ê・ô は数えない）。

## 必要なもの

```
pip install stanza
mkdir -p ~/.local/share/dragoman-data/vi/unihan && cd ~/.local/share/dragoman-data/vi
curl -LO https://kaikki.org/dictionary/Vietnamese/kaikki.org-dictionary-Vietnamese.jsonl
curl -L -o unihan/Unihan.zip https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip && (cd unihan && unzip Unihan.zip)
python3 -c "import stanza, os; d = os.path.expanduser('~/.local/share/dragoman-data/vi/stanza');
  stanza.download('vi', model_dir=d, processors='tokenize,pos,depparse');
  stanza.download('vi', model_dir=d, processors={'tokenize': 'vtb_charlm'}, package=None)"
cd - && python3 tools/build_vietnamese_dic.py     # → ~/.local/share/dragoman-data/vi/vietnamese.sqlite
```

* Stanza 1.15（Apache 2.0）のベトナム語モデル（約330MB。tokenize・pos・depparse と事前学習の語ベクトル・文字の言語モデル。
  全部入りの default.zip（520MB）は要らない）。学習データは UD Vietnamese-VTB（CC BY-SA 4.0）
* Wiktionary（kaikki.org の抽出、約80MB、CC BY-SA）: 約4万2千語。品詞・英語の語義・漢越語の漢字（語源の
  「Sino-Vietnamese word from 生員」から。音節と字の数が合うもの約1万1千語）・字喃 / 漢字の表記・量詞・ハノイの発音（IPA）
* Unihan（Unicode License v3）の kVietnamese と、Wiktionary の「chữ Hán form of học」: 漢字 → 漢越音（約8千5百字）

## 語の切り分け（`vietnamese/segment.py`）

ベトナム語は音節ごとに空白で書くので、何音節で1語か（sinh viên「学生」、Việt Nam）を決めます。Stanza の切り分けを基本に、
辞書に無い2音節以上の区切り（Stanza が Nam mô A Di Đà Phật を mô A で切るなど）は使わず、辞書の見出しで分け直します
（語の数の少ない切り方。Stanza と同じ区切りは少し安く）。大文字で始まる音節の続き（Nguyễn Văn An）は辞書に無くても
Stanza の区切りのまま。訳語の表の語（trường đại học「大学」）は Stanza の区切りより先に。ことわざ・成句の見出し
（uống nước nhớ nguồn）は語に分けて訳すので切り分けには使いません。

## 構文（`vietnamese/analyzer.py`）

* 語順は 主語-動詞-目的語。格は依存関係から（nsubj → 主格、obj → 対格、前置詞の目的語 → 前置詞句、移動の動詞・ở の
  目的語 → 「〜に」、二重目的語の前のほう → 「〜に」）
* 修飾語・所有者・指示詞は名詞の後ろ（sách mới「新しい本」、mẹ tôi「私の母」、sách của tôi「私の本」、sách này「この本」）
* 数詞 + 量詞は名詞に掛かる「二匹の」（hai con chó）。数の無い量詞（con mèo）は訳さない。数える名詞（người・ngày・năm …）は
  数詞と1語に（hai người「二人」、trăm năm「百年」）。một + 名詞は「ある」。các・những は複数の印
* 相・時制: đã（過去・完了）、đang（進行）、sẽ（未来）、vừa / mới（「〜したばかりだ」）、từng / đã từng（「〜したことがある」）、
  動詞 + rồi（「もう〜した」）。相の副詞が無ければ時の語（hôm qua → 過去、ngày mai → 未来）
* 否定 không・chẳng、chưa（「まだ〜ない」）、đừng（「〜するな」）、hãy（命令）
* 助動詞・動詞の連なり: muốn（「〜たい」）、có thể（「〜できる」）、phải（「〜なければならない」）、thích + 動詞
  （「〜するのが好きだ」）、đi + 動詞（「〜しに行く」）、方向の補語（ngồi xuống「座る」、đứng lên「立ち上がる」）
* 受動: bị（被害）・được（恩恵）+（動作主）+ 動詞。動作主は「〜によって」
* 存在・所有の có: có の前は所有者「〜には」、後ろが有るもの（中国語の 有 と同じ）。形容詞の述語（Trời đẹp）は見えない繋辞を
  補う。rất + 形容詞・形容詞 + lắm / quá は「とても〜」
* 疑問: 文末の không・chưa（có … không?、… chưa?「もう〜したか」）と疑問詞（gì・ai・đâu・nào・bao giờ …）。疑問文の
  親族名詞の代名詞（anh・chị・em …）は聞き手「あなた」。「知る・言う」の動詞の後ろの疑問詞は間接疑問
* 関係節（名詞 + mà + 節、Stanza の acl）は名詞の訳に組み込む。補文の rằng / là（「〜と」「〜ことを」）、従属節
  （nếu … thì「〜なら」、vì … nên「〜ので」）。従属節の後ろの thì・nên は訳さない
* trời + mưa「雨が降る」、người + 国名「〜人」、tiếng + 国名「〜語」、anh ấy・chị ấy（「彼」「彼女」）

## カタカナ読み（`vietnamese/katakana.py`）

`--kana` はハノイの発音から音節ごとに: xin chào → シン チャオ、cảm ơn → カム オン、Hà Nội → ハー ノイ、phở → フォー、
bánh mì → バイン ミー、áo dài → アオ ザイ。

* 頭子音 d・gi・r は [z] で「ザ」行、v は「ヴ」、ph は「フ」、ch・tr は「チャ」行、x・s は「サ」行、nh は「ニャ」行、
  ng・ngh は「ガ」行、đ は「ダ」行
* 末子音 -m「ム」、-n・-ng・-nh「ン」、-p「ップ」、-t「ット」、-c・-ch「ック」。-anh・-ach は「アイン・アイック」
* 母音1つで終わる音節は「ー」（bà → バー）。声調は書かない

## 見本

* `samples/vietnamese.txt`: 自作の文（節ごとの文法事項）と、パブリックドメインの文（グエン・ズー『金雲翹』の冒頭、ことわざ）

## まだできないこと

* 文脈による人称代名詞の訳し分け（anh「兄・あなた・彼」を疑問文・命令文のほかは「彼」に）。敬語・文末の助詞のニュアンス
  （ạ・nhé・nhỉ は訳さない）
* 名詞 + 名詞の複合（chữ tài「才能という字」）、詩の語順。英語の語義の訳せない語（bể dâu「all the vicissitudes of human life」）
* 字喃・漢字の文の入力（漢越語の漢字は語の注・語源（-E）に出すだけ）。主語・目的語の再現率の評価（UD Vietnamese-VTB）
