"""
NaaTak Time - Daily Cartoon Drama YouTube Shorts Bot
Styles: Saas-Bahu scenes + WhatsApp chat drama + Simple cartoon characters
Language: Pure Hindi
Auto-uploads daily to YouTube
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
PEXELS_API_KEY        = os.environ.get("PEXELS_API_KEY", "")

WORK_DIR = Path("output")
WORK_DIR.mkdir(exist_ok=True)

WIDTH  = 1080
HEIGHT = 1920
FPS    = 30

# Drama styles that rotate daily
STYLES = ["whatsapp", "cartoon", "saas_bahu"]

# Character color schemes
CHARACTERS = {
    "saas":    {"color": "0xFF6B6B", "name": "Saas Ji",    "emoji": "👩‍🦳"},
    "bahu":    {"color": "0xFF9FF3", "name": "Bahu",       "emoji": "👩"},
    "pati":    {"color": "0x74B9FF", "name": "Pati",       "emoji": "👨"},
    "nanand":  {"color": "0xFECE5A", "name": "Nanand",     "emoji": "👧"},
    "sasur":   {"color": "0x55EFC4", "name": "Sasur Ji",   "emoji": "👴"},
}


# ──────────────────────────────────────────────
# STEP 0: Get Trending Topics
# ──────────────────────────────────────────────
def get_trending_context():
    print("🔥 Fetching trending topics...")
    topics = []

    for subreddit in ["india", "bollywood", "indiameme", "indianmeme"]:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10",
                headers={"User-Agent": "NaaTakTime-Bot/1.0"},
                timeout=10
            )
            if r.status_code == 200:
                posts = r.json()["data"]["children"]
                for post in posts:
                    t = post["data"].get("title", "")
                    if len(t) > 5:
                        topics.append(t)
                print(f"  ✅ r/{subreddit}: {len(posts)} posts")
        except Exception as e:
            print(f"  ⚠️ {subreddit}: {e}")

    try:
        r = requests.get(
            "https://trends.google.com/trending/rss?geo=IN",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            titles = re.findall(r'<title><!\[CDATA\[(.*?)\]\]></title>', r.text)
            google = [t for t in titles if t != "Google Trends" and len(t) > 3]
            topics += google
            print(f"  ✅ Google Trends: {google[:3]}")
    except Exception as e:
        print(f"  ⚠️ Google Trends: {e}")

    if not topics:
        topics = [
            "shaadi mein drama", "kitchen fight", "festival preparation",
            "bahu ne khana nahi banaya", "saas ki shopping",
            "pati ki salary", "ghar ka kaam", "rishtedaar aa gaye",
        ]

    print(f"  🎯 {len(topics)} topics\n")
    return topics


# ──────────────────────────────────────────────
# STEP 1: Generate Drama Script
# ──────────────────────────────────────────────
def generate_script(trending_context: list, style: str):
    print(f"📝 Generating {style} drama script...")

    top_topics = trending_context[:5]

    style_prompts = {
        "whatsapp": """Write a WHATSAPP CHAT DRAMA script.
Format as a conversation between family members over WhatsApp.
Each message: CHARACTER_NAME: message text
Keep messages short like real WhatsApp texts.
Include reactions, voice note references, seen ticks drama.
Make it relatable and funny.""",

        "cartoon": """Write a CARTOON DRAMA script.
Format as stage directions + dialogue.
Characters interact in exaggerated cartoon style.
Include physical comedy moments like: *saas girti hai*, *bahu roti hai*, *pati bhaag jaata hai*
Overdramatic reactions for everything.""",

        "saas_bahu": """Write a SAAS BAHU TV SERIAL style drama script.
Over-the-top dramatic dialogue like Star Plus serials.
Include dramatic pauses (...), evil laughs, crying.
Background music moments: *dramatic music*
Plot twist at the end.
Characters: Saas Ji, Bahu, Pati, optional Nanand/Sasur."""
    }

    prompt = f"""Tu ek viral Indian YouTube Shorts channel 'NaaTak Time' ka head writer hai.
Pure Hindi mein likho — bilkul waise jaise Indian TV serials aur memes mein hoti hai.

