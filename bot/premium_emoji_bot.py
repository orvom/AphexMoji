#!/usr/bin/env python3
"""Telegram bot: reply with the custom_emoji_id ("code") of any premium
(custom) emoji sent to it.

Uses only the Python standard library (urllib) so it needs no extra
dependencies beyond a working internet connection to api.telegram.org.

Configuration:
    Set the bot token via the BOT_TOKEN environment variable, e.g.:

        export BOT_TOKEN="123456:ABC-your-token"
        python3 bot/premium_emoji_bot.py

    Never hardcode the token in source control.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.telegram.org"
POLL_TIMEOUT = 30


def api_call(token: str, method: str, params: dict | None = None, timeout: int = 35) -> dict:
    url = f"{API_ROOT}/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode()
    request = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def extract_entity_text(text: str, offset: int, length: int) -> str:
    # Telegram entity offsets/lengths are in UTF-16 code units, not
    # Python string indices, so slice via a UTF-16 round trip.
    encoded = text.encode("utf-16-le")
    chunk = encoded[offset * 2:(offset + length) * 2]
    return chunk.decode("utf-16-le")


def find_custom_emoji(message: dict) -> list[tuple[str, str]]:
    text = message.get("text") or message.get("caption") or ""
    entities = message.get("entities") or message.get("caption_entities") or []
    found = []
    for entity in entities:
        if entity.get("type") == "custom_emoji":
            emoji = extract_entity_text(text, entity["offset"], entity["length"])
            found.append((emoji, entity["custom_emoji_id"]))
    return found


def handle_message(token: str, message: dict) -> None:
    chat_id = message["chat"]["id"]

    if message.get("text", "").startswith("/start"):
        api_call(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "Send me a message containing a premium (custom) emoji "
                    "and I'll reply with its code (custom_emoji_id).",
        })
        return

    matches = find_custom_emoji(message)
    if not matches:
        return

    lines = [f"{emoji} -> `{custom_emoji_id}`" for emoji, custom_emoji_id in matches]
    api_call(token, "sendMessage", {
        "chat_id": chat_id,
        "text": "\n".join(lines),
        "parse_mode": "Markdown",
    })


def run(token: str) -> None:
    me = api_call(token, "getMe")
    if not me.get("ok"):
        raise RuntimeError(f"getMe failed: {me}")
    print(f"Logged in as @{me['result']['username']}", flush=True)

    offset = 0
    while True:
        try:
            updates = api_call(
                token,
                "getUpdates",
                {"offset": offset, "timeout": POLL_TIMEOUT},
                timeout=POLL_TIMEOUT + 10,
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"Network error, retrying: {exc}", file=sys.stderr, flush=True)
            time.sleep(5)
            continue

        if not updates.get("ok"):
            print(f"getUpdates error: {updates}", file=sys.stderr, flush=True)
            time.sleep(5)
            continue

        for update in updates["result"]:
            offset = update["update_id"] + 1
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue
            try:
                handle_message(token, message)
            except Exception as exc:  # keep the loop alive on per-message errors
                print(f"Error handling message: {exc}", file=sys.stderr, flush=True)


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Set the BOT_TOKEN environment variable first.", file=sys.stderr)
        sys.exit(1)
    run(token)


if __name__ == "__main__":
    main()
