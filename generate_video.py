import os
import json
import base64
import wave
import subprocess
import urllib.request
import urllib.error

# ============================================================
# IT DOCTOR AI - VIDEO GENERATOR WITH GEMINI TTS
# ============================================================

OUTPUT_VIDEO = "it_doctor_ai_day1.mp4"
AUDIO_FILE = "voice.wav"
TEMP_VIDEO = "video_without_voice.mp4"

# 1. CHECK INPUT FILES
# ------------------------------------------------------------

if not os.path.isfile("video_data.json"):
    raise FileNotFoundError("video_data.json was not found.")

with open("video_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

voiceover = data.get("voiceover")
scenes = data.get("scenes")

if not isinstance(voiceover, str) or not voiceover.strip():
    raise ValueError("video_data.json needs a non-empty voiceover.")

if not isinstance(scenes, list) or not scenes:
    raise ValueError("video_data.json needs a non-empty scenes list.")

for i, scene in enumerate(scenes):
    if not isinstance(scene, dict) or not scene.get("text"):
        raise ValueError(f"Scene {i + 1} needs a text field.")

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing from GitHub Actions secrets."
    )


# 2. GENERATE AI VOICE WITH GEMINI
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
        result = json.loads(response.read().decode("utf-8"))

except urllib.error.HTTPError as e:
    print(f"Gemini API error: HTTP {e.code}")
    print(e.read().decode("utf-8", errors="replace"))
    raise

except urllib.error.URLError as e:
    raise RuntimeError(f"Gemini connection failed: {e}") from e


# 3. EXTRACT AUDIO
# ------------------------------------------------------------

audio_data = None

# Standard Interactions API response
output_audio = result.get("output_audio")

if isinstance(output_audio, dict):
    audio_data = output_audio.get("data")

# Fallback for responses containing audio in output steps
if not audio_data:
    for step in reversed(result.get("steps", [])):
        for item in reversed(step.get("content", [])):
            if item.get("type") == "audio" and item.get("data"):
                audio_data = item["data"]
                break
        if audio_data:
            break

if not audio_data:
    print("Gemini response:")
    print(json.dumps(result, indent=2)[:10000])
    raise RuntimeError("Gemini response contained no audio data.")

try:
    pcm_data = base64.b64decode(audio_data, validate=True)
except Exception as e:
    raise RuntimeError("Could not decode Gemini audio.") from e

if not pcm_data:
    raise RuntimeError("Gemini returned empty audio.")

# Gemini TTS default audio: 24 kHz, mono, 16-bit PCM.
# Add a WAV header so FFmpeg can read the audio correctly.
with wave.open(AUDIO_FILE, "wb") as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(24000)
    wav.writeframes(pcm_data)

print("AI voice generated successfully!")


# 4. CREATE VIDEO SCENES
# ------------------------------------------------------------

print("Creating video scenes...")

scene_files = []

for i, scene in enumerate(scenes):
    scene_file = f"scene_{i}.mp4"
    text_file = f"scene_text_{i}.txt"

    duration = 6.7 if i < len(scenes) - 1 else 6.5

    with open(text_file, "w", encoding="utf-8") as f:
        f.write(str(scene["text"]))

    scene_files.append(scene_file)

    video_filter = (
        "drawtext="
        f"textfile={text_file}:"
        "expansion=none:"
        "font=DejaVuSans-Bold:"
        "fontcolor=white:"
        "fontsize=58:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2"
    )

    command = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x071A2B:s=1080x1920:r=25:d={duration}",
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        scene_file
    ]

    subprocess.run(command, check=True)
    print(f"Scene {i + 1}/{len(scenes)} created.")


# 5. CREATE CONCAT FILE
# ------------------------------------------------------------

with open("concat.txt", "w", encoding="utf-8") as f:
    for filename in scene_files:
        absolute_path = os.path.abspath(filename)
        f.write(f"file '{absolute_path}'\n")


# 6. JOIN ALL SCENES
# ------------------------------------------------------------

print("Joining video scenes...")

subprocess.run(
    [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", "concat.txt",
        "-c", "copy",
        TEMP_VIDEO
    ],
    check=True
)


# 7. ADD AI VOICE TO VIDEO
# ------------------------------------------------------------

print("Adding AI voice to video...")

subprocess.run(
    [
        "ffmpeg", "-y",
        "-i", TEMP_VIDEO,
        "-i", AUDIO_FILE,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        OUTPUT_VIDEO
    ],
    check=True
)


# 8. VERIFY FINAL OUTPUT
# ------------------------------------------------------------

if not os.path.isfile(OUTPUT_VIDEO):
    raise RuntimeError("Final MP4 was not created.")

if os.path.getsize(OUTPUT_VIDEO) == 0:
    raise RuntimeError("Final MP4 is empty.")

# Confirm that the output contains both video and audio streams.
check = subprocess.run(
    [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        OUTPUT_VIDEO
    ],
    capture_output=True,
    text=True,
    check=True
)

streams = json.loads(check.stdout).get("streams", [])
stream_types = {s.get("codec_type") for s in streams}

if "video" not in stream_types:
    raise RuntimeError("Final MP4 has no video stream.")

if "audio" not in stream_types:
    raise RuntimeError("Final MP4 has no audio stream.")

print("")
print("======================================")
print(" IT DOCTOR AI VIDEO CREATED!")
print("======================================")
print(f"Video: {OUTPUT_VIDEO}")
print("Video stream: OK")
print("Audio stream: OK")
print("======================================")
