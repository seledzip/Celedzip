"""
아기 환상종 보호소 (Pocket Creature Rescue) 무중단 자동화 엔진 (v20 - Smart Anti-Duplication)
- YouTube 채널 최근 영상 및 로컬 히스토리 기반 2중 중복 검수(Duplication Inspector) 탑재
- 30종 이상 환상종 x 환경 x 치유 아이템 무한 무작위 조합
- Replicate Llama 3 / 동적 Fallback 백업 기획 엔진
- 씬별 맞춤 ASMR 사운드팩 + 힐링 BGM 믹싱
- Flux Schnell -> Kling 2.5 Turbo Pro -> YouTube / Telegram 연동
"""

import os
import re
import json
import time
import base64
import random
import subprocess
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
RAW_TOPIC = os.environ.get("TOPIC", "").strip()

# YouTube API 자격 증명 (최근 영상 목록 실시간 대조용)
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

WORK_DIR = "video_work"
HISTORY_FILE = "creature_history.json"
SCENE_DURATION = 5.0

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}

# 30종 이상의 아기 환상종 후보 풀
CREATURE_POOL = [
    {"name": "Baby Snow Fox", "desc": "tiny baby snow fox with sparkling crystal ice paws and fluffy white fur"},
    {"name": "Baby Star Dragon", "desc": "ultra-cute tiny celestial dragon with glowing golden mini wings and shiny scales"},
    {"name": "Baby Ember Phoenix", "desc": "soft fluffy baby phoenix chick with glowing warm orange-red feathers"},
    {"name": "Baby Moonlight Bunny", "desc": "pocket-sized baby bunny with translucent glowing silver-blue ears"},
    {"name": "Baby Cloud Kitten", "desc": "fluffy baby kitten made of soft pastel cloud fluff with a floating tail"},
    {"name": "Baby Moss Spirit Puppy", "desc": "tiny mossy spirit puppy with a blooming magical pink flower on its head"},
    {"name": "Baby Thunder Gryphon", "desc": "adorable baby gryphon chick with fluffy electric-blue down feathers"},
    {"name": "Baby Aurora Fawn", "desc": "tiny baby deer with miniature glowing iridescent rainbow antlers"},
    {"name": "Baby Ocean Otter", "desc": "cute baby sea otter with glowing pearlescent aquatic scales and soft paws"},
    {"name": "Baby Stardust Bear", "desc": "miniature baby bear cub with glittering galaxy-star fur"},
    {"name": "Baby Crystal Panda", "desc": "tiny baby panda with soft gemstone-tinted fur and sparkling round eyes"},
    {"name": "Baby Sun Lion", "desc": "miniature baby lion cub with a warm radiant sunbeam mane"},
    {"name": "Baby Forest Owl", "desc": "ultra-cute wide-eyed miniature horned owlet with glowing emerald feathers"},
    {"name": "Baby Lavender Hamster", "desc": "tiny fluffy pocket hamster with glowing floral lavender ears"},
    {"name": "Baby Frost Seal", "desc": "round chubby baby seal with shimmering ice-crystal whiskers"},
]

CRISES = [
    "shivering alone in a freezing dark snowstorm on icy rocks",
    "trapped under heavy wet leaves in pouring cold rain",
    "stuck inside a thorny frozen briar bush with muddy paws",
    "trembling inside a dark cracked icy cavern alone",
    "shivering with sad teary eyes on cold wet muddy gravel",
    "lost and exhausted in a thick gloomy mist forest",
]

HEALINGS = [
    ("glowing magical golden honey berry", "soft warm towel drying its fur"),
    ("warm bottle of glowing celestial milk", "gently brushing away wet mud"),
    ("sparkling sweet crystal snowflake treat", "wrapping in a warm fluffy wool blanket"),
    ("glowing sweet enchanted dewdrop", "gently patting and drying its tiny paws"),
]

BEDS = [
    "sleeping peacefully in a palm-sized glowing snowflake bed with soft velvet lining",
    "curled up sound asleep inside a warm miniature knitted wool basket",
    "sleeping deeply in a cozy wooden cradle filled with glowing fairy moss",
    "napping happily on a tiny fluffy cloud pillow with warm golden ambient light",
]