AAJ KE TRENDING TOPICS (inse inspiration lo):
{chr(10).join([f"- {t}" for t in top_topics])}

{style_prompts.get(style, style_prompts["saas_bahu"])}

RULES:
- Pure Hindi only — koi English words nahi except common ones like "WhatsApp", "ok", "bye"
- Maximum funny aur relatable banao
- 55-65 seconds ka content
- Har line pe tension ya comedy honi chahiye
- End mein twist ya punchline zaroor ho
- Viewer ko comment karne par majboor karo

OUTPUT ONLY RAW JSON:
{{"title": "viral hindi title max 55 chars no special chars", "thumbnail_text": "3 CAPS HINDI WORDS IN ENGLISH SCRIPT", "characters": ["Saas Ji", "Bahu", "Pati"], "dialogue": [{{"character": "Saas Ji", "line": "dialogue here", "emotion": "angry"}}, {{"character": "Bahu", "line": "dialogue here", "emotion": "crying"}}], "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"], "style": "{style}"}}"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.95,
            "max_tokens": 1500
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

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fix common issue: unescaped quotes inside string values
        import re as re2
        # Remove control characters
        content = re2.sub(r'[\x00-\x1f\x7f]', '', content)
        # Try to fix unescaped quotes within values (basic heuristic)
        content = content.replace('\\"', '"').replace('"', '\\"')
        content = content.replace('\\"{', '{').replace('}\\"', '}')
        content = content.replace('\\"[', '[').replace(']\\"', ']')
        content = content.replace(': \\"', ': "').replace('\\",', '",').replace('\\"}', '"}')
        content = content.replace('\\"\\n', '"\n')
        try:
            data = json.loads(content)
        except Exception as e2:
            print(f"  ⚠️ JSON still broken, retrying generation...")
            raise Exception(f"JSON parse failed even after cleanup: {e2}")
    print(f"  ✅ Title: {data['title']}")
    print(f"  ✅ Characters: {data.get('characters', [])}")
    print(f"  ✅ Dialogue lines: {len(data.get('dialogue', []))}\n")
    return data


# ──────────────────────────────────────────────
# STEP 2: Generate Voiceovers for Each Character
# ──────────────────────────────────────────────
def generate_character_voices(dialogue: list):
    print("🎙️ Generating character voices...")

    from gtts import gTTS

    # Different voice settings per character type
    voice_settings = {
        "saas":   {"speed": "0.92", "pitch": "-2"},   # Slower, lower = older woman
        "bahu":   {"speed": "1.05", "pitch": "+2"},   # Slightly faster = younger
        "pati":   {"speed": "1.0",  "pitch": "-4"},   # Normal, deeper = man
        "nanand": {"speed": "1.1",  "pitch": "+3"},   # Faster, higher = young girl
        "sasur":  {"speed": "0.88", "pitch": "-5"},   # Slowest, deepest = old man
    }

    audio_segments = []
    silence_path   = WORK_DIR / "silence.mp3"

    # Create 0.4s silence for between dialogues
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", "0.4", "-c:a", "libmp3lame",
        str(silence_path)
    ], capture_output=True)

    for i, item in enumerate(dialogue):
        char_name = item.get("character", "Saas Ji").lower()
        line      = item.get("line", "")
        emotion   = item.get("emotion", "normal")

        if not line.strip():
            continue

        # Map character name to type
        char_type = "bahu"
        for key in voice_settings:
            if key in char_name.lower():
                char_type = key
                break

        raw_path  = WORK_DIR / f"voice_{i}_raw.mp3"
        proc_path = WORK_DIR / f"voice_{i}.mp3"

        try:
            tts = gTTS(text=line.strip(), lang='hi', slow=False)
            tts.save(str(raw_path))

            # Apply character-specific audio processing
            settings = voice_settings.get(char_type, voice_settings["bahu"])
            speed    = settings["speed"]

            # Emotion-based processing
            if emotion in ["angry", "gussa"]:
                audio_filter = f"atempo={speed},volume=1.4,bass=g=2"
            elif emotion in ["crying", "rona", "sad"]:
                audio_filter = f"atempo={float(speed)*0.9},volume=0.9,aecho=0.8:0.9:100:0.3"
            elif emotion in ["happy", "khush"]:
                audio_filter = f"atempo={float(speed)*1.05},volume=1.2,treble=g=3"
            elif emotion in ["shocked", "shocked"]:
                audio_filter = f"atempo={float(speed)*1.1},volume=1.3"
            else:
                audio_filter = f"atempo={speed},volume=1.1"

            r = subprocess.run([
                "ffmpeg", "-y", "-i", str(raw_path),
                "-af", audio_filter,
                str(proc_path)
            ], capture_output=True)

            if r.returncode != 0 or not proc_path.exists():
                # Simple fallback
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(raw_path),
                    "-af", f"atempo={speed}",
                    str(proc_path)
                ], capture_output=True)

            audio_segments.append({
                "audio":     proc_path,
                "character": item.get("character", ""),
                "line":      line,
                "emotion":   emotion,
                "char_type": char_type
            })
            print(f"  ✅ {item.get('character')}: {line[:30]}...")

        except Exception as e:
            print(f"  ⚠️ Voice failed for line {i}: {e}")

    # Concatenate all voices with silence between
    if not audio_segments:
        raise Exception("No audio segments generated!")

    concat_file = WORK_DIR / "audio_concat.txt"
    with open(concat_file, "w") as f:
        for j, seg in enumerate(audio_segments):
            f.write(f"file '{seg['audio'].absolute()}'\n")
            if j < len(audio_segments) - 1:
                f.write(f"file '{silence_path.absolute()}'\n")

    final_audio = WORK_DIR / "final_voice.mp3"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(final_audio)
    ], check=True, capture_output=True)

    print(f"  ✅ All voices merged: {final_audio.stat().st_size//1024}KB\n")
    return final_audio, audio_segments


