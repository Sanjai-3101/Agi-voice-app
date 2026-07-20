import os, re, urllib.parse, urllib.request
from flask import Flask, abort, jsonify, render_template, request

app = Flask(__name__)

def get_vid(q):
    try:
        req = urllib.request.Request(f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}", headers={"User-Agent": "Mozilla/5.0"})
        ids = re.findall(r"\"videoId\":\"([^\"]+)\"", urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
        return ids[0] if ids else None
    except Exception: return None

@app.route("/", methods=["GET"])
def home(): return render_template("index.html")

@app.route("/agent", methods=["POST"])
def ai_agent_router():
    d = request.get_json(silent=True)
    if not d or "text_command" not in d: abort(400, description="Missing 'text_command' in request body")
    
    # Normalize command text to reduce speech-to-text misspellings
    cmd = d["text_command"].strip().lower()

    if "youtube" in cmd:
        q = cmd
        for p in ["open youtube and search", "open youtube and play", "open youtube", "search for", "search", "and play", "play", "on youtube"]:
            q = q.replace(p, "")
        q = q.strip()
        target = "https://www.youtube.com" if not q else (
            f"https://www.youtube.com/watch?v={vid}&autoplay=1" if (vid := get_vid(q)) 
            else f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
        )

    elif any(k in cmd for k in ["gmail", "email", "mail", "message"]):
        to, body = "", ""

        # Flexible pattern matching for names/recipients
        # Handles "send to", "update to", "mail to", "message to", or just "to"
        to_match = re.search(r"(?:update|send|mail|message)?\s*to\s+([a-zA-Z0-9._%+\s]+?)(?=\s+(?:and|type|write|saying|with|content|that|message|$))", cmd)
        if to_match:
            raw_to = to_match.group(1).strip()
            # Fix common spoken email errors (e.g., "dot", "at", spaces)
            clean_to = raw_to.replace(" at ", "@").replace(" dot ", ".").replace(" ", "")
            to = clean_to if "@" in clean_to else f"{clean_to}@gmail.com"

        # Flexible pattern matching for body/message text
        body_match = re.search(r"(?:type|write|saying|content|message|that)\s+(.*)", cmd)
        if body_match and (b := body_match.group(1).strip()):
            body = b[0].upper() + b[1:]

        target = f"https://mail.google.com/mail/u/0/?view=cm&fs=1&to={urllib.parse.quote(to)}&body={urllib.parse.quote(body)}" if to or body else "https://mail.google.com"

    else:
        target = f"https://www.google.com/search?q={urllib.parse.quote_plus(cmd)}"

    return jsonify({"action": "open_tab", "url": target})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
