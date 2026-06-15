"""
RahasyaFacts - Dark & Mysterious Facts YouTube Shorts Bot
Fixed: Voice quality, multi-photo slideshow, bg music, clean SEO tags
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
# STEP 0: Fetch Trending Topics in India
# ──────────────────────────────────────────────
def get_trending_context():
    print("🔥 Fetching trending topics in India...")
    all_topics = []

    # Reddit India memes
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

    # Google Trends India
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

    print(f"  🎯 {len(all_topics)} trending topics fetched")
    return all_topics


# ──────────────────────────────────────────────
# STEP 1: Generate Script
# ──────────────────────────────────────────────
def generate_script(trending_context: list):
    print("\n📝 Generating script...")

    top_topics   = trending_context[:3]
    backup_topic = random.choice(trending_context[3:]) if len(trending_context) > 3 else "dark Indian history"

    prompt = f"""You are a viral YouTube Shorts scriptwriter for RahasyaFacts — India's top dark facts channel.

TRENDING IN INDIA RIGHT NOW:
{chr(10).join([f"- {t}" for t in top_topics])}
BACKUP: {backup_topic}

Find a DARK, MYSTERIOUS or SHOCKING fact connected to these trends and write a 45-55 second Hinglish script.

Rules:
- Natural Hinglish like real Indian Gen Z speaks
- Short sentences max 8 words
- Use: "Bhai", "Yaar", "Suno", "No way", "Literally"
- Hook must be shocking in first 5 words
- Build suspense, end with jaw-dropping twist
- NO stage directions

