import os
import re
import urllib.parse
import urllib.request
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)

# Add your contacts here (lowercase keys)
CONTACTS = {
    "sharanbalaji": "sharanbalaji@gmail.com",
    "sharan balaji": "sharanbalaji@gmail.com",
    "sharan": "sharanbalaji@gmail.com",
}


def get_first_youtube_video_id(search_query):
    """Searches YouTube and returns the video ID of the first result."""
    try:
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        
        # Extract the first watch video ID from YouTube HTML
        video_ids = re.findall(r"\"videoId\":\"([^\"]+)\"", html)
        if video_ids:
            return video_ids[0]
    except Exception as e:
        print(f"Error fetching YouTube video ID: {e}")
    return None


@app.route("/", methods=["GET"])
def home():
    """Serves the dashboard directly."""
    return render_template("index.html")


@app.route("/agent", methods=["POST"])
def ai_agent_router():
    """Processes text/voice commands and returns redirection target URLs."""
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")

    command = data["text_command"].strip().lower()

    # -------------------------------------------------------------
    # 1. YOUTUBE HANDLER (Search & Direct Play)
    # -------------------------------------------------------------
    if "youtube" in command:
        # Clean out command keywords to leave the raw search query
        query = command
        for phrase in [
            "open youtube and search",
            "open youtube and play",
            "open youtube",
            "search for",
            "search",
            "and play",
            "play",
            "on youtube",
        ]:
            query = query.replace(phrase, "")
        
        query = query.strip()

        if query:
            # Get actual top video ID to enable true autoplay
            video_id = get_first_youtube_video_id(query)
            if video_id:
                target_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
            else:
                # Fallback to search results page if lookup fails
                encoded_query = urllib.parse.quote_plus(query)
                target_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        else:
            target_url = "https://www.youtube.com"

        return jsonify({"action": "open_tab", "url": target_url})

    # -------------------------------------------------------------
    # 2. GMAIL HANDLER (Compose with To & Body)
    # -------------------------------------------------------------
    elif "gmail" in command or "email" in command or "mail" in command:
        recipient_email = ""
        body_text = ""

        # Extract Recipient: Look after "to" or "update to"
        to_match = re.search(r"(?:update to|to)\s+([a-zA-Z0-9_\s]+?)(?=\s+(?:and|type|write|saying|with|$))", command)
        if to_match:
            raw_recipient = to_match.group(1).strip().lower()
            
            # Lookup in contact dictionary, else use as raw email address
            if raw_recipient in CONTACTS:
                recipient_email = CONTACTS[raw_recipient]
            elif "@" in raw_recipient:
                recipient_email = raw_recipient
            else:
                # Fallback check if parts of the name match contacts
                for name, email in CONTACTS.items():
                    if name in raw_recipient:
                        recipient_email = email
                        break

        # Extract Message Body: Look after "type", "write", "saying", or "content"
        body_match = re.search(r"(?:type|write|saying|content)\s+(.*)", command)
        if body_match:
            body_text = body_match.group(1).strip()
            # Capitalize first letter of the message body
            if body_text:
                body_text = body_text[0].upper() + body_text[1:]

        # Build Gmail direct compose URL
        if recipient_email or body_text:
            params = {
                "view": "cm",
                "fs": "1",
                "to": recipient_email,
                "body": body_text,
            }
            target_url = f"https://mail.google.com/mail/?{urllib.parse.urlencode(params)}"
        else:
            target_url = "https://mail.google.com"

        return jsonify({"action": "open_tab", "url": target_url})

    # -------------------------------------------------------------
    # 3. DEFAULT FALLBACK
    # -------------------------------------------------------------
    encoded_command = urllib.parse.quote_plus(command)
    return jsonify({
        "action": "open_tab",
        "url": f"https://www.google.com/search?q={encoded_command}"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
