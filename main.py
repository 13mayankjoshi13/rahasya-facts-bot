"""
RahasyaFacts - Dark & Mysterious Facts YouTube Shorts Bot
Fully automated: Script → Voiceover → Images → Video → Upload
"""

import os
import json
import time
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
GROQ_API_KEY          = os.environ["GROQ_API_KEY"]
YOUTUBE_CLIENT_ID     = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
PEXELS_API_KEY        = os.environ.get("PEXELS_API_KEY", "").strip())
HF_API_KEY            = os.environ.get("HF_API_KEY", "")

WORK_DIR = Path("output")
WORK_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# STEP 1: Generate Script via Groq
# ──────────────────────────────────────────────
def generate_script():
    print("📝 Generating script with Groq...")

    prompt = """You are a viral YouTube Shorts scriptwriter for an Indian dark facts channel called 'RahasyaFacts'.

Write a 45-60 second script in proper Hinglish (natural mix of Hindi and English like Indians actually speak).

IMPORTANT - Write naturally like a person speaks, NOT like a robot. Use short punchy sentences.

Rules:
- Hook must be SHOCKING in first 3 seconds
- Use natural Hindi words mixed with English (e.g. "Yaar, ye sun ke aapka dimaag ghoom jayega")
- Short dramatic sentences with pauses
- Build suspense throughout
- End with a mind-blowing twist or cliffhanger
- NO [PAUSE] markers - write naturally flowing script

Also provide:
- title: Clickbait Hindi/Hinglish YouTube title (max 60 chars, no special chars)
- thumbnail_text: 3-4 dramatic words in CAPS for thumbnail (English only, no apostrophes)
- search_keyword: One English word to search stock footage (e.g. "mystery", "forest", "ancient", "space", "fire")
- tags: 10 relevant YouTube tags as array

Output ONLY valid JSON, no markdown, no backticks:
{"title": "...", "thumbnail_text": "...", "search_keyword": "...", "tags": ["..."], "script": "..."}"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85,
            "max_tokens": 1000
        }
    )

    resp_json = response.json()
    content = resp_json["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if model still adds them
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            if "{" in part:
                content = part.replace("json", "", 1).strip()
                break

    # Clean up common issues
    content = content.replace("**", "").strip()

    data = json.loads(content)
    print(f"✅ Title: {data['title']}")
    return data


# ──────────────────────────────────────────────
# STEP 2: Generate Voiceover via gTTS
# ──────────────────────────────────────────────
def generate_voiceover(script: str):
    print("🎙️ Generating voiceover with gTTS...")

    # Clean script
    clean_script = script.strip()

    audio_path = WORK_DIR / "voiceover.mp3"
    fast_path  = WORK_DIR / "voiceover_fast.mp3"

    from gtts import gTTS
    # Use 'hi' for Hindi — sounds much more natural than en-in
    tts = gTTS(text=clean_script, lang='hi', slow=False)
    tts.save(str(audio_path))

    # Speed up slightly with ffmpeg (1.15x) — fixes the "too slow" problem
    subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-filter:a", "atempo=1.15",
        str(fast_path)
    ], capture_output=True, check=True)

    print(f"✅ Voiceover saved and speed adjusted")
    return fast_path


# ──────────────────────────────────────────────
# STEP 3: Get Background Videos from Pexels (Free)
# ──────────────────────────────────────────────
def get_background_videos(keyword: str, num: int = 3):
    """Fetch free stock videos from Pexels API"""
    print(f"🎬 Fetching stock videos for: {keyword}...")

    print(f"🔑 Pexels key found: {bool(PEXELS_API_KEY)} length: {len(PEXELS_API_KEY)}")
    if not PEXELS_API_KEY:
        print("⚠️ No PEXELS_API_KEY — using dark gradient fallback")
        return generate_fallback_images(num)

    try:
        response = requests.get(
            f"https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": f"{keyword} dark mysterious",
                "orientation": "portrait",
                "size": "medium",
                "per_page": num
            },
            timeout=15
        )
        data = response.json()
        video_paths = []

        for i, video in enumerate(data.get("videos", [])[:num]):
            # Get smallest HD file
            video_files = sorted(
                [f for f in video["video_files"] if f.get("quality") in ["hd", "sd"]],
                key=lambda x: x.get("width", 0)
            )
            if not video_files:
                continue

            video_url = video_files[0]["link"]
            vid_path = WORK_DIR / f"bg_video_{i}.mp4"

            vid_response = requests.get(video_url, timeout=30)
            with open(vid_path, "wb") as f:
                f.write(vid_response.content)

            video_paths.append(vid_path)
            print(f"  ✅ Video {i+1} downloaded")

        if video_paths:
            return video_paths, "video"

    except Exception as e:
        print(f"  ⚠️ Pexels error: {e}")

    return generate_fallback_images(num), "image"


def generate_fallback_images(num: int):
    """Dark gradient fallback images"""
    paths = []
    # More interesting gradients
    gradients = [
        "0x0a0a0a", "0x1a0a2e", "0x16213e",
        "0x0f3460", "0x1a1a2e", "0x2d1b69"
    ]
    for i in range(num):
        path = WORK_DIR / f"fallback_{i}.jpg"
        color = gradients[i % len(gradients)]
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color}:size=1080x1920:duration=1",
            "-vframes", "1", str(path)
        ], capture_output=True)
        paths.append(path)
    return paths


# ──────────────────────────────────────────────
# STEP 4: Assemble Video with FFmpeg
# ──────────────────────────────────────────────
def assemble_video(bg_assets, asset_type: str, audio_path: Path, script_data: dict):
    print("🎬 Assembling final video...")

    output_path = WORK_DIR / "final_short.mp4"

    # Get audio duration
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(audio_path)
    ], capture_output=True, text=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])
    print(f"  Audio duration: {duration:.1f}s")

    # Clean thumbnail text
    thumbnail_text = script_data.get("thumbnail_text", "RAHASYA FACTS")
    thumbnail_text = (thumbnail_text
        .replace("'", "").replace('"', '')
        .replace("**", "").replace(":", "")
        .replace("(", "").replace(")", "")
        .upper()
    )

    if asset_type == "video" and bg_assets:
        # Concat video clips properly
        concat_file = WORK_DIR / "videos.txt"
        with open(concat_file, "w") as f:
            total = 0
            idx = 0
            while total < duration + 10:
                vid = bg_assets[idx % len(bg_assets)]
                f.write(f"file '{vid.absolute()}'\n")
                total += 8
                idx += 1

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-i", str(audio_path),
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                f"drawtext=text='{thumbnail_text}':"
                "fontsize=68:fontcolor=white:borderw=5:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.08:"
                "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                "drawtext=text='@RahasyaFacts':"
                "fontsize=32:fontcolor=white@0.8:borderw=2:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.93:"
                "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration),
            "-r", "30",
            str(output_path)
        ]
    else:
        # Image slideshow fallback
        img_duration = duration / len(bg_assets)
        concat_file = WORK_DIR / "images.txt"
        with open(concat_file, "w") as f:
            for img in bg_assets:
                f.write(f"file '{img.absolute()}'\n")
                f.write(f"duration {img_duration:.2f}\n")
            f.write(f"file '{bg_assets[-1].absolute()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(audio_path),
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                f"drawtext=text='{thumbnail_text}':"
                "fontsize=68:fontcolor=white:borderw=5:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.08:"
                "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
                "drawtext=text='@RahasyaFacts':"
                "fontsize=32:fontcolor=white@0.8:borderw=2:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.93:"
                "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-r", "30",
            str(output_path)
        ]

    subprocess.run(cmd, check=True)
    print(f"✅ Video assembled: {output_path}")
    return output_path


# ──────────────────────────────────────────────
# STEP 5: Upload to YouTube
# ──────────────────────────────────────────────
def get_youtube_token():
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": YOUTUBE_REFRESH_TOKEN,
            "grant_type": "refresh_token"
        }
    )
    return response.json()["access_token"]


def upload_to_youtube(video_path: Path, script_data: dict):
    print("📤 Uploading to YouTube...")

    access_token = get_youtube_token()
    title = script_data["title"]
    tags = script_data.get("tags", ["facts", "mystery", "rahasya", "shorts"])

    description = f"""{title}

