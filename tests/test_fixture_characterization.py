"""実フィードスナップショット(tests/fixtures/)に対する現状挙動の固定テスト

ここでの数値はPR3時点の「現状」であり、正しさの保証ではない。
PR4以降でスコアリングや語彙をさらに調整した際に、意図した差分だけが
出ていることを確認するためのベースライン。

各フィクスチャの ai_pass は日付フィルタをかけない全件に対する
filter_ai_related 通過数（時刻に依存しないようにするため）。
実装本体（aion.selector.filters.matched_ai_keywords）をそのまま使うことで、
このテスト自体が独自にキーワード判定ロジックを再実装して現行実装と乖離するのを防ぐ。
"""

import feedparser
import pytest

from aion.collector.rss import parse_published_date
from aion.models import Article
from aion.selector.filters import matched_ai_keywords

# (フィクスチャファイル名, 取得件数, 日付パース成功件数, AI キーワード通過件数)
BASELINE = [
    ("itmedia_aiplus.xml", 20, 20, 19),
    ("zenn.xml", 20, 20, 12),
    ("hatena_bookmark_tech.xml", 30, 30, 13),
    ("techno_edge.xml", 50, 50, 31),
    # 現在このURLはRSSではなくHTMLページを返しており、feedparserが0件になる。
    # フィード設定側のURL切れとして別途扱う（PR2のスコープ外）。
    ("google_cloud_japan_blog.xml", 0, 0, 0),
    ("arxiv_cs_ai.xml", 223, 223, 102),
]


@pytest.mark.parametrize("filename,fetched,dated,ai_pass", BASELINE)
def test_fixture_baseline(fixtures_dir, filename, fetched, dated, ai_pass):
    text = (fixtures_dir / filename).read_text(encoding="utf-8")
    parsed = feedparser.parse(text)

    assert len(parsed.entries) == fetched

    dated_count = sum(1 for e in parsed.entries if parse_published_date(e) is not None)
    assert dated_count == dated

    def to_article(entry) -> Article:
        summary = (entry.get("summary", "") or entry.get("description", ""))[:500]
        return Article(
            title=entry.get("title", "No Title"),
            url=entry.get("link", ""),
            source="fixture",
            category="tech",
            summary=summary or None,
        )

    ai_pass_count = sum(1 for e in parsed.entries if matched_ai_keywords(to_article(e)))
    assert ai_pass_count == ai_pass
