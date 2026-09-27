import json
import subprocess

with open("video_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

scenes = data["scenes"]

# Create scene text files
for i, scene in enumerate(scenes):
    with open(f"scene_{i}.txt", "w", encoding="utf-8") as f:
        f.write(scene["text"])

# Build a simple professional vertical Short
inputs = []
filters = []

for i, scene in enumerate(scenes):
    duration = 6.7 if i < 5 else 6.5

    inputs.extend([
        "-f", "lavfi",
        "-i",
        f"color=c=0x071A2B:s=1080x1920:d={duration}"
    ])

    safe_text = (
        scene["text"]
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
    )

    filters.append(
        f"[{i}:v]"
        f"drawtext="
        f"fontcolor=white:"
        f"fontsize=58:"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/2:"
        f"text='{safe_text}'"
        f"[v{i}]"
    )

concat_inputs = "".join(f"[v{i}]" for i in range(len(scenes)))

filter_complex = (
    ";".join(filters)
    + ";"
    + concat_inputs
    + f"concat=n={len(scenes)}:v=1:a=0[outv]"
)

command = [
    "ffmpeg",
    "-y",
    *inputs,
    "-filter_complex",
    filter_complex,
    "-map",
    "[outv]",
    "-c:v",
    "libx264",
    "-preset",
    "veryfast",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
    "it_doctor_ai_day1.mp4"
]

subprocess.run(command, check=True)

print("IT Doctor AI Day 1 Short created successfully!")
