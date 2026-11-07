#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語の語の項目: Stanza (UD Vietnamese-VTB で学習したモデル) で切り分け・品詞・依存関係を付け、
# 機能語 (代名詞・量詞・前置詞・相の副詞・助詞 …) はここの表、内容語の訳は辞書 (Wiktionary の英語の語義を core/en_ja.py で)
#
import functools
import os

from dragoman.core import paths
from . import dictionary

STANZA_DIR = paths.data('vi', 'stanza')

# 代名詞 → (訳, 人称, 数)。親族名詞の代名詞 (anh・chị・em・ông・bà …) は3人称で、疑問文では2人称に (analyzer)
PRONOUNS = {'tôi': ('私', 1, 'sg'), 'tao': ('俺', 1, 'sg'), 'tớ': ('僕', 1, 'sg'), 'mình': ('自分', 1, 'sg'),
            'ta': ('我々', 1, 'pl'), 'chúng tôi': ('私たち', 1, 'pl'), 'chúng ta': ('私たち', 1, 'pl'),
            'chúng mình': ('私たち', 1, 'pl'), 'chúng tao': ('俺たち', 1, 'pl'), 'mày': ('お前', 2, 'sg'),
            'cậu': ('君', 2, 'sg'), 'bạn': ('あなた', 2, 'sg'), 'các bạn': ('あなたたち', 2, 'pl'),
            'nó': ('それ,彼', 3, 'sg'), 'hắn': ('あいつ', 3, 'sg'), 'họ': ('彼ら', 3, 'pl'), 'chúng nó': ('彼ら', 3, 'pl'),
            'anh': ('彼', 3, 'sg'), 'chị': ('彼女', 3, 'sg'), 'em': ('君', 2, 'sg'), 'ông': ('彼', 3, 'sg'),
            'bà': ('彼女', 3, 'sg'), 'cô': ('彼女', 3, 'sg'), 'chú': ('おじさん', 3, 'sg'), 'bác': ('おじさん', 3, 'sg'),
            'anh ấy': ('彼', 3, 'sg'), 'chị ấy': ('彼女', 3, 'sg'), 'ông ấy': ('彼', 3, 'sg'), 'bà ấy': ('彼女', 3, 'sg'),
            'cô ấy': ('彼女', 3, 'sg'), 'em ấy': ('その子', 3, 'sg'), 'cậu ấy': ('彼', 3, 'sg'),
            'mọi người': ('みんな', 3, 'pl'), 'tất cả': ('すべて', 3, 'pl'), 'ai': ('誰', 3, 'sg'), 'gì': ('何', 3, 'sg'),
            'cái gì': ('何', 3, 'sg'), 'đây': ('これ,ここ', 3, 'sg'), 'đó': ('それ', 3, 'sg'), 'đấy': ('それ', 3, 'sg'),
            'kia': ('あれ', 3, 'sg'), 'này': ('これ', 3, 'sg'), 'đâu': ('どこ', 3, 'sg'), 'ở đâu': ('どこ', 3, 'sg'),
            'ai đó': ('誰か', 3, 'sg'), 'gì đó': ('何か', 3, 'sg'), 'người ta': ('人々', 3, 'pl')}
# 親族名詞の代名詞: 疑問文・命令文・呼びかけでは聞き手 (「あなた」)
KINSHIP = {'anh': 'あなた', 'chị': 'あなた', 'em': '君', 'ông': 'あなた', 'bà': 'あなた', 'cô': 'あなた', 'chú': 'おじさん',
           'bác': 'あなた'}
PRONOUN_GENDERS = {'anh': 'm', 'ông': 'm', 'chú': 'm', 'bác': 'm', 'chị': 'f', 'bà': 'f', 'cô': 'f', 'anh ấy': 'm',
                   'ông ấy': 'm', 'chị ấy': 'f', 'bà ấy': 'f', 'cô ấy': 'f', 'cậu ấy': 'm'}
