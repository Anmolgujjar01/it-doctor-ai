import os
import json
import base64
import subprocess
import urllib.request
import urllib.error

# ============================================================
# IT Doctor AI - Day 1 Short + AI Voice
# ============================================================

# ------------------------------------------------------------
# 1. Load video data
# ------------------------------------------------------------

with open("video_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

voiceover = data["voiceover"]
scenes = data["scenes"]

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY secret was not found.")


# ------------------------------------------------------------
# 2. Gemini TTS
# ------------------------------------------------------------

print("Generating AI voice...")

url = "https://generativelanguage.googleapis.com/v1beta/interactions"

payload = {
    "model": "gemini-3.1-flash-tts-preview",
    "input": voiceover,
    "response_format": {
        "type": "audio"
    },
    "generation_config": {
        "speech_config": [
            {
                "voice": "Kore"
            }
        ]
    }
}

request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    },
    method="POST"
)

try:
    with urllib.request.urlopen(request) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as e:
    error_body = e.read().decode(
        "utf-8",
        errors="replace"
    )

    print("Gemini API Error:")
    print(error_body)

    raise


# ------------------------------------------------------------
# 3. Get audio
# ------------------------------------------------------------

if "output_audio" not in result:
    print("Gemini response:")
    print(json.dumps(result, indent=2))

    raise RuntimeError(
        "Gemini did not return audio."
    )

audio_data = result["output_audio"]["data"]

if not audio_data:
    raise RuntimeError(
        "Gemini returned empty audio."
    )

with open("voice.wav", "wb") as f:
    f.write(
        base64.b64decode(audio_data)
    )

print("AI voice generated successfully!")


# ------------------------------------------------------------
# 4. Create individual video scenes
# ------------------------------------------------------------

print("Creating scenes...")

scene_files = []

for i, scene in enumerate(scenes):

    scene_file = f"scene_{i}.mp4"
    scene_files.append(scene_file)

    duration = 6.7 if i < len(scenes) - 1 else 6.5

    text = scene["text"]

    text = (
        text.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace(":", "\\:")
            .replace(",", "\\,")
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",

        "-i",
        f"color=c=0x071A2B:s=1080x1920:d={duration}",

        "-vf",
        (
            "drawtext="
            "fontcolor=white:"
            "fontsize=58:"
            "font=DejaVuSans-Bold:"
            "x=(w-text_w)/2:"
            "y=(h-text_h)/2:"
            f"text='{text}'"
        ),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-pix_fmt",
        "yuv420p",

        "-an",

        scene_file
    ]

    subprocess.run(
        command,
        check=True
    )

    print(
        f"Scene {i + 1} created."
    )


# ------------------------------------------------------------
# 5. Create concat file
# ------------------------------------------------------------

with open(
    "concat.txt",
    "w",
    encoding="utf-8"
) as f:

    for scene_file in scene_files:

        absolute_path = os.path.abspath(
            scene_file
        )

        f.write(
            f"file '{absolute_path}'\n"
        )


# ------------------------------------------------------------
# 6. Join scenes
# ------------------------------------------------------------

print("Joining scenes...")

subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-f",
        "concat",

        "-safe",
        "0",

        "-i",
        "concat.txt",

        "-c",
        "copy",

        "video_without_voice.mp4"
    ],
    check=True
)


# ------------------------------------------------------------
# 7. Add AI voice
# ------------------------------------------------------------

print("Adding AI voice...")

subprocess.run(
    [
        "ffmpeg",
        "-y",

        "-i",
        "video_without_voice.mp4",

        "-i",
        "voice.wav",

        "-map",
        "0:v:0",

        "-map",
        "1:a:0",

        "-c:v",
        "copy",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-shortest",

        "-movflags",
        "+faststart",

        "it_doctor_ai_day1.mp4"
    ],
    check=True
)


# ------------------------------------------------------------
# 8. Finished
# ------------------------------------------------------------

print("")
print("======================================")
print(" IT DOCTOR AI VIDEO CREATED!")
print("======================================")
print("")
print("Video: it_doctor_ai_day1.mp4")
print("AI Voice: SUCCESS")
print("======================================")
