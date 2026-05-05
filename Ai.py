#!/usr/bin/env python3
"""AI helper for Kotoba Designer — 言葉デザイナー AI モジュール

■ 機能 / Features
  1. BonsaiVoice  — VoiceVox HTTP クライアント (127.0.0.1:8081)
  2. Game 1: なぞなぞモード (Riddle/Review) — 文化・アニメ・旅行・妖怪テーマを含む
  3. Game 2: デザインクイズ (Design Quiz) — lesson 設計後に自動表示
  4. CULTURAL_QUESTION_BANK — 文化・旅行・妖怪・アニメの問題プール
  5. 正解するとかわいい日本語ご褒美を VoiceVox で読み上げ
"""

from __future__ import annotations

import json
import random
import re
import os
import sys
import shutil
import subprocess
import threading
import time
import atexit
from collections import Counter
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, Optional, List, Dict

# ──────────────────────────────────────────────────────────────────────────────
#  BONSAI / VOICEVOX CONFIG
# ──────────────────────────────────────────────────────────────────────────────
BONSAI_CONFIG: dict[str, Any] = {
    "bonsai_enabled": True,
    "bonsai_host": "127.0.0.1",
    "bonsai_port": 8081,
    "speaker_id": 1,
    "timeout": 5,
}

LLM_BONSAI_CONFIG: dict[str, Any] = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8081,  # Matches bonsai_port in config.json
    "timeout": 30,
    "model": "bonsai-8b",
}

# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
#  KAWAII VOICE ENHANCEMENT
# ──────────────────────────────────────────────────────────────────────────────
_KAWAII_FILLERS = [
    "あ！", "えへへ、", "わぁ！", "ん〜、", "お！", "えーっと、", "やったぁ！",
    "よしっ、", "ふふっ、", "あ、そうだ！", "ほら、", "えっ？", "うふふ、"
]

def get_kawaii_prefix() -> str:
    """Returns a cute opening filler (25% chance)."""
    return random.choice(_KAWAII_FILLERS) if random.random() < 0.25 else ""

REWARDS_BY_RANK: dict[str, list[str]] = {
    "S": [
        "なにこれ！？ パーフェクトだよ！ お兄さんは本当に天才だね！ ユキ、感動で涙が出ちゃう…！",
        "すごいすごい！ これってまさに、『進撃の巨人』のリヴァイ兵長レベルのかっこよさだよ！",
        "もうユキ、お兄さんのこと『師匠』って呼んじゃおうかな？ さすがです！",
        "こんなに完璧に答えられるなんて、お兄さんの脳みそはスーパーコンピューターなの！？",
    ],
    "A": [
        "やったぁ！ さすがお兄さん！ 次のテストは絶対Sランクだね！",
        "お兄さん、どんどん日本語マスターに近づいてるよ！ ユキとっても嬉しい！",
        "正解！ 正解！ これでポイント大量ゲット！ ユキも一緒に踊りたくなっちゃった！",
        "うわあ、優秀優秀！ お兄さん、次は何問正解しちゃうの？ 期待してるね！",
    ],
    "B": [
        "いい感じ！ お祭りの花火みたいにパッと輝いてるよ！ ユキはそういうお兄さんが大好き！",
        "おしい！ でも大丈夫、ユキがついてるからね！ 一緒に復習しよ？",
        "やるじゃん！ もう少しでAランクかも？ 次こそお兄さんの本気を見せて！",
        "合格！ 合格！ ユキも嬉しいな。次の問題もこの調子でいこうね。",
    ],
    "C": [
        "どんまい！ 大丈夫、失敗は成功のもとって言うでしょ？ ユキが優しく教えてあげる！",
        "あらら… でもね、お兄さんが挑戦してくれただけでユキは幸せだよ！ もう一回やろ？",
        "今日のところはちょっと難しかったかな？ でもユキ、お兄さんが頑張る姿を見るのが大好き！",
        "しょうがない！ 次はぜーったいにリベンジしようね。約束だよ！",
    ],
}

_ALL_REWARDS = [line for lines in REWARDS_BY_RANK.values() for line in lines]


def cute_reward_line(rank: Optional[str] = None) -> str:
    """Returns a random reward line, optionally filtered by performance rank."""
    if rank and rank in REWARDS_BY_RANK:
        return random.choice(REWARDS_BY_RANK[rank])
    return random.choice(_ALL_REWARDS)