INTERROGATIVE_PRONOUNS = {'ai', 'gì', 'cái gì', 'đâu', 'ở đâu'}
# 名詞の後ろの指示詞 (sách này「この本」) と、名詞の前の数量の語 (mỗi người「それぞれの人」)
DEMONSTRATIVES = {'này': 'この', 'đó': 'その', 'đấy': 'その', 'ấy': 'その', 'kia': 'あの', 'nọ': 'あの', 'nào': 'どの',
                  'đây': 'この'}
PRENOMINAL = {'mỗi': 'それぞれの', 'mọi': 'すべての', 'vài': 'いくつかの', 'nhiều': 'たくさんの', 'ít': '少しの',
              'tất cả': 'すべての', 'cả': 'すべての', 'từng': '一つ一つの', 'một vài': 'いくつかの', 'một số': 'いくつかの',
              'các': '', 'những': '', 'mấy': '何', 'bao nhiêu': 'いくつの', 'một': '一'}
PLURAL_MARKERS = {'các', 'những'}
NUMBERS = {'không': 0, 'một': 1, 'mốt': 1, 'hai': 2, 'ba': 3, 'bốn': 4, 'tư': 4, 'năm': 5, 'lăm': 5, 'sáu': 6, 'bảy': 7,
           'bẩy': 7, 'tám': 8, 'chín': 9, 'mười': 10, 'mươi': 10, 'trăm': 100, 'nghìn': 1000, 'ngàn': 1000,
           'vạn': 10000, 'triệu': 1000000, 'linh': 0, 'lẻ': 0}
# 量詞 → 日本語の助数詞 (hai con chó「二匹の犬」)。数の無い量詞 (con mèo「(その) 猫」) は訳さない
CLASSIFIERS = {'con': '匹', 'cái': 'つ', 'chiếc': 'つ', 'quyển': '冊', 'cuốn': '冊', 'tờ': '枚', 'tấm': '枚', 'bức': '枚',
               'lá': '枚', 'ngôi': '軒', 'căn': '軒', 'toà': '棟', 'tòa': '棟', 'người': '人', 'đứa': '人', 'vị': '名',
               'cây': '本', 'quả': '個', 'trái': '個', 'bông': '輪', 'đôi': '組', 'bộ': '揃い', 'bài': '編', 'viên': '個',
               'hòn': '個', 'bản': '部', 'cốc': '杯', 'ly': '杯', 'chén': '杯', 'bát': '杯', 'chai': '本', 'lần': '回',
               'tuổi': '歳', 'ngày': '日', 'năm': '年', 'tháng': 'か月', 'giờ': '時間', 'phút': '分', 'chuyến': '便',
               'cơn': '回', 'mảnh': '切れ', 'tòa nhà': '棟', 'nhà': '軒', 'câu': '文', 'chữ': '字', 'ngọn': '本',
               'dòng': '行', 'cành': '本', 'củ': '個', 'gói': '包み', 'hộp': '箱', 'túi': '袋', 'đĩa': '皿', 'tô': '杯'}
# 前置詞 → 訳 (前置詞句は共通の解析器で「〜で」の句に)
PREPOSITIONS = {'ở': '〜で', 'tại': '〜で', 'trong': '〜の中で', 'ngoài': '〜の外で', 'trên': '〜の上で', 'dưới': '〜の下で',
                'giữa': '〜の間で', 'bên cạnh': '〜のそばで', 'cạnh': '〜のそばで', 'sau': '〜の後で', 'trước': '〜の前で',
                'với': '〜と', 'cùng': '〜と一緒に', 'cùng với': '〜と一緒に', 'cho': '〜に', 'từ': '〜から', 'đến': '〜まで',
                'tới': '〜まで', 'về': '〜について', 'vào': '〜に', 'bằng': '〜で', 'bởi': '〜によって', 'như': '〜のように',
                'theo': '〜に従って', 'vì': '〜のために', 'qua': '〜を通って', 'khỏi': '〜から', 'sang': '〜へ',
                'lên': '〜へ', 'xuống': '〜へ', 'ra': '〜へ', 'gần': '〜の近くで', 'quanh': '〜の周りで',
                'trừ': '〜を除いて', 'ngoài ra': '〜のほかに', 'của': '〜の', 'đối với': '〜に対して', 'nhờ': '〜のおかげで',
                'thay': '〜の代わりに', 'giống như': '〜のように', 'kể từ': '〜以来'}
