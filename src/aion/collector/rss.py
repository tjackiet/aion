"""RSS フィード収集モジュール"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import httpx
import yaml

from aion.models import Article, FeedConfig, FeedsConfig

JST = ZoneInfo("Asia/Tokyo")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# AI関連キーワード（タイトルフィルタ用）
AI_KEYWORDS = [
    # 基本用語
    "AI", "人工知能", "機械学習", "ディープラーニング", "深層学習",
    # LLM関連
    "LLM", "大規模言語モデル", "GPT", "Claude", "Gemini", "ChatGPT",
    "生成AI", "生成系AI", "Copilot", "RAG",
    # エージェント
    "AIエージェント", "エージェント", "Agent",
    # 技術用語
    "プロンプト", "ファインチューニング", "トランスフォーマー",
    "ニューラルネットワーク", "自然言語処理", "NLP",
    # サービス・企業
    "OpenAI", "Anthropic", "DeepMind", "Hugging Face",
    # 応用分野
    "画像生成", "音声認識", "自動運転", "ロボット",
]


def load_feeds_config(config_path: Path | None = None) -> FeedsConfig:
    """フィード設定をYAMLから読み込む"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "feeds.yaml"

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return FeedsConfig(**data)


def parse_published_date(entry: dict) -> datetime | None:
    """RSSエントリから公開日時をパース

    feedparser の published_parsed / updated_parsed は UTC に正規化された
    time.struct_time を返す。UTCとして解釈してからJSTに変換する。
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=UTC).astimezone(JST)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=UTC).astimezone(JST)
    return None


def fetch_feed(feed_config: FeedConfig) -> list[Article]:
    """単一のRSSフィードから記事を取得"""
    articles = []

    # User-Agentを設定してRSSを取得（一部サイトはブロック対策が必要）
    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(feed_config.url, headers=headers, follow_redirects=True, timeout=30)
    response.raise_for_status()
    parsed = feedparser.parse(response.text)

    for entry in parsed.entries:
        published = parse_published_date(entry)
        summary = entry.get("summary", "") or entry.get("description", "")

        article = Article(
            title=entry.get("title", "No Title"),
            url=entry.get("link", ""),
            source=feed_config.name,
            category=feed_config.category,
            published=published,
            summary=summary[:500] if summary else None,  # 長すぎる場合は切り詰め
        )
        articles.append(article)

    return articles


def fetch_all_feeds(config_path: Path | None = None) -> list[Article]:
    """全フィードから記事を取得"""
    config = load_feeds_config(config_path)
    all_articles = []

    for feed_config in config.feeds:
        if not feed_config.enabled:
            continue

        try:
            articles = fetch_feed(feed_config)
            all_articles.extend(articles)
            print(f"✓ {feed_config.name}: {len(articles)}件取得")
        except Exception as e:
            print(f"✗ {feed_config.name}: エラー - {e}")

    return all_articles


def count_undated_by_source(articles: list[Article]) -> dict[str, int]:
    """公開日時をパースできなかった記事数を情報源ごとに集計

    日付フィルタはこれらを黙って除外するため、件数を可視化する。
    """
    counts: dict[str, int] = {}
    for article in articles:
        if article.published is None:
            counts[article.source] = counts.get(article.source, 0) + 1
    return counts


def filter_recent_articles(articles: list[Article], days: int = 1) -> list[Article]:
    """直近N日間の記事をフィルタリング"""
    cutoff = datetime.now(JST) - timedelta(days=days)
    return [a for a in articles if a.published and a.published >= cutoff]


def filter_ai_related(articles: list[Article]) -> list[Article]:
    """AI関連の記事のみをフィルタリング（タイトルベース）"""
    def is_ai_related(article: Article) -> bool:
        title = article.title.upper()
        summary = (article.summary or "").upper()
        text = title + " " + summary
        return any(kw.upper() in text for kw in AI_KEYWORDS)

    return [a for a in articles if is_ai_related(a)]


def collect(days: int = 1, ai_filter: bool = True) -> list[Article]:
    """メイン収集関数: フィード取得 + フィルタリング"""
    print(f"RSSフィードを取得中...")
    articles = fetch_all_feeds()
    print(f"合計 {len(articles)} 件の記事を取得")

    undated = count_undated_by_source(articles)
    if undated:
        detail = ", ".join(f"{source} {count}件" for source, count in undated.items())
        print(f"⚠ 公開日時を取得できず除外: {sum(undated.values())} 件（{detail}）")

    filtered = filter_recent_articles(articles, days=days)
    print(f"直近{days}日間の記事: {len(filtered)} 件")

    if ai_filter:
        filtered = filter_ai_related(filtered)
        print(f"AI関連記事: {len(filtered)} 件")

    return filtered
