"""スコア順の並べ替えとカテゴリ別クォータによる要約対象の選定

これ以前は summarizer が articles[:max_articles] で先頭N件を切っていた。
記事はフィード取得順（feeds.yaml の並び順）で積まれているため、先頭にある
ITmedia AI+ が要約枠を全部食い、後ろにある Zenn / はてブ / テクノエッジ /
arXiv は一件も選ばれないという構造になっていた。
選定はここに集約し、summarizer は渡された記事を要約するだけにする。
"""

from aion.models import Article

DEFAULT_MAX_ARTICLES = 10

# カテゴリごとの配分比。max_articles がこの合計と異なる場合は比率として按分する。
CATEGORY_QUOTA = {
    "business": 3,
    "tech": 4,
    "research": 3,
}


def _sort_key(article: Article) -> tuple:
    """スコア降順・新しい順で並べる。同点時の順序を安定させるため title まで見る。

    published が None の記事は最後に回す。
    """
    published_rank = -article.published.timestamp() if article.published else float("inf")
    return (-article.score, published_rank, article.title)


def rank_articles(articles: list[Article]) -> list[Article]:
    """スコア降順に並べ替えた新しいリストを返す"""
    return sorted(articles, key=_sort_key)


def allocate_quota(max_articles: int, quota: dict[str, int] | None = None) -> dict[str, int]:
    """配分比を max_articles 件に按分する（最大剰余法）

    合計が max_articles ちょうどになるよう、切り捨てで余った枠を小数部の大きい
    カテゴリから順に配る。
    """
    quota = quota or CATEGORY_QUOTA
    total_weight = sum(quota.values())
    if total_weight <= 0 or max_articles <= 0:
        return dict.fromkeys(quota, 0)

    exact = {cat: max_articles * weight / total_weight for cat, weight in quota.items()}
    allocated = {cat: int(value) for cat, value in exact.items()}

    remaining = max_articles - sum(allocated.values())
    # 小数部が大きい順（同率はカテゴリ名順）に余りを配る
    for category in sorted(exact, key=lambda c: (-(exact[c] - allocated[c]), c))[:remaining]:
        allocated[category] += 1

    return allocated


def select_for_summary(
    articles: list[Article],
    max_articles: int = DEFAULT_MAX_ARTICLES,
    quota: dict[str, int] | None = None,
) -> list[Article]:
    """要約対象をスコア順・カテゴリ別クォータで選ぶ

    各カテゴリに割り当てた枠までスコア上位から取り、記事数が枠に満たない
    カテゴリの余り枠は全体のスコア順で埋める（クォータのせいで要約枠が
    空くのを避けるため）。返り値は全体のスコア順。
    """
    ranked = rank_articles(articles)
    allocated = allocate_quota(max_articles, quota)

    selected: list[Article] = []
    used_slots: dict[str, int] = dict.fromkeys(allocated, 0)

    for article in ranked:
        slots = allocated.get(article.category, 0)
        if used_slots.get(article.category, 0) < slots:
            used_slots[article.category] = used_slots.get(article.category, 0) + 1
            selected.append(article)

    # クォータで埋まらなかった枠をスコア順で補充
    if len(selected) < max_articles:
        chosen = {id(a) for a in selected}
        for article in ranked:
            if len(selected) >= max_articles:
                break
            if id(article) not in chosen:
                selected.append(article)

    return rank_articles(selected)


def category_breakdown(articles: list[Article]) -> dict[str, int]:
    """カテゴリごとの件数を数える（ログ表示用）"""
    counts: dict[str, int] = {}
    for article in articles:
        counts[article.category] = counts.get(article.category, 0) + 1
    return counts
