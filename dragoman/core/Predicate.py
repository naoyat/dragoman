#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dragoman.core.LatinObject import LatinObject
from dragoman.core.Word import Word

from dragoman.core.AndOr import AndOr, braced
from dragoman.core.PrepClause import PrepClause
from dragoman.core import language
from .japanese import JaVerb, copula_predicate, copula_conjunctive
from . import verb_flags as Verb
from .animacy import is_animate

TENSE_LABELS = {'imperfect': '未完了', 'future': '未来', 'perfect': '完了',
                'past-perfect': '過去完了', 'future-perfect': '未来完了', 'aorist': 'アオリスト'}


def english_verb_label(verb, negated=False):
    labels = [TENSE_LABELS[verb.attrib('tense')]] if verb.attrib('tense') in TENSE_LABELS else []
    if verb.attrib('voice') == 'passive':
        labels.append('受動')
    elif verb.attrib('voice') in ('middle', 'middle-passive'):
        labels.append('中動')
    if verb.attrib('mood') in ('subjunctive', 'imperative', 'optative'):
        labels.append({'subjunctive': '接続法', 'imperative': '命令', 'optative': '希求'}[verb.attrib('mood')])
    if negated:
        labels.append('否定')
    return '[%s]' % '・'.join(labels) if labels else ''