# 場所・時の前置詞の後ろでは「〜に」(動詞の後ろの到達点: đặt sách trên bàn「机の上に 置く」は analyzer で)
CONJUNCTIONS = {'và': 'と,そして', 'với': 'と', 'hoặc': 'または', 'hay': 'または,それとも', 'hoặc là': 'または',
                'nhưng': 'しかし', 'nhưng mà': 'しかし', 'mà': 'しかし', 'song': 'しかし', 'còn': '一方',
                'rồi': 'それから', 'nên': 'だから', 'cho nên': 'だから', 'vì vậy': 'だから', 'vì thế': 'だから',
                'do đó': 'だから', 'thế nhưng': 'しかし', 'tuy nhiên': 'しかし', 'vả lại': 'しかも', 'và rồi': 'そして',
                'vì': '〜ので', 'bởi vì': '〜ので', 'tại vì': '〜ので', 'do': '〜ので', 'nếu': 'もし', 'giá mà': 'もし',
                'khi': '〜とき', 'lúc': '〜とき', 'tuy': '〜けれども', 'mặc dù': '〜けれども', 'dù': '〜ても',
                'dẫu': '〜ても', 'để': '〜ために', 'sau khi': '〜後で', 'trước khi': '〜前に', 'trong khi': '〜間に',
                'cho đến khi': '〜まで', 'cho tới khi': '〜まで', 'hễ': '〜たびに', 'thì': ''}
SUBORDINATORS = {'vì': ('ので', None), 'bởi vì': ('ので', None), 'tại vì': ('ので', None), 'do': ('ので', None),
                 'nếu': ('なら', None), 'giá mà': ('なら', None), 'khi': ('とき', None), 'lúc': ('とき', None),
                 'tuy': ('けれども', None), 'mặc dù': ('けれども', None), 'dù': ('ても', None), 'dẫu': ('ても', None),
                 'sau khi': ('後で', 'perfect'), 'trước khi': ('前に', 'present'), 'trong khi': ('間に', None),
                 'cho đến khi': ('まで', 'present'), 'cho tới khi': ('まで', 'present'), 'để': ('ために', 'present')}
# 動詞の前の相・時制の副詞 → 時制
ASPECTS = {'đã': 'perfect', 'đang': 'progressive', 'sẽ': 'future', 'vừa': 'perfect', 'mới': 'perfect',
           'vừa mới': 'perfect', 'sắp': 'future', 'từng': 'experiential', 'đã từng': 'experiential', 'đương': 'progressive'}
ASPECT_FORMS = {'đã': '過去・完了 (đã + 動詞)', 'đang': '進行 (đang + 動詞)', 'sẽ': '未来 (sẽ + 動詞)',
                'vừa': '直前の完了 (vừa + 動詞「〜したばかり」)', 'mới': '直前の完了 (mới + 動詞「〜したばかり」)',
                'vừa mới': '直前の完了 (vừa mới + 動詞「〜したばかり」)', 'sắp': '近い未来 (sắp + 動詞「もうすぐ〜する」)',
                'từng': '経験 (từng + 動詞「〜したことがある」)', 'đã từng': '経験 (đã từng + 動詞「〜したことがある」)',
                'đương': '進行 (đương + 動詞)'}
NEGATIONS = {'không': '〜ない', 'chẳng': '〜ない', 'chả': '〜ない', 'chưa': 'まだ〜ない', 'đừng': '〜するな', 'chớ': '〜するな',
             'không hề': '決して〜ない', 'chẳng hề': '決して〜ない', 'chưa hề': '一度も〜ない'}
# 助動詞 + 動詞: 動詞に付ける形 (muốn đi「行きたい」)
MODALS = {'muốn': 'たい', 'có thể': 'ことができる', 'phải': 'なければならない', 'cần': '必要がある', 'nên': 'べきだ',
          'định': 'つもりだ', 'dám': '勇気がある', 'biết': 'ことができる', 'cần phải': 'なければならない',
          'không thể': 'ことができない', 'thích': 'のが好きだ', 'hãy': 'なさい', 'được': 'てもよい', 'toan': 'つもりだ',
          'mong': 'たい', 'chắc': 'だろう', 'có lẽ': 'かもしれない', 'bắt đầu': '始める', 'thôi': 'やめる'}
