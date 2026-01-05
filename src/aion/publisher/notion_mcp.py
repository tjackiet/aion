"""Notion MCP を使った書き出しモジュール"""

import asyncio
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# AION ページの ID（Notion で接続許可済み）
AION_PAGE_ID = "2de5c334-809d-8071-b9f0-dad7930ed626"
JST = ZoneInfo("Asia/Tokyo")


async def call_notion_mcp(tool_name: str, arguments: dict) -> dict:
    """Notion MCP サーバーのツールを呼び出す"""
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote", "https://mcp.notion.com/sse"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初期化
            await session.initialize()

            # ツール呼び出し
            result = await session.call_tool(tool_name, arguments)
            return result


def publish_to_notion_sync(report_content: str, title: str | None = None) -> str:
    """レポートを Notion に書き出す（同期版）"""
    return asyncio.run(publish_to_notion(report_content, title))


async def publish_to_notion(report_content: str, title: str | None = None) -> str:
    """レポートを Notion に書き出す"""
    if title is None:
        date_str = datetime.now(JST).strftime("%Y年%m月%d日")
        title = f"AION デイリーレポート - {date_str}"

    print(f"Notion に書き出し中: {title}")

    try:
        # Notion MCP の notion-create-pages ツールを使用
        # pages は配列形式、parent で親ページを指定
        result = await call_notion_mcp("notion-create-pages", {
            "parent": {"page_id": AION_PAGE_ID},
            "pages": [
                {
                    "properties": {"title": title},
                    "content": report_content
                }
            ]
        })

        print(f"Notion への書き出し完了")

        # 結果からURLを取得
        if hasattr(result, 'content') and result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    return content.text

        return str(result)

    except Exception as e:
        print(f"Notion への書き出しに失敗: {e}")
        raise