# ──────────────────────────────────────────────
# STEP 3: Generate Drama Background Music
# ──────────────────────────────────────────────
def get_drama_music(duration: float):
    print("🎵 Generating drama background music...")

    music_path = WORK_DIR / "bg_music.mp3"
    dur        = duration + 3

    # Dramatic violin-style music using FFmpeg
    # High frequency = dramatic/tense feel like TV serial music
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}",   # A4 note
        "-f", "lavfi", "-i", f"sine=frequency=523:duration={dur}",   # C5 note
        "-f", "lavfi", "-i", f"sine=frequency=659:duration={dur}",   # E5 note
        "-f", "lavfi", "-i", f"sine=frequency=880:duration={dur}",   # A5 note
        "-filter_complex",
        (
            "[0]volume=0.06,tremolo=f=4:d=0.3[a];"
            "[1]volume=0.04,tremolo=f=4:d=0.3[b];"
            "[2]volume=0.03,tremolo=f=6:d=0.4[c];"
            "[3]volume=0.02,tremolo=f=8:d=0.5[d];"
            "[a][b][c][d]amix=inputs=4:duration=longest,"
            "lowpass=f=2000,volume=0.7[out]"
        ),
        "-map", "[out]",
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(music_path)
    ], capture_output=True)

    if r.returncode == 0 and music_path.exists():
        print(f"  ✅ Drama music: {music_path.stat().st_size//1024}KB\n")
        return music_path

    print("  ⚠️ Music generation failed\n")
    return None


# ──────────────────────────────────────────────
# STEP 4: Create Video Based on Style
# ──────────────────────────────────────────────
def create_video(style: str, script_data: dict, audio_segments: list,
                 final_audio: Path, music_path, duration: float):
    print(f"🎬 Creating {style} style video...")

    if style == "whatsapp":
        return create_whatsapp_video(script_data, audio_segments, final_audio, music_path, duration)
    elif style == "cartoon":
        return create_cartoon_video(script_data, audio_segments, final_audio, music_path, duration)
    else:
        return create_saas_bahu_video(script_data, audio_segments, final_audio, music_path, duration)


