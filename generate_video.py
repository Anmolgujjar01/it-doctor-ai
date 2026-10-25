
import asyncio
import json
import math
import os
import shutil
import subprocess
import wave
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# IT DOCTOR AI - FREE-FIRST VIDEO GENERATOR
# Output: vertical MP4 with Urdu narration, visuals,
# estimated Urdu subtitles and generated ambient music.
# ============================================================

OUT = Path("output")
ASSETS = OUT / "assets"
OUT.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

VIDEO = OUT / "it_doctor_ai_day1.mp4"
VOICE = OUT / "voice.mp3"
MUSIC = OUT / "ambient.wav"
SRT = OUT / "subtitles.srt"

W, H, FPS = 1080, 1920, 25
VOICE_NAME = os.getenv("URDU_VOICE", "ur-PK-AsadNeural")
WIDTH, HEIGHT = W, H


def run(cmd):
    subprocess.run(cmd, check=True)


def duration_of(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return float(result.stdout.strip())


def get_font(size):
    # Prefer Urdu Nastaliq; fall back to an installed font.
    candidates = [
        "/usr/share/fonts/truetype/noto/"
        "NotoNastaliqUrdu-Regular.ttf",
        "/usr/share/fonts/truetype/noto/"
        "NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)

    try:
        path = subprocess.check_output(
            ["fc-match", "-f", "%{file}", "Noto Nastaliq Urdu"],
            text=True
        ).strip()
        if path and os.path.isfile(path):
            return ImageFont.truetype(path, size)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    return ImageFont.load_default()


def load_data():
    path = Path("video_data.json")
    if not path.is_file():
        raise FileNotFoundError("video_data.json not found.")

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    voiceover = data.get("voiceover")
    scenes = data.get("scenes")

    if not isinstance(voiceover, str) or not voiceover.strip():
        raise ValueError("A non-empty voiceover is required.")

    if not isinstance(scenes, list) or not scenes:
        raise ValueError("At least one scene is required.")

    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict) or not str(
            scene.get("text", "")
        ).strip():
            raise ValueError(f"Scene {i + 1} needs text.")

    return voiceover.strip(), scenes


async def generate_voice(text):
    print("Generating Urdu narration...")

    communicate = edge_tts.Communicate(
        text,
        VOICE_NAME,
        rate="+0%",
        volume="+0%"
    )
    await communicate.save(str(VOICE))

    if not VOICE.exists() or VOICE.stat().st_size == 0:
        raise RuntimeError("Urdu TTS did not produce audio.")


def create_visual(scene, index):
    """Create a unique procedural technology scene."""
    image = Image.new("RGB", (W, H), "#071426")
    pixels = image.load()

    # Dark blue vertical gradient.
    for y in range(H):
        t = y / H
        color = (
            int(5 + 4 * t),
            int(18 + 20 * t),
            int(38 + 30 * t)
        )
        for x in range(W):
            pixels[x, y] = color

    draw = ImageDraw.Draw(image, "RGBA")

    # Circuit-like lines and glowing nodes.
    for k in range(16):
        x = (index * 137 + k * 71) % W
        y = (k * 149 + 100) % H
        draw.line(
            [(x, y), (W - x // 2, y), (W - x // 2, y + 120)],
            fill=(30, 170, 255, 90),
            width=3
        )
        draw.ellipse(
            (x - 7, y - 7, x + 7, y + 7),
            fill=(60, 210, 255, 180)
        )

    # Central technology emblem.
    cx, cy = W // 2, H // 2 - 100
    for radius in (115, 145, 175):
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            outline=(0, 190, 255, 170),
            width=5
        )

    draw.rounded_rectangle(
        (cx - 75, cy - 75, cx + 75, cy + 75),
        radius=20,
        outline=(100, 220, 255, 255),
        width=7
    )
    draw.text(
        (cx, cy),
        "IT",
        font=ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            92
        ),
        fill="white",
        anchor="mm"
    )

    # Scene heading.
    title_font = get_font(64)
    subtitle_font = get_font(38)
    heading = str(scene["text"]).strip()

    # Keep the image heading readable; subtitle carries narration.
    words = heading.split()
    lines = []
    line = ""

    for word in words:
        candidate = (line + " " + word).strip()
        if len(candidate) > 22 and line:
            lines.append(line)
            line = word
        else:
            line = candidate

    if line:
        lines.append(line)

    lines = lines[:4]
    y = H - 600

    for line in lines:
        draw.text(
            (W // 2 + 3, y + 4),
            line,
            font=title_font,
            fill=(0, 0, 0, 210),
            anchor="mm",
            align="center",
            direction="rtl" if any(
                "\u0600" <= c <= "\u06ff" for c in line
            ) else "ltr"
        )
        draw.text(
            (W // 2, y),
            line,
            font=title_font,
            fill=(240, 250, 255, 255),
            anchor="mm",
            align="center",
            direction="rtl" if any(
                "\u0600" <= c <= "\u06ff" for c in line
            ) else "ltr"
        )
        y += 90

    draw.text(
        (W // 2, H - 160),
        "IT DOCTOR AI",
        font=subtitle_font,
        fill=(60, 205, 255, 255),
        anchor="mm"
    )

    path = ASSETS / f"scene_{index:03}.png"
    image.save(path)
    return path


def create_music(seconds):
    """Generate quiet, synthetic ambient music without downloads."""
    print("Generating background music...")

    sample_rate = 22050
    total = max(1, int(seconds * sample_rate))
    chunk_size = sample_rate * 5

    with wave.open(str(MUSIC), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        offset = 0

        while offset < total:
            count = min(chunk_size, total - offset)
            t = (
                np.arange(offset, offset + count, dtype=np.float64)
                / sample_rate
            )

            fade = np.minimum(1.0, t / 2.0)
            tones = (
                0.45 * np.sin(2 * math.pi * 110 * t)
                + 0.25 * np.sin(2 * math.pi * 164.81 * t)
                + 0.15 * np.sin(2 * math.pi * 220 * t)
            )

            envelope = 0.5 + 0.5 * np.sin(
                2 * math.pi * 0.08 * t
            )
            signal = tones * envelope * fade * 0.07

            stereo = np.column_stack(
                (signal, signal * 0.92)
            )
            pcm = np.clip(
                stereo * 32767, -32768, 32767
            ).astype("<i2")

            wav.writeframes(pcm.tobytes())
            offset += count


def make_srt(text, seconds):
    """Create approximate-timing captions from narration text."""
    words = text.split()
    if not words:
        raise ValueError("Voiceover contains no words.")

    # About 7 words per caption, adjusted to total duration.
    chunks = [
        words[i:i + 7]
        for i in range(0, len(words), 7)
    ]

    def stamp(t):
        ms = int(t * 1000)
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with SRT.open("w", encoding="utf-8-sig") as f:
        position = 0

        for i, chunk in enumerate(chunks, start=1):
            start = seconds * position / len(words)
            position += len(chunk)
            end = seconds * position / len(words)

            # Prevent zero-length subtitle entries.
            end = max(start + 0.3, end)
            caption = " ".join(chunk)

            f.write(
                f"{i}\n{stamp(start)} --> {stamp(end)}\n"
                f"{caption}\n\n"
            )


def main():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"{tool} is not installed.")

    voiceover, scenes = load_data()

    asyncio.run(generate_voice(voiceover))
    voice_seconds = duration_of(VOICE)

    print(f"Voice duration: {voice_seconds:.1f} seconds")

    # Distribute scenes across the voice duration.
    scene_seconds = voice_seconds / len(scenes)
    scene_files = []

    for i, scene in enumerate(scenes):
        image_path = create_visual(scene, i)
        video_path = ASSETS / f"clip_{i:03}.mp4"

        # Small overlap-free clips; identical dimensions and FPS.
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-framerate", str(FPS),
            "-i", str(image_path),
            "-t", f"{scene_seconds:.4f}",
            "-vf", f"scale={W}:{H},format=yuv420p",
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-r", str(FPS),
            str(video_path)
        ])

        scene_files.append(video_path)
        print(f"Visual {i + 1}/{len(scenes)} created.")

    concat_file = ASSETS / "concat.txt"

    with concat_file.open("w", encoding="utf-8") as f:
        for clip in scene_files:
            path = str(clip.resolve()).replace("'", "'\\''")
            f.write(f"file '{path}'\n")

    silent_video = ASSETS / "silent.mp4"

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        str(silent_video)
    ])

    # The narration text provides approximate, not phoneme-level,
    # subtitle timing.
    make_srt(voiceover, voice_seconds)
    create_music(voice_seconds)

    print("Adding subtitles and mixing audio...")

    # Keep subtitle path simple and relative to the working directory.
    subtitle_path = str(SRT.resolve()).replace("\\", "/")
    subtitle_path = subtitle_path.replace(":", r"\:")

    subtitle_filter = (
        f"subtitles='{subtitle_path}':"
        "force_style='FontName=Noto Naskh Arabic,"
        "FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,BorderStyle=1,"
        "Outline=2,Shadow=1,Alignment=2,MarginV=100'"
    )

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(silent_video),
        "-i", str(VOICE),
        "-i", str(MUSIC),
        "-filter_complex",
        (
            f"[0:v]{subtitle_filter}[v];"
            "[1:a]volume=1.0[voice];"
            "[2:a]volume=0.10[music];"
            "[voice][music]amix=inputs=2:"
            "duration=first:dropout_transition=2[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{voice_seconds:.3f}",
        "-movflags", "+faststart",
        str(VIDEO)
    ])

    if not VIDEO.exists() or VIDEO.stat().st_size == 0:
        raise RuntimeError("Final MP4 was not created.")

    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,width,height",
        "-of", "json", str(VIDEO)
    ], capture_output=True, text=True, check=True)

    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    types = {s.get("codec_type") for s in streams}

    if not {"video", "audio"}.issubset(types):
        raise RuntimeError("MP4 is missing video or audio.")

    print("\n====================================")
    print("IT DOCTOR AI VIDEO CREATED!")
    print(f"File: {VIDEO}")
    print(f"Voice: {VOICE_NAME}")
    print(f"Duration: {voice_seconds:.1f} seconds")
    print("Video, audio and subtitles: OK")
    print("====================================")


if __name__ == "__main__":
    main()