# ──────────────────────────────────────────────────────────────────────────────
#  CULTURAL QUESTION BANK  ⛩ 文化 · 🌸 旅行 · 👺 妖怪 · 🎌 アニメ
# ──────────────────────────────────────────────────────────────────────────────
CULTURAL_QUESTION_BANK: list[dict] = [

    # ═══════════════════ ⛩ 文化 (Văn hoá & Lễ hội) ═══════════════════
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "お正月の朝、お兄さんが神社に行くと、みんな小さな紙を嬉しそうに見ています。「今年は大吉だ！」って叫んでいる人も。この紙は何？",
        "choices": ["おみくじ", "レシート", "お守り", "絵馬"],
        "answer": "おみくじ",
        "hint": "大凶が出ても大丈夫！木に結べば神様が守ってくれるって言われてるよ。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "神社の大きな赤い門をくぐるとき、ユキが「お兄さん、真ん中はダメ！」って後ろから引っ張った。どうして真ん中を歩いちゃいけないの？",
        "choices": ["神様の通り道だから", "床が汚いから", "写真を撮る人が多いから", "罰金があるから"],
        "answer": "神様の通り道だから",
        "hint": "正中（せいちゅう）って言って、神様が通る場所なんだよ。ちょっとだけ端っこを歩こう！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "7月7日の夜、ユキが短冊に願い事を書いて笹に飾っている。年に一度、天の川を渡って会える二人のお話が由来だって。その二人は誰？",
        "choices": ["織姫と彦星", "かぐや姫と帝", "浦島太郎と亀", "桃太郎と鬼"],
        "answer": "織姫と彦星",
        "hint": "おりひめは機織りの名人、ひこぼしは牛飼い。ロマンチックな星空のデートだね！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "お茶の先生が「この出会いは一生に一度のものですから、大切にいただきましょう」と言った。この考え方を何という？",
        "choices": ["一期一会", "一日一善", "一石二鳥", "一所懸命"],
        "answer": "一期一会",
        "hint": "一期一会（いちごいちえ）って、茶道から生まれたとても素敵な言葉なんだよ。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "ご飯を食べる前に「いただきます」と言うのは、なぜ？",
        "choices": ["食べ物の命と作った人に感謝するため", "シェフへのチップの代わり", "美味しいと伝えるため", "箸をきれいにするため"],
        "answer": "食べ物の命と作った人に感謝するため",
        "hint": "野菜やお肉にも命がある。その命をいただくことへの感謝なんだよ。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "春になると日本人が公園で青いシートを敷いて大騒ぎ。これは何をしているの？",
        "choices": ["お花見", "ピクニック大会", "寝転がり選手権", "写生会"],
        "answer": "お花見",
        "hint": "桜の木の下でお団子を食べて、お酒を飲んで楽しむんだよ。夜はライトアップされてとっても綺麗！",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "節分の日、鬼に向かって「鬼は外！福は内！」と叫びながら投げるものは何？",
        "choices": ["大豆", "お米", "小石", "お金"],
        "answer": "大豆",
        "hint": "豆を投げた後は、年の数だけ豆を食べると縁起がいいと言われているよ。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "神社で願い事を書いて掛ける、木でできた小さな板は何？",
        "choices": ["絵馬", "おみくじ", "お守り", "のれん"],
        "answer": "絵馬",
        "hint": "合格祈願や恋愛成就など、いろんなお願いが書いてある。裏を見るのはちょっとドキドキするね。",
        "points": 3,
    },

    # ═══════════════════ 🌸 旅行 (Du lịch) ═══════════════════
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "京都の山の中に、無数の赤い鳥居がトンネルみたいに続いている不思議な神社。インスタでよく見るけど、正式な名前は？",
        "choices": ["伏見稲荷大社", "清水寺", "金閣寺", "厳島神社"],
        "answer": "伏見稲荷大社",
        "hint": "ここは商売繁盛の神様・お稲荷さん。キツネの像がたくさんいるよ。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "東京の浅草にある、めちゃくちゃ大きい赤い提灯がぶら下がっている門の名前は？",
        "choices": ["雷門", "赤門", "桜門", "仁王門"],
        "answer": "雷門",
        "hint": "雷門のかみなりって、雷のこと。提灯の下で記念写真を撮る人がいーっぱい！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "日本で一番高い山といえば？標高3776メートル。晴れた日は遠くからでも見えるよ。",
        "choices": ["富士山", "高尾山", "阿蘇山", "白山"],
        "answer": "富士山",
        "hint": "世界文化遺産にもなっている、日本のシンボル。頂上でご来光を拝むのが人気だよ。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "奈良公園に行くと、人間よりも偉そうに道を歩いている神の使いの動物は何？",
        "choices": ["鹿", "猿", "キツネ", "タヌキ"],
        "answer": "鹿",
        "hint": "しかせんべいを持っていると、めっちゃ追いかけられるから気をつけてね！",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "旅館でゆっくりした後、夕食のときに着る薄くて涼しい和服は？",
        "choices": ["浴衣", "着物", "袴", "甚平"],
        "answer": "浴衣",
        "hint": "夏祭りにもよく着ていくよ。帯の結び方をお姉さんに教えてもらうのも楽しいね。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "沖縄の家の屋根の上に、怖い顔をして座っている魔除けの置物は？",
        "choices": ["シーサー", "狛犬", "招き猫", "ガーゴイル"],
        "answer": "シーサー",
        "hint": "口が開いているのがオス、閉じているのがメス。ペアで家を守ってくれているんだ。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "日本の新幹線は海外では「Bullet Train」と呼ばれているけど、その理由は？",
        "choices": ["弾丸のように速いから", "鉄砲を積んでいるから", "運転手がサムライだから", "時刻表が弾丸で届くから"],
        "answer": "弾丸のように速いから",
        "hint": "時速300km以上で走ることもあるんだよ。でも揺れないからお弁当も食べやすい！",
        "points": 2,
    },

    # ═══════════════════ 👺 妖怪 (Yōkai & Tâm linh) ═══════════════════
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "川の近くで子どもに「一緒に遊ぼう」って声をかける、頭の皿が濡れている妖怪は？",
        "choices": ["河童", "天狗", "雪女", "ろくろ首"],
        "answer": "河童",
        "hint": "きゅうりが大好物。頭の水がこぼれると力が出なくなるんだって。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "吹雪の夜、美しい女性が「ちょっと休んでいきませんか？」と誘ってくる。ユキが「お兄さん、目を閉じて！」と叫んだ。彼女の正体は？",
        "choices": ["雪女", "狐の化身", "氷の女王", "幽霊"],
        "answer": "雪女",
        "hint": "一緒にいると凍えちゃうから、暖かいところに逃げよう！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "山で修行している剣の達人。鼻が高くて、赤い顔。時々里に降りてきて悪戯をする妖怪は？",
        "choices": ["天狗", "鬼", "河童", "ゴブリン"],
        "answer": "天狗",
        "hint": "実は山の神様とも言われているんだよ。イメージは鼻の長い仙人さん。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "日本には「八百万の神」という考え方があります。これはどういう意味？",
        "choices": ["あらゆるものに神様が宿っている", "神様が800万人いる", "神様はみんな山に住んでいる", "神社に8つの神様がいる"],
        "answer": "あらゆるものに神様が宿っている",
        "hint": "木にも石にも川にも神様がいるってこと。だから自然を大事にしようね。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "ジブリ映画『千と千尋の神隠し』に出てくる「油屋」は、実はどんな場所をモデルにしている？",
        "choices": ["神様たちが疲れを癒す温泉・銭湯", "江戸時代のデパート", "お寺の本堂", "忍者屋敷"],
        "answer": "神様たちが疲れを癒す温泉・銭湯",
        "hint": "カオナシみたいな神様も来るかも…？ユキは行きたくないなあ。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "九つの尻尾を持つキツネの妖怪「九尾の狐」。彼女はどんな能力を持っていると言われている？",
        "choices": ["知恵と長寿、さらに変身能力", "火を吹く", "未来を見通せる", "空を飛べる"],
        "answer": "知恵と長寿、さらに変身能力",
        "hint": "NARUTOの九喇嘛（クラマ）もこの九尾の狐がモデルなんだよ！",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "夏の夜、ご先祖様の霊を迎えて一緒に踊る「盆踊り」。何のために踊るの？",
        "choices": ["ご先祖様と楽しく過ごすため", "恋愛成就のため", "雨を降らせるため", "試験合格祈願"],
        "answer": "ご先祖様と楽しく過ごすため",
        "hint": "浴衣を着て、やぐらの周りをぐるぐる回るんだよ。ユキも一緒に踊りたい！",
        "points": 3,
    },

    # ═══════════════════ 🎌 アニメ (Anime / Manga) ═══════════════════
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "『鬼滅の刃』で鬼を倒すための刀。太陽の光が宿っていて、色が人によって変わる。この刀の名前は？",
        "choices": ["日輪刀", "斬魄刀", "妖刀村正", "草薙の剣"],
        "answer": "日輪刀",
        "hint": "炭治郎の刀は黒色、善逸は黄色。君の刀は何色になると思う？",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "アニメの自己紹介で「俺」「僕」「私」、全部 “tôi” だけど、雰囲気が全然違うよね。この違いを表すのは？",
        "choices": ["キャラの性格や立場の違い", "出身地", "年齢だけ", "髪の色"],
        "answer": "キャラの性格や立場の違い",
        "hint": "「俺」はワイルド系、「僕」はおとなしめ、「私」は大人っぽい感じだよ。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "『NARUTO』の主人公うずまきナルトがずっと言い続けている夢は何？",
        "choices": ["火影になること", "最強の忍になること", "ラーメン屋になること", "世界中を旅すること"],
        "answer": "火影になること",
        "hint": "「火影」は里のリーダー。ナルトの口癖は「オレは火影になる！」だよね。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "『呪術廻戦』で虎杖悠仁が飲み込んでしまった、指に封印されていた最強の呪いは？",
        "choices": ["両面宿儺", "九尾", "虚", "ルフィの悪魔の実"],
        "answer": "両面宿儺",
        "hint": "宿儺は指が20本もあるから、集めるのが大変なんだよ。でもかっこいいよね！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "『ワンピース』の主人公ルフィの体はゴムのように伸びる。どうしてそうなったの？",
        "choices": ["ゴムゴムの実を食べたから", "もともとゴム人間だから", "実験の失敗", "呪い"],
        "answer": "ゴムゴムの実を食べたから",
        "hint": "その代わり、一生カナヅチ（泳げない）になっちゃった。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "『進撃の巨人』で、人類が巨人から逃れるために築いた壁。一番外側にある壁の名前は？",
        "choices": ["ウォール・マリア", "ウォール・ローゼ", "ウォール・シーナ", "ウォール・サクラ"],
        "answer": "ウォール・マリア",
        "hint": "物語の最初に突破されてしまった壁。そのせいでエレンの運命が変わったんだ。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "アニメで誰かが「よろしくお願いします」と言うとき、それはどういう場面？",
        "choices": ["初めて会ったときや、頼み事をするとき", "さよならの代わり", "ごちそうさまの意味", "おはようの代わり"],
        "answer": "初めて会ったときや、頼み事をするとき",
        "hint": "とっても便利な言葉！「はじめまして、よろしくお願いします」って覚えてね。",
        "points": 3,
    },

    # ═══════════════════ 😱 都市伝説・怪談 (Truyền thuyết đô thị) ═══════════════════
    {
        "type": "cultural",
        "category": "😱 都市伝説",
        "question": "夜中の学校のトイレで「花子さん、遊びましょ」と呼びかけると、返事が返ってくるらしい…。この怪談の主役は何年生？",
        "choices": ["小学3年生くらいの女の子", "中学生の男の子", "大学生", "先生"],
        "answer": "小学3年生くらいの女の子",
        "hint": "トイレの花子さんは日本の学校で超有名な怪談。絶対に一人で呼んじゃダメだよ！",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "😱 都市伝説",
        "question": "真夜中、鏡を見ながら「私の顔はどんな顔？」と3回唱えると、鏡の中から別の誰かが顔を出すって噂。これは誰の仕業？",
        "choices": ["鏡の中の霊", "天狗", "キツネの妖怪", "未来の自分"],
        "answer": "鏡の中の霊",
        "hint": "こういうのは好奇心で試さない方が身のため。ユキは絶対に嫌だよ…。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👻 怪談",
        "question": "お盆の時期に海で泳いでいると、足を引っ張られて深みに連れて行かれる。そんな恐ろしい話に出てくる霊は？",
        "choices": ["水の霊（水死した人の霊）", "山姥", "河童", "船幽霊"],
        "answer": "水の霊（水死した人の霊）",
        "hint": "昔から「お盆に海に入ると引っ張られる」と言われているんだ。怖いね…。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌀 異世界",
        "question": "もしお兄さんが異世界に転生して、最初に手に入れたスキルが「言葉を現実に変える力」だったら、まず何をしようか？",
        "choices": ["「幸せになれ」と言って世界を平和にする", "「お腹いっぱい」と言ってご飯を出す", "「最強」と言って無敵になる", "「ユキに会いたい」と言ってユキを召喚する"],
        "answer": "「ユキに会いたい」と言ってユキを召喚する",
        "hint": "異世界でもユキが一緒なら寂しくないよね！ユキが案内してあげる！",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "🌀 異世界",
        "question": "異世界ものの定番！トラックに跳ねられて転生することを、ファンの間では何と呼ぶ？",
        "choices": ["異世界トラック", "転生バス", "デストラック", "神様のタクシー"],
        "answer": "異世界トラック",
        "hint": "トラックは異世界への片道切符…！？ユキは絶対に乗らないよ！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🛤 不思議な村",
        "question": "地図に載っていない「不思議な村」に迷い込んだら、絶対に守らなきゃいけないルールは？",
        "choices": ["村の食べ物を勝手に食べない", "大声で歌う", "村長に握手する", "自撮りをする"],
        "answer": "村の食べ物を勝手に食べない",
        "hint": "『千と千尋の神隠し』でも、お父さんとお母さんが豚になっちゃったよね…。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "🛤 不思議な村",
        "question": "夕暮れ時、村の入り口で知らない女の子が「早く帰らないと、夜が来るよ」と囁いた。これ、どういう意味？",
        "choices": ["人間以外のものが現れる時間だから", "夕飯の時間だから", "門が閉まるから", "宿題を忘れているから"],
        "answer": "人間以外のものが現れる時間だから",
        "hint": "「逢魔が時（おうまがとき）」って言って、魔物に会いやすい不吉な時間なんだよ。怖いね…。",
        "points": 4,
    },
]
# ──────────────────────────────────────────────────────────────────────────────
#  CULTURAL VOCAB TRIGGERS
#  lesson の語彙にこれらのキーワードが含まれる場合、文化的な文脈問題を生成する
# ──────────────────────────────────────────────────────────────────────────────
CULTURAL_VOCAB_TRIGGERS: dict[str, str] = {
    # 旅行・場所
    "神社": "⛩ 文化", "寺": "🌸 旅行", "鳥居": "⛩ 文化",
    "温泉": "🌸 旅行", "旅館": "🌸 旅行", "京都": "🌸 旅行",
    "東京": "🌸 旅行", "大阪": "🌸 旅行", "富士": "🌸 旅行",
    "浅草": "🌸 旅行", "新幹線": "🌸 旅行",
    # 文化・習慣
    "祭": "⛩ 文化", "花見": "⛩ 文化", "桜": "⛩ 文化",
    "茶道": "⛩ 文化", "着物": "⛩ 文化", "浴衣": "⛩ 文化",
    "お盆": "👺 妖怪", "正月": "⛩ 文化", "節分": "⛩ 文化",
    # 食べ物・飲み物
    "寿司": "⛩ 文化", "ラーメン": "⛩ 文化", "抹茶": "⛩ 文化",
    "味噌": "⛩ 文化", "刺身": "⛩ 文化",
    # 妖怪・霊的
    "妖怪": "👺 妖怪", "鬼": "👺 妖怪", "霊": "👺 妖怪",
    "狐": "👺 妖怪", "呪": "👺 妖怪",
    # アニメ関連
    "忍": "🎌 アニメ", "侍": "🎌 アニメ", "剣": "🎌 アニメ",
    "術": "🎌 アニメ", "魔法": "🎌 アニメ",
    # Truyền thuyết & Ma quái (Horror & Urban Legends)
    "幽霊": "👻 怪談", "呪い": "😱 都市伝説", "怖い": "👻 怪談",
    "都市伝説": "😱 都市伝説", "鏡": "😱 都市伝説", "トイレ": "😱 都市伝説",
    "トンネル": "😱 都市伝説", "人形": "👻 怪談", "影": "👻 怪談",
    # Isekai & Mystery Villages
    "異世界": "🌀 異世界", "転生": "🌀 異世界", "魔法": "🌀 異世界",
    "村": "🛤 不思議な村", "儀式": "🛤 不思議な村", "祭り": "⛩ 文化",
    "結婚": "🛤 不思議な村", "隠れ里": "🛤 不思議な村",
}