# ──────────────────────────────────────────────
# Style A: WhatsApp Chat Video
# ──────────────────────────────────────────────
def create_whatsapp_video(script_data, audio_segments, final_audio, music_path, duration):
    print("  📱 Creating WhatsApp chat style...")

    output_path = WORK_DIR / "final_short.mp4"
    frames_dir  = WORK_DIR / "frames"
    frames_dir.mkdir(exist_ok=True)

    # WhatsApp color scheme
    bg_color      = "1E1E1E"   # Dark background
    sent_color    = "005C4B"   # Dark green (sent)
    received_color = "2A2A2A"  # Dark grey (received)
    text_color    = "FFFFFF"

    dialogue = script_data.get("dialogue", [])
    if not dialogue:
        raise Exception("No dialogue found!")

    # Calculate timing for each message
    msg_duration = duration / max(len(dialogue), 1)

    # Generate each frame with progressive chat reveal
    frame_paths = []
    visible_msgs = []

    for i, seg in enumerate(audio_segments[:len(dialogue)]):
        visible_msgs.append({
            "character": seg["character"],
            "line":      seg["line"],
            "char_type": seg["char_type"]
        })

        # Determine if sent or received (alternate)
        is_sent = (i % 2 == 1)

        # Build drawtext commands for all visible messages
        frame_path = frames_dir / f"frame_{i:04d}.png"

        # Create frame with Python + FFmpeg drawtext
        text_filters = []
        y_pos = 200

        # Title at top
        title_clean = re.sub(r'[^a-zA-Z0-9 \u0900-\u097F]', '', script_data.get('title', 'NaaTak Time'))

        text_filters.append(
            f"drawtext=text='NaaTak Time':"
            f"fontsize=42:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=60:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        )

        for j, msg in enumerate(visible_msgs[-8:]):  # Show last 8 messages
            char_name  = msg["character"]
            line       = msg["line"][:40]  # Truncate long lines
            char_is_sent = (j % 2 == 1)

            # Clean text for FFmpeg
            clean_line = re.sub(r"['\"\[\]{}|\\^~`<>]", "", line)
            clean_name = re.sub(r"['\"\[\]{}|\\^~`<>]", "", char_name)

            if char_is_sent:
                x_pos = "w-text_w-60"
                bubble_color = "005C4B"
            else:
                x_pos = "60"
                bubble_color = "2A2A2A"

            # Character name
            text_filters.append(
                f"drawtext=text='{clean_name}':"
                f"fontsize=22:fontcolor=55EFC4:borderw=2:bordercolor=black:"
                f"x={x_pos}:y={y_pos}:"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            )
            y_pos += 30

            # Message text
            text_filters.append(
                f"drawtext=text='{clean_line}':"
                f"fontsize=28:fontcolor=white:borderw=2:bordercolor=black:"
                f"box=1:boxcolor={bubble_color}@0.95:boxborderw=15:"
                f"x={x_pos}:y={y_pos}:"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            )
            y_pos += 80

        # Generate frame
        vf = ",".join(text_filters)
        r = subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=#{bg_color}:size={WIDTH}x{HEIGHT}:duration=0.04",
            "-vframes", "1",
            "-vf", vf,
            str(frame_path)
        ], capture_output=True)

        if r.returncode == 0:
            frame_paths.append((frame_path, msg_duration))

    if not frame_paths:
        raise Exception("No frames generated!")

    # Build concat file
    concat_file = WORK_DIR / "frames.txt"
    with open(concat_file, "w") as f:
        for fpath, fdur in frame_paths:
            f.write(f"file '{fpath.absolute()}'\n")
            f.write(f"duration {fdur:.3f}\n")
        f.write(f"file '{frame_paths[-1][0].absolute()}'\n")

    return finalize_video(concat_file, final_audio, music_path, duration,
                          script_data, output_path, is_image_concat=True)


