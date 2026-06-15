"""
RahasyaFacts - Dark & Mysterious Facts YouTube Shorts Bot
Rock solid version - takes time but works perfectly
"""

import os
import json
import re
import random
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
PEXELS_API_KEY        = os.environ["PEXELS_API_KEY"]

WORK_DIR = Path("output")
WORK_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────
# STEP 0: Trending Topics
# ──────────────────────────────────────────────
def get_trending_context():
    print("🔥 Fetching trending topics in India...")
    all_topics = []

    for subreddit in ["indiameme", "indianmeme", "bollywood", "india"]:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10",
                headers={"User-Agent": "RahasyaFacts-Bot/1.0"},
                timeout=10
            )
            if r.status_code == 200:
                posts = r.json()["data"]["children"]
                for post in posts:
                    title = post["data"].get("title", "")
                    if len(title) > 5:
                        all_topics.append(title)
                print(f"  ✅ r/{subreddit}: {len(posts)} posts")
        except Exception as e:
            print(f"  ⚠️ Reddit {subreddit}: {e}")

    try:
        r = requests.get(
            "https://trends.google.com/trending/rss?geo=IN",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', r.text)
            google = [t for t in titles if t != "Google Trends" and len(t) > 3]
            all_topics += google
            print(f"  ✅ Google Trends: {google[:3]}")
    except Exception as e:
        print(f"  ⚠️ Google Trends: {e}")

    if not all_topics:
        all_topics = [
            "Indian historical mystery", "shocking ancient ritual",
            "mysterious disappearance India", "dark Mughal secret",
            "haunted place India", "unknown Indian scientist",
            "dark royal family secret", "shocking space fact",
        ]

    print(f"  🎯 {len(all_topics)} topics fetched")
    return all_topics


# ──────────────────────────────────────────────
# STEP 1: Generate Script
# ──────────────────────────────────────────────
def generate_script(trending_context: list):
    print("\n📝 Generating script...")

    top_topics   = trending_context[:3]
    backup_topic = random.choice(trending_context[3:]) if len(trending_context) > 3 else "dark Indian history"

    prompt = f"""You are a viral YouTube Shorts scriptwriter for RahasyaFacts — India's top dark facts channel loved by Gen Z.

TRENDING IN INDIA RIGHT NOW:
{chr(10).join([f"- {t}" for t in top_topics])}
BACKUP: {backup_topic}

Find a DARK, MYSTERIOUS or SHOCKING fact connected to these trends and write a 50-60 second Hinglish script.

SCRIPT RULES:
- Natural Hinglish like real Indian Gen Z speaks — mix Hindi and English naturally
- Short punchy sentences, max 8 words each
- Use: "Bhai", "Yaar", "Suno", "No way", "Literally", "Sacchi mein"
- First sentence must be SO shocking viewer cannot scroll away
- Build suspense with each line — save biggest reveal for last
- End with a jaw-dropping twist that makes them share it
- NO stage directions, NO [PAUSE] tags — just natural speech

OUTPUT ONLY RAW JSON — no markdown, no backticks, no explanation:
{{"title": "viral hinglish title max 55 chars no quotes no colons no special chars", "thumbnail_text": "3 TO 4 CAPS ENGLISH WORDS ONLY NO SPECIAL CHARS", "visual_keywords": ["specific search term 1", "specific search term 2", "specific search term 3", "specific search term 4"], "bg_music_mood": "dark", "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"], "script": "the full hinglish script here"}}"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.95,
            "max_tokens": 1200
        }
    )

    content = response.json()["choices"][0]["message"]["content"].strip()

    if "```" in content:
        for part in content.split("```"):
            if "{" in part:
                content = part.replace("json", "", 1).strip()
                break

    content = content.replace("**", "").strip()
    start = content.find("{")
    end   = content.rfind("}") + 1
    if start != -1 and end > start:
        content = content[start:end]

    data = json.loads(content)
    print(f"  ✅ Title: {data['title']}")
    print(f"  ✅ Keywords: {data.get('visual_keywords', [])}")
    return data


# ──────────────────────────────────────────────
# STEP 2: Voiceover
# ──────────────────────────────────────────────
def generate_voiceover(script: str):
    print("\n🎙️ Generating voiceover...")

    raw_path  = WORK_DIR / "voice_raw.mp3"
    fast_path = WORK_DIR / "voice_final.mp3"

    from gtts import gTTS
    tts = gTTS(text=script.strip(), lang='hi', slow=False)
    tts.save(str(raw_path))
    print(f"  ✅ Raw audio: {raw_path.stat().st_size // 1024}KB")

    # Speed up 1.15x + slight pitch raise for energy
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_path),
        "-filter:a", "atempo=1.15,aecho=0.8:0.88:60:0.4",
        str(fast_path)
    ], capture_output=True)

    if r.returncode != 0 or not fast_path.exists():
        # Simple fallback — just speed up
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_path),
            "-filter:a", "atempo=1.15",
            str(fast_path)
        ], capture_output=True, check=True)

    print(f"  ✅ Final audio: {fast_path.stat().st_size // 1024}KB")
    return fast_path


# ──────────────────────────────────────────────
# STEP 3: Download Visuals from Pexels
# ──────────────────────────────────────────────
def download_visuals(visual_keywords: list):
    print(f"\n🎬 Downloading visuals...")
    all_photos = []

    for keyword in visual_keywords[:4]:
        print(f"  🔍 Searching photos: '{keyword}'")
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": keyword, "per_page": 5, "orientation": "portrait"},
                timeout=15
            )
            photos = r.json().get("photos", [])
            print(f"    Found {len(photos)} photos")

            downloaded = 0
            for photo in photos:
                if downloaded >= 2:
                    break
                # Try best quality available
                url = (photo["src"].get("portrait") or
                       photo["src"].get("large") or
                       photo["src"].get("medium"))
                if not url:
                    continue

                path = WORK_DIR / f"photo_{len(all_photos)}.jpg"
                try:
                    pr = requests.get(url, timeout=30)
                    if pr.status_code == 200 and len(pr.content) > 5000:
                        with open(path, "wb") as f:
                            f.write(pr.content)
                        # Verify valid image with ffprobe
                        check = subprocess.run(
                            ["ffprobe", "-v", "error", "-show_entries",
                             "stream=codec_type", "-of", "default=noprint_wrappers=1", str(path)],
                            capture_output=True, text=True
                        )
                        if "video" in check.stdout:
                            all_photos.append(path)
                            downloaded += 1
                            print(f"    ✅ Photo {len(all_photos)}: {path.name} ({len(pr.content)//1024}KB)")
                except Exception as e:
                    print(f"    ⚠️ Download failed: {e}")

        except Exception as e:
            print(f"  ⚠️ Pexels search failed for '{keyword}': {e}")

    print(f"  📊 Total photos: {len(all_photos)}")

    # Pad with fallbacks if needed
    while len(all_photos) < 5:
        fallbacks = generate_fallback_images(5 - len(all_photos))
        all_photos += fallbacks
        print(f"  ➕ Added {len(fallbacks)} fallback images")

    return all_photos


def generate_fallback_images(num: int):
    paths = []
    gradients = ["0x0a0a0a", "0x1a0a2e", "0x16213e", "0x0f3460", "0x1a1a2e", "0x2d1b69"]
    for i in range(num):
        path  = WORK_DIR / f"fallback_{len(paths)}.jpg"
        color = gradients[i % len(gradients)]
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color}:size=1080x1920:duration=1",
            "-vframes", "1", str(path)
        ], capture_output=True)
        if r.returncode == 0:
            paths.append(path)
    return paths


# ──────────────────────────────────────────────
# STEP 4: Background Music — Generate with FFmpeg (no download needed!)
# ──────────────────────────────────────────────
def get_bg_music(mood: str, duration: float):
    """Generate dark ambient music using FFmpeg sine waves — 100% reliable, no downloads"""
    print(f"\n🎵 Generating background music ({mood}, {duration:.1f}s)...")

    music_path = WORK_DIR / "bg_music.mp3"

    # Different frequency combinations per mood for different feels
    mood_settings = {
        "dark":     {"freq1": 60,  "freq2": 90,  "freq3": 120, "vol": 0.15},
        "suspense": {"freq1": 80,  "freq2": 110, "freq3": 160, "vol": 0.12},
        "horror":   {"freq1": 40,  "freq2": 60,  "freq3": 80,  "vol": 0.18},
        "mystery":  {"freq1": 100, "freq2": 150, "freq3": 200, "vol": 0.10},
    }

    s = mood_settings.get(mood, mood_settings["dark"])
    dur = duration + 2

    # Generate layered sine wave ambient music using FFmpeg
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={s['freq1']}:duration={dur},"
            f"volume={s['vol']}"
        ),
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={s['freq2']}:duration={dur},"
            f"volume={s['vol'] * 0.7}"
        ),
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={s['freq3']}:duration={dur},"
            f"volume={s['vol'] * 0.5}"
        ),
        "-filter_complex",
        "[0][1][2]amix=inputs=3:duration=longest,lowpass=f=300,volume=0.6[aout]",
        "-map", "[aout]",
        "-c:a", "mp3", "-b:a", "128k",
        str(music_path)
    ], capture_output=True)

    if r.returncode == 0 and music_path.exists() and music_path.stat().st_size > 1000:
        print(f"  ✅ Music generated ({music_path.stat().st_size // 1024}KB)")
        return music_path

    print(f"  ⚠️ Music generation failed: {r.stderr.decode()[-100:]}")
    return None


# ──────────────────────────────────────────────
# STEP 5: Assemble Video
# ──────────────────────────────────────────────
def assemble_video(photos: list, audio_path: Path, music_path, script_data: dict):
    print("\n🎬 Assembling final video...")

    output_path = WORK_DIR / "final_short.mp4"
    bg_path     = WORK_DIR / "background.mp4"
    audio_mix   = WORK_DIR / "audio_mix.mp3"

    # Get audio duration
    result   = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)
    ], capture_output=True, text=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])
    print(f"  ⏱️ Audio duration: {duration:.1f}s")
    print(f"  📸 Photos: {len(photos)}")

    # Clean thumbnail text
    thumbnail_text = re.sub(r'[^A-Z0-9 ]', '', script_data.get("thumbnail_text", "RAHASYA FACTS").upper()).strip()
    if not thumbnail_text:
        thumbnail_text = "RAHASYA FACTS"

    # ── BUILD SLIDESHOW ──
    # Each photo gets equal screen time
    img_duration = duration / len(photos)
    print(f"  🖼️ Each photo: {img_duration:.1f}s")

    concat_file = WORK_DIR / "slideshow.txt"
    with open(concat_file, "w") as f:
        for photo in photos:
            f.write(f"file '{photo.absolute()}'\n")
            f.write(f"duration {img_duration:.3f}\n")
        # Add last frame again to prevent black flash
        f.write(f"file '{photos[-1].absolute()}'\n")

    # Convert slideshow to video with smooth scaling (no zoom to avoid crashes)
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "setsar=1"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-t", str(duration + 0.5),
        "-r", "25", "-an",
        str(bg_path)
    ], capture_output=True)

    if r.returncode != 0:
        print(f"  ❌ Slideshow error: {r.stderr.decode()[-300:]}")
        raise Exception("Slideshow assembly failed")

    print(f"  ✅ Slideshow: {bg_path.stat().st_size // 1024}KB")

    # ── MIX AUDIO ──
    if music_path and music_path.exists() and music_path.stat().st_size > 1000:
        r = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-i", str(music_path),
            "-filter_complex",
            (
                "[0:a]volume=1.0,apad[voice];"
                "[1:a]volume=0.08[music];"
                "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            ),
            "-map", "[aout]",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(audio_mix)
        ], capture_output=True)

        if r.returncode == 0 and audio_mix.stat().st_size > 1000:
            final_audio = audio_mix
            print(f"  ✅ Audio mixed: {audio_mix.stat().st_size // 1024}KB")
        else:
            final_audio = audio_path
            print(f"  ⚠️ Audio mix failed — using voice only")
            print(f"  ⚠️ Error: {r.stderr.decode()[-200:]}")
    else:
        final_audio = audio_path
        print("  ℹ️ No bg music")

    # ── FINAL COMBINE: VIDEO + AUDIO + TEXT ──
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(bg_path),
        "-i", str(final_audio),
        "-vf", (
            # Dark vignette edges
            "vignette=PI/4,"
            # Title text at top
            f"drawtext=text='{thumbnail_text}':"
            "fontsize=58:fontcolor=white:borderw=5:bordercolor=black@0.9:"
            "box=1:boxcolor=black@0.3:boxborderw=10:"
            "x=(w-text_w)/2:y=h*0.06:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Channel watermark
            "drawtext=text='@RahasyaFacts':"
            "fontsize=26:fontcolor=white@0.9:borderw=2:bordercolor=black:"
            "x=(w-text_w)/2:y=h*0.93:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path)
    ], capture_output=True)

    if r.returncode != 0:
        print(f"  ❌ Final combine error: {r.stderr.decode()[-300:]}")
        raise Exception("Final video assembly failed")

    size = output_path.stat().st_size
    print(f"  ✅ Final video: {size // 1024}KB ({size // (1024*1024)}MB)")

    if size < 200000:
        raise Exception(f"Output video too small ({size//1024}KB) — something went wrong!")

    return output_path


# ──────────────────────────────────────────────
# STEP 6: SEO
# ──────────────────────────────────────────────
def generate_seo(script_data: dict, trending_context: list):
    print("\n🔍 Generating SEO...")

    title = script_data.get("title", "Dark Facts India")

    power_words = ["Shocking", "Dark Secret", "Hidden Truth", "Scary", "Mysterious"]
    has_power   = any(w.lower() in title.lower() for w in power_words)
    if not has_power and len(title) < 45:
        title = f"{random.choice(power_words)} {title}"
    title = title[:100]

    def clean_tag(t):
        return re.sub(r'[^a-zA-Z0-9 ]', '', str(t)).strip()[:30]

    ai_tags   = [clean_tag(t) for t in script_data.get("tags", []) if clean_tag(t)]
    base_tags = [
        "facts", "shorts", "viral", "trending", "india",
        "dark facts", "mystery", "rahasya", "indian mystery",
        "mysterious facts", "horror facts", "unknown facts india",
        "rahasya facts", "anokhe facts", "hindi facts",
        "RahasyaFacts", "youtubeshorts", "viralshorts", "shorts india",
    ]
    trend_tags = [clean_tag(" ".join(t.split()[:2])) for t in trending_context[:3]]

    final_tags = list(dict.fromkeys(
        [t for t in ai_tags + base_tags + trend_tags if len(t) > 1]
    ))[:30]

    description = (
        f"{title}\n\n"
        "Subscribe for daily dark and mysterious facts!\n"
        "Share if this fact shocked you!\n"
        "Comment below what you think!\n\n"
        "dark facts india mysterious facts hindi shocking indian history "
        "rahasya facts india ke rahasya horror facts hindi\n\n"
        f"Trending: {' '.join(trending_context[:2])}\n\n"
        "#Shorts #RahasyaFacts #DarkFacts #MysteriousFacts "
        "#IndianFacts #ViralShorts #Hindi #Rahasya"
    )

    print(f"  ✅ Title: {title}")
    print(f"  ✅ Tags: {len(final_tags)}")
    return {"title": title, "description": description[:4900], "tags": final_tags}


# ──────────────────────────────────────────────
# STEP 7: Upload to YouTube
# ──────────────────────────────────────────────
def get_youtube_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id":     YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": YOUTUBE_REFRESH_TOKEN,
            "grant_type":    "refresh_token"
        }
    )
    return r.json()["access_token"]


def upload_to_youtube(video_path: Path, seo: dict):
    print("\n📤 Uploading to YouTube...")

    # Check file size before uploading
    size = video_path.stat().st_size
    print(f"  📁 File size: {size // 1024}KB")
    if size < 200000:
        raise Exception(f"Video too small to upload: {size//1024}KB")

    access_token = get_youtube_token()

    safe_tags = [re.sub(r'[^a-zA-Z0-9 ]', '', t).strip() for t in seo["tags"]]
    safe_tags = [t for t in safe_tags if len(t) > 1][:30]

    metadata = {
        "snippet": {
            "title":                seo["title"][:100],
            "description":          seo["description"][:4900],
            "tags":                 safe_tags,
            "categoryId":           "27",
            "defaultLanguage":      "hi",
            "defaultAudioLanguage": "hi"
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False,
            "embeddable":              True,
            "publicStatsViewable":     True
        }
    }

    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization":         f"Bearer {access_token}",
            "Content-Type":          "application/json",
            "X-Upload-Content-Type": "video/mp4"
        },
        json=metadata
    )

    print(f"  📡 API status: {init.status_code}")
    if init.status_code not in [200, 201]:
        print(f"  ❌ API error: {init.text[:500]}")
        raise Exception(f"YouTube API error: {init.status_code}")

    upload_url = init.headers["Location"]

    with open(video_path, "rb") as f:
        video_data = f.read()

    print(f"  ⬆️ Uploading {len(video_data)//1024}KB...")
    up = requests.put(
        upload_url,
        headers={
            "Content-Type":   "video/mp4",
            "Content-Length": str(len(video_data))
        },
        data=video_data,
        timeout=300
    )

    video_id = up.json().get("id")
    if not video_id:
        print(f"  ❌ Upload response: {up.text[:300]}")
        raise Exception("Upload failed — no video ID returned")

    print(f"  ✅ Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("\n🚀 RahasyaFacts Bot Starting...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    try:
        # Step 0: Trending topics
        trending = get_trending_context()

        # Step 1: Script
        script = generate_script(trending)

        # Step 2: Voiceover
        audio = generate_voiceover(script["script"])

        # Step 3: Visuals
        keywords = script.get("visual_keywords", ["mystery dark", "ancient ruins", "dark forest night", "mysterious India"])
        photos   = download_visuals(keywords)

        # Step 4: Get audio duration for music generation
        result   = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio)
        ], capture_output=True, text=True)
        duration = float(json.loads(result.stdout)["format"]["duration"])

        # Step 5: Generate background music (no download — made with FFmpeg)
        music = get_bg_music(script.get("bg_music_mood", "dark"), duration)

        # Step 6: Assemble video
        video = assemble_video(photos, audio, music, script)

        # Step 7: SEO
        seo = generate_seo(script, trending)

        # Step 8: Upload
        video_id = upload_to_youtube(video, seo)

        print(f"\n🎉 SUCCESS!")
        print(f"🔗 https://youtube.com/shorts/{video_id}")
        print(f"📌 {seo['title']}")
        print(f"🏷️ {len(seo['tags'])} SEO tags")

    except Exception as e:
        import traceback
        print(f"\n❌ {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
