"""
RahasyaFacts - Dark & Mysterious Facts YouTube Shorts Bot
Full Version: Meme trends + Trending topics + Real visuals + BG Music + Auto upload
"""

import os
import json
import re
import time
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
# STEP 0: Fetch Trending Memes & Topics in India
# ──────────────────────────────────────────────
def get_trending_context():
    """Fetch trending memes from Reddit India + Google Trends India"""
    print("🔥 Fetching trending memes and topics in India...")

    meme_topics = []
    google_topics = []

    # SOURCE 1: Reddit India memes (r/indiameme + r/indianmeme)
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
                        meme_topics.append(title)
                print(f"  ✅ r/{subreddit}: {len(posts)} posts fetched")
        except Exception as e:
            print(f"  ⚠️ Reddit r/{subreddit} failed: {e}")

    # SOURCE 2: Google Trends India
    try:
        r = requests.get(
            "https://trends.google.com/trending/rss?geo=IN",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', r.text)
            google_topics = [t for t in titles if t != "Google Trends" and len(t) > 3]
            print(f"  ✅ Google Trends: {google_topics[:5]}")
    except Exception as e:
        print(f"  ⚠️ Google Trends failed: {e}")

    # SOURCE 3: Twitter/X trending India (scrape via nitter)
    twitter_topics = []
    try:
        r = requests.get(
            "https://nitter.net/search?q=%23india+OR+%23bollywood+OR+%23indianmemes&f=tweets",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if r.status_code == 200:
            hashtags = re.findall(r'#(\w+)', r.text)
            twitter_topics = list(set([h for h in hashtags if len(h) > 3]))[:10]
            print(f"  ✅ Twitter hashtags: {twitter_topics[:5]}")
    except Exception as e:
        print(f"  ⚠️ Twitter scrape failed: {e}")

    # Combine all sources
    all_topics = meme_topics[:5] + google_topics[:5] + twitter_topics[:5]

    if not all_topics:
        print("  ⚠️ All sources failed — using fallback topics")
        all_topics = [
            "Indian historical mystery or hidden secret",
            "shocking ancient Indian ritual or tradition",
            "mysterious disappearance or unsolved Indian case",
            "dark secret about a famous Indian place or monument",
            "terrifying Indian supernatural legend",
            "shocking fact about Mughal era or British raj",
            "dark truth about a famous Indian personality",
            "creepy abandoned place in India",
            "mysterious tribe or village in India",
            "dark secret of an Indian royal family",
        ]

    print(f"\n  🎯 Total trending inputs: {len(all_topics)}")
    print(f"  📌 Top topics: {all_topics[:3]}")
    return all_topics


# ──────────────────────────────────────────────
# STEP 1: Generate Script via Groq
# ──────────────────────────────────────────────
def generate_script(trending_context: list):
    print("\n📝 Generating viral script with Groq...")

    # Pick top meme/trending topics as context
    top_memes    = trending_context[:3]
    backup_topic = random.choice(trending_context[3:]) if len(trending_context) > 3 else "dark Indian history"

    prompt = f"""You are a viral YouTube Shorts scriptwriter for 'RahasyaFacts' — India's #1 dark mysterious facts channel loved by Gen Z.

TODAY'S TRENDING MEMES & TOPICS IN INDIA:
{chr(10).join([f"- {t}" for t in top_memes])}

BACKUP TOPIC: {backup_topic}

YOUR TASK:
1. Look at the trending memes/topics above
2. Find a DARK, MYSTERIOUS, or SHOCKING historical/scientific fact connected to them
3. If a Bollywood actor is trending → reveal a dark unknown fact about them or their era
4. If a place is trending → reveal its dark mysterious history
5. If a meme format is trending → use that same energy/style in your script
6. If topics don't connect to dark facts → use the backup topic

Write a 45-55 second script in NATURAL Hinglish (exactly how Indian Gen Z speaks):
- Mix Hindi + English naturally like "Yaar ye sun ke mera dimaag ghoom gaya"
- Short punchy sentences, max 8-10 words each
- Use meme-style language: "Bhai", "Yaar", "No way", "Literally", "Bro sach mein"
- First line MUST be so shocking viewer can't scroll
- Build suspense sentence by sentence
- End with a jaw-dropping twist or reveal
- Make it feel like a juicy secret being whispered, not a school lecture

ALSO PROVIDE:
- title: Ultra viral Hinglish title with curiosity gap (use numbers, questions, shocking claims) — max 55 chars, no quotes or colons or special chars
- thumbnail_text: 3-4 CAPS dramatic English words for thumbnail overlay (no apostrophes, no special chars, no quotes)
- visual_keywords: Array of 4 SPECIFIC English search terms for stock footage matching the story topic exactly (e.g. ["ancient mughal palace", "dark jungle night", "old scroll manuscript", "mysterious ruins India"])
- bg_music_mood: one word only — "dark" or "suspense" or "horror" or "mystery"
- tags: 10 YouTube tags as array

OUTPUT ONLY RAW VALID JSON — no markdown, no backticks, no explanation, nothing else:
{{"title": "...", "thumbnail_text": "...", "visual_keywords": ["...", "...", "...", "..."], "bg_music_mood": "...", "tags": ["..."], "script": "..."}}"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.95,
            "max_tokens": 1200
        }
    )

    resp_json = response.json()
    content   = resp_json["choices"][0]["message"]["content"].strip()

    # Strip markdown fences
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            if "{" in part:
                content = part.replace("json", "", 1).strip()
                break

    content = content.replace("**", "").strip()

    # Extract JSON object
    start = content.find("{")
    end   = content.rfind("}") + 1
    if start != -1 and end > start:
        content = content[start:end]

    data = json.loads(content)
    print(f"  ✅ Title: {data['title']}")
    print(f"  ✅ Visual keywords: {data.get('visual_keywords', [])}")
    print(f"  ✅ Music mood: {data.get('bg_music_mood', 'dark')}")
    return data


# ──────────────────────────────────────────────
# STEP 2: Generate Voiceover (Natural Hindi)
# ──────────────────────────────────────────────
def generate_voiceover(script: str):
    print("\n🎙️ Generating voiceover...")

    clean_script = script.strip()
    audio_path   = WORK_DIR / "voiceover.mp3"
    fast_path    = WORK_DIR / "voiceover_fast.mp3"

    from gtts import gTTS
    tts = gTTS(text=clean_script, lang='hi', slow=False)
    tts.save(str(audio_path))

    # Speed up 1.2x — more energetic, less robotic
    subprocess.run([
        "ffmpeg", "-y", "-i", str(audio_path),
        "-filter:a", "atempo=1.2",
        str(fast_path)
    ], capture_output=True, check=True)

    print(f"  ✅ Voiceover ready (1.2x speed)")
    return fast_path


# ──────────────────────────────────────────────
# STEP 3: Download Topic-Specific Visuals
# ──────────────────────────────────────────────
def download_visuals(visual_keywords: list):
    """Download topic-matched videos + photos from Pexels"""
    print(f"\n🎬 Downloading topic-specific visuals...")

    all_assets = []

    for keyword in visual_keywords[:4]:
        print(f"  🔍 Searching: '{keyword}'")

        # Try video first
        try:
            r = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": keyword, "per_page": 3, "size": "small"},
                timeout=15
            )
            videos = r.json().get("videos", [])
            for video in videos[:1]:
                files = sorted(
                    video.get("video_files", []),
                    key=lambda x: x.get("width", 9999)
                )
                if not files:
                    continue
                url  = files[0]["link"]
                path = WORK_DIR / f"asset_{len(all_assets)}.mp4"
                vr   = requests.get(url, timeout=30)
                if vr.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(vr.content)
                    all_assets.append(("video", path))
                    print(f"  ✅ Video: {keyword}")
                    break
        except Exception as e:
            print(f"  ⚠️ Video failed '{keyword}': {e}")

        # Also grab a photo
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": keyword, "per_page": 3, "orientation": "portrait"},
                timeout=15
            )
            photos = r.json().get("photos", [])
            for photo in photos[:1]:
                url  = photo["src"].get("large") or photo["src"].get("medium")
                if not url:
                    continue
                path = WORK_DIR / f"asset_{len(all_assets)}.jpg"
                pr   = requests.get(url, timeout=20)
                if pr.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(pr.content)
                    all_assets.append(("image", path))
                    print(f"  ✅ Photo: {keyword}")
                    break
        except Exception as e:
            print(f"  ⚠️ Photo failed '{keyword}': {e}")

    print(f"  📊 Total assets downloaded: {len(all_assets)}")

    if not all_assets:
        print("  ⚠️ No assets — using dark gradient fallback")
        paths = generate_fallback_images(6)
        return [("image", p) for p in paths]

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
# STEP 4: Download Free Background Music
# ──────────────────────────────────────────────
def get_bg_music(mood: str):
    """Download royalty-free suspense/dark music from Pixabay"""
    print(f"\n🎵 Getting background music (mood: {mood})...")

    music_urls = {
        "dark":     "https://cdn.pixabay.com/download/audio/2022/03/24/audio_2cdb05b432.mp3",
        "suspense": "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946b2ded06.mp3",
        "horror":   "https://cdn.pixabay.com/download/audio/2023/03/09/audio_c5af65f1d1.mp3",
        "mystery":  "https://cdn.pixabay.com/download/audio/2022/08/02/audio_884fe92c21.mp3",
    }

    url        = music_urls.get(mood, music_urls["dark"])
    music_path = WORK_DIR / "bg_music.mp3"

    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(music_path, "wb") as f:
                f.write(r.content)
            print(f"  ✅ Background music downloaded")
            return music_path
    except Exception as e:
        print(f"  ⚠️ Music download failed: {e}")

    return None


# ──────────────────────────────────────────────
# STEP 5: Assemble Final Video with FFmpeg
# ──────────────────────────────────────────────
def assemble_video(assets: list, audio_path: Path, music_path, script_data: dict):
    print("\n🎬 Assembling final Short video...")

    output_path = WORK_DIR / "final_short.mp4"
    temp_path   = WORK_DIR / "temp_video.mp4"

    # Get audio duration
    result   = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(audio_path)
    ], capture_output=True, text=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])
    print(f"  Audio duration: {duration:.1f}s")

    # Clean thumbnail text — remove all chars that break FFmpeg
    thumbnail_text = script_data.get("thumbnail_text", "RAHASYA FACTS")
    thumbnail_text = (thumbnail_text
        .replace("'", "").replace('"', '').replace("**", "")
        .replace(":", "").replace("(", "").replace(")", "")
        .replace("/", "").replace("\\", "").replace(",", "")
        .replace("!", "").replace("?", "").upper().strip()
    )

    # Separate videos and images
    videos = [(t, p) for t, p in assets if t == "video"]
    images = [(t, p) for t, p in assets if t == "image"]

    # ── STEP A: Build background video ──
    if videos:
        concat_file = WORK_DIR / "concat.txt"
        with open(concat_file, "w") as f:
            total, idx = 0, 0
            while total < duration + 10:
                _, vpath = videos[idx % len(videos)]
                f.write(f"file '{vpath.absolute()}'\n")
                total += 6
                idx   += 1

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-t", str(duration + 2), "-r", "30", "-an",
            str(temp_path)
        ], check=True, capture_output=True)
        print("  ✅ Video background assembled")

    elif images:
        img_duration = duration / len(images)
        concat_file  = WORK_DIR / "images.txt"
        with open(concat_file, "w") as f:
            for _, ipath in images:
                f.write(f"file '{ipath.absolute()}'\n")
                f.write(f"duration {img_duration:.2f}\n")
            _, last = images[-1]
            f.write(f"file '{last.absolute()}'\n")

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "zoompan=z='min(zoom+0.002,1.3)':d=125:s=1080x1920:fps=25"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-t", str(duration + 2), "-r", "25", "-an",
            str(temp_path)
        ], check=True, capture_output=True)
        print("  ✅ Image slideshow assembled with zoom effect")

    else:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=0x1a0a2e:size=1080x1920:duration={duration+2}",
            "-c:v", "libx264", "-preset", "fast", "-r", "30", "-an",
            str(temp_path)
        ], check=True, capture_output=True)
        print("  ⚠️ Using dark fallback background")

    # ── STEP B: Mix voiceover + background music ──
    if music_path and music_path.exists():
        audio_mix = WORK_DIR / "audio_mix.mp3"
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(music_path),
            "-i", str(audio_path),
            "-filter_complex",
            "[0:a]volume=0.10[music];[1:a]volume=1.0[voice];[voice][music]amix=inputs=2:duration=second[aout]",
            "-map", "[aout]",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(audio_mix)
        ], check=True, capture_output=True)
        final_audio = audio_mix
        print("  ✅ Audio mixed with background music (10% volume)")
    else:
        final_audio = audio_path
        print("  ⚠️ No bg music — using voiceover only")

    # ── STEP C: Add text overlays + combine everything ──
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(temp_path),
        "-i", str(final_audio),
        "-vf", (
            # Dark overlay for readability
            "colorchannelmixer=rr=0.7:gg=0.7:bb=0.7,"
            # Thumbnail title at top
            f"drawtext=text='{thumbnail_text}':"
            "fontsize=62:fontcolor=white:borderw=5:bordercolor=black:"
            "x=(w-text_w)/2:y=h*0.07:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Channel watermark at bottom
            "drawtext=text='@RahasyaFacts':"
            "fontsize=28:fontcolor=white@0.9:borderw=2:bordercolor=black:"
            "x=(w-text_w)/2:y=h*0.93:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-r", "30",
        str(output_path)
    ], check=True)

    print(f"  ✅ Final video assembled!")
    return output_path


# ──────────────────────────────────────────────
# STEP 6: SEO Optimization
# ──────────────────────────────────────────────
def generate_seo(script_data: dict, trending_context: list):
    """Generate fully optimized title, description, tags for YouTube SEO"""
    print("\n🔍 Generating SEO optimization...")

    title  = script_data["title"]
    tags   = script_data.get("tags", [])
    script = script_data.get("script", "")

    # ── TITLE SEO ──
    # YouTube title best practices:
    # - Most searched words FIRST
    # - Power words that trigger curiosity
    # - Under 60 chars so it doesn't get cut off
    seo_power_words = [
        "Shocking", "Dark Secret", "Hidden Truth", "Nobody Knows",
        "Scary", "Mysterious", "Viral", "Untold", "Banned", "Leaked"
    ]

    # If title doesn't start with a power word, prepend one
    has_power_word = any(w.lower() in title.lower() for w in seo_power_words)
    if not has_power_word and len(title) < 45:
        title = f"{random.choice(seo_power_words[:5])} - {title}"
    title = title[:100]

    # ── TAGS SEO ──
    # YouTube allows up to 500 chars of tags
    # Mix of: broad tags + niche tags + trending tags + Hindi tags
    base_tags = [
        # Broad high-volume tags
        "facts", "shorts", "viral", "trending", "india",
        # Niche tags
        "dark facts", "mystery", "rahasya", "indian mystery",
        "dark secrets india", "shocking facts hindi",
        "mysterious facts", "horror facts", "unknown facts india",
        # Hindi tags (rank in Hindi searches)
        "rahasya facts", "anokhe facts", "dark rahasya",
        "hindi facts", "india ka rahasya", "shocking sach",
        # Channel brand tags
        "RahasyaFacts", "rahasya facts channel",
        # Shorts specific
        # Shorts specific
        "youtubeshorts", "shortsvideo", "viralshorts",
        "trending shorts", "shorts india",
    ]

    # Add AI generated tags from script
    ai_tags = [t.lower().strip() for t in tags if len(t) > 2]

    # Add trending topic tags
    trend_tags = []
    for topic in trending_context[:3]:
        words = topic.split()[:2]
        trend_tags.append(" ".join(words).lower())

    # Combine all tags, deduplicate, limit to 500 chars total
    all_tags = list(dict.fromkeys(ai_tags + base_tags + trend_tags))
    final_tags = []
    char_count = 0
    for tag in all_tags:
        # Clean tag — remove all special chars YouTube doesn't allow
        clean_tag = re.sub(r'[<>\[\]{}|\\^~`]', '', tag).strip()
        clean_tag = clean_tag[:30]  # max 30 chars per tag
        if not clean_tag or len(clean_tag) < 2:
            continue
        if char_count + len(clean_tag) + 1 < 490:
            final_tags.append(clean_tag)
            char_count += len(clean_tag) + 1
    print(f"  ✅ Total tags: {len(final_tags)}")

    # ── DESCRIPTION SEO ──
    # YouTube indexes description for search
    # Best practice: keywords in first 2 lines, then engagement CTAs, then hashtags
    trending_str = ", ".join(trending_context[:3])

    # Extract key topic words from script for description keywords
    seo_description = f"""{title}

{script[:200]}...

━━━━━━━━━━━━━━━━━━━━━━
🔔 Subscribe karo — Har din ek nayi dark mysterious fact!
📲 Share karo apne doston ke saath!
👇 Comment karo — Kya tumhe pehle se pata tha ye rahasya?
━━━━━━━━━━━━━━━━━━━━━━

🔍 Is video mein hai: dark facts india, mysterious facts hindi, shocking indian history, rahasya facts, anokhe tathya, india ke rahasya, horror facts hindi

📌 Trending today: {trending_str}

━━━━━━━━━━━━━━━━━━━━━━
#Shorts #RahasyaFacts #DarkFacts #MysteriousFacts #IndianFacts
#ViralShorts #HindiFacts #Rahasya #IndianMystery #ShockingFacts
#DarkSecrets #HorrorFacts #AndhereRahasya #IndiaKaRahasya
#{' #'.join([t.replace(' ', '') for t in final_tags[:15]])}
━━━━━━━━━━━━━━━━━━━━━━

⚠️ Disclaimer: Ye facts research aur public sources se liye gaye hain."""

    print(f"  ✅ SEO description ready ({len(seo_description)} chars)")
    print(f"  ✅ Optimized title: {title}")

    return {
        "title":       title,
        "description": seo_description,
        "tags":        final_tags
    }


# ──────────────────────────────────────────────
# STEP 7: Upload to YouTube
# ──────────────────────────────────────────────
def get_youtube_token():
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id":     YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": YOUTUBE_REFRESH_TOKEN,
            "grant_type":    "refresh_token"
        }
    )
    return response.json()["access_token"]


def upload_to_youtube(video_path: Path, script_data: dict, seo: dict):
    print("\n📤 Uploading to YouTube with full SEO...")

    access_token = get_youtube_token()

    metadata = {
        "snippet": {
            "title":           seo["title"][:100],
            "description":     seo["description"][:5000],
            "tags": cleaned_tags,
            "categoryId":      "27",   # 27 = Education (better for facts channels)
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi"
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False,
            "license":                 "youtube",
            "embeddable":              True,
            "publicStatsViewable":     True
        }
    }

    init_response = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization":         f"Bearer {access_token}",
            "Content-Type":          "application/json",
            "X-Upload-Content-Type": "video/mp4"
        },
        json=metadata
    )

    cleaned_tags = [re.sub(r'[^a-zA-Z0-9 ]', '', t).strip() for t in seo["tags"] if len(t.strip()) > 1]
    print(f"  🏷️ Final tags being sent: {cleaned_tags}")
    print(f"  📡 YouTube API status: {init_response.status_code}")
    print(f"  📡 YouTube API response: {init_response.text[:500]}")
    upload_url = init_response.headers["Location"]

    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_response = requests.put(
        upload_url,
        headers={
            "Content-Type":   "video/mp4",
            "Content-Length": str(len(video_data))
        },
        data=video_data
    )

    video_id = upload_response.json().get("id")
    print(f"  ✅ Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────
def main():
    print("\n🚀 RahasyaFacts Bot Starting...")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    try:
        # Step 0: Get trending memes + topics
        trending_context = get_trending_context()

        # Step 1: Generate script based on trends
        script_data = generate_script(trending_context)

        # Step 2: Voiceover
        audio_path = generate_voiceover(script_data["script"])

        # Step 3: Topic-specific visuals from Pexels
        visual_keywords = script_data.get("visual_keywords", ["mystery", "dark forest", "ancient ruins", "night sky"])
        assets = download_visuals(visual_keywords)

        # Step 4: Background music
        mood       = script_data.get("bg_music_mood", "dark")
        music_path = get_bg_music(mood)

        # Step 5: Assemble video
        video_path = assemble_video(assets, audio_path, music_path, script_data)

        # Step 6: SEO optimization
        seo = generate_seo(script_data, trending_context)

        # Step 7: Upload to YouTube with full SEO
        video_id = upload_to_youtube(video_path, script_data, seo)

        print(f"\n🎉 SUCCESS!")
        print(f"🔗 https://youtube.com/shorts/{video_id}")
        print(f"📌 Title: {seo['title']}")
        print(f"🏷️ Tags: {len(seo['tags'])} tags applied")

    except Exception as e:
        import traceback
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
