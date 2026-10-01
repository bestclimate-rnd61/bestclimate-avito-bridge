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
PRELAUNCH_MODE = os.getenv("BUFFER_PRELAUNCH_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}


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
            "User-Agent": "sitkoalex-ai-business-buffer-bridge/1.3",
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
    data = gql("""
        query GetAccount {
          account { organizations { id name } }
        }
    """)
    orgs = ((data.get("account") or {}).get("organizations") or [])
    if not orgs:
        raise RuntimeError("No Buffer organizations found")

    instagram_channels = []
    for org in orgs:
        org_id = org["id"]
        channel_data = gql("""
            query GetChannels($orgId: OrganizationId!) {
              channels(input: { organizationId: $orgId }) { id name service }
            }
        """, {"orgId": org_id})
        for channel in channel_data.get("channels") or []:
            service = str(channel.get("service") or "").strip().lower()
            name = str(channel.get("name") or "").strip().lower()
            if service == "instagram":
                instagram_channels.append((org_id, channel))
                if name == TARGET_CHANNEL:
                    return org_id, channel["id"]

    if len(instagram_channels) == 1:
        org_id, channel = instagram_channels[0]
        return org_id, channel["id"]
    raise RuntimeError(f"Instagram channel '{TARGET_CHANNEL}' not found")


def existing_posts(org_id: str, channel_id: str) -> dict[str, dict]:
    data = gql("""
        query GetPosts($orgId: OrganizationId!, $channelId: ChannelId!) {
          posts(
            first: 100
            input: {
              organizationId: $orgId
              filter: { channelIds: [$channelId] }
              sort: [{ field: createdAt, direction: desc }]
            }
          ) {
            edges { node { id text status dueAt channelId } }
          }
        }
    """, {"orgId": org_id, "channelId": channel_id})
    edges = (((data.get("posts") or {}).get("edges")) or [])
    posts = {}
    for edge in edges:
        node = edge.get("node") or {}
        text = str(node.get("text") or "").strip()
        if text:
            posts[text] = node
            print("BUFFER_BRIDGE_EXISTING " + json.dumps({
                "post_id": node.get("id"),
                "status": node.get("status"),
                "due_at": node.get("dueAt"),
                "text_preview": text[:120]
            }, ensure_ascii=False), flush=True)
    return posts


def item_is_prelaunch_draft(item: dict) -> bool:
    return PRELAUNCH_MODE and not bool(item.get("publish_during_prelaunch"))


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

    draft_now = item_is_prelaunch_draft(item)
    mode = "addToQueue" if draft_now else str(item.get("mode") or "shareNow")
    input_data = {
        "text": caption,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": mode,
        "saveToDraft": draft_now,
        "assets": [{media_kind: {"url": media_url}}],
        "metadata": {
            "instagram": {
                "type": content_type,
                "shouldShareToFeed": bool(item.get("share_to_feed", content_type != "story")),
            }
        },
    }

    data = gql("""
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess { post { id text dueAt status channelId } }
            ... on MutationError { message }
          }
        }
    """, {"input": input_data})
    result = data.get("createPost") or {}
    if result.get("message"):
        raise RuntimeError(result["message"])
    post = result.get("post")
    if not post:
        raise RuntimeError(f"Unexpected createPost response: {result}")
    return post


def edit_existing(post_id: str, input_patch: dict) -> dict:
    payload = {"id": post_id, **input_patch}
    data = gql("""
        mutation EditPost($input: EditPostInput!) {
          editPost(input: $input) {
            ... on PostActionSuccess { post { id text dueAt status channelId } }
            ... on MutationError { message }
          }
        }
    """, {"input": payload})
    result = data.get("editPost") or {}
    if result.get("message"):
        raise RuntimeError(result["message"])
    post = result.get("post")
    if not post:
        raise RuntimeError(f"Unexpected editPost response: {result}")
    return post


def share_existing_now(post_id: str) -> dict:
    return edit_existing(post_id, {"mode": "shareNow", "schedulingType": "automatic", "saveToDraft": False})


def move_existing_to_draft(post_id: str) -> dict:
    return edit_existing(post_id, {"saveToDraft": True})


def main() -> int:
    print("BUFFER_BRIDGE_START " + json.dumps({"prelaunch_mode": PRELAUNCH_MODE}), flush=True)
    if not QUEUE_FILE.exists():
        print(f"BUFFER_BRIDGE_NO_QUEUE file={QUEUE_FILE}", flush=True)
        return 0

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    if not isinstance(queue, list):
        raise RuntimeError("Queue file must contain a JSON array")

    org_id, channel_id = discover_target()
    existing = existing_posts(org_id, channel_id)
    added = skipped = errors = promoted = paused = 0

    for item in queue:
        if added + promoted + paused >= MAX_ADD_PER_RUN:
            break
        if not isinstance(item, dict) or not item.get("approved"):
            continue
        caption = str(item.get("caption") or "").strip()
        if not caption:
            skipped += 1
            continue

        current = existing.get(caption)
        draft_now = item_is_prelaunch_draft(item)
        if current:
            status = str(current.get("status") or "").lower()
            if status == "sent":
                skipped += 1
                continue
            if draft_now:
                if status == "draft":
                    skipped += 1
                    continue
                try:
                    post = move_existing_to_draft(str(current.get("id")))
                    paused += 1
                    print("BUFFER_BRIDGE_MOVED_TO_DRAFT " + json.dumps({
                        "queue_id": item.get("id"),
                        "post_id": post.get("id"),
                        "status": post.get("status"),
                        "due_at": post.get("dueAt")
                    }, ensure_ascii=False), flush=True)
                except Exception as exc:
                    errors += 1
                    print("BUFFER_BRIDGE_ITEM_ERROR " + json.dumps({
                        "queue_id": item.get("id"), "error": str(exc)[:500]
                    }, ensure_ascii=False), flush=True)
                    break
                continue
            try:
                post = share_existing_now(str(current.get("id")))
                promoted += 1
                print("BUFFER_BRIDGE_SHARE_NOW " + json.dumps({
                    "queue_id": item.get("id"),
                    "post_id": post.get("id"),
                    "status": post.get("status"),
                    "due_at": post.get("dueAt")
                }, ensure_ascii=False), flush=True)
            except Exception as exc:
                errors += 1
                print("BUFFER_BRIDGE_ITEM_ERROR " + json.dumps({
                    "queue_id": item.get("id"), "error": str(exc)[:500]
                }, ensure_ascii=False), flush=True)
                break
            continue

        try:
            post = create_post(channel_id, item)
            existing[caption] = post
            added += 1
            print("BUFFER_BRIDGE_ADDED " + json.dumps({
                "queue_id": item.get("id"),
                "post_id": post.get("id"),
                "status": post.get("status"),
                "due_at": post.get("dueAt"),
                "prelaunch_mode": PRELAUNCH_MODE,
                "publish_during_prelaunch": bool(item.get("publish_during_prelaunch"))
            }, ensure_ascii=False), flush=True)
        except Exception as exc:
            errors += 1
            print("BUFFER_BRIDGE_ITEM_ERROR " + json.dumps({
                "queue_id": item.get("id"), "error": str(exc)[:500]
            }, ensure_ascii=False), flush=True)
            break

    print("BUFFER_BRIDGE_DONE " + json.dumps({
        "channel": TARGET_CHANNEL,
        "prelaunch_mode": PRELAUNCH_MODE,
        "added": added,
        "promoted": promoted,
        "paused": paused,
        "skipped": skipped,
        "errors": errors
    }, ensure_ascii=False), flush=True)
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