class Predicate (LatinObject):
    def __init__(self, verb):
        self.verb = verb
        self.case_slot = {}
        self.modifiers = []
        self.first_item = verb.items[0]
        self.surface = verb.surface
        self.surface_len = len(self.surface)
        self.conjunction = None
        self.subordinates = []  # 従属節 (独立奪格など)
        self.subordinate = False  # 不定詞句の中の述語 (主語は sum でも「は」でなく「が」)
        self.gap = None  # 関係節の述語なら空所の役割 ('Nom' なら主語を補わない)
        self.language = language.current()  # 訳すときにもこの言語の設定を使う (訳は解析の後で行うので)
        self.is_sum = self.language.is_copula(self.first_item.item.get('pres1sg', None))  # 繋辞 (sum)

    def add_nominal(self, case, obj):
        # self.objects[case] = self.objects.get(case, []).append(obj)
        if case in self.case_slot:
            self.case_slot[case].append(obj)
        else:
            self.case_slot[case] = [obj]

    def add_subordinate(self, clause):
        self.subordinates.append(clause)

    def add_modifier(self, adv):
        self.modifiers.append(adv)

    def is_verb(self):
        return True

    def person(self):
        return self.first_item.attrib('person')
    def number(self):
        return self.first_item.attrib('number')
    def mood(self):
        return self.first_item.attrib('mood')

    def detail(self):
        return self.verb.detail()

    def _particle(self, case, obj):
        """言語の設定 (Language.particle) で決まる、格の枠の語の助詞。決まらなければ None (既定の助詞)"""
        return self.language.particle(case, obj, self) if self.language.particle else None

    def _asks_other_than_subject(self):
        """主語のほかに疑問詞がある (副詞・目的語・前置詞句の中)"""
        from .Question import is_interrogative
        nodes = list(self.modifiers) + ([self.conjunction] if self.conjunction else [])
        for case, objs in self.case_slot.items():
            if case != 'Nom':
                for obj in objs:
                    nodes += list(getattr(obj, 'words', [])) if isinstance(obj, PrepClause) else [obj]
        nodes += [m for n in nodes if isinstance(n, Word) for m in getattr(n, 'modifiers', [])]   # which book の which
        return any(isinstance(n, Word) and (is_interrogative(n) or n.items and n.items[0].attrib('interrogative'))
                   for n in nodes)

    def _negative(self):
        """否定の副詞 (nōn, не, нет, οὐ, na) がある文か"""
        if self.first_item.attrib('negative'):
            return True  # 否定の接頭辞の付いた動詞 (ペルシア語の نمی‌روم「行かない」)
        words = list(self.modifiers) + ([self.conjunction] if self.conjunction else [])
        return any(is_negation(w, self.language) or
                   (isinstance(w, Word) and w.items and w.items[0].ja.endswith(('〜ない', '〜しない')))
                   for w in words)

    def _personal_subject(self, case_slot):
        noms = case_slot.get('Nom', []) + (case_slot.get('Nom/Acc', []) if self.person() == 3 else [])
        return len(noms) == 1 and isinstance(noms[0], Word) and noms[0].items[0].pos == 'pronoun' and \
            _animate(noms[0])

    def _existential(self, case_slot):
        """存在・所有の文か: 繋辞で、主格が名詞類1つだけ (補語の形容詞が無い) で、所有者 (与格、述語の枠に残った属格) か
        場所 (前置詞句・処格) がある (Mihi est liber, Est in hortō rosa, У меня есть книга, ἔστι μοι βιβλίον)。
        繋辞の項目に existential があればそれだけで (ロシア語の нет + 生格)。
        存在文なら主語が人のとき 'animate'、それ以外は True"""
        if not self.is_sum:
            return False
        noms = case_slot.get('Nom', []) + (case_slot.get('Nom/Acc', []) if self.person() == 3 else [])
        if len(noms) != 1 or not _nominal(noms[0]) or case_slot.get('Acc'):
            return False  # 対格があれば存在文ではない (繋辞は対格を取らない)
        if isinstance(noms[0], Word) and noms[0].items and noms[0].items[0].attrib('complement') and \
                self.gap in ('Nom', 'Nom/Acc'):
            return False  # 関係節の主語が空所で、残りは補語 (qui est ce qu'on nomme …「{…}ことである」)
        place = any(isinstance(case, tuple) for case in case_slot if case_slot[case]) or bool(case_slot.get('Loc'))
        possessor = any(case_slot.get(case) for case in self.language.possessor_cases)
        if self.first_item.attrib('existential'):
            pass
        elif isinstance(noms[0], Word) and noms[0].items[0].pos == 'pronoun':
            if not place:
                return False  # 代名詞の主語は場所があるときだけ (hoc est …「これは…だ」は存在文でない)
        elif not (place or possessor):
            return False
        return 'animate' if _animate(noms[0]) else True

    def _accusative(self, case_slot, tr):
        """対格の枠の訳を tr に足す (枠は空にする)。否定の語があれば True"""
        acc_objs = case_slot['Acc']
        case_slot['Acc'] = []
        accs, negated = [], False
        for obj in acc_objs:
            t, neg = obj.translate()
            if neg: negated = True
            accs.append(t)
        accs = [braced(acc[:-1] if acc[-1:] == 'が' else acc) for acc in accs]
        particles = [self._particle('Acc', obj) for obj in acc_objs]
        if any(particles):
            tr.append('='.join(t + (p or 'を') for t, p in zip(accs, particles)))  # 時の対格「〜の間」など
        else:
            tr.append('='.join(accs) + 'を')
        return negated

    def translate(self):
        # 訳の組み立てで格スロットを並べ替えるので、作業用のコピーを使う
        # (self.case_slot を書き換えると、表示や再度の translate() の結果が変わってしまう)
        case_slot = {case: list(objs) for case, objs in self.case_slot.items()}
        tr = []
        negated = False

        verb = self.first_item
        person = verb.attrib('person', 0)

        if self.conjunction:
            if self.conjunction.surface.lower() in self.language.and_words:   # 文の頭の Et も
                t = 'そして'
            else:
                t, neg = self.conjunction.translate()
                if neg: negated = True
                if t.endswith(('〜ない', '〜しない')):
                    negated = True  # 文頭の否定の副詞 (nūllō pactō, nōn jam)
                    t = t.split('〜')[0]
            tr.append(t)

        # 独立奪格は文の頭に、述語的な分詞 (花を摘みながら) は主語の後に置く
        for clause in self.subordinates:
            if not getattr(clause, 'adverbial', False):
                tr.append(clause.translate()[0])

        cases_ja = self.language.case_particles

        sum_complement = []
        is_existential = self._existential(case_slot)
        if is_existential and self._personal_subject(case_slot):
            # 人称代名詞が主語なら主語を先に「は」で (私たちは劇場にいた)。場所は「〜に」
            is_existential = 'personal'
        elif is_existential:
            # 存在・所有の文は、場所・所有者を先に。場所は「〜に」(森にライオンがいる)、所有者は「〜には」(私には本がある)。
            # 場所に「〜には」を付けると主題・対比 (森というところにはライオンがいるものだ) の含みになるので付けない。
            # ただし否定の文は「〜には」が自然 (部屋には机がない、シチリアにはケレースがいなかった)
            negative = self._negative()
            for case, objs in list(case_slot.items()):
                if not objs or not (isinstance(case, tuple) or case == 'Loc' or case in self.language.possessor_cases):
                    continue
                for obj in objs:
                    t, neg = obj.translate(existential=True) if isinstance(obj, PrepClause) else obj.translate()
                    if neg: negated = True
                    if isinstance(case, tuple):
                        place = t if isinstance(obj, PrepClause) else _existential_place(t)
                        tr.append(place + 'は' if negative and not place.endswith('には') else place)
                    else:
                        tr.append(t + ('に' if case == 'Loc' and not negative else 'には'))
                case_slot[case] = []
        # Nominative
        noms = []
        nom_acc_objs = case_slot.get('Nom/Acc', [])
        if 'Nom' in case_slot or (person == 3 and nom_acc_objs):
            nom_objs = case_slot.get('Nom', [])
            # nom_acc_objs = case_slot.get('Nom/Acc', [])

            demand = 2 if self.is_sum else 1
            supply = len(nom_objs)
            if supply < demand and nom_acc_objs:
                insufficient = demand - supply
                nom_objs += nom_acc_objs[0:insufficient]
                nom_acc_objs = nom_acc_objs[insufficient:]

            # 繋辞の文で冠詞の付いた主格があれば、それが主語 (ギリシア語: θεὸς ἦν ὁ λόγος「ことばは神であった」)
            articled = [o for o in nom_objs if self.is_sum and _has_article(o)]
            focused = [o for o in nom_objs if self.is_sum and self._particle('Nom', o)]
            from .Question import is_interrogative
            asked = [o for o in nom_objs if self.is_sum and (is_interrogative(o) or isinstance(o, Word) and o.items and
                                                             o.items[0].attrib('complement'))]
            others = [o for o in nom_objs if o not in asked]
            if asked and others and all(_nominal(o) for o in others):   # 主語になれる名詞句があるときだけ
                # 疑問詞・解析器が補語と決めた語は補語 (Who is that man? → その男は誰であるか、he is a doctor の doctor)
                articled = [o for o in nom_objs if o not in asked]
            if focused and len(focused) < len(nom_objs):
                # 言語の設定で主題「は」になる句 (タガログ語の ang、ハワイ語の ʻo) を主語に (He kumu ʻo ia「彼は先生である」)
                articled = focused
            for obj in nom_objs:
                nom, neg = obj.translate()
                if neg: negated = True

                if is_existential:
                    noms.append(nom)  # 存在・所有の文の主語 (Mihi est liber「私には本がある」の liber)
                elif articled:
                    if obj in articled:
                        noms.append(nom)
                    else:
                        sum_complement.append(obj)
                elif self.is_sum:
                    # 形容詞（修飾語）の場合 (サンスクリットでは代名詞も名詞と同じく主語になる: tat tvam asi)
                    nominal = ('noun', 'pronoun') if self.language.pronoun_subject or getattr(obj, 'relatives', None) \
                        else ('noun',)   # 関係節の付いた代名詞は主語になる (Quae dīxistī, ea vēra sunt)
                    if isinstance(obj, Word) and obj.items[0].pos not in nominal or \
                            isinstance(obj, Word) and obj.items[0].attrib('complement') and \
                            (len(nom_objs) > 1 or self.gap in ('Nom', 'Nom/Acc')):
                        # sum なら補語として (解析器が補語と決めた語: 関係節 qui est ce qu'on nomme … の ce)
                        sum_complement.append(obj)
                    elif len(nom_objs) == 1 and self.language.pronoun_subject and isinstance(obj, Word) and \
                            obj.items[0].pos == 'pronoun':
                        noms.append(nom)  # 主格の代名詞だけなら主語 (мы были в театре「私たちは劇場にいた」)
                    elif (len(noms) > 0 or len(nom_objs) == 1):
                        sum_complement.append(obj)
                    else:
                        noms.append(nom)
                else:
                    # 形容詞（修飾語）の場合
                    # (代名詞は訳語が「〜の」のもの (他の, 各人(の)) だけ)
                    if isinstance(obj, Word) and (obj.items[0].pos not in ('noun', 'pronoun') or
                                                  obj.items[0].pos == 'pronoun' and nom.endswith(('の', '(の)'))):
                        # sumでなければそういう人や物として
                        nom += '(人,物)'
                    noms.append(nom)

        if nom_acc_objs:
            case_slot['Acc'] = case_slot.get('Acc', []) + nom_acc_objs
            case_slot['Nom/Acc'] = []

        if not noms and verb.attrib('mood') != 'imperative' and not (self.is_sum and case_slot.get('Inf')) and \
                self.gap not in ('Nom', 'Nom/Acc'):   # 関係節で主語が空所なら補わない ({歌う}少女)
            pn = str(self.person()) + str(self.number())
            subj_ja = {'1sg':'私', '2sg':'あなた', '3sg':'彼,彼女,それ',
                       '1pl':'我々', '2pl':'あなた方', '3pl':'彼ら,彼女ら,それら'}
            if verb.attrib('subject_ja'):
                noms.append(verb.attrib('subject_ja'))   # 解析器が決めた補う主語 (前の節の nous「私たち」)
            elif verb.attrib('shared_subject'):
                pass   # 主節と同じ主語は補わない (Ela disse que me ama「彼女が {私を 愛する}と 言った」。core/Adverbial.py)
            elif pn in subj_ja:
                noms.append(subj_ja[pn])

        if noms:
            nom_case_ja = 'が'
            if self.is_sum and not self.subordinate and (not is_existential or is_existential == 'personal'):
                nom_case_ja = 'は'
            if getattr(self, 'question', False) and self._asks_other_than_subject():
                nom_case_ja = 'は'   # 疑問詞のある疑問文の主語は主題 (あなたは どこで 住むか、駅は どこに あるか)
            nom_particle = next((p for p in (self._particle('Nom', o) for o in self.case_slot.get('Nom', [])) if p), None)
            if nom_particle:
                nom_case_ja = nom_particle  # 言語の設定で決まる主格の助詞 (タガログ語の焦点「は」)
            joined = '='.join(braced(n) for n in noms)   # 訳語の候補は括ってから助詞 ({彼,彼女,それ}が)
            if joined.endswith(nom_case_ja):
                nom_case_ja = ''  # 訳語に助詞まで入っているもの (何が)
            tr.append(joined + nom_case_ja)

        for clause in self.subordinates:
            if getattr(clause, 'adverbial', False):
                tr.append(clause.translate()[0])

        if verb.attrib('object_first') and case_slot.get('Acc'):
            # 目的語を先に (中国語の把構文: 他把书放在桌子上「彼が / 本を / 机の上に / 置く」)
            negated = self._accusative(case_slot, tr) or negated

        for case, objs in list(case_slot.items()):
            if case in ('Nom', 'Nom/Acc', 'Acc', 'Inf', 'Q'): continue
            if not objs: continue
            if isinstance(case, tuple):
                # prep-clause
                case_ja = '' # case.encode('utf-8')
            else:
                case_ja = cases_ja[case]
            trs = []
            existential_place = is_existential == 'personal' and isinstance(case, tuple)
            for obj in objs:
                t, neg = obj.translate(existential=True) if existential_place and isinstance(obj, PrepClause) else \
                    obj.translate()
                if neg: negated = True  # neque ... neque ... は主語以外の枠にも現れる
                if existential_place and not isinstance(obj, PrepClause):
                    t = _existential_place(t)
                trs.append(t)
            particles = [self._particle(case, obj) for obj in objs] if not isinstance(case, tuple) else []
            if is_existential == 'personal' and (case == 'Loc' or case in self.language.possessor_cases):
                particles = ['に'] * len(objs)
            if existential_place:
                trs = [t[:-2] + 'に' if t.endswith('には') else t for t in trs]  # 私たちは劇場にいた
            if case_ja or any(particles):
                trs = [braced(t) for t in trs]
            if any(particles):
                # 言語の設定で語ごとに助詞を決める (ギリシア語: ἀκούω + 属格「〜を」, 比較の属格「〜より」)
                tr.append('='.join(t + (p or case_ja) for t, p in zip(trs, particles)))
            else:
                tr.append('='.join(trs) + case_ja)

        # Accusative
        if case_slot.get('Acc'):
            negated = self._accusative(case_slot, tr) or negated

        # 不定詞句 ({少年が 遊ぶ}と / {本を 読む}ことが)
        for clause in case_slot.get('Inf', []):
            tr.append(clause.translate()[0])
        # 間接疑問 ({何が なる ことを 望んでいた}かを)
        for clause in case_slot.get('Q', []):
            tr.append(clause.translate()[0])

        if verb.attrib('negative'):
            negated = True  # 否定の接頭辞の付いた動詞 (ペルシア語の na- / ne-)
        # adverb
        for adv in self.modifiers:
            if is_negation(adv, self.language):
                negated = True
                continue
            ja = adv.items[0].ja
            if ja.endswith(('〜ない', '〜しない')):
                # 否定の副詞 (nūllō pactō「決して〜ない」, nusquam「どこにも〜ない」): 述語を否定形にする
                negated = True
                ja = ja.split('〜')[0]
            tr.append(ja)

        jas = verb.ja.split(',')

        # flags
        if verb.attrib('mood') == 'imperative':
            flag = Verb.IMPERATIVE
        else:
        # elif verb.attrib('mood') == 'indicative':
            # とりあえず直説法で出しておく
            flag = Verb.INDICATIVE

        if verb.attrib('voice') == 'passive':
            flag |= Verb.PASSIVE

        tense = verb.attrib('tense')
        if tense == 'imperfect':
            flag |= Verb.PAST | Verb.ING
        elif tense in ('perfect', 'aorist', 'pluperfect'):  # ギリシア語のアオリストは過去の形で
            flag |= Verb.PERFECT
        elif tense == 'progressive':
            flag |= Verb.ING  # 現在進行 (ヒンディー語の पढ़ रहा है「読んでいる」)
        elif tense == 'future':
            flag |= Verb.FUTURE