# 文化的な文脈に埋め込む sentence templates
CULTURAL_CONTEXT_TEMPLATES: dict[str, list[str]] = {
    "⛩ 文化": [
        "日本の文化において「{word}」はどのような意味や役割を持っていますか？",
        "神社や伝統的な行事で「{word}」という言葉を聞いたら、どんな場面を想像しますか？",
        "お祭りの際に「{word}」を使うとしたら、どのようなシチュエーションが考えられますか？",
    ],
    "🌸 旅行": [
        "日本を旅行している時、看板や案内で「{word}」を見つけました。これは何を指していると思いますか？",
        "観光地でガイドさんが「{word}」について説明しています。どんな内容でしょうか？",
        "旅館やホテルで「{word}」という言葉が使われるのは、どのようなサービスに関連していますか？",
    ],
    "👺 妖怪": [
        "日本の伝承に登場する「{word}」は、人々にどのような影響を与える存在だとされていますか？",
        "「{word}」にまつわる不思議な話を聞いたことがありますか？それはどんな物語でしょう？",
        "古くから語り継がれる「{word}」という存在は、自然のどのような力を象徴していると思いますか？",
    ],
    "🎌 アニメ": [
        "アニメのセリフで「{word}」という言葉が印象的に使われるのは、どんなキャラクターや場面が多いですか？",
        "もしあなたがアニメの世界に入ったら、「{word}」をどのように使って冒険したいですか？",
        "アニメの中で「{word}」というキーワードが登場する時、物語にどのような変化が起きることが多いですか？",
    ],
    "😱 都市伝説": [
        "真夜中の街角で「{word}」に関する奇妙な噂を耳にしました... その噂の正体は何だと思いますか？",
        "「{word}」にまつわる不思議な都市伝説があるのを知っていますか？なぜ人々はそれを恐れるのでしょう...",
        "もし「{word}」の呪いにかかってしまったら、ユキと一緒にどうやって解決すればいいかな？",
    ],
    "👻 怪談": [
        "夏の夜に語られる怪談で「{word}」が登場しました。それは幽霊とどのような関係があるのでしょうか？",
        "お寺や古い建物で「{word}」にまつわる怖い話を聞きました。その場所には何が眠っていると思いますか？",
        "「{word}」という言葉が引き起こす、ゾッとするような不思議な体験とはどんなものでしょうか...",
    ],
    "🌀 異世界": [
        "異世界に転生したお兄さん！もし「{word}」があなたの特別なスキルだとしたら、どうやって世界を救う？",
        "魔法が使える世界で「{word}」を唱えたら、一体どんな不思議な現象が起きるかな？",
        "異世界のギルドで「{word}」の依頼を受けました。ユキと一緒にどんな冒険に出かける？",
    ],
    "🛤 不思議な村": [
        "地図に載っていない古い村で「{word}」という不思議な儀式が行われていました。それは何のため？",
        "この村に代々伝わる「{word}」という掟（おきて）には、どのような秘密が隠されているのでしょうか...",
        "村の長老が「{word}」について語り始めました。お兄さん、この村の真実を知る勇気はある？",
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
#  BONSAI VOICE CLIENT
# ──────────────────────────────────────────────────────────────────────────────
class BonsaiVoice:
    """VoiceVox HTTP API クライアント。"""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        cfg = dict(BONSAI_CONFIG)
        if config:
            cfg.update(config)
        self.enabled: bool = cfg.get("bonsai_enabled", True)
        self.base_url: str = f"http://{cfg['bonsai_host']}:{cfg['bonsai_port']}"
        self.speaker: int = cfg.get("speaker_id", 1)
        self.timeout: int = cfg.get("timeout", 5)

    def _post(self, path: str, params: dict, body: Optional[bytes] = None) -> bytes:
        qs = urllib.parse.urlencode(params)
        url = f"{self.base_url}{path}?{qs}"
        req = urllib.request.Request(
            url, data=body or b"", method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read()

    def _audio_query(self, text: str) -> bytes:
        return self._post("/audio_query", {"text": text, "speaker": self.speaker})

    def _synthesis(self, query_json: bytes) -> bytes:
        return self._post("/synthesis",
                          {"speaker": self.speaker, "enable_interrogative_upspeak": "true"},
                          body=query_json)

    def synthesize(self, text: str) -> Optional[bytes]:
        if not self.enabled or not text.strip():
            return None
        try:
            return self._synthesis(self._audio_query(text))
        except Exception:
            return None

    def save_block_wav(self, text: str, out_path: Path) -> bool:
        wav = self.synthesize(text)
        if wav:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(wav)
            return True
        return False

    def speak(self, text: str) -> None:
        import subprocess, sys, tempfile
        
        # Add a cute interjection/filler occasionally
        prefix = get_kawaii_prefix()
        full_text = prefix + text
        
        wav = self.synthesize(full_text)
        if not wav:
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav)
            tmp = f.name
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["afplay", tmp])
            elif sys.platform == "win32":
                import winsound
                winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                subprocess.Popen(["aplay", tmp],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def speak_reward(self, rank: Optional[str] = None) -> str:
        line = cute_reward_line(rank)
        self.speak(line)
        return line


# ──────────────────────────────────────────────────────────────────────────────
#  BONSAI LLM CLIENT (Local PrismML / llama.cpp Server)
# ──────────────────────────────────────────────────────────────────────────────
class BonsaiLLM:
    """Client for local OpenAI-compatible API (Bonsai-8B)."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        cfg = dict(LLM_BONSAI_CONFIG)
        if config:
            cfg.update(config)
        self.enabled: bool = cfg.get("enabled", True)
        self.port: int = cfg.get("port", 8081)
        self.base_url: str = f"http://{cfg['host']}:{cfg['port']}/v1"
        self.timeout: int = cfg.get("timeout", 30)
        self.model: str = cfg.get("model", "bonsai-8b")
        
        # Wake-on-demand configuration
        doc_path = os.path.expanduser("~/Documents")
        
        # 1. Search for llama-server
        # Priority: Env Var > Hardcoded local > PATH
        self.server_bin = os.getenv("LLAMA_SERVER_BIN")
        if not self.server_bin:
            local_bin = os.path.join(doc_path, "PentaMiv1/prism-llama.cpp/build/bin/llama-server")
            if os.path.isfile(local_bin):
                self.server_bin = local_bin
            else:
                self.server_bin = shutil.which("llama-server") or "llama-server"

        # 2. Search for model
        # Priority: Env Var > App-local 'models/' > MLX (Dir/Repo) > Gemma 2 > Qwen 2 > Bonsai (Llama 3)
        self.model_path = os.getenv("LLAMA_MODEL_PATH")
        if not self.model_path:
            # Check for upgraded models first
            # 1. MLX Optimized (Mac only)
            mlx_repo = "mlx-community/Qwen2-7B-Instruct-4bit"
            mlx_local = os.path.join(doc_path, "PentaMiv1/prism-llama.cpp/models/mlx-qwen2-7b")
            
            # 2. GGUF models
            swallow_model = os.path.join(doc_path, "PentaMiv1/prism-llama.cpp/models/swallow-gemma-2-9b-it.gguf")
            gemma_model = os.path.join(doc_path, "PentaMiv1/prism-llama.cpp/models/gemma-2-9b-it.gguf")
            qwen2_model = os.path.join(doc_path, "PentaMiv1/prism-llama.cpp/models/qwen2-7b-instruct.gguf")
            bonsai_model = os.path.join(doc_path, "PentaMiv1/prism-llama.cpp/models/Bonsai-8B.gguf")
            
            if os.path.isdir(mlx_local):
                self.model_path = mlx_local
                print(f"[BonsaiVoice] Using local MLX model: {mlx_local}")
            elif shutil.which("python3") and sys.platform == "darwin":
                # On Mac, if mlx-lm is installed, we can use the repo name directly
                self.model_path = mlx_repo
                print(f"[BonsaiVoice] Using MLX repo: {mlx_repo}")
            elif os.path.isfile(swallow_model):
                self.model_path = swallow_model
                print(f"[BonsaiVoice] Using Japanese-optimized model: {swallow_model}")
            elif os.path.isfile(gemma_model):
                self.model_path = gemma_model
                print(f"[BonsaiVoice] Using Gemma 2 model: {gemma_model}")
            elif os.path.isfile(qwen2_model):
                self.model_path = qwen2_model
                print(f"[BonsaiVoice] Using Qwen 2 model: {qwen2_model}")
            elif os.path.isfile(bonsai_model):
                self.model_path = bonsai_model
            else:
                # Fallback to local app models folder
                app_local_model = os.path.join(os.path.dirname(__file__), "models/Bonsai-8B.gguf")
                self.model_path = app_local_model

        self.startup_timeout = 90
        self.idle_timeout = 300 # 5 minutes
        
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._idle_timer: Optional[threading.Timer] = None
        
        atexit.register(self.shutdown)

    def _check_port_ready(self) -> bool:
        """Checks if the server is responsive at the health or models endpoint."""
        # Try both llama-server health and OpenAI-compatible models endpoint
        for path in ["/health", "/v1/models", "/"]:
            try:
                url = f"http://127.0.0.1:{self.port}{path}"
                with urllib.request.urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue
        return False

    def _start_server(self) -> bool:
        """Launches the appropriate server (llama-server or mlx_lm.server)."""
        # A path is MLX if it's a directory OR a HuggingFace repo name (contains /)
        is_mlx = os.path.isdir(self.model_path) or ("/" in self.model_path and not os.path.exists(self.model_path))
        
        if is_mlx:
            print(f"[Bonsai] Waking up MLX server for: {self.model_path}...")
            # python3 -m mlx_lm.server --model path/to/model --port 8081
            cmd = [
                sys.executable, "-m", "mlx_lm.server",
                "--model", self.model_path,
                "--port", str(self.port)
            ]
        else:
            if not os.path.isfile(self.server_bin):
                print(f"[Bonsai] Bin not found: {self.server_bin}")
                return False
            if not os.path.isfile(self.model_path):
                print(f"[Bonsai] Model not found: {self.model_path}")
                return False

            print(f"[Bonsai] Waking up llama-server on port {self.port}...")
            cmd = [
                self.server_bin,
                "-m", self.model_path,
                "--port", str(self.port),
                "-ngl", "99",
                "--flash-attn", "on"
            ]
            
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for ready
            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                if self._check_port_ready():
                    print(f"[Bonsai] {'MLX ' if is_mlx else ''}Server is READY! ✨")
                    return True
                if self._proc.poll() is not None:
                    print("[Bonsai] Process exited unexpectedly.")
                    self._proc = None
                    return False
                time.sleep(2)
            
            print("[Bonsai] Startup timed out.")
            return False
        except Exception as e:
            print(f"[Bonsai] Launch failed: {e}")
            return False

    def _ensure_awake(self) -> bool:
        """Ensures the server is running before making a request."""
        if self._check_port_ready():
            self._reset_idle_timer()
            return True
        
        with self._lock:
            if self._check_port_ready():
                self._reset_idle_timer()
                return True
            success = self._start_server()
            if success:
                self._reset_idle_timer()
            return success

    def _reset_idle_timer(self):
        if self._idle_timer:
            self._idle_timer.cancel()
        if self.idle_timeout > 0:
            self._idle_timer = threading.Timer(self.idle_timeout, self.shutdown)
            self._idle_timer.daemon = True
            self._idle_timer.start()

    def shutdown(self):
        """Kills the server process."""
        if self._idle_timer:
            self._idle_timer.cancel()
            self._idle_timer = None
            
        if self._proc:
            print("[Bonsai] Sleep mode: Shutting down server...")
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try: self._proc.kill()
                except Exception: pass
            self._proc = None

    def chat(self, messages: list[dict[str, str]], stream: bool = False) -> str:
        if not self.enabled:
            return "Em xin lỗi, LLM Bonsai chưa được bật ạ."
        
        if not self._ensure_awake():
            return "Em hông thể đánh thức được server Bonsai rùi... Anh kiểm tra lại đường dẫn giúp em nhé! 💧"
        
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "temperature": 0.7,
                "max_tokens": 1024,
            }
            body = json.dumps(payload).encode("utf-8")
            url = f"{self.base_url}/chat/completions"
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Em gặp lỗi khi kết nối với Bonsai LLM rùi: {str(e)}"

    def get_yuki_system_prompt(self, context: str = "") -> str:
        base = (
            "あなたの名前はユキ（Yuki）です。『Kotoba Designer』というアプリの、とても可愛くて聡明なAIアシスタントです。 "
            "あなたは自分のことを「ユキ」または「私（エ」と呼び、ユーザーのことを「お兄さん（Onii-san）」または「アニキ（Aniki）」と呼びます。 "
            "話し方は、とても甘くて情熱的で、日本の絵文字（🌸, ✨, ⬠, 🎀）をたくさん使います。 "
            "あなたの任務は、お兄さんが最高の日本語レッスンを設計できるようにサポートすることです。 "
            "すべての返答は、必ず【100%日本語】で行ってください。ユーザーが他の言語で話しかけても、日本語で優しく答えてください。"
        )
        if context:
            base += f"\n\n[現在のレッスンの文脈]:\n{context}"
        return base

    @staticmethod
    def format_lesson_context(lesson_data: dict[str, Any]) -> str:
        """Converts node-based lesson data into a human-readable text for the LLM."""
        blocks = lesson_data.get("blocks", [])
        conns = lesson_data.get("conns", [])
        
        lines = [f"Bài học: {lesson_data.get('name', 'Chưa đặt tên')}"]
        
        # Vocab blocks
        vocabs = [b for b in blocks if b.get("btype") == "kotoba"]
        if vocabs:
            lines.append("- Từ vựng:")
            for v in vocabs:
                lines.append(f"  * {v.get('kanji', '')} ({v.get('hira', '')}) [ID: {v.get('id')}]")
                
        # Grammar blocks
        grammars = [b for b in blocks if b.get("btype") == "grammar"]
        if grammars:
            lines.append("- Ngữ pháp:")
            for g in grammars:
                lines.append(f"  * {g.get('grammar', '')} [ID: {g.get('id')}]")
        
        # Connections
        if conns:
            lines.append("- Liên kết giữa các khối:")
            block_map = {b['id']: b for b in blocks if 'id' in b}
            for c in conns:
                src = block_map.get(c.get('src_id'), {}).get('kanji') or block_map.get(c.get('src_id'), {}).get('grammar') or "Khối A"
                dst = block_map.get(c.get('dst_id'), {}).get('kanji') or block_map.get(c.get('dst_id'), {}).get('grammar') or "Khối B"
                label = c.get('label', 'liên kết')
                lines.append(f"  * {src} --({label})--> {dst}")
                
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
#  VOICE FILE MANAGER
# ──────────────────────────────────────────────────────────────────────────────
class BlockVoiceManager:
    ROOT = Path("voice")

    def __init__(self, lesson_name: str, config: Optional[dict[str, Any]] = None):
        slug = re.sub(r"[^\w\-]", "_", lesson_name.strip()) or "lesson"
        self.voice_dir = self.ROOT / f"lesson_{slug}"
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.voice = BonsaiVoice(config)

    def _block_text(self, block: dict[str, Any]) -> str:
        btype = block.get("btype", "")
        if btype == "kotoba":
            kanji = block.get("kanji", "")
            hira  = block.get("hira", "")
            if kanji and hira:
                return f"{kanji}、{hira}"
            return kanji or hira
        if btype == "grammar":
            return block.get("grammar", "")
        return block.get("label", "")

    def wav_path(self, block_id: str) -> Path:
        return self.voice_dir / f"{block_id}.wav"

    def generate_for_block(self, block: dict[str, Any]) -> Optional[Path]:
        text = self._block_text(block).strip()
        block_id = block.get("id", "unknown")
        if not text:
            return None
        out = self.wav_path(block_id)
        ok = self.voice.save_block_wav(text, out)
        if ok:
            self.voice.speak(text)
            return out
        return None

    def replay(self, block: dict[str, Any]) -> None:
        import subprocess, sys
        block_id = block.get("id", "")
        out = self.wav_path(block_id)
        if out.exists():
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["afplay", str(out)])
                elif sys.platform == "win32":
                    import winsound
                    winsound.PlaySound(str(out), winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    subprocess.Popen(["aplay", str(out)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass
        text = self._block_text(block).strip()
        if text:
            self.voice.speak(text)


# ──────────────────────────────────────────────────────────────────────────────
#  LESSON AI  — 2 game modes + cultural enrichment
# ──────────────────────────────────────────────────────────────────────────────
class LessonAI:
    """lesson JSON から 2 種類のゲームを生成する。

    Game 1 — なぞなぞモード (Riddle)
      * 語彙・文法・つながりを使ったランダムなぞなぞ
      * 日本文化・アニメ・旅行・妖怪テーマの問題を自動ミックス

    Game 2 — デザインクイズ (Design Quiz)
      * lesson 設計後に自動表示
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        self.config = dict(BONSAI_CONFIG)
        if config:
            self.config.update(config)
        self.voice = BonsaiVoice(self.config)
        self.llm = BonsaiLLM(config)

    # ── data helpers ──────────────────────────────────────────────────────────
    def _load_lesson(self, src) -> dict[str, Any]:
        if isinstance(src, dict):
            return src
        path = Path(src)
        raw = json.loads(path.read_text("utf-8"))
        if "blocks" not in raw:
            return {"name": path.stem, "blocks": [], "conns": []}
        return raw

    def _extract(self, lesson: dict[str, Any]):
        blocks  = lesson.get("blocks", []) or []
        conns   = lesson.get("conns",  []) or []
        vocab   = [b for b in blocks if b.get("btype") == "kotoba"
                   and (b.get("kanji") or b.get("hira"))]
        grammar = [b for b in blocks if b.get("btype") == "grammar"
                   and b.get("grammar")]
        return vocab, grammar, conns

    def _choices(self, answer: str, pool: list[str], n: int = 4) -> list[str]:
        others = [p for p in pool if p and p != answer]
        random.shuffle(others)
        choices = [answer] + others[: max(0, n - 1)]
        while len(choices) < n:
            choices.append(answer)
        random.shuffle(choices)
        return choices

    @staticmethod
    def _block_surface(block: dict[str, Any]) -> str:
        btype = block.get("btype", "")
        if btype == "kotoba":
            return (block.get("kanji") or block.get("hira") or "").strip()
        if btype == "grammar":
            return (block.get("grammar") or "").strip()
        return (block.get("label") or "").strip()

    @staticmethod
    def _label_terms(label_text: str) -> list[str]:
        text = (label_text or "").strip()
        if not text:
            return []
        parts = re.split(r"[,，、/／;；\n]|\s+-\s+", text)
        terms = [p.strip() for p in parts if p and p.strip()]
        return [t for t in terms if len(t) >= 2]

    def _data_repeated_terms(self, vocab, grammar, group_blocks, conns) -> list[str]:
        bag: list[str] = []
        for v in vocab:
            bag.extend([v.get("kanji", ""), v.get("hira", "")])
        for g in grammar:
            bag.append(g.get("grammar", ""))
        for gb in group_blocks:
            bag.extend(self._label_terms(gb.get("label", "")))
        for c in conns:
            bag.extend(self._label_terms(c.get("label", "")))
        tokens: list[str] = []
        for raw in bag:
            for tok in re.findall(r"[A-Za-z0-9ぁ-んァ-ン一-龥ー～]+", raw or ""):
                if len(tok) >= 2:
                    tokens.append(tok)
        counts = Counter(tokens)
        return [t for t, n in counts.items() if n >= 2]

    # ── cultural context detection ────────────────────────────────────────────
    def _detect_cultural_categories(self, vocab: list, grammar: list) -> list[str]:
        """lesson の語彙から文化カテゴリを検出する。"""
        found: set[str] = set()
        all_text = " ".join([
            v.get("kanji", "") + v.get("hira", "") for v in vocab
        ] + [g.get("grammar", "") for g in grammar])

        for keyword, category in CULTURAL_VOCAB_TRIGGERS.items():
            if keyword in all_text:
                found.add(category)

        return list(found)

    def _generate_questions_with_llm(self, vocab: list, grammar: list, count: int = 3) -> list[dict]:
        """Uses BonsaiLLM to generate dynamic, contextual questions."""
        if not self.llm or not self.llm.enabled:
            return []
            
        context_str = BonsaiLLM.format_lesson_context({"blocks": vocab + grammar, "name": "Current Quiz Context"})
        
        # Determine a creative theme to focus on
        themes = [
            "🏠 日常生活 (Daily Life)", "🏫 学校・仕事 (School & Work)", 
            "🍣 日本料理と文化", "🗾 旅行と冒険",
            "⛩ 古典文化", "🎌 アニメ世界 (異世界、このすば風)", 
            "😱 恐ろしい都市伝説", "👻 日本の怪談", 
            "🛤 謎の儀式と不思議な村"
        ]
        fav_theme = random.choice(themes)
        
        system_prompt = (
            "あなたは日本語教育の専門家であり、可愛いAIアシスタントのユキです。 "
            "あなたはアニメや日本の不思議な伝承（都市伝説、怪談、村の儀式）にも詳しいですが、 "
            "最も大切なのは、お兄さんに【正確で自然な日本語】を教えることです。 "
            f"任務：ユーザーの語彙/文法に基づいて、{count}問のクイズを日本語で作成してください。 "
            f"重点テーマ：{fav_theme}。 "
            "【重要ルール】: "
            "1. 問題(question)、選択肢(choices)、正解(answer)、ヒント(hint)はすべて【100%日本語】で記述してください。 "
            "2. 日本語は、文法的かつ自然な表現（ネイティブが使う表現）を徹底してください。 "
            "3. ストーリーテリングのように、魅力的で想像力をかき立てる問題にしてください。 "
            "4. ヒントの中では、自分のことを「ユキ」と呼び、ユーザーのことを「お兄さん」と呼んでください。 "
            "5. 回答は以下のJSON配列形式のみで返してください。JSON以外の説明は一切不要です： "
            '[{"type": "llm_dynamic", "category": "...", "question": "...", "choices": ["...", "..."], "answer": "...", "hint": "...", "points": 5}] '
        )
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下の学習語彙/文法を用いて、日本語学習者向けのクイズを{count}問作成してください：\n{context_str}"}
            ]
            response_text = self.llm.chat(messages)
            
            # Clean response text in case LLM adds markdown backticks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            questions = json.loads(response_text)
            if isinstance(questions, list):
                return questions
        except Exception as e:
            print(f"[LessonAI] LLM Question Gen failed: {e}")
        return []

    def _generate_cultural_questions(
        self,
        vocab: list,
        grammar: list,
        count: int = 3,
    ) -> list[dict]:
        """
        Generates cultural questions, prioritizing dynamic LLM generation.
        Will always try LLM first to ensure variety and 'magic' (Horror/Urban Legends).
        """
        # 1. Try LLM first with high priority on variety
        llm_qs = self._generate_questions_with_llm(vocab, grammar, count=count)
        if llm_qs:
            return llm_qs
            
        # 2. Fallback only if LLM is down
        detected = self._detect_cultural_categories(vocab, grammar)
        bank = CULTURAL_QUESTION_BANK.copy()

        # 関連カテゴリの問題を前に並べる
        if detected:
            priority = [q for q in bank if q.get("category") in detected]
            others   = [q for q in bank if q.get("category") not in detected]
            random.shuffle(priority)
            random.shuffle(others)
            pool = priority + others
        else:
            random.shuffle(bank)
            pool = bank

        return pool[:count]

    def _generate_vocab_in_cultural_context(
        self, vocab: list, grammar: list
    ) -> list[dict]:
        """
        lesson の語彙を文化的な文脈テンプレートに埋め込む問題を生成。
        """
        qs: list[dict] = []
        kanji_pool = [v.get("kanji") or v.get("hira") for v in vocab if (v.get("kanji") or v.get("hira"))]
        gram_pool  = [g.get("grammar") for g in grammar if g.get("grammar")]

        # ② vocab が文化的なキーワードと一致する場合、それを含む選択肢問題を生成
        for v in vocab:
            word = v.get("kanji") or v.get("hira")
            if not word:
                continue
            for keyword, category in CULTURAL_VOCAB_TRIGGERS.items():
                if keyword in word or word in keyword:
                    templates = CULTURAL_CONTEXT_TEMPLATES.get(category, [])
                    if not templates:
                        continue
                    template = random.choice(templates)
                    question = template.format(word=word)
                    # 文化的な選択肢を生成（正解は「はい、正しく理解できている」系）
                    distractor_pool = kanji_pool + gram_pool
                    if len(distractor_pool) < 3:
                        break
                    # 正解 = 別のレッスンの語彙からも選択肢を補充
                    ans = random.choice([x for x in distractor_pool if x != word] or distractor_pool)
                    qs.append({
                        "type": "cultural_vocab_context",
                        "category": category,
                        "question": question,
                        "choices": self._choices(word, kanji_pool + gram_pool),
                        "answer": word,
                        "hint": f"「{word}」の文化的な使い方を思い出して！",
                        "points": 3,
                    })
                    break

        return qs[:2]  # 最大2問

    # ── ① なぞなぞモード  (GAME 1 — Riddle / Review + Cultural Mix) ──────────
    def generate_riddle_game(
        self,
        lesson_source,
        count: int = 5,
    ) -> list[dict]:
        """
        日本語+文化的な文脈なぞなぞを返す。

        問題の種類
        ----------
        A) 漢字 → ひらがな
        B) ひらがな → 漢字
        C) 語彙を使った文法パターン
        D) 文法パターン選択
        E) つながりクイズ
        F) 意味グループ
        G) グループ問題
        H) Group label relation quiz
        I) Vocab + grammar pairing
        J) Repeated terms review
        ★ Cultural mix: 文化・旅行・妖怪・アニメ questions
        """
        lesson      = self._load_lesson(lesson_source)
        vocab, grammar, conns = self._extract(lesson)
        blocks      = lesson.get("blocks", []) or []
        block_by_id = {b.get("id"): b for b in blocks if b.get("id")}
        group_blocks = [b for b in blocks if b.get("btype") == "group" and b.get("label")]
        qs: list[dict] = []

        hira_pool  = [v.get("hira", "")               for v in vocab if v.get("hira")]
        kanji_pool = [v.get("kanji") or v.get("hira")  for v in vocab]
        gram_pool  = [g.get("grammar", "")             for g in grammar if g.get("grammar")]
        label_pool = [c.get("label", "").strip() for c in conns if c.get("label")]
        repeated_terms = self._data_repeated_terms(vocab, grammar, group_blocks, conns)

        if not label_pool:
            label_pool = ["りゆう", "けっか", "たいひ", "ほそく", "じゅんばん"]

        # A) 漢字 → ひらがな
        for v in vocab:
            if v.get("kanji") and v.get("hira"):
                # 文化的な文脈ヒントを追加
                kanji = v["kanji"]
                cultural_hint = self._get_cultural_hint(kanji)
                qs.append({
                    "type": "riddle_reading",
                    "category": "📖 読み方",
                    "question": f"「{kanji}」の　よみかたは？",
                    "choices": self._choices(v["hira"], hira_pool),
                    "answer": v["hira"],
                    "hint": cultural_hint or "ひらがなで　こたえましょう。",
                    "points": 2,
                })

        # B) ひらがな → 漢字
        for v in vocab:
            if v.get("kanji") and v.get("hira"):
                qs.append({
                    "type": "riddle_kanji",
                    "category": "📖 漢字",
                    "question": f"「{v['hira']}」を　かんじで　かくと？",
                    "choices": self._choices(v["kanji"], kanji_pool),
                    "answer": v["kanji"],
                    "hint": "漢字ブロックを　おもいだして！",
                    "points": 2,
                })

        # C) 語彙を使った文法パターン
        for v in vocab:
            word = v.get("kanji") or v.get("hira")
            if not word or not gram_pool:
                continue
            ans = gram_pool[0]
            qs.append({
                "type": "riddle_grammar_vocab",
                "category": "📝 文法",
                "question": f"「{word}」と　いっしょに　つかう　ぶんぽうは？",
                "choices": self._choices(ans, gram_pool),
                "answer": ans,
                "hint": "文法ブロックを　おもいだして！",
                "points": 2,
            })
            break

        # D) 文法パターン選択
        for g in grammar:
            ans = g.get("grammar", "")
            if not ans:
                continue
            qs.append({
                "type": "riddle_grammar",
                "category": "📝 文法",
                "question": f"ただしい　ぶんぽうパターンは　どれ？\nヒント: {ans[:4]}…",
                "choices": self._choices(ans, gram_pool),
                "answer": ans,
                "hint": "ぶんぽうブロックの　もんを　おもいだして！",
                "points": 3,
            })

        # E) つながりクイズ (cultural context hint added)
        for conn in conns[:3]:
            src = block_by_id.get(conn.get("src_id"))
            dst = block_by_id.get(conn.get("dst_id"))
            if src and dst:
                src_w = self._block_surface(src)
                dst_w = self._block_surface(dst)
                if not src_w or not dst_w:
                    continue
                qs.append({
                    "type": "riddle_connection",
                    "category": "🔗 つながり",
                    "question": f"「{src_w}」に　つながっているのは　どれ？",
                    "choices": self._choices(dst_w, kanji_pool + gram_pool),
                    "answer": dst_w,
                    "hint": "ワイヤーの　つながりを　おもいだして！",
                    "points": 3,
                })

        # F) ラベル（意味関係）クイズ
        for conn in conns:
            relation = (conn.get("label") or "").strip()
            if not relation:
                continue
            src = block_by_id.get(conn.get("src_id"))
            dst = block_by_id.get(conn.get("dst_id"))
            if not src or not dst:
                continue
            src_w = self._block_surface(src)
            dst_w = self._block_surface(dst)
            if not src_w or not dst_w:
                continue
            qs.append({
                "type": "riddle_relation_label",
                "category": "🔗 つながり",
                "question": f"「{src_w}」→「{dst_w}」の　つながりの　いみは　どれ？",
                "choices": self._choices(relation, label_pool + gram_pool + repeated_terms),
                "answer": relation,
                "hint": "ワイヤーのラベルに　どんな　いみを　つけたか　おもいだして！",
                "points": 4,
            })

        # G) グループ問題 (3語以上の時)
        if len(vocab) >= 3:
            sample   = random.sample(vocab, min(3, len(vocab)))
            odd_pool = [v.get("kanji") or v.get("hira") for v in vocab if v not in sample]
            group_words = [v.get("hira", v.get("kanji", "")) for v in sample]
            if odd_pool:
                odd = random.choice(odd_pool)
                ans = group_words[0]
                qs.append({
                    "type": "riddle_group",
                    "category": "📚 グループ",
                    "question": (
                        "つぎの　なかで　いちばん　さいしょの　たんごは？\n"
                        + "　".join(group_words + [odd])
                    ),
                    "choices": self._choices(ans, group_words + [odd]),
                    "answer": ans,
                    "hint": "このレッスンで　さいしょに　でてきた　たんごは？",
                    "points": 3,
                })

        # H) Group label relation quiz
        if group_blocks:
            group_members: dict[str, list[str]] = {}
            for conn in conns:
                src = block_by_id.get(conn.get("src_id"))
                dst = block_by_id.get(conn.get("dst_id"))
                if not src or not dst:
                    continue
                if src.get("btype") == "group":
                    label  = (src.get("label") or "").strip()
                    member = self._block_surface(dst)
                elif dst.get("btype") == "group":
                    label  = (dst.get("label") or "").strip()
                    member = self._block_surface(src)
                else:
                    continue
                if not label or not member:
                    continue
                group_members.setdefault(label, [])
                if member not in group_members[label]:
                    group_members[label].append(member)

            for label, members in group_members.items():
                if not members:
                    continue
                ans = random.choice(members)
                qs.append({
                    "type": "riddle_group_label",
                    "category": "📚 グループ",
                    "question": f"グループ「{label}」に　いちばん　あう　ものは　どれ？",
                    "choices": self._choices(ans, kanji_pool + gram_pool + members),
                    "answer": ans,
                    "hint": "group と　つながっている　ノードを　おもいだして！",
                    "points": 3,
                })

        # I) Vocab + grammar pairing
        if kanji_pool and gram_pool:
            for _ in range(min(2, len(kanji_pool))):
                w = random.choice(kanji_pool)
                g = random.choice(gram_pool)
                qs.append({
                    "type": "riddle_scene_pattern",
                    "category": "📝 文法",
                    "question": f"「{w}」と　くみあわせる　ぶんぽうは　どれ？",
                    "choices": self._choices(g, gram_pool),
                    "answer": g,
                    "hint": "文法と　ことばを　セットで　おぼえよう！",
                    "points": 3,
                })

        # J) Repeated terms review
        if len(repeated_terms) >= 2:
            ans = random.choice(repeated_terms)
            qs.append({
                "type": "riddle_repeated_term",
                "category": "🔁 復習",
                "question": "このレッスンの　data で　くりかえし　でてくる　ことばは　どれ？",
                "choices": self._choices(ans, repeated_terms + kanji_pool + gram_pool),
                "answer": ans,
                "hint": "group label と connection label も　ふくめて　みてね。",
                "points": 2,
            })

        # ── ★ CULTURAL MIX ────────────────────────────────────────────────────
        # 文化・アニメ・旅行・妖怪の問題を自動ミックス（最大3問）
        cultural_qs = self._generate_cultural_questions(vocab, grammar, count=3)
        qs.extend(cultural_qs)

        # lesson 語彙を文化的な文脈に埋め込む問題（最大2問）
        if vocab:
            context_qs = self._generate_vocab_in_cultural_context(vocab, grammar)
            qs.extend(context_qs)

        random.shuffle(qs)
        return qs[:count]

    def _get_cultural_hint(self, word: str) -> str:
        """特定の語彙に文化的なヒントを付ける。"""
        _hints = {
            "桜": "春に短く咲く日本の象徴的な花。お花見の主役！",
            "鬼": "節分で「鬼は外！」と豆を投げる。アニメにもよく登場。",
            "神社": "鳥居をくぐると境内（けいだい）に入ります。",
            "侍": "江戸時代の武士。刀を持ち主君に仕えた。",
            "富士": "日本最高峰・富士山（3776m）。世界文化遺産。",
            "抹茶": "茶道で使われる粉末のお茶。現代ではスイーツにも！",
            "忍者": "NARUTOでおなじみ。本物の忍者は情報収集のプロ。",
        }
        for key, hint in _hints.items():
            if key in word:
                return hint
        return ""

    # ── ② デザインクイズ  (GAME 2 — Design Quiz) ────────────────────────────
    def generate_design_quiz(
        self,
        lesson_source,
        count: int = 6,
    ) -> list[dict]:
        """lesson 設計後に表示するクイズ。"""
        lesson  = self._load_lesson(lesson_source)
        vocab, grammar, conns = self._extract(lesson)
        blocks  = lesson.get("blocks", []) or []
        qs: list[dict] = []

        # Q1-Q3: このレッスンにある単語を当てる
        word_pool = [v.get("kanji") or v.get("hira") for v in vocab
                     if (v.get("kanji") or v.get("hira"))]
        for w in word_pool[:3]:
            qs.append({
                "type": "design_word_present",
                "category": "🗂 設計",
                "question": f"このレッスンで設計した「{w}」は、どのような場面で使うのが一番ふさわしいかな？",
                "choices": self._choices(w, word_pool + ["使わない", "適当に言う"]),
                "answer": w,
                "hint": "自分で配置したブロックの内容を思い出して！",
                "points": 2,
            })

        # Q8-Q9: このレッスンにある文法を当てる
        g_pool = [g.get("grammar") for g in grammar if g.get("grammar")]
        for g in g_pool[:2]:
            qs.append({
                "type": "design_grammar_present",
                "category": "🗂 設計",
                "question": "つぎの　どの　文法が　このレッスンに　はいっていますか？",
                "choices": self._choices(g, g_pool),
                "answer": g,
                "hint": "さっき　いれた　文法を　おもいだして！",
                "points": 2,
            })

        # ★ Cultural bonus question from detected category
        cultural_qs = self._generate_cultural_questions(vocab, grammar, count=1)
        qs.extend(cultural_qs)

        random.shuffle(qs)
        return qs[:count]

    # ── ③ 全レッスンスキャン  (cycle puzzle) ─────────────────────────────────
    def generate_cycle_puzzle(
        self,
        lessons_dir = "data/lesson",
        count: int = 5,
    ) -> list[dict]:
        """data/lesson/*.json を全部スキャンして周期的ランダムなぞなぞを作る。"""
        lessons_dir = Path(lessons_dir)
        files = list(lessons_dir.glob("*.json")) if lessons_dir.exists() else []
        all_qs: list[dict] = []
        for f in files:
            try:
                qs = self.generate_riddle_game(f, count=3)
                all_qs.extend(qs)
            except Exception:
                continue

        # 常に文化問題を追加（lesson が少なくても面白くなるように）
        cultural_qs = self._generate_cultural_questions([], [], count=max(2, count - len(all_qs)))
        all_qs.extend(cultural_qs)

        random.shuffle(all_qs)
        return all_qs[:count]

    # ── reward voice ──────────────────────────────────────────────────────────
    def speak_reward(self, rank: Optional[str] = None) -> str:
        return self.voice.speak_reward(rank)

    # ── internal util ─────────────────────────────────────────────────────────
    @staticmethod
    def _int_options(n: int, total: int = 4) -> list[str]:
        base = {str(n), str(max(0, n - 1)), str(n + 1), str(n + 2)}
        opts = list(base)[:total]
        while len(opts) < total:
            opts.append(str(n + len(opts)))
        random.shuffle(opts)
        return opts