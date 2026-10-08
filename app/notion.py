"""Publishes artifacts to Notion as pages under one parent page."""

import httpx

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
MAX_TEXT = 2000
MAX_BLOCKS = 100


def _text(content: str) -> list[dict]:
    return [{"type": "text", "text": {"content": content[:MAX_TEXT]}}]


def _block(kind: str, content: str) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": _text(content)}}


def to_blocks(data, depth: int = 0) -> list[dict]:
    """Renders artifact JSON as headings and bullets. Nested lists stay flat to keep within API limits."""
    blocks: list[dict] = []
    if isinstance(data, dict):
        for key, value in data.items():
            label = key.replace("_", " ").capitalize()
            if isinstance(value, (dict, list)):
                blocks.append(_block("heading_3" if depth else "heading_2", label))
                blocks.extend(to_blocks(value, depth + 1))
            else:
                blocks.append(_block("bulleted_list_item", f"{label}: {value}"))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or item.get("pain") or item.get("id")
                if title:
                    blocks.append(_block("heading_3", str(title)))
                blocks.extend(to_blocks(item, depth + 1))
            else:
                blocks.append(_block("bulleted_list_item", str(item)))
    else:
        blocks.append(_block("paragraph", str(data)))
    return blocks


class NotionPublisher:
    def __init__(self, token: str, parent_page_id: str, client: httpx.Client | None = None):
        self.parent_page_id = parent_page_id
        self.http = client or httpx.Client(
            base_url=NOTION_API,
            headers={"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION},
            timeout=30,
        )

    def publish(self, title: str, body: dict) -> str:
        blocks = to_blocks(body)
        page = self.http.post(
            "/pages",
            json={
                "parent": {"page_id": self.parent_page_id},
                "properties": {"title": {"title": _text(title)}},
                "children": blocks[:MAX_BLOCKS],
            },
        )
        page.raise_for_status()
        page_id = page.json()["id"]
        for start in range(MAX_BLOCKS, len(blocks), MAX_BLOCKS):
            self.http.patch(f"/blocks/{page_id}/children", json={"children": blocks[start : start + MAX_BLOCKS]}).raise_for_status()
        return page.json()["url"]
