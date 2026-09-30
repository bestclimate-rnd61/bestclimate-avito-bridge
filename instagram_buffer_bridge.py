import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_URL = "https://api.buffer.com"
QUEUE_FILE = Path(os.getenv("BUFFER_QUEUE_FILE", "instagram_content_queue.json"))
TARGET_CHANNEL = os.getenv("BUFFER_CHANNEL_NAME", "sitkoalex.ai.business").strip().lower()
MAX_ADD_PER_RUN = int(os.getenv("BUFFER_MAX_ADD_PER_RUN", "10"))


def gql(query: str, variables: dict | None = None) -> dict:
    token = os.getenv("BUFFER_API_KEY")
    if not token:
        raise RuntimeError("BUFFER_API_KEY is not configured")
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "sitkoalex-ai-business-buffer-bridge/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Buffer HTTP {exc.code}: {body[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Buffer network error: {exc}") from exc
    if data.get("errors"):
        raise RuntimeError(f"Buffer GraphQL errors: {data['errors']}")
    return data.get("data") or {}


def discover_target() -> tuple[str, str]:
    data = gql(
        """
        query GetAccount {
          account {
            organizations { id name }
          }
        }
        """
    )
    orgs = ((data.get("account") or {}).get("organizations") or [])
    if not orgs:
        raise RuntimeError("No Buffer organizations found")

    for org in orgs:
        org_id = org["id"]
        channel_data = gql(
            """
            query GetChannels($orgId: OrganizationId!) {
              channels(input: { organizationId: $orgId }) {
                id
                name
                service
              }
            }
            """,
            {"orgId": org_id},
        )
        channels = channel_data.get("channels") or []
        for channel in channels:
            name = str(channel.get("name") or "").strip().lower()
            service = str(channel.get("service") or "").strip().lower()
            if service == "instagram" and name == TARGET_CHANNEL:
                return org_id, channel["id"]

    # Fallback: if there is exactly one Instagram channel, use it.
    instagram_channels = []
    for org in orgs:
        org_id = org["id"]
        channel_data = gql(
            """
            query GetChannels($orgId: OrganizationId!) {
              channels(input: { organizationId: $orgId }) { id name service }
            }
            """,
            {"orgId": org_id},
        )
        for channel in channel_data.get("channels") or []:
            if str(channel.get("service") or "").lower() == "instagram":
                instagram_channels.append((org_id, channel))
    if len(instagram_channels) == 1:
        org_id, channel = instagram_channels[0]
        return org_id, channel["id"]
    raise RuntimeError(f"Instagram channel '{TARGET_CHANNEL}' not found")


def existing_texts(org_id: str, channel_id: str) -> set[str]:
    data = gql(
        """
        query GetPosts($orgId: OrganizationId!, $channelId: ChannelId!) {
          posts(
            first: 100
            input: {
              organizationId: $orgId
              filter: { channelIds: [$channelId] }
              sort: [{ field: createdAt, direction: desc }]
            }
          ) {
            edges {
              node { id text status dueAt channelId }
            }
          }
        }
        """,
        {"orgId": org_id, "channelId": channel_id},
    )
    edges = (((data.get("posts") or {}).get("edges")) or [])
    return {str((edge.get("node") or {}).get("text") or "").strip() for edge in edges}


def create_post(channel_id: str, item: dict) -> dict:
    caption = str(item.get("caption") or "").strip()
    media_url = str(item.get("media_url") or "").strip()
    content_type = str(item.get("type") or "reel").strip().lower()
    if not caption:
        raise ValueError("caption is required")
    if content_type not in {"reel", "story", "post"}:
        raise ValueError(f"unsupported type: {content_type}")
    if not media_url:
        raise ValueError("media_url is required for Instagram")

    media_kind = str(item.get("media_kind") or ("video" if content_type in {"reel", "story"} else "image")).lower()
    if media_kind not in {"video", "image"}:
        raise ValueError(f"unsupported media_kind: {media_kind}")

    input_data = {
        "text": caption,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
        "assets": [{media_kind: {"url": media_url}}],
        "metadata": {
            "instagram": {
                "type": content_type,
                "shouldShareToFeed": bool(item.get("share_to_feed", content_type != "story")),
            }
        },
    }

    data = gql(
        """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess {
              post { id text dueAt status channelId }
            }
            ... on MutationError { message }
          }
        }
        """,
        {"input": input_data},
    )
    result = data.get("createPost") or {}
    if result.get("message"):
        raise RuntimeError(result["message"])
    post = result.get("post")
    if not post:
        raise RuntimeError(f"Unexpected createPost response: {result}")
    return post


def main() -> int:
    print("BUFFER_BRIDGE_START", flush=True)
    if not QUEUE_FILE.exists():
        print(f"BUFFER_BRIDGE_NO_QUEUE file={QUEUE_FILE}", flush=True)
        return 0

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    if not isinstance(queue, list):
        raise RuntimeError("Queue file must contain a JSON array")

    org_id, channel_id = discover_target()
    seen = existing_texts(org_id, channel_id)
    added = 0
    skipped = 0
    errors = 0

    for item in queue:
        if added >= MAX_ADD_PER_RUN:
            break
        if not isinstance(item, dict) or not item.get("approved"):
            continue
        caption = str(item.get("caption") or "").strip()
        if not caption or caption in seen:
            skipped += 1
            continue
        try:
            post = create_post(channel_id, item)
            seen.add(caption)
            added += 1
            print(
                "BUFFER_BRIDGE_ADDED " + json.dumps(
                    {"queue_id": item.get("id"), "post_id": post.get("id"), "due_at": post.get("dueAt")},
                    ensure_ascii=False,
                ),
                flush=True,
            )
        except Exception as exc:
            errors += 1
            print(
                "BUFFER_BRIDGE_ITEM_ERROR " + json.dumps(
                    {"queue_id": item.get("id"), "error": str(exc)[:500]},
                    ensure_ascii=False,
                ),
                flush=True,
            )
            # Buffer Free queue limit or validation errors should not fan out.
            break

    print(
        "BUFFER_BRIDGE_DONE " + json.dumps(
            {"channel": TARGET_CHANNEL, "added": added, "skipped": skipped, "errors": errors},
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
