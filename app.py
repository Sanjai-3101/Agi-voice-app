import os, re, urllib.parse, urllib.request
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)
CONTACTS = {"sharanbalaji": "sharanbalaji@gmail.com", "sharan balaji": "sharanbalaji@gmail.com", "sharan": "sharanbalaji@gmail.com"}

def get_first_youtube_video_id(query):
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8")
        ids = re.findall(r"\"videoId\":\"([^\"]+)\"", html)
        return ids[0] if ids else None
    except Exception:
        return None

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/agent", methods=["POST"])
def ai_agent_router():
    data = request.get_json(silent=True)
    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")

    command = data["text_command"].strip().lower()

    if "youtube" in command:
        query = command
        for p in ["open youtube and search", "open youtube and play", "open youtube", "search for", "search", "and play", "play", "on youtube"]:
            query = query.replace(p, "")
        query = query.strip()
        if query:
            vid = get_first_youtube_video_id(query)
            target = f"https://www.youtube.com/watch?v={vid}&autoplay=1" if vid else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        else:
            target = "https://www.youtube.com"
        return jsonify({"action": "open_tab", "url": target})

    elif any(kw in command for kw in ["gmail", "email", "mail"]):
        recipient, body = "", ""
        for name, email in CONTACTS.items():
            if name in command:
                recipient = email
                break

        if not recipient:
            to_match = re.search(r"(?:update to|to)\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(?:and|type|write|saying|with|$))", command)
            if to_match:
                clean = to_match.group(1).strip().replace(" at ", "@").replace(" dot ", ".").replace(" ", "")
                recipient = CONTACTS.get(clean, clean.replace("gmail.com", "@gmail.com") if "gmail.com" in clean and "@" not in clean else clean)

        body_match = re.search(r"(?:type|write|saying|content)\s+(.*)", command)
        if body_match and body_match.group(1).strip():
            b = body_match.group(1).strip()
            body = b[0].upper() + b[1:]

        recipient = recipient.replace(" ", "")
        if recipient or body:
            target = f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={urllib.parse.quote(recipient)}&body={urllib.parse.quote(body)}"
        else:
            target = "https://mail.google.com"
        return jsonify({"action": "open_tab", "url": target})

    return jsonify({"action": "open_tab", "url": f"https://www.google.com/search?q={urllib.parse.quote_plus(command)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