Output ONLY raw JSON no markdown no backticks:
{{"title": "viral hinglish title max 55 chars no special chars", "thumbnail_text": "3 CAPS WORDS", "visual_keywords": ["specific keyword 1", "specific keyword 2", "specific keyword 3", "specific keyword 4"], "bg_music_mood": "dark", "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"], "script": "the full script here"}}"""

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
# STEP 2: Voiceover - Using gTTS with best settings
# ──────────────────────────────────────────────
def generate_voiceover(script: str):
    print("\n🎙️ Generating voiceover...")

    audio_path = WORK_DIR / "voiceover.mp3"
    fast_path  = WORK_DIR / "voiceover_fast.mp3"

    from gtts import gTTS
    # Use 'hi' for natural Hindi voice
    tts = gTTS(text=script.strip(), lang='hi', slow=False)
    tts.save(str(audio_path))

    # Speed 1.15x + slight bass boost for dramatic effect
    result = subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-filter:a", "atempo=1.15,equalizer=f=100:width_type=o:width=2:g=3",
        str(fast_path)
    ], capture_output=True)

    if result.returncode != 0:
        # Fallback: just speed up without EQ
        subprocess.run([
            "ffmpeg", "-y", "-i", str(audio_path),
            "-filter:a", "atempo=1.15",
            str(fast_path)
        ], capture_output=True, check=True)

    print("  ✅ Voiceover ready")
    return fast_path


# ──────────────────────────────────────────────
# STEP 3: Download Multiple Topic-Specific Visuals
# ──────────────────────────────────────────────
def download_visuals(visual_keywords: list):
    print(f"\n🎬 Downloading visuals for: {visual_keywords}")

    all_assets = []

    for keyword in visual_keywords[:4]:
        print(f"  🔍 '{keyword}'")

        # Try photo from Pexels (more reliable than video)
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": keyword, "per_page": 5},
                timeout=15
            )
            photos = r.json().get("photos", [])
            print(f"    📸 Pexels photos found: {len(photos)}")

            for photo in photos[:2]:  # grab 2 photos per keyword
                url  = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"].get("medium")
                if not url:
                    continue
                path = WORK_DIR / f"photo_{len(all_assets)}.jpg"
                pr   = requests.get(url, timeout=20)
                if pr.status_code == 200 and len(pr.content) > 1000:
                    with open(path, "wb") as f:
                        f.write(pr.content)
                    # Verify it's a valid image
                    check = subprocess.run(
                        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
                        capture_output=True, text=True
                    )
                    if '"codec_type": "video"' in check.stdout or '"codec_name"' in check.stdout:
                        all_assets.append(("image", path))
                        print(f"    ✅ Photo saved: {path.name}")
                        break
        except Exception as e:
            print(f"    ⚠️ Photo failed: {e}")

        # Also try video
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": keyword, "per_page": 3},
                timeout=15
            )
            videos = r.json().get("videos", [])
            print(f"    🎬 Pexels videos found: {len(videos)}")

            for video in videos[:1]:
                files = sorted(video.get("video_files", []), key=lambda x: x.get("width", 9999))
                if not files:
                    continue
                url  = files[0]["link"]
                path = WORK_DIR / f"video_{len(all_assets)}.mp4"
                vr   = requests.get(url, timeout=30)
                if vr.status_code == 200 and len(vr.content) > 10000:
                    with open(path, "wb") as f:
                        f.write(vr.content)
                    all_assets.append(("video", path))
                    print(f"    ✅ Video saved: {path.name}")
                    break
        except Exception as e:
            print(f"    ⚠️ Video failed: {e}")

    print(f"  📊 Total assets: {len(all_assets)}")

    # Always ensure at least 4 assets for smooth slideshow
    if len(all_assets) < 4:
        print("  ➕ Adding fallback images to fill slideshow")
        fallbacks = generate_fallback_images(4 - len(all_assets))
        all_assets += [("image", p) for p in fallbacks]

    return all_assets


def generate_fallback_images(num: int):
    paths = []
    gradients = ["0x0a0a0a", "0x1a0a2e", "0x16213e", "0x0f3460", "0x1a1a2e", "0x2d1b69"]
    for i in range(num):
        path  = WORK_DIR / f"fallback_{i}.jpg"
        color = gradients[i % len(gradients)]
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={color}:size=1080x1920:duration=1",
            "-vframes", "1", str(path)
        ], capture_output=True)
        paths.append(path)
    return paths


# ──────────────────────────────────────────────
# STEP 4: Background Music
# ──────────────────────────────────────────────
def get_bg_music(mood: str):
    print(f"\n🎵 Downloading background music ({mood})...")

    # Multiple fallback URLs per mood
    music_options = {
        "dark": [
            "https://cdn.pixabay.com/download/audio/2022/03/24/audio_2cdb05b432.mp3",
            "https://cdn.pixabay.com/download/audio/2021/11/01/audio_cb4f5a2c08.mp3",
        ],
        "suspense": [
            "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946b2ded06.mp3",
            "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d1718ab41b.mp3",
        ],
        "horror": [
            "https://cdn.pixabay.com/download/audio/2023/03/09/audio_c5af65f1d1.mp3",
            "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a73467.mp3",
        ],
        "mystery": [
            "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3",
            "https://cdn.pixabay.com/download/audio/2021/08/09/audio_dc39bede17.mp3",
        ],
    }

    urls       = music_options.get(mood, music_options["dark"])
    music_path = WORK_DIR / "bg_music.mp3"

    for url in urls:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 10000:
                with open(music_path, "wb") as f:
                    f.write(r.content)
                print(f"  ✅ Music downloaded ({len(r.content)//1024}KB)")
                return music_path
        except Exception as e:
            print(f"  ⚠️ Music URL failed: {e}")

    print("  ⚠️ All music URLs failed")
    return None


# ──────────────────────────────────────────────
# STEP 5: Assemble Video
# ──────────────────────────────────────────────
def assemble_video(assets: list, audio_path: Path, music_path, script_data: dict):
    print("\n🎬 Assembling video...")

    output_path = WORK_DIR / "final_short.mp4"
    bg_path     = WORK_DIR / "background.mp4"
    audio_mix   = WORK_DIR / "audio_mix.aac"

    # Get audio duration
    result   = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_path)
    ], capture_output=True, text=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])
    print(f"  Duration: {duration:.1f}s | Assets: {len(assets)}")

    # Clean thumbnail text
    thumbnail_text = re.sub(r'[^A-Z0-9 ]', '', script_data.get("thumbnail_text", "RAHASYA FACTS").upper()).strip()
    if not thumbnail_text:
        thumbnail_text = "RAHASYA FACTS"

    # ── BUILD SLIDESHOW from all assets ──
    images = [(t, p) for t, p in assets if t == "image"]
    videos = [(t, p) for t, p in assets if t == "video"]

    # Convert videos to images (extract frame) for uniform slideshow
    all_images = list(images)
    for i, (_, vpath) in enumerate(videos):
        frame_path = WORK_DIR / f"frame_{i}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(vpath),
            "-ss", "00:00:01", "-vframes", "1",
            str(frame_path)
        ], capture_output=True)
        if frame_path.exists() and frame_path.stat().st_size > 1000:
            all_images.append(("image", frame_path))

    # If still no images, use fallbacks
    if not all_images:
        fallbacks = generate_fallback_images(4)
        all_images = [("image", p) for p in fallbacks]

    # Each image shows for equal duration
    num_images   = len(all_images)
    img_duration = duration / num_images
    print(f"  📸 Slideshow: {num_images} images × {img_duration:.1f}s each")

    # Write concat file
    concat_file = WORK_DIR / "slideshow.txt"
    with open(concat_file, "w") as f:
        for _, ipath in all_images:
            f.write(f"file '{ipath.absolute()}'\n")
            f.write(f"duration {img_duration:.3f}\n")
        # Repeat last image to avoid black end frame
        _, last = all_images[-1]
        f.write(f"file '{last.absolute()}'\n")

    # Build slideshow with zoom effect
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", (
            "scale=1920:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan=z='if(eq(on,1),1.0,min(zoom+0.0008,1.2))'"
            ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            ":d=1:s=1080x1920:fps=25"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-t", str(duration + 0.5), "-r", "25", "-an",
        str(bg_path)
    ], capture_output=True)

    if r.returncode != 0:
        print(f"  ⚠️ Zoom effect failed, using simple slideshow")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-t", str(duration + 0.5), "-r", "25", "-an",
            str(bg_path)
        ], check=True, capture_output=True)

    print("  ✅ Slideshow built")

    # ── MIX AUDIO ──
    if music_path and music_path.exists() and music_path.stat().st_size > 1000:
        r = subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(music_path),
            "-i", str(audio_path),
            "-filter_complex",
            "[0:a]volume=0.08[music];[1:a]volume=1.0[voice];[music][voice]amix=inputs=2:duration=second[aout]",
            "-map", "[aout]",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            str(audio_mix)
        ], capture_output=True)

        if r.returncode == 0:
            final_audio = audio_mix
            print("  ✅ Audio mixed with bg music")
        else:
            final_audio = audio_path
            print(f"  ⚠️ Audio mix failed: {r.stderr.decode()[-200:]}")
    else:
        final_audio = audio_path
        print("  ⚠️ No bg music available")

    # ── COMBINE: VIDEO + AUDIO + TEXT ──
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(bg_path),
        "-i", str(final_audio),
        "-vf", (
            # Darken edges for dramatic look
            "vignette=PI/5,"
            # Title at top
            f"drawtext=text='{thumbnail_text}':"
            "fontsize=58:fontcolor=white:borderw=5:bordercolor=black@0.8:"
            "x=(w-text_w)/2:y=h*0.07:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Watermark at bottom
            "drawtext=text='@RahasyaFacts':"
            "fontsize=26:fontcolor=white@0.85:borderw=2:bordercolor=black:"
            "x=(w-text_w)/2:y=h*0.93:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-r", "25",
        str(output_path)
    ], check=True)

    print(f"  ✅ Final video ready!")
    return output_path


# ──────────────────────────────────────────────
# STEP 6: SEO
# ──────────────────────────────────────────────
def generate_seo(script_data: dict, trending_context: list):
    print("\n🔍 Generating SEO...")

    title = script_data.get("title", "Dark Facts India")

    # Power words
    power_words = ["Shocking", "Dark Secret", "Hidden Truth", "Scary", "Mysterious", "Untold"]
    has_power   = any(w.lower() in title.lower() for w in power_words)
    if not has_power and len(title) < 45:
        title = f"{random.choice(power_words)} {title}"
    title = title[:100]

    # Build clean tags — only alphanumeric and spaces
    def clean_tag(t):
        return re.sub(r'[^a-zA-Z0-9 ]', '', str(t)).strip()[:30]

    ai_tags = [clean_tag(t) for t in script_data.get("tags", []) if clean_tag(t)]

    base_tags = [
        "facts", "shorts", "viral", "trending", "india",
        "dark facts", "mystery", "rahasya", "indian mystery",
        "mysterious facts", "horror facts", "unknown facts india",
        "rahasya facts", "anokhe facts", "hindi facts",
        "RahasyaFacts", "youtubeshorts", "viralshorts", "shorts india",
    ]

    trend_tags = []
    for topic in trending_context[:3]:
        tag = clean_tag(" ".join(topic.split()[:2]))
        if tag:
            trend_tags.append(tag)

    all_tags   = list(dict.fromkeys(ai_tags + base_tags + trend_tags))
    final_tags = [t for t in all_tags if len(t) > 1][:30]

    # Description — clean, no special unicode box chars
    desc = f"""{title}