#        if advs != []:
#            print "{", ', '.join(advs), "}",
        if verb.attrib('gloss_lang') == 'en':
            # 英語の訳語 (Wiktionary 由来) は活用させず、時制などを添える
            verb_tr = jas[0] + english_verb_label(verb, negated and not self.is_sum)
        elif flag & Verb.IMPERATIVE and verb.attrib('person') == 1 and not negated:
            # 1人称の命令 (Parlons「話そう」、ラテン語の接続法の勧奨 eāmus「行こう」)
            from .japanese import japanese_form
            verb_tr = ','.join(japanese_form(ja, False, 'volitional', 'present', False) for ja in jas)
        else:
            # 活用して同じ形になる訳語は1つに (知る,知っている → 知らない)
            verb_tr = ','.join(dict.fromkeys(JaVerb(ja).form(flag, negated and not self.is_sum) for ja in jas))
        if is_existential:
            # 存在・所有: 「ある / いる」(否定は「ない / いない」)
            verb_tr = JaVerb('いる' if is_existential in ('animate', 'personal') else 'ある').form(flag & ~Verb.ING,
                                                                                                negated)
            negated = False
        elif self.is_sum and not sum_complement and verb.attrib('gloss_lang', 'ja') == 'ja':
            # 補語の無い繋辞は存在の意味で (εἰμί「有る,居る,存在する,〜である」→ 有った,居た,存在した)
            existential = [ja for ja in jas if not ja.startswith(('〜', '～'))]
            if existential:
                verb_tr = ','.join(JaVerb(ja).form(flag, negated) for ja in existential)
                negated = False
        if is_existential:
            pass
        elif self.is_sum and sum_complement:
            verb_tr = '='.join(copula_translation(obj, copula_tense(tense), negated) for obj in sum_complement)
        elif negated and self.is_sum:
            verb_tr = '¬'+ verb_tr  # 補語の無い sum (〜である) は否定の形を作れない

        if case_slot.get('Inf'):
            verb_tr = verb_tr.lstrip('〜～')  # {本を 読む}ことが できる (possum の訳語は「〜できる」)
        if verb.attrib('concessive') and verb.attrib('gloss_lang', 'ja') == 'ja' and not self.is_sum:
            # 譲歩「〜しても」(ロシア語の сколько бы … ни плёл「どれほど 紡いでも」。解析器が印を付けたもの)
            from .japanese import japanese_form
            verb_tr = ','.join(japanese_form(ja, False, 'te', 'present', negated) + 'も' for ja in jas)
            negated = False
        if verb.attrib('wish') and verb.attrib('gloss_lang', 'ja') == 'ja':
            # 祈願の接続法 (古英語の sī þīn nama ġehālgod「君の名前が神聖にされるように」。解析器が印を付けたものだけ)
            verb_tr = ','.join(v + 'ように' for v in verb_tr.split(','))
        if getattr(self, 'question', False) and not flag & Verb.IMPERATIVE:
            # 直接疑問 (住むか・来たか)。補語の訳語の候補 (医者,医師である) は最後にだけ
            verb_tr = verb_tr + 'か' if self.is_sum and sum_complement else ','.join(v + 'か' for v in verb_tr.split(','))
        tr.append(verb_tr)

