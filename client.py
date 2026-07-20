import os
import webbrowser
from flask import Flask, jsonify, render_template, request
import requests
import speech_recognition as sr

app = Flask(__name__)  # Looks in ./templates/ by default

RENDER_API_URL = "https://agi-voice-app.onrender.com/agent"


@app.route("/")
def home():
    """Serves index.html to the user browser."""
    return render_template("index.html")


@app.route("/trigger", methods=["POST"])
def listen_and_execute():
    recognizer = sr.Recognizer()

    try:
        with sr.Microphone() as source:
            print("\n🔴 Listening... State your command")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

        print("🔄 Transcribing voice...")
        user_command = recognizer.recognize_google(audio)
        print(f'🎤 You said: "{user_command}"')

        # Send command to Cloud Router API
        print("🚀 Sending to Render AI Agent...")
        response = requests.post(
            RENDER_API_URL, json={"text_command": user_command}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("action") == "open_tab":
                target_url = data.get("url")
                print(f"🎯 Directive received! Opening: {target_url}")
                webbrowser.open_new_tab(target_url)
                return jsonify(
                    {
                        "status": "success",
                        "command_heard": user_command,
                        "message": f"Opened tab: {target_url}",
                    }
                )

            return jsonify(
                {
                    "status": "no_action",
                    "command_heard": user_command,
                    "message": "No action required.",
                }
            )

        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Agent couldn't process this command.",
                }
            ),
            400,
        )

    except sr.WaitTimeoutError:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Listening timed out. No speech detected.",
                }
            ),
            400,
        )
    except sr.UnknownValueError:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Could not understand the audio.",
                }
            ),
            400,
        )
    except Exception as e:
        return (
            jsonify({"status": "error", "error": f"Error occurred: {str(e)}"}),
            500,
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="127.0.0.1", port=port, debug=True)