Subscribe for daily dark and mysterious facts!
Share if this fact shocked you!
Comment below what you think!

dark facts india mysterious facts hindi shocking indian history rahasya facts india ke rahasya horror facts hindi

Trending: {' '.join(trending_context[:2])}

#Shorts #RahasyaFacts #DarkFacts #MysteriousFacts #IndianFacts #ViralShorts #Hindi #Rahasya"""

    print(f"  ✅ Tags: {len(final_tags)} | Title: {title}")
    return {"title": title, "description": desc[:4900], "tags": final_tags}


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

    access_token = get_youtube_token()

    # Final tag clean — guaranteed safe for YouTube API
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

    print(f"  🏷️ Tags ({len(safe_tags)}): {safe_tags[:5]}...")

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

    up = requests.put(
        upload_url,
        headers={"Content-Type": "video/mp4", "Content-Length": str(len(video_data))},
        data=video_data
    )

    video_id = up.json().get("id")
    print(f"  ✅ Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("\n🚀 RahasyaFacts Bot Starting...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    try:
        trending   = get_trending_context()
        script     = generate_script(trending)
        audio      = generate_voiceover(script["script"])
        assets     = download_visuals(script.get("visual_keywords", ["mystery", "ancient ruins", "dark forest", "night sky"]))
        music      = get_bg_music(script.get("bg_music_mood", "dark"))
        video      = assemble_video(assets, audio, music, script)
        seo        = generate_seo(script, trending)
        video_id   = upload_to_youtube(video, seo)

        print(f"\n🎉 SUCCESS!")
        print(f"🔗 https://youtube.com/shorts/{video_id}")
        print(f"📌 {seo['title']}")
        print(f"🏷️ {len(seo['tags'])} SEO tags applied")

    except Exception as e:
        import traceback
        print(f"\n❌ {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