# 文末の助詞 (疑問の không・chưa は analyzer で)
FINAL_PARTICLES = {'à', 'ạ', 'nhé', 'nhỉ', 'chứ', 'vậy', 'thế', 'nha', 'hả', 'hở', 'cơ', 'kìa', 'đấy', 'nhá', 'chăng',
                   'ư', 'sao', 'đi', 'thôi'}
QUESTION_PARTICLES = {'không', 'chưa', 'à', 'hả', 'hở', 'chứ', 'chăng', 'ư', 'sao', 'nhỉ', 'chưa ạ', 'không ạ'}
# 程度の副詞 (形容詞の前・後ろ)
DEGREE_BEFORE = {'rất': 'とても', 'hơi': '少し', 'khá': 'かなり', 'quá': 'あまりに', 'thật': '本当に', 'cực kỳ': '極めて',
                 'vô cùng': '非常に', 'hết sức': '非常に', 'càng': 'ますます', 'nhất': '最も'}
DEGREE_AFTER = {'lắm': 'とても', 'quá': 'とても', 'nhất': '最も', 'hơn': 'もっと', 'thế': 'そんなに', 'vậy': 'そんなに',
                'ghê': 'すごく', 'cực': 'すごく'}
# 時の語 → 時制 (相の副詞の無い動詞に)
TIME_TENSES = {'hôm qua': 'perfect', 'hôm kia': 'perfect', 'năm ngoái': 'perfect', 'tuần trước': 'perfect',
               'tháng trước': 'perfect', 'năm trước': 'perfect', 'ngày xưa': 'perfect', 'hồi đó': 'perfect',
               'lúc nãy': 'perfect', 'vừa rồi': 'perfect', 'ngày mai': 'future', 'mai': 'future', 'ngày kia': 'future',
               'năm sau': 'future', 'năm tới': 'future', 'tuần sau': 'future', 'tuần tới': 'future',
               'tháng sau': 'future', 'tháng tới': 'future', 'sau này': 'future'}
# 国・言語の名前 (người + 国名「〜人」、tiếng + 国名「〜語」)
NATIONS = {'việt nam': 'ベトナム', 'việt': 'ベトナム', 'nhật': '日本', 'nhật bản': '日本', 'trung quốc': '中国',
           'hoa': '中国', 'hán': '漢', 'anh': '英', 'pháp': 'フランス', 'mỹ': 'アメリカ', 'đức': 'ドイツ', 'nga': 'ロシア',
           'hàn': '韓国', 'hàn quốc': '韓国', 'thái': 'タイ', 'lào': 'ラオス', 'campuchia': 'カンボジア', 'ý': 'イタリア',
           'tây ban nha': 'スペイン', 'ấn độ': 'インド', 'triều tiên': '朝鮮', 'khmer': 'クメール', 'chăm': 'チャム',
           'kinh': 'キン', 'miên': 'クメール', 'la tinh': 'ラテン', 'hy lạp': 'ギリシア', 'phạn': 'サンスクリット'}
LANGUAGE_NAMES = {'anh': '英', 'pháp': 'フランス', 'việt': 'ベトナム', 'nhật': '日本', 'trung': '中国', 'hoa': '中国',
                  'hán': '漢', 'phạn': 'サンスクリット', 'la tinh': 'ラテン'}
