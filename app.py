import os
import urllib.parse
from flask import Flask, abort, jsonify, render_template, request

# Flask automatically looks inside the 'templates/' folder for index.html
app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    """Serves the dashboard directly from Render."""
    return render_template("index.html")


@app.route("/agent", methods=["POST"])
def ai_agent_router():
    """Processes text commands and returns redirection target URLs."""
    data = request.get_json(silent=True)

    if not data or "text_command" not in data:
        abort(400, description="Missing 'text_command' in request body")

    command = data["text_command"].strip().lower()

    APP_MAPPING = {
        "youtube": (
            "https://www.youtube.com/results?search_query={query}",
            "https://www.youtube.com",
        ),
        "amazon": (
            "https://www.amazon.com/s?k={query}",
            "https://www.amazon.com",
        ),
        "gmail": (
            "https://mail.google.com/mail/u/0/#search/{query}",
            "https://mail.google.com",
        ),
        "email": (
            "https://mail.google.com/mail/u/0/#search/{query}",
            "https://mail.google.com",
        ),
        "netflix": (
            "https://www.netflix.com/search?q={query}",
            "https://www.netflix.com",
        ),
        "spotify": (
            "https://open.spotify.com/search/{query}",
            "https://open.spotify.com",
        ),
        "google": (
            "https://www.google.com/search?q={query}",
            "https://www.google.com",
        ),
        "wikipedia": (
            "https://en.wikipedia.org/wiki/Special:Search?search={query}",
            "https://en.wikipedia.org",
        ),
        "github": (
            "https://github.com/search?q={query}",
            "https://github.com",
        ),
        "twitter": ("https://x.com/search?q={query}", "https://x.com"),
        "x": ("https://x.com/search?q={query}", "https://x.com"),
    }

    triggers = ["search for", "search", "find", "look up"]

    for app_name, (search_template, fallback_url) in APP_MAPPING.items():
        if app_name in command:
            search_query = None

            for trigger in triggers:
                if trigger in command:
                    parts = command.split(trigger, 1)
                    if len(parts) > 1 and parts[1].strip():
                        raw_query = (
                            parts[1]
                            .strip()
                            .replace(f"in {app_name}", "")
                            .replace(f"on {app_name}", "")
                            .strip()
                        )
                        if raw_query:
                            search_query = raw_query
                            break

            if not search_query:
                cleaned = (
                    command.replace("open", "")
                    .replace("and", "")
                    .replace(app_name, "")
                    .strip()
                )
                if cleaned:
                    search_query = cleaned

            if search_query:
                encoded_query = urllib.parse.quote_plus(search_query)
                target_url = search_template.format(query=encoded_query)
            else:
                target_url = fallback_url

            return jsonify({"action": "open_tab", "url": target_url})

    # Fallback to Google Search
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