#        tr.append(self.first_item.ja )

        if self.language.topic_first:
            # 主題 (「は」の句) を先頭に (タガログ語の焦点: 魚は / 男が / 買った)
            topics = [t for t in tr[:-1] if t.endswith('は') and not t.endswith('には')] + \
                [t for t in tr[:-1] if t.endswith('には')]
            tr = topics[:1] + [t for t in tr if t not in topics[:1]]
        return (' / '.join(tr), False)




def _nominal(obj):
    return isinstance(obj, AndOr) or (isinstance(obj, Word) and obj.items and obj.items[0].pos in ('noun', 'pronoun'))


def _animate(obj):
    if isinstance(obj, Word) and obj.items:
        return is_animate(obj.items[0])
    if isinstance(obj, AndOr):
        return any(_animate(w) for words in obj.words_slots for w in words)
    return False


def _existential_place(t):
    """存在の文の場所の前置詞句 (前置詞句でない語の訳): 最初の訳だけにして「〜に」に ({庭}〜で,〜の中で → {庭}〜に)。
    所有の前置詞句 (ロシア語の у + 生格「〜には」) はそのまま"""
    brace = t.rfind('}')
    head, gloss = t[:brace + 1], t[brace + 1:]  # 中括弧の中 (前置詞の目的語の訳) の読点では切らない
    first = head + gloss.split(',')[0]
    if first.endswith('には'):
        return first
    if first.endswith(('で', 'に')):
        return first[:-1] + 'に'
    if first[-1:].isascii():
        return first  # 英語の訳語 (πρός「towards」) には助詞を付けない
    return first + 'に'


