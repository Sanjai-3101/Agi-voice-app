import os
import re
import json
import urllib.parse

import requests
from flask import Flask, abort, jsonify, render_template, request

# Flask automatically looks inside the 'templates/' folder for index.html
app = Flask(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Get a free key at https://console.cloud.google.com/apis/library/youtube.googleapis.com
# and set it as an environment variable before running the app.
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

# Name -> email lookup used to resolve spoken names ("sharanbalaji") into a
# real address for Gmail's compose URL. Gmail's compose link needs an actual
# email address, so a bare name won't resolve unless it's mapped here.
# You can also supply this as a JSON object in the CONTACTS_JSON env var,
# e.g. CONTACTS_JSON='{"sharanbalaji": "sharan.balaji@example.com"}'
DEFAULT_CONTACTS = {
    "sharanbalaji": "sharanbalaji@example.com",
}
try:
    CONTACTS = {**DEFAULT_CONTACTS, **json.loads(os.environ.get("CONTACTS_JSON", "{}"))}
except json.JSONDecodeError:
    CONTACTS = DEFAULT_CONTACTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_youtube_query(raw_command: str) -> str | None:
    """Pull the search phrase out of a YouTube voice command.

    Handles things like:
      "open youtube and search vijay songs and play"
      "youtube search for lofi beats"
      "search anirudh songs on youtube and play it"
    """
    command = raw_command.lower()

    match = re.search(
        r"(?:search|find|look\s?up)(?:\s+for)?\s+(.+)",
        command,
    )
    if not match:
        return None

    query = match.group(1)

    # Strip trailing "and play", "play it", "on/in youtube" noise.
    query = re.sub(r"\b(and\s+)?play(\s+it)?\b.*$", "", query)
    query = re.sub(r"\b(on|in)\s+youtube\b", "", query)
    query = query.strip(" .!?")

    return query or None


def extract_gmail_fields(raw_command: str):
    """Pull the recipient and body text out of a Gmail voice command.

    Handles things like:
      "open gmail and update to sharanbalaji and type You have completed your assignment"
      "gmail to john and type see you tomorrow"

    Returns (to_name_or_email, body_text) — either may be None if not found.
    Case is preserved for the extracted body/name; only keyword matching is
    done case-insensitively.
    """
    lowered = raw_command.lower()

    to_name = None
    to_match = re.search(r"\bto\s+(.+?)(?:\s+and\s+type\b|\s+type\b|$)", lowered)
    if to_match:
        to_name = to_match.group(1).strip(" .!?")

    body_text = None
    type_match = re.search(r"\btype\s+(.+)$", raw_command, re.IGNORECASE)
    if type_match:
        body_text = type_match.group(1).strip(" .!?")

    return to_name, body_text


def resolve_email(name_or_email: str) -> str:
    """Map a spoken name to a real email address, or pass through if it
    already looks like one."""
    if not name_or_email:
        return ""
    candidate = name_or_email.strip()
    if "@" in candidate:
        return candidate
    key = candidate.lower().replace(" ", "")
    return CONTACTS.get(key, candidate)  # falls back to raw text if unknown


def youtube_top_video_url(query: str) -> str:
    """Return the direct watch URL for the top search result, using the
    YouTube Data API. Falls back to a search-results page if no API key is
    configured or the lookup fails."""
    fallback = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"

    if not YOUTUBE_API_KEY:
        return fallback

    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "id",
                "q": query,
                "type": "video",
                "maxResults": 1,
                "key": YOUTUBE_API_KEY,
            },
            timeout=5,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return fallback
        video_id = items[0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
    except (requests.RequestException, KeyError, ValueError):
        return fallback


def gmail_compose_url(to_email: str, body: str, subject: str = "") -> str:
    """Build a Gmail compose link. This only opens a pre-filled draft —
    there's no way to trigger an actual send via URL, so the user always
    has to review and hit Send themselves."""
    params = {"view": "cm", "fs": "1"}
    if to_email:
        params["to"] = to_email
    if subject:
        params["su"] = subject
    if body:
        params["body"] = body
    return "https://mail.google.com/mail/?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    """Serves the dashboard directly from Render."""
    return render_template("index.html")


@app.route("/agent", methods=["POST"])
def ai_agent_router():
    """Processes text/voice commands and returns redirection target URLs."""
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")

    raw_command = data["text_command"].strip()
    command = raw_command.lower()

    # ---------------- YouTube: search + play ----------------
    if "youtube" in command:
        query = extract_youtube_query(raw_command)
        if query:
            target_url = youtube_top_video_url(query)
        else:
            target_url = "https://www.youtube.com"
        return jsonify({"action": "open_tab", "url": target_url})

    # ---------------- Gmail: auto-compose (never sends) ----------------
    if "gmail" in command or "email" in command:
        to_name, body_text = extract_gmail_fields(raw_command)
        to_email = resolve_email(to_name) if to_name else ""
        target_url = gmail_compose_url(to_email, body_text or "")
        return jsonify({"action": "open_tab", "url": target_url})

    # ---------------- Fallback to Google Search ----------------
    encoded_command = urllib.parse.quote_plus(command)
    return jsonify(
        {
            "action": "open_tab",
            "url": f"https://www.google.com/search?q={encoded_command}",
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
