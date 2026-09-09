#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵光记客服 FAQ 检索器（自包含，无外部依赖）。

用法:
    python3 retrieve.py "客户原话" [--top N] [--data-dir /path/to/qa]

输出: JSON，形如
    {"matches":[{"qid":"Q5.6","question":"...","answer":"...","score":0.83}], "total":82}
匹配失败时 matches 为空。
"""

import re
import sys
import json
import math
import argparse
from pathlib import Path

# 数据目录：默认相对本脚本向上四级
# skills/lingji-qa/scripts/retrieve.py -> scripts -> lingji-qa -> skills -> 插件根 -> data/qa
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "qa"

# 必须转人工的关键主题（命中时提醒客服勿代答）
HUMAN_ONLY = ["退款", "退货", "投诉", "注销", "隐私", "数据恢复", "订单核验", "账号申诉"]


def load_qa(data_dir: Path):
    """解析所有 FAQ md，返回 QA 列表。每个 QA: {qid, question, answer, file, _bg}"""
    qa = []
    if not data_dir.exists():
        return qa
    for f in sorted(data_dir.glob("*.md")):
        if f.name == "index.md":
            continue
        text = f.read_text(encoding="utf-8")
        # 以 "### Qx.y 标题" 作为条目分隔
        parts = re.split(r"\n###\s+(Q[\d]+(?:\.[\d]+)*)\s+([^\n]+)", text)
        # parts[0] 为前缀，其后每 3 段为 (qid, 标题, 正文)
        for i in range(1, len(parts), 3):
            qid = parts[i].strip()
            qtitle = parts[i + 1].strip()
            body = parts[i + 2].strip()
            if not qid or not body:
                continue
            qa.append(
                {
                    "qid": qid,
                    "question": qtitle,
                    "answer": body,
                    "file": f.name,
                    "_qbg": bigrams(qtitle),       # 仅问题标题（标准表述）
                    "_abg": bigrams(body),         # 仅答案
                    "_bg": bigrams(qtitle + " " + body),
                }
            )
    return qa


def build_df(qa: list):
    """计算每个二元组的文档频率（IDF 用），出现越少的词权重越高"""
    df = {}
    for item in qa:
        for b in item["_bg"]:
            df[b] = df.get(b, 0) + 1
    return df


def normalize(s: str) -> str:
    """去空白、保留中文与字母数字"""
    s = s.lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[^\w\u4e00-\u9fff]", "", s)
    return s


# 无语义信号的疑问语气/高频二元组，匹配时直接忽略，避免噪声（如"什么""怎么"）
STOP_BIGRAMS = {
    "什么", "有什", "怎么", "么办", "为什", "为何", "哪些", "有哪",
    "什么样", "么样", "怎样", "如何", "何如",
    "吗", "呢", "呀", "哈", "哦", "亲", "哒", "嗯", "啊", "吧", "啦",
    "嘞", "诶", "嘛", "咱", "额", "哎", "喂", "嘞", "咯",
}


def bigrams(s: str) -> set:
    s = normalize(s)
    if len(s) <= 1:
        return {s} if s else set()
    return {s[i : i + 2] for i in range(len(s) - 1)} - STOP_BIGRAMS


def coverage(query_bg: set, text: str) -> float:
    """query 二元组在 text 中的覆盖率"""
    if not query_bg:
        return 0.0
    text_bg = bigrams(text)
    if not text_bg:
        return 0.0
    overlap = len(query_bg & text_bg)
    return overlap / len(query_bg)


def cosine(query_bg: set, doc_bg: set, df: dict, N: int) -> float:
    """TF-IDF 余弦相似度。query_bg 为查询二元组多重集，doc_bg 为文档二元组多重集。"""
    if not query_bg:
        return 0.0

    def idf(b):
        return math.log(N / (df.get(b, 0) + 1)) + 1.0

    qv = {}
    for b in query_bg:
        qv[b] = qv.get(b, 0) + 1
    # query 向量加权
    qw = {b: c * idf(b) for b, c in qv.items()}

    dv = {}
    for b in doc_bg:
        dv[b] = dv.get(b, 0) + 1
    dw = {b: c * idf(b) for b, c in dv.items()}

    common = set(qw) & set(dw)
    if not common:
        return 0.0
    dot = sum(qw[b] * dw[b] for b in common)
    nq = math.sqrt(sum(v * v for v in qw.values()))
    nd = math.sqrt(sum(v * v for v in dw.values()))
    if nd == 0 or nq == 0:
        return 0.0
    return dot / (nq * nd)


def score_qa(query: str, qa_item: dict, df: dict, N: int) -> float:
    """以「问题标题」为主（0.8）、「答案」为辅（0.2）做余弦匹配。

    客户原话本质上是在描述一个"问题"，因此优先与标准问题标题对齐；
    仅当客户描述症状（只出现在答案里）时，答案部分提供召回补充。
    """
    q_bg = bigrams(query)
    if not q_bg:
        return 0.0
    cq = cosine(q_bg, qa_item["_qbg"], df, N)   # 对问题标题
    ca = cosine(q_bg, qa_item["_abg"], df, N)   # 对答案
    return 0.8 * cq + 0.2 * ca


# 低于此相似度视为无关，过滤噪声
MIN_SCORE = 0.04


def retrieve(query: str, qa: list, top_n: int = 3):
    df = build_df(qa)
    N = len(df) + 1
    scored = []
    for item in qa:
        sc = score_qa(query, item, df, N)
        if sc >= MIN_SCORE:
            scored.append((sc, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    matches = []
    for sc, item in scored[:top_n]:
        matches.append(
            {
                "qid": item["qid"],
                "question": item["question"],
                "answer": item["answer"],
                "score": round(sc, 3),
            }
        )
    return matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="客户原话")
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    qa = load_qa(data_dir)
    if not qa:
        print(json.dumps({"matches": [], "total": 0, "error": "FAQ data not found"}, ensure_ascii=False))
        return

    matches = retrieve(args.query, qa, args.top)

    # 转人工提示
    need_human = [k for k in HUMAN_ONLY if k in args.query]

    out = {
        "matches": matches,
        "total": len(qa),
        "need_human": need_human,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