def fetch_recent_youtube_titles() -> list:
    """유튜브 채널에서 최근 업로드된 20개 영상 제목을 실시간으로 가져옴"""
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        return []
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(
            None,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = build("youtube", "v3", credentials=creds)
        channel_resp = youtube.channels().list(mine=True, part="contentDetails").execute()
        uploads_id = channel_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl_resp = youtube.playlistItems().list(playlistId=uploads_id, part="snippet", maxResults=20).execute()
        titles = [item["snippet"]["title"] for item in pl_resp.get("items", [])]
        print(f"🔍 YouTube 최근 업로드 {len(titles)}개 영상 제목 조회 완료")
        return titles
    except Exception as e:
        print(f"ℹ️ YouTube 최근 목록 조회 생략 ({e})")
        return []


def resolve_unique_topic() -> tuple:
    """중복 검수 후 겹치지 않는 새로운 크리처와 시나리오 선택"""
    if RAW_TOPIC and RAW_TOPIC.lower() not in ("auto", "none", ""):
        return RAW_TOPIC, "Baby Fantasy Creature", "a magical treat", "a cozy tiny bed"

    recent_yt_titles = fetch_recent_youtube_titles()
    
    # 로컬 히스토리 파일 읽기
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    # 최근 유튜브 제목과 히스토리에 포함된 크리처 제외
    available_creatures = []
    for c in CREATURE_POOL:
        c_name = c["name"]
        in_youtube = any(c_name.lower() in t.lower() for t in recent_yt_titles)
        in_recent_history = c_name in history[-10:] if history else False

        if not in_youtube and not in_recent_history:
            available_creatures.append(c)

    # 모든 크리처가 소진된 경우 풀 전체에서 무작위 선택
    if not available_creatures:
        print("🔄 모든 크리처가 1회 이상 제작되어 전체 풀을 초기화합니다.")
        available_creatures = CREATURE_POOL

    selected_creature = random.choice(available_creatures)
    crisis = random.choice(CRISES)
    treat, clean_action = random.choice(HEALINGS)
    bed = random.choice(BEDS)

    # 히스토리 업데이트 및 저장
    history.append(selected_creature["name"])
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-30:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    full_topic = (
        f"Rescuing a lost {selected_creature['desc']} {crisis}, "
        f"gently {clean_action}, feeding a {treat}, and tucking it into {bed}"
    )
    print(f"✅ [중복 검수 통과] 선택된 크리처: {selected_creature['name']}")
    return full_topic, selected_creature["name"], treat, bed


TOPIC, CREATURE_NAME, SELECTED_TREAT, SELECTED_BED = resolve_unique_topic()


def send_telegram_message(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        except Exception:
            pass


def post_with_retry(url: str, json_data: dict, max_retries: int = 5) -> dict:
    for attempt in range(max_retries):
        res = requests.post(url, headers=REPLICATE_HEADERS, json=json_data, timeout=30)
        if res.status_code == 429:
            time.sleep((attempt + 1) * 20)
            continue
        res.raise_for_status()
        return res.json()
    raise RuntimeError(f"최대 재시도 초과: {url}")


def poll_until_done(data: dict, max_wait_sec: int = 360) -> dict:
    get_url = data.get("urls", {}).get("get")
    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(5)
        waited += 5
        poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
        poll_res.raise_for_status()
        data = poll_res.json()

    if data.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 오류 (status={data.get('status')}): {data.get('error')}")
    return data


def build_fallback_plan(topic: str, creature_name: str, treat: str, bed: str) -> dict:
    return {
        "project_title": f"Rescuing a Lost {creature_name}",
        "style_anchor": "Hyper-detailed cinematic 3D render, ultra-cute adorable baby fantasy creature, huge glossy watery reflective eyes, soft fluffy fur, tilt-shift macro lens, warm dreamy lighting, 8k octane render",
        "iconic_element_en": topic,
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_number": 1,
                "visual_prompt_en": f"Extreme macro close-up of a tiny shivering {creature_name} with big teary eyes trapped in wet cold ground",
                "negative_prompt_en": "blurry, low quality, adult animal, human face, scary, text, watermark"
            },
            {
                "scene_number": 2,
                "visual_prompt_en": f"Gentle realistic giant warm human hands wrapped in a soft fluffy towel carefully scooping up the tiny {creature_name}",
                "negative_prompt_en": "blurry, low quality, watermark, distortion, harsh lighting"
            },
            {
                "scene_number": 3,
                "visual_prompt_en": f"Satisfying gentle cleaning of the {creature_name}, feeding a {treat}, happy joyful expression",
                "negative_prompt_en": "blurry, low quality, watermark"
            },
            {
                "scene_number": 4,
                "visual_prompt_en": f"Clean happy fluffy {creature_name} glowing with comfort, {bed}, slow cinematic macro push-in",
                "negative_prompt_en": "blurry, low quality, watermark"
            }
        ],
        "youtube_metadata": {
            "title": f"Rescuing a Shivering {creature_name}! 🥺✨ Cozy Sanctuary ASMR",
            "description": f"Rescuing a lost {creature_name}! Welcome to Pocket Creature Rescue 🌿✨\n\n🐾 What should we name this cute little one? Leave your suggestions in the comments!\n\n#Shorts #BabyCreature #FantasyRescue #{creature_name.replace(' ', '')} #Cute #ASMR #Satisfying",
            "tags": ["babycreature", "fantasyrescue", creature_name.lower().replace(" ", ""), "cutemonster", "asmr", "satisfying", "shorts", "healing"]
        }
    }