def _has_article(obj):
    return isinstance(obj, Word) and any(isinstance(m, Word) and m.items and m.items[0].pos == 'article'
                                         for m in obj.modifiers)


def is_negation(word, lang=None):
    return isinstance(word, Word) and (lang or language.current()).is_negation(word.surface)


def copula_tense(tense):
    if tense in ('imperfect', 'perfect', 'past-perfect'):
        return 'past'
    if tense in ('future', 'future-perfect'):
        return 'future'
    return 'present'


def _is_adjective(obj):
    if isinstance(obj, AndOr):
        return obj.pos == 'adj'
    return isinstance(obj, Word) and bool(obj.items) and obj.items[0].pos in ('adj', 'participle')


def copula_translation(obj, tense, negated):
    """sum の補語を述語の形に (大きい / 幸福であった / 農夫ではない)。並列した形容詞は 長くて広い"""
    if isinstance(obj, AndOr) and obj.pos == 'adj':
        heads = [words[0] for words in obj.words_slots]
        first = [copula_conjunctive(w.translate()[0], True, negated) for w in heads[:-1]]
        return ''.join(first) + copula_predicate(heads[-1].translate()[0], True, tense, negated, also=True)
    gloss = obj.translate()[0]
    # 修飾語 ({美しい}少女 / {人生の}満ちた) はそのまま前に置き、後ろの語だけを述語の形にする
    modifier, head = '', gloss
    own = obj.items[0].ja if isinstance(obj, Word) and obj.items and obj.items[0].ja else None
    if own and own != gloss and (gloss.endswith(own) or gloss.endswith(braced(own))):
        # 修飾語の付いた語: 語の訳の前までが修飾語 (人生の + 満ちた,沢山の。訳語の候補は括らずに述語の形に)
        modifier, head = gloss[:-len(braced(own) if gloss.endswith(braced(own)) else own)], own
    elif '}' in gloss:
        cut = gloss.rindex('}') + 1
        modifier, head = gloss[:cut], gloss[cut:]
    if head.endswith('が') and len(head) > 1 and isinstance(obj, Word) and obj.items and obj.items[0].pos == 'pronoun':
        head = head[:-1]   # 助詞まで入った訳語 (quis「誰が」→ 誰である)
    if not head:
        # 括った並列 ({匂い,香り}と{形,型,姿}) など: 名詞の述語の形 (である / ではない / であった) を後ろに
        return gloss + copula_predicate('〇', False, tense, negated)[1:]
    return modifier + copula_predicate(head, _is_adjective(obj), tense, negated)
