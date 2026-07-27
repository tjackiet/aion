"""pytest共通フィクスチャ"""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from aion.models import Article

FIXTURES_DIR = Path(__file__).parent / "fixtures"
JST = ZoneInfo("Asia/Tokyo")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def make_article():
    """テスト用のArticleを組み立てるファクトリフィクスチャ

    published_offset は datetime.now(JST) からの相対時間。None なら published=None。
    """

    def _make(
        title: str = "テスト記事",
        summary: str | None = None,
        source: str = "テストソース",
        category: str = "tech",
        published_offset: timedelta | None = None,
    ) -> Article:
        published = None
        if published_offset is not None:
            published = datetime.now(JST) + published_offset

        return Article(
            title=title,
            url="https://example.com/article",
            source=source,
            category=category,
            published=published,
            summary=summary,
        )

    return _make
