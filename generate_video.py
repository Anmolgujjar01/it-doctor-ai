import os
import json
import base64
import subprocess
import urllib.request
import urllib.error

# ============================================================
# IT Doctor AI - Day 1 Short + Gemini AI Voice
# ============================================================

# 1. Load video data
# ------------------------------------------------------------

with open("video_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

voiceover = data["voiceover"]
scenes = data["scenes"]

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY secret was not found. "
        "Add it in GitHub repository Actions secrets."
    )

if not voiceover or not scenes:
    raise RuntimeError(
        "video_data.json must contain voiceover and scenes."
    )


# 2. Generate AI voice using Gemini TTS
# ------------------------------------------------------------

print("Generating AI voice with Gemini...")

url = "https://generativelanguage.googleapis.com/v1beta/interactions"

payload = {
    "model": "gemini-3.1-flash-tts-preview",
    "input": voiceover,
    "response_format": {
        "type": "audio",
        "mime_type": "audio/wav"
    },
    "generation_config": {
        "speech_config": [
            {"voice": "Kore"}
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
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as e:
    error_body = e.read().decode(
        "utf-8", errors="replace"
    )

    print("Gemini API Error:", e.code)
    print(error_body)
    raise

except urllib.error.URLError as e:
    raise RuntimeError(
        f"Could not connect to Gemini API: {e}"
    ) from e


# 3. Extract audio from Gemini response
# ------------------------------------------------------------

audio_data = None

# Raw REST API response: steps -> model_output -> content -> audio
for step in reversed(result.get("steps", [])):
    if step.get("type") != "model_output":
        continue

    for item in reversed(step.get("content", [])):
        if item.get("type") == "audio" and item.get("data"):
            audio_data = item["data"]
            break

    if audio_data:
        break

# Also support an output_audio response, if present.
if not audio_data:
    output_audio = result.get("output_audio", {})

    if isinstance(output_audio, dict):
        audio_data = output_audio.get("data")

if not audio_data:
    print("Gemini response did not contain audio.")
    print(json.dumps(result, indent=2)[:10000])

    raise RuntimeError(
        "Gemini returned no audio data. "
        "Check the API response and model access."
    )

try:
    audio_bytes = base64.b64decode(
        audio_data, validate=True
    )
except Exception as e:
    raise RuntimeError(
        "Could not decode Gemini audio data."
    ) from e

if not audio_bytes:
    raise RuntimeError("Gemini returned empty audio.")

# We requested audio/wav, so save the returned WAV bytes directly.
with open("voice.wav", "wb") as f:
    f.write(audio_bytes)

# Check for a valid WAV header.
with open("voice.wav", "rb") as f:
    if f.read(4) != b"RIFF":
        raise RuntimeError(
            "The audio response is not a WAV file. "
            "Check Gemini response_format."
        )

print("AI voice generated successfully!")
print(f"Audio size: {len(audio_bytes)} bytes")


# 4. Create individual video scenes
# ------------------------------------------------------------

print("Creating video scenes...")

scene_files = []

for i, scene in enumerate(scenes):

    scene_file = f"scene_{i}.mp4"
    text_file = f"scene_text_{i}.txt"
    scene_files.append(scene_file)

    duration = 6.7 if i < len(scenes) - 1 else 6.5
    text = str(scene["text"])

    # A text file prevents apostrophes and commas in captions
    # from breaking FFmpeg's drawtext filter.
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(text)

    video_filter = (
        "drawtext="
        f"textfile={text_file}:"
        "expansion=none:"
        "fontcolor=white:"
        "fontsize=58:"
        "font=DejaVuSans-Bold:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2"
    )

    command = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x071A2B:s=1080x1920:d={duration}",
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        scene_file
    ]

    subprocess.run(command, check=True)

    print(f"Scene {i + 1}/{len(scenes)} created.")


# 5. Create concat file
# ------------------------------------------------------------

with open("concat.txt", "w", encoding="utf-8") as f:
    for scene_file in scene_files:
        absolute_path = os.path.abspath(scene_file)

        # Escape single quotes for FFmpeg concat syntax.
        absolute_path = absolute_path.replace("'", "'\\''")

        f.write(f"file '{absolute_path}'\n")


# 6. Join video scenes
# ------------------------------------------------------------

print("Joining video scenes...")

subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "concat.txt",
        "-c", "copy",
        "video_without_voice.mp4"
    ],
    check=True
)


# 7. Add AI voice to the video
# ------------------------------------------------------------

print("Adding AI voice to video...")

subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-i", "video_without_voice.mp4",
        "-i", "voice.wav",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        "it_doctor_ai_day1.mp4"
    ],
    check=True
)


# 8. Verify final video
# ------------------------------------------------------------

if (
    not os.path.exists("it_doctor_ai_day1.mp4")
    or os.path.getsize("it_doctor_ai_day1.mp4") == 0
):
    raise RuntimeError("Final video was not created successfully.")

print("")
print("======================================")
print(" IT DOCTOR AI VIDEO CREATED!")
print("======================================")
print("Video: it_doctor_ai_day1.mp4")
print("AI Voice: Generated")
print("======================================")