# ──────────────────────────────────────────────
# Style B: Cartoon Character Video
# ──────────────────────────────────────────────
def create_cartoon_video(script_data, audio_segments, final_audio, music_path, duration):
    print("  🎨 Creating cartoon style...")

    output_path = WORK_DIR / "final_short.mp4"
    frames_dir  = WORK_DIR / "frames"
    frames_dir.mkdir(exist_ok=True)

    dialogue     = script_data.get("dialogue", [])
    msg_duration = duration / max(len(audio_segments), 1)
    frame_paths  = []

    for i, seg in enumerate(audio_segments):
        char_type = seg.get("char_type", "bahu")
        char_info = CHARACTERS.get(char_type, CHARACTERS["bahu"])
        line      = seg["line"][:45]
        emotion   = seg.get("emotion", "normal")
        frame_path = frames_dir / f"frame_{i:04d}.png"

        # Clean text
        clean_line = re.sub(r"['\"\[\]{}|\\^~`<>@]", "", line)
        char_name  = re.sub(r"['\"\[\]{}|\\^~`<>@]", "", seg["character"])

        # Emotion face
        emotion_faces = {
            "angry":   ">:(",
            "crying":  ":'(",
            "happy":   ":D",
            "shocked": ":O",
            "normal":  ":)",
            "gussa":   ">:(",
            "rona":    ":'(",
        }
        face = emotion_faces.get(emotion, ":)")

        # Character position — alternate sides
        is_left = (i % 2 == 0)
        char_x  = "100" if is_left else "w-300"
        bubble_x = "220" if is_left else "60"
        bubble_align = "60" if is_left else "w-text_w-60"

        # Build cartoon frame with character body + speech bubble
        vf = (
            # Dark purple background
            f"drawbox=x=0:y=0:w={WIDTH}:h={HEIGHT}:color=1a0a2e@1:t=fill,"
            # Ground line
            f"drawbox=x=0:y=1500:w={WIDTH}:h=50:color=2d1b69@1:t=fill,"
            # Character body (circle head)
            f"drawbox=x={char_x}:y=1000:w=120:h=120:color={char_info['color'][2:]}@0.9:t=fill,"
            # Character torso
            f"drawbox=x={char_x}:y=1120:w=120:h=200:color={char_info['color'][2:]}@0.8:t=fill,"
            # Character name
            f"drawtext=text='{char_name}':"
            f"fontsize=26:fontcolor=yellow:borderw=2:bordercolor=black:"
            f"x={bubble_align}:y=940:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Face expression
            f"drawtext=text='{face}':"
            f"fontsize=36:fontcolor=black:"
            f"x={char_x}:y=1025:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Speech bubble background
            f"drawbox=x=60:y=600:w=960:h=280:color=FFFFFF@0.15:t=fill,"
            f"drawbox=x=60:y=600:w=960:h=280:color=FFFFFF@0.4:t=3,"
            # Dialogue text
            f"drawtext=text='{clean_line}':"
            f"fontsize=34:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=680:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Channel watermark
            f"drawtext=text='@NaaTakTime':"
            f"fontsize=24:fontcolor=white@0.7:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y=h*0.935:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )

        r = subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c=1a0a2e:size={WIDTH}x{HEIGHT}:duration=0.04",
            "-vframes", "1", "-vf", vf,
            str(frame_path)
        ], capture_output=True)

        if r.returncode == 0 and frame_path.exists():
            frame_paths.append((frame_path, msg_duration))
            print(f"  ✅ Frame {i+1}: {char_name}")
        else:
            print(f"  ⚠️ Frame {i+1} failed: {r.stderr.decode()[-100:]}")

    if not frame_paths:
        raise Exception("No cartoon frames generated!")

    concat_file = WORK_DIR / "frames.txt"
    with open(concat_file, "w") as f:
        for fpath, fdur in frame_paths:
            f.write(f"file '{fpath.absolute()}'\n")
            f.write(f"duration {fdur:.3f}\n")
        f.write(f"file '{frame_paths[-1][0].absolute()}'\n")

    return finalize_video(concat_file, final_audio, music_path, duration,
                          script_data, output_path, is_image_concat=True)


