import json
import subprocess

with open("video_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

title = data["title"]
hook = data["hook"]

# Create a simple 40-second vertical video
# This is our first automation test.

command = [
    "ffmpeg",
    "-y",
    "-f", "lavfi",
    "-i", "color=c=0x071A2B:s=1080x1920:d=40",
    "-vf",
    (
        "drawtext="
        "fontcolor=white:"
        "fontsize=64:"
        "x=(w-text_w)/2:"
        "y=700:"
        f"text='{hook.replace(chr(39), chr(92)+chr(39))}'"
    ),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "it_doctor_ai_day1.mp4"
]

subprocess.run(command, check=True)

print("Video created successfully!")