# 訳語を決めておく語 (Wiktionary の最初の語義が外れるもの・訳せないもの)
GLOSSES = {'là': '〜である', 'có': '持つ,ある', 'ở': 'いる,住む', 'đi': '行く', 'đến': '来る,着く', 'về': '帰る',
           'tới': '着く', 'ra': '出る', 'vào': '入る', 'lên': '上がる', 'xuống': '下りる', 'sang': '渡る',
           'làm': 'する,作る', 'cho': '与える', 'nói': '言う,話す', 'biết': '知っている', 'hiểu': '分かる',
           'yêu': '愛する', 'thương': '愛する', 'nhớ': '覚えている,懐かしむ', 'quên': '忘れる', 'gặp': '会う', 'chờ': '待つ',
           'đợi': '待つ', 'mở': '開ける', 'đóng': '閉める', 'gọi': '呼ぶ', 'tên': '名前', 'sinh viên': '学生',
           'học sinh': '生徒', 'thầy giáo': '先生', 'cô giáo': '先生', 'giáo viên': '教師', 'thầy': '先生',
           'bác sĩ': '医者', 'cơm': 'ご飯', 'cà phê': 'コーヒー', 'trà': 'お茶', 'nước': '水', 'phở': 'フォー',
           'bánh mì': 'パン', 'áo dài': 'アオザイ', 'nhà': '家', 'trường': '学校', 'chợ': '市場', 'trời': '空,天気',
           'mưa': '雨', 'nắng': '日差し', 'gió': '風', 'tiếng': '言葉,音', 'chữ': '文字', 'người': '人', 'ngày': '日',
           'đêm': '夜', 'sáng': '朝', 'tối': '夜', 'năm': '年', 'tháng': '月', 'tuần': '週', 'hôm nay': '今日',
           'hôm qua': '昨日', 'ngày mai': '明日', 'bây giờ': '今', 'khỏe': '元気な', 'khoẻ': '元気な', 'vui': 'うれしい',
           'buồn': '悲しい', 'cũ': '古い', 'già': '年老いた', 'trẻ': '若い', 'xa': '遠い', 'gần': '近い', 'to': '大きい',
           'cao': '高い', 'thấp': '低い', 'dài': '長い', 'ngắn': '短い', 'nóng': '暑い', 'lạnh': '寒い', 'ngon': 'おいしい',
           'đắt': '高い', 'rẻ': '安い', 'dễ': '易しい', 'khó': '難しい', 'tốt': '良い', 'xấu': '悪い', 'mệt': '疲れた',
           'đói': '空腹の', 'no': '満腹の', 'Phật': '仏', 'phật': '仏', 'đức phật': '仏陀', 'bồ tát': '菩薩',
           'pháp': '法', 'tăng': '僧', 'chùa': '寺', 'kinh': '経', 'tâm': '心', 'niết bàn': '涅槃', 'thiền': '禅',
           'tu': '修行する', 'cảm ơn': '感謝する', 'cám ơn': '感謝する', 'xin chào': 'こんにちは', 'chào': '挨拶する',
           'xin lỗi': 'すみません', 'thích': '好む', 'muốn': '欲しい', 'cần': '必要とする', 'được': '得る',
           'bị': '被る', 'mất': '失う', 'thấy': '見える,感じる', 'xem': '見る', 'nhìn': '見る', 'nghe': '聞く',
           'đọc': '読む', 'viết': '書く', 'học': '学ぶ', 'dạy': '教える', 'hỏi': '尋ねる', 'trả lời': '答える',
           'làm việc': '働く', 'ngủ': '寝る', 'thức': '起きている', 'dậy': '起きる', 'ngồi': '座る', 'đứng': '立つ',
           'chạy': '走る', 'bay': '飛ぶ', 'bơi': '泳ぐ', 'hát': '歌う', 'múa': '踊る', 'chơi': '遊ぶ', 'sống': '生きる,住む',
           'chết': '死ぬ', 'sinh': '生まれる', 'lấy': '取る', 'đưa': '渡す', 'gửi': '送る', 'mang': '持って行く',
           'tìm': '探す', 'thấy được': '見つける', 'giúp': '助ける', 'tin': '信じる', 'nghĩ': '思う,考える',
           'cảm thấy': '感じる', 'trở thành': '〜になる', 'thành': '〜になる', 'bắt đầu': '始める', 'kết thúc': '終わる',
           'xong': '終える', 'quyển sách': '本', 'cuốn sách': '本', 'sách': '本', 'vở': 'ノート', 'bút': 'ペン',
           'bàn': '机', 'ghế': '椅子', 'cửa': '戸', 'cửa sổ': '窓', 'xe': '車', 'xe máy': 'バイク', 'xe đạp': '自転車',
           'máy bay': '飛行機', 'tàu': '船,列車', 'đường': '道', 'thành phố': '都市', 'làng': '村', 'quê': '故郷',
           'đất nước': '国', 'mẹ': '母', 'bố': '父', 'cha': '父', 'ba': '父', 'má': '母', 'con': '子供', 'vợ': '妻',
           'chồng': '夫', 'bạn bè': '友人たち', 'bạn': '友人', 'em gái': '妹', 'em trai': '弟', 'anh trai': '兄',
           'chị gái': '姉', 'ông bà': '祖父母', 'gia đình': '家族', 'trẻ em': '子供', 'đàn ông': '男', 'đàn bà': '女',
           'phụ nữ': '女性', 'con trai': '息子,男の子', 'con gái': '娘,女の子', 'cô gái': '少女', 'chàng trai': '若者',
           'mèo': '猫', 'chó': '犬', 'chim': '鳥', 'cá': '魚', 'gà': '鶏', 'trâu': '水牛', 'bò': '牛', 'ngựa': '馬',
           'hoa': '花', 'cây': '木', 'lá': '葉', 'sông': '川', 'núi': '山', 'biển': '海', 'mặt trời': '太陽',
           'mặt trăng': '月', 'trăng': '月', 'sao': '星', 'đất': '土地', 'tiền': 'お金', 'việc': '仕事', 'công việc': '仕事',
           'chuyện': '話', 'câu chuyện': '物語', 'bài hát': '歌', 'thơ': '詩', 'lòng': '心', 'tình yêu': '愛',
           'hạnh phúc': '幸福な', 'đời': '人生', 'cuộc đời': '人生', 'quá khứ': '過去', 'tương lai': '未来',
           'độc lập': '独立', 'tự do': '自由', 'dân tộc': '民族', 'nhân dân': '人民', 'tổ quốc': '祖国',
           'quý': '貴い', 'nhà văn': '作家', 'nữa': 'もう', 'hay': '面白い', 'nhau': '互いに', 'ghét': '憎む', 'nguồn': '源', 'khéo': '巧みな', 'cõi': '世界', 'mệnh': '運命', 'tài': '才能', 'sớm': '早い', 'muộn': '遅い', 'đại học': '大学', 'trường đại học': '大学', 'mắng': '叱る', 'đánh': '打つ,殴る', 'khen': '褒める', 'phạt': '罰する', 'cắn': '噛む', 'nhà thơ': '詩人', 'nhà báo': '記者', 'nhà khoa học': '科学者', 'hơn': 'より〜', 'không có gì': '何もない'}