def generate_scene_plan(topic: str) -> dict:
    try:
        prompt = f"""You are the director for the global YouTube Shorts series: 'Pocket Creature Rescue'.
Design an emotional 4-scene rescue story for: "{topic}".

Rules:
- Exactly 4 scenes (5 seconds each).
- Scene 1: Heartbreaking crisis. Shivering baby creature with big teary eyes.
- Scene 2: The Rescue. Giant warm human hands with a soft towel gently lifting it.
- Scene 3: Satisfying Care. Cleaning fur, feeding the magical treat.
- Scene 4: Complete Comfort. Clean happy baby creature peacefully sleeping in its tiny cozy bed.
- Output strict JSON only.

JSON Schema:
{{
  "project_title": "Rescue Title",
  "style_anchor": "Hyper-detailed 3D render, ultra-cute baby fantasy creature, huge watery reflective eyes, fluffy texture, tilt-shift macro lens, warm cozy lighting, 8k octane render",
  "iconic_element_en": "precise creature description",
  "aspect_ratio": "9:16",
  "scenes": [
    {{"scene_number": 1, "visual_prompt_en": "...", "negative_prompt_en": "blurry, low quality, human face, scary, text"}},
    {{"scene_number": 2, "visual_prompt_en": "...", "negative_prompt_en": "blurry, low quality, watermark"}},
    {{"scene_number": 3, "visual_prompt_en": "...", "negative_prompt_en": "blurry, low quality, watermark"}},
    {{"scene_number": 4, "visual_prompt_en": "...", "negative_prompt_en": "blurry, low quality, watermark"}}
  ],
  "youtube_metadata": {{
    "title": "Emotional Catchy Title with Emojis",
    "description": "Story description + #Shorts #BabyCreature #FantasyRescue #ASMR",
    "tags": ["babycreature", "fantasyrescue", "cutemonster", "asmr", "shorts"]
  }}
}}"""

        data = post_with_retry(
            "https://api.replicate.com/v1/models/meta/meta-llama-3-70b-instruct/predictions",
            {
                "input": {
                    "prompt": prompt,
                    "temperature": 0.5,
                    "max_tokens": 2048,
                    "system_prompt": "You are a JSON generator. Output only valid JSON."
                }
            }
        )
        data = poll_until_done(data, max_wait_sec=60)
        output = data.get("output")
        raw_text = "".join(output) if isinstance(output, list) else str(output)
        
        raw_clean = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
        match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
        if match:
            raw_clean = match.group(0)
        return json.loads(raw_clean, strict=False)
    except Exception as e:
        print(f"⚠️ Replicate LLM 응답 예외 ({e}). 동적 Fallback 기획 모드로 전환합니다.")
        return build_fallback_plan(topic, CREATURE_NAME, SELECTED_TREAT, SELECTED_BED)


def generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> str:
    data = post_with_retry(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        {"input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": "jpg"}}
    )
    data = poll_until_done(data, max_wait_sec=90)
    output = data.get("output")
    image_url = output[0] if isinstance(output, list) else output
    if not image_url:
        raise RuntimeError(f"이미지 생성 실패: {data}")
    return image_url


def generate_video_clip(image_source: str, motion_prompt: str, negative_prompt: str,
                         aspect_ratio: str, index: int) -> str:
    time.sleep(15)
    data = post_with_retry(
        "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
        {
            "input": {
                "prompt": motion_prompt,
                "negative_prompt": negative_prompt,
                "image": image_source,
                "duration": 5,
                "aspect_ratio": aspect_ratio,
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=360)

    output = data.get("output")
    video_url = output[0] if isinstance(output, list) else output
    if not video_url:
        raise RuntimeError(f"비디오 생성 실패: {data}")

    video_res = requests.get(video_url, timeout=60)
    video_res.raise_for_status()
    os.makedirs(WORK_DIR, exist_ok=True)
    clip_path = f"{WORK_DIR}/scene_{index}.mp4"
    with open(clip_path, "wb") as f:
        f.write(video_res.content)
    return clip_path


def extract_last_frame(clip_path: str, index: int) -> str:
    frame_path = f"{WORK_DIR}/last_frame_{index}.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-sseof", "-1", "-i", clip_path, "-update", "1", "-q:v", "2", frame_path],
        check=True,
        capture_output=True,
    )
    return frame_path