# ──────────────────────────────────────────────
# Style C: Saas Bahu TV Serial Style
# ──────────────────────────────────────────────
def create_saas_bahu_video(script_data, audio_segments, final_audio, music_path, duration):
    print("  📺 Creating Saas Bahu TV serial style...")

    output_path = WORK_DIR / "final_short.mp4"
    frames_dir  = WORK_DIR / "frames"
    frames_dir.mkdir(exist_ok=True)

    msg_duration = duration / max(len(audio_segments), 1)
    frame_paths  = []

    # TV serial color palette
    bg_colors = ["1a0530", "2d0a4e", "3d1060", "1a0530"]

    for i, seg in enumerate(audio_segments):
        char_type  = seg.get("char_type", "bahu")
        char_info  = CHARACTERS.get(char_type, CHARACTERS["bahu"])
        line       = seg["line"][:50]
        emotion    = seg.get("emotion", "normal")
        frame_path = frames_dir / f"frame_{i:04d}.png"
        bg_col     = bg_colors[i % len(bg_colors)]

        clean_line = re.sub(r"['\"\[\]{}|\\^~`<>@]", "", line)
        char_name  = re.sub(r"['\"\[\]{}|\\^~`<>@]", "", seg["character"])

        # Emotion indicator
        emotion_text = {
            "angry":   "GUSSA MODE ON",
            "crying":  "RO RAHI HAI...",
            "shocked": "SHOCK LAG GAYA!",
            "happy":   "KHUSH HAI!",
            "normal":  "",
            "evil":    "SHAITAN HANSI...",
        }.get(emotion, "")

        # TV serial style — dramatic close-up look
        vf_parts = [
            # Rich dramatic background
            f"drawbox=x=0:y=0:w={WIDTH}:h={HEIGHT}:color={bg_col}@1:t=fill",
            # Decorative border top
            f"drawbox=x=0:y=0:w={WIDTH}:h=8:color=FFD700@1:t=fill",
            # Decorative border bottom
            f"drawbox=x=0:y={HEIGHT-8}:w={WIDTH}:h=8:color=FFD700@1:t=fill",
            # Channel name top
            "drawtext=text='NaaTak Time':"
            "fontsize=38:fontcolor=FFD700:borderw=3:bordercolor=black:"
            "x=(w-text_w)/2:y=25:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # Star decoration
            f"drawtext=text='★ ★ ★':"
            f"fontsize=30:fontcolor=FFD700:borderw=1:bordercolor=black:"
            f"x=(w-text_w)/2:y=80:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # Character emoji (large)
            f"drawtext=text='{char_info['emoji']}':"
            f"fontsize=180:fontcolor=white:"
            f"x=(w-text_w)/2:y=280:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # Character name plate
            f"drawbox=x=200:y=820:w=680:h=60:color=FFD700@0.9:t=fill",
            f"drawtext=text='{char_name}':"
            f"fontsize=32:fontcolor=black:borderw=0:"
            f"x=(w-text_w)/2:y=832:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # Emotion indicator
        ]

        if emotion_text:
            vf_parts.append(
                f"drawtext=text='{emotion_text}':"
                f"fontsize=28:fontcolor=FF6B6B:borderw=2:bordercolor=black:"
                f"x=(w-text_w)/2:y=900:"
                f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            )

        # Dramatic dialogue box
        vf_parts += [
            f"drawbox=x=40:y=1000:w={WIDTH-80}:h=350:color=000000@0.7:t=fill",
            f"drawbox=x=40:y=1000:w={WIDTH-80}:h=350:color=FFD700@0.6:t=4",
            # Quote marks
            f"drawtext=text='\"':"
            f"fontsize=80:fontcolor=FFD700@0.5:borderw=0:"
            f"x=60:y=1010:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # Dialogue
            f"drawtext=text='{clean_line}':"
            f"fontsize=36:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=1100:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # Episode style text
            f"drawtext=text='Aaj Ka Natak':"
            f"fontsize=26:fontcolor=FFD700@0.8:borderw=1:bordercolor=black:"
            f"x=(w-text_w)/2:y=1420:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # Watermark
            f"drawtext=text='@NaaTakTime':"
            f"fontsize=24:fontcolor=white@0.6:borderw=2:bordercolor=black:"
            f"x=(w-text_w)/2:y={HEIGHT-50}:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

        vf = ",".join(vf_parts)

        r = subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={bg_col}:size={WIDTH}x{HEIGHT}:duration=0.04",
            "-vframes", "1", "-vf", vf,
            str(frame_path)
        ], capture_output=True)

        if r.returncode == 0 and frame_path.exists():
            frame_paths.append((frame_path, msg_duration))
            print(f"  ✅ Frame {i+1}: {char_name} ({emotion})")
        else:
            print(f"  ⚠️ Frame {i+1} failed: {r.stderr.decode()[-150:]}")

    if not frame_paths:
        raise Exception("No TV serial frames generated!")

    concat_file = WORK_DIR / "frames.txt"
    with open(concat_file, "w") as f:
        for fpath, fdur in frame_paths:
            f.write(f"file '{fpath.absolute()}'\n")
            f.write(f"duration {fdur:.3f}\n")
        f.write(f"file '{frame_paths[-1][0].absolute()}'\n")

    return finalize_video(concat_file, final_audio, music_path, duration,
                          script_data, output_path, is_image_concat=True)