# 動詞として読むときの訳 (名詞と動詞の両方の語: mưa「雨・雨が降る」)
VERB_GLOSSES = {'mưa': '雨が降る', 'tên': '名付ける', 'con': '', 'người': ''}
VERB_GLOSSES = {k: v for k, v in VERB_GLOSSES.items() if v}

GENDER = 'c'


@functools.lru_cache(maxsize=1)
def _pipelines():
    import logging
    import stanza
    logging.getLogger('stanza').setLevel(logging.ERROR)
    common = dict(dir=STANZA_DIR, download_method=None, logging_level='ERROR', package=None)
    tok = stanza.Pipeline('vi', processors={'tokenize': 'vtb_charlm'}, tokenize_no_ssplit=True, **common)
    parse = stanza.Pipeline('vi', processors={'tokenize': 'vtb_charlm', 'pos': 'vtb_charlm', 'lemma': 'identity',
                                              'depparse': 'vtb_charlm'}, tokenize_pretokenized=True, **common)
    return tok, parse


def available():
    if not dictionary.available() or not os.path.isdir(os.path.join(STANZA_DIR, 'vi')):
        return False
    try:
        import stanza  # noqa: F401
    except ImportError:
        return False
    return True


def tokenize(sylls):
    """音節の列 → Stanza の語の列 (空白でつないだ音節)。Stanza が使えなければ None"""
    try:
        tok, _ = _pipelines()
    except (ImportError, OSError, ValueError):
        return None
    doc = tok(' '.join(sylls))
    return [t.text for s in doc.sentences for t in s.tokens]


