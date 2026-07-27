"""AION データモデル定義"""

from datetime import datetime

from pydantic import BaseModel, Field


class Article(BaseModel):
    """記事データモデル"""

    title: str = Field(..., description="記事タイトル")
    url: str = Field(..., description="記事URL")
    source: str = Field(..., description="情報源名")
    category: str = Field(..., description="カテゴリ (business/tech/research)")
    published: datetime | None = Field(None, description="公開日時")
    summary: str | None = Field(None, description="記事概要（RSSから取得）")
    content: str | None = Field(None, description="記事本文")

    # LLM生成フィールド
    ai_summary: str | None = Field(None, description="AI生成要約")
    why_it_matters: str | None = Field(None, description="Why it matters")

    # 選定ロジックの可視化用フィールド（--explain で利用）
    matched_keywords: list[str] = Field(default_factory=list, description="マッチしたAIキーワード")
    excluded_reason: str | None = Field(None, description="選定から除外された理由（通過時はNone）")


class FeedConfig(BaseModel):
    """RSSフィード設定"""

    name: str
    url: str
    category: str
    enabled: bool = True


class FeedsConfig(BaseModel):
    """フィード設定ファイル全体"""

    feeds: list[FeedConfig]
