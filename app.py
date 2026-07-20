import os
import re
import urllib.parse
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)

# Mock address book for name resolution
CONTACTS = {
    "sharanbalaji": "sharanbalaji@gmail.com",
    "sharan": "sharanbalaji@gmail.com",
    # Add more contact mappings here as needed
}

@app.route("/", methods=["GET"])
def home():
    """Serves the dashboard directly."""
    return render_template("index.html")

@app.route("/agent", methods=["POST"])
def ai_agent_router():
    """Processes text/voice commands and returns redirection URLs."""
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")
        
    command = data["text_command"].strip().lower()

    # -------------------------------------------------------------
    # 1. YOUTUBE HANDLER
    # -------------------------------------------------------------
    if "youtube" in command:
        # Check if user wants to play something specific
        # Example: "open youtube and search vijay songs and play"
        play_match = re.search(r"(?:search|play|find)\s+(.*?)(?:\s+and\s+play|\s+on\s+youtube|$)", command)
        
        # Alternative pattern extraction if match is empty
        query = None
        if play_match:
            query = play_match.group(1).replace("open youtube", "").replace("youtube", "").strip()
            
        if not query or query == "and":
            # Fallback cleaning if string regex didn't extract cleanly
            query = command.replace("open youtube", "").replace("search", "").replace("and play", "").replace("play", "").strip()

        if query:
            encoded_query = urllib.parse.quote_plus(query)
            # &autoplay=1 helps trigger auto-play on direct video hits / search results
            target_url = f"https://www.youtube.com/results?search_query={encoded_query}&autoplay=1"
        else:
            target_url = "https://www.youtube.com"

        return jsonify({"action": "open_tab", "url": target_url})

    # -------------------------------------------------------------
    # 2. GMAIL / EMAIL HANDLER
    # -------------------------------------------------------------
    elif "gmail" in command or "email" in command or "mail" in command:
        recipient_email = ""
        body_text = ""
        
        # Extract recipient ("to sharanbalaji" or "update to sharanbalaji")
        to_match = re.search(r"(?:to|update to)\s+([a-zA-Z0-9._%+-]+(?:\@[a-zA-Z0-9.-]+\.[a-zA-Z]{2 composition})?)", command)
        if to_match:
            raw_recipient = to_match.group(1).strip()
            # Check if name exists in contact list, otherwise use raw input/email
            recipient_email = CONTACTS.get(raw_recipient, raw_recipient)

        # Extract message body ("type ...", "body ...", or "saying ...")
        body_match = re.search(r"(?:type|write|saying|content)\s+(.*)", command)
        if body_match:
            body_text = body_match.group(1).strip()

        # Build Gmail direct compose deep-link
        if recipient_email or body_text:
            params = {
                "view": "cm",
                "fs": "1",
                "to": recipient_email,
                "body": body_text
            }
            target_url = f"https://mail.google.com/mail/?{urllib.parse.urlencode(params)}"
        else:
            target_url = "https://mail.google.com"

        return jsonify({"action": "open_tab", "url": target_url})

    # -------------------------------------------------------------
    # 3. DEFAULT FALLBACK (Google Search)
    # -------------------------------------------------------------
    encoded_command = urllib.parse.quote_plus(command)
    return jsonify({
        "action": "open_tab",
        "url": f"https://www.google.com/search?q={encoded_command}"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
