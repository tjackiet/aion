"""実フィードスナップショット(tests/fixtures/)に対する現状挙動の固定テスト

ここでの数値はPR2時点の「現状」であり、正しさの保証ではない。
PR3以降でキーワード改善やURL正規化を入れた際に、意図した差分だけが
出ていることを確認するためのベースライン。

各フィクスチャの ai_pass は日付フィルタをかけない全件に対する
filter_ai_related 通過数（時刻に依存しないようにするため）。
"""

import feedparser
import pytest

from aion.collector.rss import parse_published_date
from aion.selector.filters import AI_KEYWORDS

# (フィクスチャファイル名, 取得件数, 日付パース成功件数, AI キーワード通過件数)
BASELINE = [
    ("itmedia_aiplus.xml", 20, 20, 19),
    ("zenn.xml", 20, 20, 12),
    ("hatena_bookmark_tech.xml", 30, 30, 16),
    ("techno_edge.xml", 50, 50, 32),
    # 現在このURLはRSSではなくHTMLページを返しており、feedparserが0件になる。
    # フィード設定側のURL切れとして別途扱う（PR2のスコープ外）。
    ("google_cloud_japan_blog.xml", 0, 0, 0),
    ("arxiv_cs_ai.xml", 223, 223, 189),
]


def _is_ai_related(title: str, summary: str) -> bool:
    text = (title + " " + summary).upper()
    return any(kw.upper() in text for kw in AI_KEYWORDS)


@pytest.mark.parametrize("filename,fetched,dated,ai_pass", BASELINE)
def test_fixture_baseline(fixtures_dir, filename, fetched, dated, ai_pass):
    text = (fixtures_dir / filename).read_text(encoding="utf-8")
    parsed = feedparser.parse(text)

    assert len(parsed.entries) == fetched

    dated_count = sum(1 for e in parsed.entries if parse_published_date(e) is not None)
    assert dated_count == dated

    ai_pass_count = sum(
        1
        for e in parsed.entries
        if _is_ai_related(e.get("title", "No Title"), (e.get("summary", "") or e.get("description", ""))[:500])
    )
    assert ai_pass_count == ai_pass
