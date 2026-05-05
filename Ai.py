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
        "すごい！　きょうも　えらいね！",
        "やったね！　きみは　さいこうだよぉ！",
        "ぱちぱち！　ほんとうに　すごすぎるよぉ！",
        "さすが！　お兄ちゃん、かっこいい！",
        "完璧だよ！　ユキ、感動しちゃった！",
    ],
    "A": [
        "よくできました！　だいすき！",
        "すてき！　にほんごが　どんどん　じょうずになってるよ！",
        "せいかい！　にほんご　マスターへ　またいっぽ　ちかづいたね！",
        "いい感じ、いい感じ！　その調子だよ！",
    ],
    "B": [
        "やるじゃん！　またいっしょに　やろうね！",
        "かしこい！　もっともっと　いっしょに　がんばろう？",
        "お祭りで花火みたいに　ぱあっと輝いてるよ！",
        "合格点だよ！　えへへ、次も頑張ろうね？",
    ],
    "C": [
        "だいじょうぶ！　ユキが　ずっと　ついてるからね！",
        "つぎは　もっと　いっしょに　がんばろう？　ねっ？",
        "どんまい！　あきらめないで、お兄ちゃん！",
        "ユキと一緒に、もう一回練習してみない？",
    ]
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

    # ────────────── ⛩ 文化 (Culture & Festivals) ─────────────────────────────
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "初詣（はつもうで）とは、何をする行事ですか？",
        "choices": ["新年に神社や寺へお参りする", "夏に花火を見る", "お盆に墓参りをする", "冬至にゆず湯に入る"],
        "answer": "新年に神社や寺へお参りする",
        "hint": "お正月の習慣。「初」=はじめて + 「詣でる」=お参りする。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "神社の鳥居（とりい）をくぐるとき、マナーとして正しいのは？",
        "choices": ["中央をさける（神様の通り道）", "走って通る", "帽子をかぶったまま入る", "大声で話しながら通る"],
        "answer": "中央をさける（神様の通り道）",
        "hint": "鳥居の中央「正中」は神様が歩く道とされています。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "七夕（たなばた）の伝説で、1年に一度だけ天の川を渡って会える2人は？",
        "choices": ["織姫（おりひめ）と彦星（ひこぼし）", "浦島太郎と亀", "かぐや姫と帝", "桃太郎と鬼"],
        "answer": "織姫（おりひめ）と彦星（ひこぼし）",
        "hint": "7月7日の夜、天の川に橋ができると言われています。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "茶道（さどう）で使われる「一期一会（いちごいちえ）」の意味は？",
        "choices": ["一生に一度の出会いを大切に", "お茶を一杯飲む作法", "一年に一回の特別な行事", "一度しか会えない人のこと"],
        "answer": "一生に一度の出会いを大切に",
        "hint": "この瞬間は二度と戻らない。茶道の根本的な考え方です。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "「いただきます」を食事の前に言うのは、なぜですか？",
        "choices": ["食材の命をいただく感謝の気持ち", "シェフへのお礼", "食事が美味しいという意味", "準備完了を知らせるため"],
        "answer": "食材の命をいただく感謝の気持ち",
        "hint": "動植物の「命」をいただくという日本文化の美しい考え方。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "花見（はなみ）の「花」とは主に何の花を指しますか？",
        "choices": ["桜（さくら）", "梅（うめ）", "菊（きく）", "蓮（はす）"],
        "answer": "桜（さくら）",
        "hint": "春に短く咲き、日本の象徴とも言える花です。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "お正月に神社で引く、運勢が書かれた紙のことを何と言いますか？",
        "choices": ["おみくじ", "お守り", "絵馬（えま）", "御朱印（ごしゅいん）"],
        "answer": "おみくじ",
        "hint": "大吉・吉・末吉・凶などが書かれています。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "節分（せつぶん）で「鬼は外、福は内」と叫びながら何を撒きますか？",
        "choices": ["大豆（だいず）", "お米", "塩", "砂"],
        "answer": "大豆（だいず）",
        "hint": "2月3日頃に行われ、邪気を追い払う意味があります。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "⛩ 文化",
        "question": "神社に願い事を書いて掛ける木の板のことを何と言いますか？",
        "choices": ["絵馬（えま）", "御朱印（ごしゅいん）", "お守り（おまもり）", "注連縄（しめなわ）"],
        "answer": "絵馬（えま）",
        "hint": "受験合格や恋愛成就など、様々な願い事を書きます。",
        "points": 3,
    },

    # ────────────── 🌸 旅行 (Travel & Famous Places) ──────────────────────────
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "京都（きょうと）にある千本の朱色の鳥居が有名な神社はどれですか？",
        "choices": ["伏見稲荷大社（ふしみいなりたいしゃ）", "明治神宮", "浅草寺", "春日大社"],
        "answer": "伏見稲荷大社（ふしみいなりたいしゃ）",
        "hint": "SNSで超有名！山の中にオレンジ色の鳥居が続きます。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "東京・浅草（あさくさ）にある、巨大な赤提灯で有名な門の名前は？",
        "choices": ["雷門（かみなりもん）", "赤門（あかもん）", "桜門", "仁王門（におうもん）"],
        "answer": "雷門（かみなりもん）",
        "hint": "浅草寺の入り口。観光写真の定番スポットです。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "日本で最も高い山の名前は？（標高3776m）",
        "choices": ["富士山（ふじさん）", "高尾山（たかおさん）", "白山（はくさん）", "槍ヶ岳（やりがたけ）"],
        "answer": "富士山（ふじさん）",
        "hint": "世界文化遺産にも登録されている、日本の象徴。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "奈良（なら）公園で有名な、神聖とされる動物は何ですか？",
        "choices": ["鹿（しか）", "猿（さる）", "狐（きつね）", "タヌキ"],
        "answer": "鹿（しか）",
        "hint": "観光客にせんべいをねだってきます。春日大社の神の使いです。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "旅館（りょかん）に泊まるとき、夕食後に着る薄い和服は？",
        "choices": ["浴衣（ゆかた）", "着物（きもの）", "袴（はかま）", "甚平（じんべい）"],
        "answer": "浴衣（ゆかた）",
        "hint": "夏祭りでも着ます。着物より薄くてカジュアルです。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "沖縄（おきなわ）の屋根の上にある、魔除けの守り神の置物は？",
        "choices": ["シーサー", "狛犬（こまいぬ）", "お地蔵様（じぞうさま）", "達磨（だるま）"],
        "answer": "シーサー",
        "hint": "口を開けた雄と、口を閉じた雌が一対になっています。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🌸 旅行",
        "question": "「新幹線（しんかんせん）」の英語ニックネームは何ですか？",
        "choices": ["Bullet Train", "Rocket Train", "Ninja Express", "Samurai Rail"],
        "answer": "Bullet Train",
        "hint": "弾丸（だんがん）= Bullet。速さの象徴です。",
        "points": 2,
    },

    # ────────────── 👺 妖怪・霊 (Yokai & Spiritual) ───────────────────────────
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "頭に皿を持ち、水辺で人を引き込む日本の妖怪の名前は？",
        "choices": ["河童（かっぱ）", "天狗（てんぐ）", "雪女（ゆきおんな）", "座敷童（ざしきわらし）"],
        "answer": "河童（かっぱ）",
        "hint": "頭の皿に水が入っています。キュウリが大好物！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "吹雪の夜に現れる、美しく恐ろしい女性の妖怪は？",
        "choices": ["雪女（ゆきおんな）", "河童（かっぱ）", "天狗（てんぐ）", "鬼（おに）"],
        "answer": "雪女（ゆきおんな）",
        "hint": "冷たい吐息で人を凍らせるとも言われます。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "長い鼻と赤い顔が特徴で、山に住む剣術の達人と言われる妖怪は？",
        "choices": ["天狗（てんぐ）", "河童（かっぱ）", "鬼（おに）", "狐（きつね）"],
        "answer": "天狗（てんぐ）",
        "hint": "山岳信仰と深く関わり、烏天狗と大天狗の2種類がいます。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "神道（しんとう）では、自然の物（岩・川・山）に宿る霊のことを総称して何と言いますか？",
        "choices": ["八百万の神（やおよろずのかみ）", "幽霊（ゆうれい）", "悪霊（あくりょう）", "鬼（おに）"],
        "answer": "八百万の神（やおよろずのかみ）",
        "hint": "あらゆるものに神が宿るという、日本古来の考え方です。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "「千と千尋の神隠し」（スタジオジブリ）の「油屋」は何をモチーフにしていますか？",
        "choices": ["神様が集う温泉・銭湯の世界", "江戸時代の商店街", "仏教の寺院", "戦国時代のお城"],
        "answer": "神様が集う温泉・銭湯の世界",
        "hint": "八百万の神々が疲れを癒しにやってくる場所です。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "日本の伝説で「九尾の狐（きゅうびのきつね）」はどのような存在ですか？",
        "choices": ["知恵と長寿を持つ、時に危険な霊獣", "純粋に幸運をもたらす神様", "農業の守護霊", "海の神様の使い"],
        "answer": "知恵と長寿を持つ、時に危険な霊獣",
        "hint": "「NARUTO」でも九尾として大活躍！尻尾が増えるほど強くなります。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "👺 妖怪",
        "question": "お盆（おぼん）の時期に行われる「盆踊り（ぼんおどり）」は何のための踊りですか？",
        "choices": ["先祖の霊を迎えて、共に過ごすため", "春の豊作を祈るため", "若者の成長を祝うため", "天気を良くするための祈雨"],
        "answer": "先祖の霊を迎えて、共に過ごすため",
        "hint": "お盆は先祖の霊が戻ってくる期間。8月中旬に行われます。",
        "points": 3,
    },

    # ────────────── 🎌 アニメ (Anime Context) ─────────────────────────────────
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "「鬼滅の刃（きめつのやいば）」で鬼を倒すことができる刀は何ですか？",
        "choices": ["日輪刀（ひにちのかたな）", "霊刀（れいとう）", "神刀（しんとう）", "業火刀（ごうかとう）"],
        "answer": "日輪刀（ひにちのかたな）",
        "hint": "太陽の光を宿した刀。使い手によって色が変わります。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "アニメでよく出てくる「俺（おれ）」「僕（ぼく）」「わたし」の違いは何ですか？",
        "choices": ["キャラの性格・男らしさ・丁寧さの違い", "年齢だけの違い", "地方方言の違い", "職業による使い分け"],
        "answer": "キャラの性格・男らしさ・丁寧さの違い",
        "hint": "「俺」は荒々しい、「僕」は謙虚・少年っぽい、「わたし」は丁寧です。",
        "points": 4,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "「NARUTO(ナルト)」の主人公の夢（目標）は何ですか？",
        "choices": ["火影（ほかげ）になること", "九尾を倒すこと", "最強の忍になること", "里を守ること"],
        "answer": "火影（ほかげ）になること",
        "hint": "「俺は絶対に火影になる！」が口癖ですね。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "「呪術廻戦（じゅじゅつかいせん）」で、虎杖悠仁（いたどりゆうじ）が取り込んだ「宿儺（すくな）」とは何ですか？",
        "choices": ["最強の呪霊（じゅれい）", "失われた術式", "封印された神様", "死んだ呪術師の魂"],
        "answer": "最強の呪霊（じゅれい）",
        "hint": "「両面宿儺」の指を飲み込んだことで物語が始まります。",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "アニメで「よろしくお願いします（よろしくおねがいします）」はどんな場面で使いますか？",
        "choices": ["初対面・依頼・感謝など多くの場面", "謝るときだけ", "さよならを言うとき", "食事の前だけ"],
        "answer": "初対面・依頼・感謝など多くの場面",
        "hint": "日本語で一番多用される表現の一つ。場面によって意味が変わります！",
        "points": 3,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "「ワンピース」でモンキー・D・ルフィの体の特徴は何ですか？",
        "choices": ["体がゴムのように伸びる", "炎を体から出せる", "氷を操ることができる", "分身を作れる"],
        "answer": "体がゴムのように伸びる",
        "hint": "ゴムゴムの実を食べた結果。でも泳げなくなりました。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "「転生したらスライムだった件」の主人公・リムルが転生した生き物は？",
        "choices": ["スライム", "ドラゴン", "ゴブリン", "ウルフ"],
        "answer": "スライム",
        "hint": "タイトルがそのまま答えです！見た目は弱そうでも実は最強。",
        "points": 2,
    },
    {
        "type": "cultural",
        "category": "🎌 アニメ",
        "question": "アニメ「進撃の巨人（しんげきのきょじん）」で、人類が暮らす三重の壁の一番外側の壁の名前は？",
        "choices": ["ウォール・マリア", "ウォール・ローゼ", "ウォール・シーナ", "ウォール・タイタン"],
        "answer": "ウォール・マリア",
        "hint": "物語冒頭で巨人に壊された、一番外側の壁です。",
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