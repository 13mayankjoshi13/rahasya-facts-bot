"""
RahasyaFacts - Dark & Mysterious Facts YouTube Shorts Bot
Fully automated: Script → Voiceover → Images → Video → Upload
"""

import os
import json
import time
import random
import requests
import subprocess
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIG — fill these in via GitHub Secrets
# ──────────────────────────────────────────────
GROQ_API_KEY       = os.environ["GROQ_API_KEY"]
YOUTUBE_CLIENT_ID  = os.environ["YOUTUBE_CLIENT_ID"]
YOUTUBE_CLIENT_SECRET = os.environ["YOUTUBE_CLIENT_SECRET"]
YOUTUBE_REFRESH_TOKEN = os.environ["YOUTUBE_REFRESH_TOKEN"]
HF_API_KEY         = os.environ.get("HF_API_KEY", "")  # optional

WORK_DIR = Path("output")
WORK_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# STEP 1: Generate Script via Groq (Free LLM)
# ──────────────────────────────────────────────
def generate_script():
    print("📝 Generating script with Groq...")

    prompt = """You are a viral YouTube Shorts scriptwriter for an Indian facts channel called 'RahasyaFacts'.

Write a 45-60 second dark, mysterious, or shocking fact video script in Hinglish (mix of Hindi and English).

Rules:
- Start with a SHOCKING hook in the first 3 seconds (make viewer unable to scroll)
- One surprising, lesser-known fact per video
- Use dramatic, curious tone
- End with a cliffhanger or mind-blowing conclusion
- Include [PAUSE] markers for dramatic effect
- Script must feel like a story, not just facts

Also provide:
- TITLE: A clickbait-style, curiosity-driven YouTube title (max 60 chars)
- THUMBNAIL_TEXT: 4-5 bold words for thumbnail overlay
- TAGS: 10 relevant YouTube tags

Output as JSON:
{
  "title": "...",
  "thumbnail_text": "...",
  "tags": ["...", "..."],
  "script": "..."
}"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "max_tokens": 1000
        }
    )

    content = response.json()["choices"][0]["message"]["content"]

    # Strip markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    data = json.loads(content.strip())
    print(f"✅ Title: {data['title']}")
    return data


# ──────────────────────────────────────────────
# STEP 2: Generate Voiceover via Edge TTS (Free)
# ──────────────────────────────────────────────
def generate_voiceover(script: str):
    print("🎙️ Generating voiceover with Edge TTS...")

    # Clean script for TTS (remove stage directions)
    clean_script = script.replace("[PAUSE]", "...").replace("[pause]", "...")

    audio_path = WORK_DIR / "voiceover.mp3"

    # Using edge-tts: Indian English voice, slightly slower for drama
    cmd = [
        "edge-tts",
        "--voice", "hi-IN-MadhurNeural",   # Hindi voice — dramatic & deep
        "--text", clean_script,
        "--rate", "-10%",                   # Slightly slower = more dramatic
        "--pitch", "-5Hz",                  # Deeper pitch = mysterious feel
        "--write-media", str(audio_path)
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ Voiceover saved: {audio_path}")
    return audio_path


# ──────────────────────────────────────────────
# STEP 3: Generate Background Images (HuggingFace)
# ──────────────────────────────────────────────
def generate_images(title: str, num_images: int = 5):
    print("🎨 Generating background images...")
    image_paths = []

    if not HF_API_KEY:
        print("⚠️ No HF_API_KEY — using dark gradient fallback images")
        return generate_fallback_images(num_images)

    # Dark, mysterious image prompts based on the title
    prompts = [
        f"dark mysterious cinematic scene, {title}, dramatic lighting, fog, shadows, ultra realistic, 4k",
        f"ancient indian mystery, dark forest, mystical glow, cinematic, dramatic atmosphere",
        f"dark cosmic space mystery, ancient ruins, dramatic shadows, atmospheric",
        f"mysterious glowing portal, dark background, dramatic lighting, ethereal",
        f"ancient secrets revealed, dark dramatic scene, cinematic quality"
    ]

    for i, prompt in enumerate(prompts[:num_images]):
        try:
            response = requests.post(
                "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
                headers={"Authorization": f"Bearer {HF_API_KEY}"},
                json={"inputs": prompt},
                timeout=60
            )
            if response.status_code == 200:
                img_path = WORK_DIR / f"img_{i}.jpg"
                with open(img_path, "wb") as f:
                    f.write(response.content)
                image_paths.append(img_path)
                print(f"  ✅ Image {i+1} generated")
            else:
                print(f"  ⚠️ Image {i+1} failed, using fallback")
                image_paths.extend(generate_fallback_images(1))
        except Exception as e:
            print(f"  ⚠️ Image {i+1} error: {e}")
            image_paths.extend(generate_fallback_images(1))
        time.sleep(1)

    return image_paths


def generate_fallback_images(num: int):
    """Generate dark gradient images using FFmpeg as fallback"""
    paths = []
    colors = ["0x0a0a0a", "0x1a0a2e", "0x16213e", "0x0f3460", "0x1a1a2e"]
    for i in range(num):
        path = WORK_DIR / f"fallback_{i}.jpg"
        color = colors[i % len(colors)]
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
def assemble_video(image_paths: list, audio_path: Path, script_data: dict):
    print("🎬 Assembling video with FFmpeg...")

    output_path = WORK_DIR / "final_short.mp4"

    # Get audio duration
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(audio_path)
    ], capture_output=True, text=True)
    duration = float(json.loads(result.stdout)["format"]["duration"])
    print(f"  Audio duration: {duration:.1f}s")

    # Create image list file for FFmpeg
    img_duration = duration / len(image_paths)
    concat_file = WORK_DIR / "images.txt"
    with open(concat_file, "w") as f:
        for img in image_paths:
            f.write(f"file '{img.absolute()}'\n")
            f.write(f"duration {img_duration:.2f}\n")
        # repeat last image to avoid black frame
        f.write(f"file '{image_paths[-1].absolute()}'\n")

    # Title text for overlay
    thumbnail_text = script_data.get("thumbnail_text", "RAHASYA FACTS")

    # FFmpeg command: images + audio + captions overlay + dark vignette
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-filter_complex",
        (
            # Scale to vertical 9:16 (1080x1920)
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            # Dark vignette for mysterious feel
            "vignette=PI/4,"
            # Animated zoom effect (Ken Burns)
            "zoompan=z='min(zoom+0.0015,1.5)':d=1:s=1080x1920:fps=30,"
            # Title text overlay
            f"drawtext=text='{thumbnail_text}':"
            "fontsize=72:fontcolor=white:borderw=4:bordercolor=black:"
            "x=(w-text_w)/2:y=h*0.12:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
            # Channel watermark
            "drawtext=text='@RahasyaFacts':"
            "fontsize=36:fontcolor=white@0.7:borderw=2:bordercolor=black:"
            "x=w*0.05:y=h*0.92:"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            "[v]"
        ),
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-r", "30",
        str(output_path)
    ]

    subprocess.run(cmd, check=True)
    print(f"✅ Video assembled: {output_path}")
    return output_path


# ──────────────────────────────────────────────
# STEP 5: Upload to YouTube
# ──────────────────────────────────────────────
def get_youtube_token():
    """Exchange refresh token for access token"""
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

🔔 Subscribe to RahasyaFacts for daily dark & mysterious facts!
📲 Share this with someone who loves mysteries!

#Shorts #RahasyaFacts #DarkFacts #MysteriousFacts #IndianFacts #ViralShorts #Facts #Mystery #Hindi #Hinglish

{' '.join(['#' + t.replace(' ', '') for t in tags])}"""

    # Step 1: Initialize upload
    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags + ["Shorts", "RahasyaFacts", "facts", "mystery"],
            "categoryId": "28",  # Science & Technology (broad)
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

    # Step 2: Upload video file
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
        # Step 1: Generate script
        script_data = generate_script()

        # Step 2: Generate voiceover
        audio_path = generate_voiceover(script_data["script"])

        # Step 3: Generate images
        image_paths = generate_images(script_data["title"], num_images=6)

        # Step 4: Assemble video
        video_path = assemble_video(image_paths, audio_path, script_data)

        # Step 5: Upload to YouTube
        video_id = upload_to_youtube(video_path, script_data)

        print(f"\n🎉 SUCCESS! Short uploaded: https://youtube.com/shorts/{video_id}")
        print(f"📌 Title: {script_data['title']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