# ──────────────────────────────────────────────
# Finalize: Add audio and encode final video
# ──────────────────────────────────────────────
def finalize_video(concat_file, final_audio, music_path, duration,
                   script_data, output_path, is_image_concat=True):
    print("  🎞️ Finalizing video...")

    bg_path   = WORK_DIR / "background.mp4"
    audio_mix = WORK_DIR / "audio_mix.mp3"

    # Build slideshow
    r = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", str(duration + 0.5),
        "-r", str(FPS), "-an",
        str(bg_path)
    ], capture_output=True)

    if r.returncode != 0:
        raise Exception(f"Slideshow failed: {r.stderr.decode()[-200:]}")

    print(f"  ✅ Slideshow: {bg_path.stat().st_size//1024}KB")

    # Mix audio
    if music_path and music_path.exists():
        r = subprocess.run([
            "ffmpeg", "-y",
            "-i", str(final_audio),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex",
            "[0:a]volume=1.2[v];[1:a]volume=0.06[m];[v][m]amix=inputs=2:duration=first[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(audio_mix)
        ], capture_output=True)
        final_audio_path = audio_mix if r.returncode == 0 else final_audio
        print(f"  ✅ Audio mixed" if r.returncode == 0 else "  ⚠️ Using voice only")
    else:
        final_audio_path = final_audio

    # Final combine
    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(bg_path),
        "-i", str(final_audio_path),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path)
    ], capture_output=True)

    if r.returncode != 0:
        raise Exception(f"Final combine failed: {r.stderr.decode()[-200:]}")

    size = output_path.stat().st_size
    print(f"  ✅ Final video: {size//1024}KB")

    if size < 200000:
        raise Exception(f"Video too small: {size//1024}KB")

    return output_path


# ──────────────────────────────────────────────
# STEP 5: SEO
# ──────────────────────────────────────────────
def generate_seo(script_data: dict, trending_context: list, style: str):
    print("🔍 Generating SEO...")

    title = script_data.get("title", "Aaj Ka Natak")

    # Add drama hook if missing
    hooks = ["😂", "😱", "🤣", "💀", "🔥"]
    if not any(h in title for h in hooks):
        hook = random.choice(["Dekho Kya Hua Jab", "Aaj Ka Bada Natak", "Ye Kya Ho Gaya"])
        if len(title) + len(hook) + 3 < 95:
            title = f"{hook} - {title}"
    title = title[:100]

    def clean_tag(t):
        return re.sub(r'[^a-zA-Z0-9 ]', '', str(t)).strip()[:28]

    ai_tags   = [clean_tag(t) for t in script_data.get("tags", []) if clean_tag(t)]
    base_tags = [
        "natak", "comedy", "shorts", "viral", "india",
        "saas bahu", "hindi comedy", "indian drama",
        "funny shorts", "hindi natak", "desi comedy",
        "NaaTakTime", "youtubeshorts", "viralshorts",
        "family drama", "indian family", "gharelu natak",
        "saas bahu drama", "hindi shorts", "trending india",
    ]
    trend_tags = [clean_tag(" ".join(t.split()[:2])) for t in trending_context[:3]]
    final_tags = list(dict.fromkeys(
        [t for t in ai_tags + base_tags + trend_tags if len(t) > 1]
    ))[:30]

    desc = (
        f"{title}\n\n"
        "Roze naye natak! Subscribe karo aur bell icon dabaao!\n"
        "Like karo agar ye scene aapke ghar mein bhi hota hai!\n"
        "Comment mein likho — Team Saas ya Team Bahu?\n\n"
        "KEYWORDS: saas bahu drama hindi comedy natak indian family drama "
        "funny shorts hindi natak desi comedy gharelu natak viral shorts india\n\n"
        f"Trending: {' | '.join(trending_context[:3])}\n\n"
        "#Shorts #NaaTakTime #SaasBahu #HindiComedy #Natak "
        "#DesiComedy #ViralShorts #IndianDrama #FunnyShorts #Hindi"
    )

    print(f"  ✅ Title: {title}")
    print(f"  ✅ Tags: {len(final_tags)}\n")
    return {"title": title, "description": desc[:4900], "tags": final_tags}


