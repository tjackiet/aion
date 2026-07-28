"""実フィードスナップショット(tests/fixtures/)に対する現状挙動の固定テスト

ここでの数値は「現状」であり、正しさの保証ではない。PR4以降でスコアリングや
語彙をさらに調整した際に、意図した差分だけが出ていることを確認するためのベースライン。

各フィクスチャの ai_pass は日付フィルタをかけない全件に対する filter_ai_related
通過数（時刻に依存しないようにするため）。実装本体（aion.selector.filters）と
実際の config/feeds.yaml をそのまま使うことで、このテスト自体が独自に判定ロジックや
フィード設定を再実装して現行実装と乖離するのを防ぐ。
"""

import feedparser
import pytest

from aion.collector.rss import parse_published_date
from aion.models import Article
from aion.selector.core import keyword_filter_exempt_sources
from aion.selector.filters import filter_ai_related

# (feeds.yaml上の情報源名, フィクスチャファイル名, 取得件数, 日付パース成功件数, 通過件数)
BASELINE = [
    ("ITmedia AI+", "itmedia_aiplus.xml", 20, 20, 19),
    ("Zenn", "zenn.xml", 20, 20, 12),
    ("はてなブックマーク（テクノロジー）", "hatena_bookmark_tech.xml", 30, 30, 13),
    ("テクノエッジ", "techno_edge.xml", 50, 50, 31),
    # 現在このURLはRSSではなくHTMLページを返しており、feedparserが0件になる。
    # フィード設定側のURL切れとして別途扱う（PR2のスコープ外）。
    ("Google Cloud Japan ブログ", "google_cloud_japan_blog.xml", 0, 0, 0),
    # ai_filter: false により全件通過。PR4a以前は102件（46%）しか通っていなかった。
    ("arXiv CS.AI", "arxiv_cs_ai.xml", 223, 223, 223),
]


def _parse_fixture(fixtures_dir, filename: str, source: str) -> tuple[list[Article], list]:
    text = (fixtures_dir / filename).read_text(encoding="utf-8")
    parsed = feedparser.parse(text)

    articles = []
    for entry in parsed.entries:
        summary = (entry.get("summary", "") or entry.get("description", ""))[:500]
        articles.append(
            Article(
                title=entry.get("title", "No Title"),
                url=entry.get("link", ""),
                source=source,
                category="tech",
                summary=summary or None,
            )
        )
    return articles, parsed.entries


@pytest.mark.parametrize("source,filename,fetched,dated,ai_pass", BASELINE)
def test_fixture_baseline(fixtures_dir, source, filename, fetched, dated, ai_pass):
    articles, entries = _parse_fixture(fixtures_dir, filename, source)

    assert len(entries) == fetched

    dated_count = sum(1 for e in entries if parse_published_date(e) is not None)
    assert dated_count == dated

    passed = filter_ai_related(articles, exempt_sources=keyword_filter_exempt_sources())
    assert len(passed) == ai_pass


def test_shipped_config_exempts_only_arxiv():
    """出荷時のfeeds.yamlでキーワードフィルタを免除しているフィードを固定する。

    免除は精度と引き換えに取りこぼしを消す操作なので、対象が増えたときに
    意図した変更かどうかレビューで気づけるようにしておく。
    """
    assert keyword_filter_exempt_sources() == frozenset({"arXiv CS.AI"})