🔔 Subscribe for daily dark & mysterious facts!
📲 Share karo agar ye fact ne aapko hairan kar diya!

#Shorts #RahasyaFacts #DarkFacts #MysteriousFacts #IndianFacts #ViralShorts #Facts #Mystery #Hindi

{' '.join(['#' + t.replace(' ', '') for t in tags])}"""

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags + ["Shorts", "RahasyaFacts", "facts", "mystery", "hindi facts"],
            "categoryId": "28",
            "defaultLanguage": "hi"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids": False
        }
    }

    init_response = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4"
        },
        json=metadata
    )

    upload_url = init_response.headers["Location"]

    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_response = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_data))
        },
        data=video_data
    )

    video_id = upload_response.json().get("id")
    print(f"✅ Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────
def main():
    print("\n🚀 RahasyaFacts Bot Starting...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    try:
        script_data = generate_script()
        audio_path  = generate_voiceover(script_data["script"])

        keyword = script_data.get("search_keyword", "mystery")
        result  = get_background_videos(keyword, num=3)

        if isinstance(result, tuple):
            bg_assets, asset_type = result
        else:
            bg_assets, asset_type = result, "image"

        video_path = assemble_video(bg_assets, asset_type, audio_path, script_data)
        video_id   = upload_to_youtube(video_path, script_data)

        print(f"\n🎉 SUCCESS! https://youtube.com/shorts/{video_id}")
        print(f"📌 Title: {script_data['title']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