# ──────────────────────────────────────────────
# STEP 6: Upload to YouTube
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
    print("📤 Uploading to YouTube...")

    size = video_path.stat().st_size
    print(f"  📁 {size//1024}KB")

    if size < 200000:
        raise Exception(f"Video too small: {size//1024}KB")

    access_token = get_youtube_token()
    safe_tags    = [re.sub(r'[^a-zA-Z0-9 ]', '', t).strip() for t in seo["tags"]]
    safe_tags    = [t for t in safe_tags if 1 < len(t) <= 30][:30]

    metadata = {
        "snippet": {
            "title":                seo["title"][:100],
            "description":          seo["description"][:4900],
            "tags":                 safe_tags,
            "categoryId":           "23",   # Comedy category
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
            "Authorization":           f"Bearer {access_token}",
            "Content-Type":            "application/json",
            "X-Upload-Content-Type":   "video/mp4",
            "X-Upload-Content-Length": str(size)
        },
        json=metadata
    )

    print(f"  📡 API: {init.status_code}")
    if init.status_code not in [200, 201]:
        raise Exception(f"YouTube API error {init.status_code}: {init.text[:300]}")

    upload_url = init.headers["Location"]
    CHUNK      = 5 * 1024 * 1024
    uploaded   = 0

    with open(video_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            end = uploaded + len(chunk) - 1
            r   = requests.put(
                upload_url,
                headers={
                    "Content-Type":   "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range":  f"bytes {uploaded}-{end}/{size}"
                },
                data=chunk, timeout=120
            )
            uploaded += len(chunk)
            print(f"  ⬆️ {100*uploaded//size}%")

            if r.status_code in [200, 201]:
                video_id = r.json().get("id")
                print(f"  ✅ https://youtube.com/shorts/{video_id}")
                return video_id
            elif r.status_code == 308:
                continue
            else:
                raise Exception(f"Upload error: {r.status_code}")

    raise Exception("Upload incomplete")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("\n🎭 NaaTak Time Bot Starting...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    try:
        # Pick style — rotate through all 3 daily
        day_of_year = datetime.now().timetuple().tm_yday
        style       = STYLES[day_of_year % len(STYLES)]
        print(f"🎨 Today's style: {style.upper()}\n")

        # Step 0: Trending
        trending = get_trending_context()

        # Step 1: Script
        script = generate_script(trending, style)

        # Step 2: Character voices
        dialogue              = script.get("dialogue", [])
        final_audio, segments = generate_character_voices(dialogue)

        # Step 3: Get audio duration
        result   = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(final_audio)
        ], capture_output=True, text=True)
        duration = float(json.loads(result.stdout)["format"]["duration"])
        print(f"⏱️ Total duration: {duration:.1f}s\n")

        # Step 4: Drama music
        music = get_drama_music(duration)

        # Step 5: Create video
        video = create_video(style, script, segments, final_audio, music, duration)

        # Step 6: SEO
        seo = generate_seo(script, trending, style)

        # Step 7: Upload
        video_id = upload_to_youtube(video, seo)

        print("\n" + "=" * 50)
        print("🎉 NaaTak Time — UPLOAD SUCCESS!")
        print(f"🔗 https://youtube.com/shorts/{video_id}")
        print(f"📌 {seo['title']}")
        print(f"🎨 Style: {style.upper()}")
        print(f"🏷️ {len(seo['tags'])} SEO tags")
        print("=" * 50)

    except Exception as e:
        import traceback
        print(f"\n❌ FAILED: {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
