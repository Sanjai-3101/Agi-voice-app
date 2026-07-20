import os
import re
import urllib.parse
import urllib.request
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)

# Map spoken names to email addresses (use lowercase)
CONTACTS = {
    "sharanbalaji": "sharanbalaji@gmail.com",
    "sharan balaji": "sharanbalaji@gmail.com",
    "sharan": "sharanbalaji@gmail.com",
}


def get_first_youtube_video_id(search_query):
    """Searches YouTube in the background and returns the first result's video ID."""
    try:
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")

        video_ids = re.findall(r"\"videoId\":\"([^\"]+)\"", html)
        if video_ids:
            return video_ids[0]
    except Exception as e:
        print(f"Error fetching YouTube video ID: {e}")
    return None


@app.route("/", methods=["GET"])
def home():
    """Serves the dashboard directly from templates/index.html."""
    return render_template("index.html")


@app.route("/agent", methods=["POST"])
def ai_agent_router():
    """Processes text/voice commands and returns target redirection URLs."""
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")

    command = data["text_command"].strip().lower()

    # =============================================================
    # 1. YOUTUBE ROUTER (Search & Direct Play)
    # =============================================================
    if "youtube" in command:
        query = command
        # Strip common filler/trigger words to isolate the subject
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
            # Retrieve video ID so YouTube opens directly into playback
            video_id = get_first_youtube_video_id(query)
            if video_id:
                target_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
            else:
                encoded_query = urllib.parse.quote_plus(query)
                target_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        else:
            target_url = "https://www.youtube.com"

        return jsonify({"action": "open_tab", "url": target_url})

    # =============================================================
    # 2. GMAIL ROUTER (Autofill Contact & Body)
    # =============================================================
    elif any(kw in command for kw in ["gmail", "email", "mail"]):
        recipient_email = ""
        body_text = ""

        # Step A: Check if any key in CONTACTS matches the spoken string directly
        for name, email in CONTACTS.items():
            if name in command:
                recipient_email = email
                break

        # Step B: Extract recipient using regex if not found in CONTACTS
        if not recipient_email:
            to_match = re.search(
                r"(?:update to|to)\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(?:and|type|write|saying|with|$))",
                command,
            )
            if to_match:
                raw_recipient = to_match.group(1).strip()

                # Clean speech recognition artifacts ("sharan balaji gmail.com" -> "sharanbalaji@gmail.com")
                clean_recipient = (
                    raw_recipient.replace(" at ", "@")
                    .replace(" dot ", ".")
                    .replace(" ", "")
                )

                if clean_recipient in CONTACTS:
                    recipient_email = CONTACTS[clean_recipient]
                else:
                    if "gmail.com" in clean_recipient and "@" not in clean_recipient:
                        clean_recipient = clean_recipient.replace("gmail.com", "@gmail.com")
                    recipient_email = clean_recipient

        # Step C: Extract email message body
        body_match = re.search(r"(?:type|write|saying|content)\s+(.*)", command)
        if body_match:
            body_text = body_match.group(1).strip()
            if body_text:
                body_text = body_text[0].upper() + body_text[1:]

        # Step D: Final pass to guarantee zero spaces in email string
        if recipient_email:
            recipient_email = recipient_email.replace(" ", "")

        # Step E: Construct direct Gmail compose URL
        if recipient_email or body_text:
            encoded_to = urllib.parse.quote(recipient_email)
            encoded_body = urllib.parse.quote(body_text)
            target_url = (
                f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={encoded_to}&body={encoded_body}"
            )
        else:
            target_url = "https://mail.google.com"

        return jsonify({"action": "open_tab", "url": target_url})

    # =============================================================
    # 3. FALLBACK (Google Search)
    # =============================================================
    encoded_command = urllib.parse.quote_plus(command)
    return jsonify({
        "action": "open_tab",
        "url": f"https://www.google.com/search?q={encoded_command}"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