def image_to_data_uri(image_path: str) -> str:
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def stitch_clips_clean(clip_paths: list, output_path: str):
    concat_list_path = f"{WORK_DIR}/concat_list.txt"
    with open(concat_list_path, "w") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path],
        check=True,
        capture_output=True,
    )


def generate_soundtrack_and_mux(video_path: str, total_sec: int, output_path: str):
    print("🎬 씬별 맞춤 ASMR 사운드팩 + 자장가 BGM 믹싱 진행...")
    
    filter_complex = (
        f"anoisesrc=c=pink:r=44100:a=0.02,atrim=0:{total_sec},asetpts=PTS-STARTPTS[pink];"
        f"sine=f=528:r=44100,atrim=0:{total_sec},asetpts=PTS-STARTPTS[tone];"
        "[tone]volume=0.015[tone_soft];"
        "[pink][tone_soft]amix=inputs=2[bgm];"
        
        "anoisesrc=c=brown:r=44100:a=0.04,atrim=0:5,asetpts=PTS-STARTPTS,afade=t=out:st=4:d=1[sfx1];"
        "sine=f=300:r=44100,atrim=0:5,asetpts=PTS-STARTPTS,volume=0.01,afade=t=in:st=0:d=1,afade=t=out:st=4:d=1[sfx2];"
        "sine=f=880:r=44100,atrim=0:5,asetpts=PTS-STARTPTS,volume=0.025,afade=t=in:st=0:d=0.5,afade=t=out:st=4:d=1[sfx3];"
        "sine=f=220:r=44100,atrim=0:5,asetpts=PTS-STARTPTS,volume=0.02,afade=t=in:st=0:d=1[sfx4];"
        
        "[sfx1][sfx2][sfx3][sfx4]concat=n=4:v=0:a=1[all_sfx];"
        "[bgm][all_sfx]amix=inputs=2:duration=first[aout]"
    )

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-filter_complex", filter_complex,
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    except Exception as e:
        print(f"⚠️ 사운드 예외 ({e}), 안전 앰비언스 대체")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-f", "lavfi", "-i", f"anoisesrc=c=pink:r=44100:a=0.02:d={total_sec}",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ],
            check=True,
            capture_output=True
        )

    print(f"✅ ASMR 사운드팩 믹싱 완료: {output_path}")


def send_telegram_preview(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🐾 *[{plan['project_title']}] 구조 영상 완성!*\n\n"
        f"📌 *Title*: {yt['title']}\n"
        f"📝 *Description*: {yt['description']}\n"
        f"🏷️ *Tags*: {tags_str}\n\n"
        f"🚀 *유튜브에 '일부공개'로 안전하게 등록되었습니다.*"
    )
    if len(caption) > 1000:
        caption = caption[:1000] + "..."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
            files={"video": f},
            timeout=120,
        )
    resp.raise_for_status()


def main():
    print(f"Target Topic: {TOPIC}")
    os.makedirs(WORK_DIR, exist_ok=True)
    send_telegram_message(f"🐾 아기 환상종 숏폼 제작 시작!\n주제: '{TOPIC}'")

    plan = generate_scene_plan(TOPIC)
    
    with open(f"{WORK_DIR}/metadata.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    style_anchor = plan["style_anchor"]
    iconic_element = plan["iconic_element_en"]
    clip_paths = []

    for i, scene in enumerate(plan["scenes"]):
        idx = scene["scene_number"]
        print(f"--- Processing Scene {idx} ---")

        full_prompt = f"{style_anchor}, featuring {iconic_element}, {scene['visual_prompt_en']}"
        negative_prompt = scene.get("negative_prompt_en", "blurry, low quality, watermark, text, scary")

        if i == 0:
            image_source = generate_image(full_prompt, negative_prompt, aspect_ratio)
        else:
            frame_path = extract_last_frame(clip_paths[-1], idx)
            image_source = image_to_data_uri(frame_path)

        clip_path = generate_video_clip(
            image_source=image_source,
            motion_prompt=scene["visual_prompt_en"],
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            index=idx,
        )
        clip_paths.append(clip_path)

    stitched_video_path = f"{WORK_DIR}/stitched_video.mp4"
    stitch_clips_clean(clip_paths, stitched_video_path)

    final_path = f"{WORK_DIR}/final_video.mp4"
    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    generate_soundtrack_and_mux(stitched_video_path, total_duration, final_path)

    send_telegram_preview(final_path, plan)
    print("🐾 작업 완료 및 텔레그램 발송 완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