class Token:
    """Stanza の語 (spaCy の Token と同じ名前の属性: i, text, tag_, pos_, dep_, head, children)"""
    def __init__(self, i, text, upos, xpos, dep):
        self.i, self.text, self.pos_, self.tag_, self.dep_ = i, text, upos, xpos, dep
        self.head = self
        self.children = []

    @property
    def subtree(self):
        out = [self]
        for c in self.children:
            out += c.subtree
        return sorted(out, key=lambda t: t.i)

    def __repr__(self):
        return '%s/%s/%s' % (self.text, self.tag_, self.dep_)


def parse(words):
    """語の列 → Token の列 (品詞・依存関係)"""
    _, nlp = _pipelines()
    doc = nlp([list(words)])
    sent = doc.sentences[0]
    tokens = [Token(k, w.text, w.upos, w.xpos, w.deprel) for k, w in enumerate(sent.words)]
    for k, w in enumerate(sent.words):
        if w.head:
            tokens[k].head = tokens[w.head - 1]
            tokens[w.head - 1].children.append(tokens[k])
    return tokens


POS_PREFERENCE = {'noun': ('noun', 'name', 'classifier', 'pronoun'), 'verb': ('verb', 'phrase'), 'adj': ('adj', 'verb'),
                  'adv': ('adv', 'particle', 'adj'), 'name': ('name', 'noun')}


@functools.lru_cache(maxsize=50000)
def gloss(word, pos):
    """語 → (訳, 'ja' / 'en', 辞書の項目)。pos の読みの語義を先に"""
    from dragoman.core import en_ja
    rows = list(dictionary.lookup(word))
    order = POS_PREFERENCE.get(pos, (pos,))
    rows.sort(key=lambda r: order.index(r['pos']) if r['pos'] in order else len(order))
    row = rows[0] if rows else None
    key = word if word in GLOSSES else word.lower()
    if pos == 'verb' and key in VERB_GLOSSES:
        return VERB_GLOSSES[key], 'ja', row
    if key in GLOSSES:
        return GLOSSES[key], 'ja', row
    for r in rows[:3]:
        if not r['en']:
            continue
        if r['pos'] == 'name' and pos != 'name' and word[:1].islower():
            continue
        ja = en_ja.translate(r['en'], pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2)
        if ja:
            return ja, 'ja', r
    if row is None or not row['en']:
        return None, None, row
    return row['en'].split(',')[0], 'en', row


def number(words):
    """数詞の列 (hai mươi ba) → 整数。読めなければ None"""
    total, current = 0, 0
    for w in words:
        w = w.lower()
        if w.isdigit():
            current = current * 10 + int(w) if current else int(w)
            continue
        n = NUMBERS.get(w)
        if n is None:
            return None
        if n == 10 and w == 'mươi':
            current = (current or 1) * 10
        elif n == 10:
            current += 10
        elif n in (100, 1000, 10000, 1000000):
            if n >= 1000:
                total += (current or 1) * n
                current = 0
            else:
                current = (current or 1) * n
        else:
            current += n
    return total + current


def kanji_number(n):
    """整数 → 漢数字 (23 → 二十三)"""
    digits = '〇一二三四五六七八九'
    if n == 0:
        return '〇'
    out = ''
    for unit, mark in ((100000000, '億'), (10000, '万')):
        if n >= unit:
            out += kanji_number(n // unit) + mark
            n %= unit
    for unit, mark in ((1000, '千'), (100, '百'), (10, '十')):
        if n >= unit:
            q = n // unit
            out += ('' if q == 1 else digits[q]) + mark
            n %= unit
    if n:
        out += digits[n]
    return out


def adverbial(ja):
    """形容詞の訳 → 副詞の形 (速い → 速く、静かな → 静かに)"""
    out = []
    for j in ja.split(','):
        if j.endswith('い') and not j.endswith(('きれい', 'きらい')):
            out.append(j[:-1] + 'く')
        elif j.endswith(('な', 'の')):
            out.append(j[:-1] + 'に')
        else:
            out.append(j + 'に')
    return ','.join(out)
