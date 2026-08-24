"""
아기 환상종 보호소 무중단 자동화 엔진 (v26.1 - 30 Creatures Zero-Duplication & Timed Subtitles, Fixed)
- [30종 환상종 풀 완비] 중복 발생 0% 보장 결정론적 순차 큐 알고리즘 적용
- 1~5씬 100% 무자막 청정 원본 렌더링 (Kling AI 글자 왜곡 원천 차단)
- 25초 병합본에 5초 단위 감성 동화 자막 단 1회 후가공 오버레이
- 텍스트 폭 자동 측정(Pillow) 기반 폰트 크기 동적 스케일링 (화면 잘림 방지)
- 28회차 달성 시 텔레그램 시즌 전환 사전 알림 발송
- [FIX] 30회차(시즌1 완료) 이후 회차 번호가 31화에 영구 고정되던 버그 수정
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

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

WORK_DIR = "video_work"
HISTORY_FILE = "creature_history.json"
SCENE_DURATION = 5.0

SFX_LIBRARY_DIR = "automation/sfx_library"
BGM_LIBRARY_DIR = "automation/sfx_library/bgm_ambient"

SCENE_SFX_MAP = {
    1: ["wind_cold_ambient", "soft_whimper_rustle"],
    2: ["soft_fabric_towel", "gentle_lift_rustle"],
    3: ["water_drops", "gentle_taps"],
    4: ["soft_blanket_tuck", "gentle_lift_rustle"],
    5: ["sparkle_chimes", "soft_blanket_tuck"],
}

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}

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
    {"name": "Baby Blossom Hedgehog", "desc": "tiny adorable hedgehog covered in soft glowing pink cherry blossom petals"},
    {"name": "Baby Amber Squirrel", "desc": "pocket baby squirrel with a glowing translucent amber gem tail"},
    {"name": "Baby Magma Turtle", "desc": "miniature warm baby turtle with a gentle glowing volcanic hot-spring shell"},
    {"name": "Baby Wind Pegasus", "desc": "ultra-cute miniature winged foal with silky flowing breeze mane"},
    {"name": "Baby Pearl Seahorse", "desc": "tiny luminous aquatic seahorse with iridescent rainbow fins"},
    {"name": "Baby Coral Axolotl", "desc": "miniature pink baby axolotl with blooming glowing coral gills"},
    {"name": "Baby Twilight Wolf", "desc": "fluffy baby wolf pup with soft glowing violet dusk fur"},
    {"name": "Baby Solar Red Panda", "desc": "adorable baby red panda with warm glowing sunburst tail stripes"},
    {"name": "Baby Rainbow Chameleon", "desc": "tiny pocket chameleon shifting through soft pastel iridescent colors"},
    {"name": "Baby Glacier Penguin", "desc": "chubby baby penguin chick wearing a sparkling crystal ice vest"},
    {"name": "Baby Golden Griffin", "desc": "miniature royal baby griffin with gleaming soft golden down feathers"},
    {"name": "Baby Celestial Peacock", "desc": "ultra-cute baby peachick with night-sky constellation tail feathers"},
    {"name": "Baby Dune Fennec", "desc": "pocket desert fennec fox with oversized warm glowing sand-fairy ears"},
    {"name": "Baby Dewdrop Frog", "desc": "tiny translucent tree frog with glowing pure morning dewdrops on its back"},
    {"name": "Baby Cosmo Whale", "desc": "palm-sized floating celestial baby whale with miniature stars orbiting around it"},
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
    "a palm-sized glowing snowflake bed with soft velvet lining",
    "a warm miniature knitted wool basket filled with glowing fairy cotton",
    "a cozy miniature wooden cradle lined with glowing magical moss",
    "a tiny fluffy cloud pillow nestled under warm golden fairy lights",
]


def fetch_recent_youtube_titles() -> list:
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
        pl_resp = youtube.playlistItems().list(playlistId=uploads_id, part="snippet", maxResults=50).execute()
        titles = [item["snippet"]["title"] for item in pl_resp.get("items", [])]
        print(f"🔍 YouTube 채널 최근 영상 {len(titles)}개 조회 완료")
        return titles
    except Exception as e:
        print(f"ℹ️ YouTube API 조회 생략 ({e})")
        return []


def send_telegram_message(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        except Exception:
            pass


def resolve_unique_topic() -> tuple:
    if RAW_TOPIC and RAW_TOPIC.lower() not in ("auto", "none", ""):
        return RAW_TOPIC, "Baby Fantasy Creature", "a magical treat", "a cozy tiny bed"

    recent_yt_titles = fetch_recent_youtube_titles()
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    used_creature_names = set(history)
    for t in recent_yt_titles:
        for c in CREATURE_POOL:
            if c["name"].lower() in t.lower():
                used_creature_names.add(c["name"])

    available_creatures = [c for c in CREATURE_POOL if c["name"] not in used_creature_names]

    if not available_creatures:
        cycle_idx = len(history) % len(CREATURE_POOL)
        selected_creature = CREATURE_POOL[cycle_idx]
    else:
        selected_creature = available_creatures[0]

    current_episode = len(history) + 1
    season = 1 if current_episode <= 30 else 2

    if current_episode == 28:
        alert_msg = (
            "🔔 [보호소 세계관 알림] 아기 환상종 시즌 1이 28회차에 도달했습니다!\n\n"
            "• 시즌 1(구조 & 수면): 앞으로 2회 남음 (총 30회 완결)\n"
            "• 31회차부터 [시즌 2: 모닝 루틴 & 힐링 스파 케어]로 전환 준비가 완료되었습니다.\n"
            "• 30회 완료 후 1시간 수면용 롱폼 컴필레이션 제작을 추천합니다."
        )
        send_telegram_message(alert_msg)

    crisis = random.choice(CRISES)
    treat, clean_action = random.choice(HEALINGS)
    bed = random.choice(BEDS)

    history.append(selected_creature["name"])
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    full_topic = (
        f"Rescuing a lost {selected_creature['desc']} {crisis}, "
        f"gently {clean_action}, feeding a {treat}, and tucking it into {bed}"
    )
    print(f"✅ [에피소드 {current_episode}화 / 시즌 {season}] 순차 배정 크리처 ({len(used_creature_names)+1}/30): {selected_creature['name']}")
    return full_topic, selected_creature["name"], treat, bed


TOPIC, CREATURE_NAME, SELECTED_TREAT, SELECTED_BED = resolve_unique_topic()


def post_with_retry(url: str, json_data: dict, max_retries: int = 5) -> dict:
    for attempt in range(max_retries):
        try:
            res = requests.post(url, headers=REPLICATE_HEADERS, json=json_data, timeout=30)
            if res.status_code == 429:
                time.sleep((attempt + 1) * 20)
                continue
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
    raise RuntimeError(f"최대 재시도 초과: {url}")


def poll_until_done(data: dict, max_wait_sec: int = 360) -> dict:
    get_url = data.get("urls", {}).get("get")
    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(5)
        waited += 5
        try:
            poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
            poll_res.raise_for_status()
            data = poll_res.json()
        except requests.exceptions.RequestException:
            continue

    if data.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 오류: {data.get('error')}")
    return data


def build_fallback_plan(topic: str, creature_name: str, treat: str, bed: str) -> dict:
    return {
        "project_title": f"Rescuing a Lost {creature_name}",
        "style_anchor": "Hyper-detailed cinematic 3D render, ultra-cute adorable baby fantasy creature, huge glossy watery reflective eyes, soft fluffy fur, tilt-shift macro lens, warm dreamy lighting, 8k octane render, no text, no watermark",
        "iconic_element_en": topic,
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_number": 1,
                "story_subtitle": f"Found a tiny {creature_name} shivering alone...",
                "visual_prompt_en": f"Extreme macro close-up of a tiny shivering {creature_name} with big teary eyes trapped in wet cold ground",
                "negative_prompt_en": "blurry, low quality, adult animal, human face, scary, text, watermark, letters"
            },
            {
                "scene_number": 2,
                "story_subtitle": "Step 1: Gentle rescue & warm towel wrap",
                "visual_prompt_en": f"Gentle realistic giant warm human hands wrapped in a soft fluffy towel carefully scooping up the tiny {creature_name}",
                "negative_prompt_en": "blurry, low quality, watermark, distortion, text, letters"
            },
            {
                "scene_number": 3,
                "story_subtitle": "Step 2: Feeding sweet enchanted treats",
                "visual_prompt_en": f"Satisfying gentle cleaning of the {creature_name}, feeding a {treat}, happy joyful smiling expression",
                "negative_prompt_en": "blurry, low quality, watermark, text, letters"
            },
            {
                "scene_number": 4,
                "story_subtitle": "Step 3: Tucking into a cozy miniature bed",
                "visual_prompt_en": f"Gentle warm hands slowly and carefully lowering the sleepy, full {creature_name} into {bed}, tucking it under a tiny cozy blanket",
                "negative_prompt_en": "blurry, low quality, watermark, text, letters"
            },
            {
                "scene_number": 5,
                "story_subtitle": "Safe and sound asleep. Goodnight little one...",
                "visual_prompt_en": f"Clean happy fluffy {creature_name} sound asleep and breathing peacefully inside {bed}, soft warm fairy lights glowing, slow cinematic macro zoom-in",
                "negative_prompt_en": "blurry, low quality, watermark, human hands, text, letters"
            }
        ],
        "youtube_metadata": {
            "title": f"Found a Shivering Baby {creature_name}! Rescue & Bedtime ASMR",
            "description": f"Rescuing a lost {creature_name}! Welcome to Pocket Creature Rescue 🌿✨\n\n🐾 What should we name this cute little one? Leave your suggestions in the comments!\n\n#Shorts #BabyCreature #{creature_name.replace(' ', '')} #Cute #ASMR",
            "tags": ["babycreature", "fantasyrescue", creature_name.lower().replace(" ", ""), "cutemonster", "asmr", "satisfying", "shorts", "healing"]
        }
    }


def generate_scene_plan(topic: str) -> dict:
    try:
        prompt = f"""You are the director for YouTube Shorts series: 'Pocket Creature Rescue'.
Design an emotional 5-scene rescue story for: "{topic}".

Rules:
- Exactly 5 scenes (5 seconds each, total 25 seconds).
- In 'story_subtitle', provide clean concise English narration (max 7 words, NO emoji).
  Scene 1: "Found a tiny {CREATURE_NAME} shivering alone..."
  Scene 2: "Step 1: Gentle rescue & warm towel wrap"
  Scene 3: "Step 2: Feeding sweet enchanted treats"
  Scene 4: "Step 3: Tucking into a cozy miniature bed"
  Scene 5: "Safe and sound asleep. Goodnight little one..."
- Title format: "Found a Shivering Baby {CREATURE_NAME}! Rescue & Bedtime ASMR"
- Output strict JSON only.

JSON Schema:
{{
  "project_title": "Rescue Title",
  "style_anchor": "Hyper-detailed 3D render, ultra-cute baby fantasy creature, huge watery reflective eyes, fluffy texture, tilt-shift macro lens, warm cozy lighting, 8k octane render, clean background, no text",
  "iconic_element_en": "precise creature description",
  "aspect_ratio": "9:16",
  "scenes": [
    {{"scene_number": 1, "story_subtitle": "...", "visual_prompt_en": "...", "negative_prompt_en": "blurry, text, watermark, letters"}},
    {{"scene_number": 2, "story_subtitle": "...", "visual_prompt_en": "...", "negative_prompt_en": "blurry, watermark, text, letters"}},
    {{"scene_number": 3, "story_subtitle": "...", "visual_prompt_en": "...", "negative_prompt_en": "blurry, watermark, text, letters"}},
    {{"scene_number": 4, "story_subtitle": "...", "visual_prompt_en": "...", "negative_prompt_en": "blurry, watermark, text, letters"}},
    {{"scene_number": 5, "story_subtitle": "...", "visual_prompt_en": "...", "negative_prompt_en": "blurry, human hands, text, letters"}}
  ],
  "youtube_metadata": {{
    "title": "Found a Shivering Baby [Name]! Rescue & Bedtime ASMR",
    "description": "Story description + What should we name this little one? #Shorts #BabyCreature #ASMR",
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
    except Exception:
        return build_fallback_plan(topic, CREATURE_NAME, SELECTED_TREAT, SELECTED_BED)


def generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> str:
    quality_enhancer = "sharp focus, ultra high detail, clean composition, studio lighting, masterpiece, no text, no watermark"
    full_prompt = f"{prompt}, {quality_enhancer}"

    data = post_with_retry(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro-ultra/predictions",
        {
            "input": {
                "prompt": full_prompt,
                "aspect_ratio": aspect_ratio,
                "output_format": "jpg",
                "raw": False,
                "safety_tolerance": 2,
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=120)
    output = data.get("output")
    image_url = output[0] if isinstance(output, list) else output
    return image_url


def generate_video_clip(image_source: str, motion_prompt: str, negative_prompt: str,
                         aspect_ratio: str, index: int) -> str:
    time.sleep(15)
    data = post_with_retry(
        "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
        {
            "input": {
                "prompt": motion_prompt,
                "negative_prompt": f"{negative_prompt}, text, letters, subtitles, watermark, blur",
                "image": image_source,
                "duration": 5,
                "aspect_ratio": aspect_ratio,
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=360)

    output = data.get("output")
    video_url = output[0] if isinstance(output, list) else output

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
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for path in clip_paths:
            clean_path = os.path.abspath(path).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path],
        check=True,
        capture_output=True,
    )


def _resolve_font_path() -> str:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else None,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _fit_fontsize_to_width(text: str, font_path: str, target_width: float,
                            start_size: int = 34, min_size: int = 22) -> int:
    if not font_path:
        return 28
    try:
        from PIL import ImageFont
        size = start_size
        while size >= min_size:
            font = ImageFont.truetype(font_path, size)
            bbox = font.getbbox(text)
            w = bbox[2] - bbox[0]
            if w <= target_width:
                return size
            size -= 1
        return min_size
    except Exception:
        return 28


def apply_timed_subtitles_post(stitched_video: str, plan: dict, output_path: str,
                                video_width: int = 1072) -> None:
    print("✍️ 25초 완성본 위에 시간대별 감성 동화 자막 오버레이 중 (동적 폭 스케일링)...")
    raw_font = _resolve_font_path()
    font_escaped = raw_font.replace("\\", "/").replace(":", "\\:") if raw_font else None

    target_width = video_width * 0.90
    draw_filters = []
    for i, sc in enumerate(plan["scenes"]):
        start_t = i * SCENE_DURATION
        end_t = (i + 1) * SCENE_DURATION
        txt = sc.get("story_subtitle", "").strip()
        txt_clean_str = re.sub(r"[^\w\s.,!?:'\-]", "", txt).strip()

        fontsize = _fit_fontsize_to_width(txt_clean_str, raw_font, target_width)

        txt_file = f"{WORK_DIR}/timed_sub_{i+1}.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(txt_clean_str)

        file_escaped = os.path.abspath(txt_file).replace("\\", "/").replace(":", "\\:")
        fontfile_clause = f"fontfile='{font_escaped}':" if font_escaped else ""

        draw_filters.append(
            f"drawtext={fontfile_clause}textfile='{file_escaped}':"
            f"fontcolor=white:fontsize={fontsize}:box=1:boxcolor=black@0.6:boxborderw=12:"
            f"x=(w-text_w)/2:y=h*0.12:enable='between(t,{start_t},{end_t})'"
        )

    vf_chain = ",".join(draw_filters)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", stitched_video,
                "-vf", vf_chain,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode(errors="ignore") if e.stderr else str(e)
        print(f"⚠️ 자막 합성 실패, 무자막 원본 복사로 안전망 가동: {err_msg[-300:]}")
        subprocess.run(["ffmpeg", "-y", "-i", stitched_video, "-c", "copy", output_path], check=True, capture_output=True)


def _pick_random_file(folder_path: str) -> str:
    if not os.path.isdir(folder_path):
        return None
    candidates = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a"))
    ]
    return random.choice(candidates) if candidates else None


def _has_any_sfx() -> bool:
    if not os.path.isdir(SFX_LIBRARY_DIR):
        return False
    if _pick_random_file(BGM_LIBRARY_DIR):
        return True
    for categories in SCENE_SFX_MAP.values():
        for cat in categories:
            if _pick_random_file(os.path.join(SFX_LIBRARY_DIR, cat)):
                return True
    return False


def generate_soundtrack_and_mux(video_path: str, total_sec: int, output_path: str):
    if not _has_any_sfx():
        _generate_synthetic_fallback_soundtrack(video_path, total_sec, output_path)
        return

    num_scenes = int(total_sec / SCENE_DURATION)
    inputs = ["-i", video_path]
    filter_parts = []

    bgm_path = _pick_random_file(BGM_LIBRARY_DIR)
    if bgm_path:
        inputs += ["-i", bgm_path]
        filter_parts.append(
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"atrim=0:{total_sec},asetpts=PTS-STARTPTS,volume=0.15,"
            f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(total_sec - 2.0, 0)}:d=2.0[bgm]"
        )
    else:
        inputs += ["-f", "lavfi", "-i", f"anoisesrc=c=pink:r=44100:a=0.015:d={total_sec}"]
        filter_parts.append(
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"volume=0.15[bgm]"
        )

    sfx_labels = []
    stream_cursor = 2
    for scene_idx in range(1, num_scenes + 1):
        offset_ms = int((scene_idx - 1) * SCENE_DURATION * 1000)
        categories = SCENE_SFX_MAP.get(scene_idx, [])
        for cat in categories:
            sfx_file = _pick_random_file(os.path.join(SFX_LIBRARY_DIR, cat))
            if sfx_file:
                inputs += ["-i", sfx_file]
                label = f"sfx{stream_cursor}"
                filter_parts.append(
                    f"[{stream_cursor}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                    f"atrim=0:{SCENE_DURATION},asetpts=PTS-STARTPTS,volume=0.35,"
                    f"afade=t=in:st=0:d=0.3,afade=t=out:st={max(SCENE_DURATION - 0.5, 0)}:d=0.5,"
                    f"adelay={offset_ms}|{offset_ms}[{label}]"
                )
                sfx_labels.append(f"[{label}]")
                stream_cursor += 1

    if sfx_labels:
        mix_inputs = "[bgm]" + "".join(sfx_labels)
        filter_parts.append(
            f"{mix_inputs}amix=inputs={1 + len(sfx_labels)}:duration=first:normalize=0,"
            f"alimiter=limit=0.95[aout]"
        )
    else:
        filter_parts.append("[bgm]alimiter=limit=0.95[aout]")

    filter_complex = ";".join(filter_parts)

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                *inputs,
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
    except Exception:
        _generate_synthetic_fallback_soundtrack(video_path, total_sec, output_path)


def _generate_synthetic_fallback_soundtrack(video_path: str, total_sec: int, output_path: str):
    filter_complex = (
        f"anoisesrc=c=pink:r=44100:a=0.02,atrim=0:{total_sec},asetpts=PTS-STARTPTS[pink];"
        f"sine=f=528:r=44100,atrim=0:{total_sec},asetpts=PTS-STARTPTS[tone];"
        "[tone]volume=0.015[tone_soft];"
        "[pink][tone_soft]amix=inputs=2[bgm];"
        f"anoisesrc=c=brown:r=44100:a=0.04,atrim=0:{total_sec},asetpts=PTS-STARTPTS,volume=0.2[sfx];"
        "[bgm][sfx]amix=inputs=2:duration=first[aout]"
    )
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


def send_telegram_preview(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🐾 *[{plan['project_title']}] 구조 영상 완성 (v26.1 30종 무중복 & 정밀 자막 엔진)!*\n\n"
        f"📌 *Title*: {yt['title']}\n"
        f"📝 *Description*: {yt['description']}\n"
        f"🏷️ *Tags*: {tags_str}\n\n"
        f"🚀 *유튜브에 '일부공개'로 등록되었습니다.*"
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
    send_telegram_message(f"🐾 아기 환상종 숏폼(v26.1 30종 무중복 엔진) 제작 시작!\n주제: '{TOPIC}'")

    plan = generate_scene_plan(TOPIC)

    with open(f"{WORK_DIR}/metadata.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    style_anchor = plan["style_anchor"]
    iconic_element = plan["iconic_element_en"]
    clip_paths = []

    for i, scene in enumerate(plan["scenes"]):
        idx = scene["scene_number"]
        print(f"--- [Clean Render] Scene {idx}/5 ---")

        full_prompt = f"{style_anchor}, featuring {iconic_element}, {scene['visual_prompt_en']}"
        negative_prompt = scene.get("negative_prompt_en", "blurry, low quality, watermark, text, scary, letters")

        if i == 0:
            image_source = generate_image(full_prompt, negative_prompt, aspect_ratio)
        else:
            frame_path = extract_last_frame(clip_paths[-1], idx)
            image_source = image_to_data_uri(frame_path)

        raw_clip = generate_video_clip(
            image_source=image_source,
            motion_prompt=scene["visual_prompt_en"],
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            index=idx,
        )
        clip_paths.append(raw_clip)

    stitched_clean_path = f"{WORK_DIR}/stitched_clean.mp4"
    stitch_clips_clean(clip_paths, stitched_clean_path)

    stitched_subbed_path = f"{WORK_DIR}/stitched_subbed.mp4"
    aspect_ratio_width = 1072 if aspect_ratio == "9:16" else 1920
    apply_timed_subtitles_post(stitched_clean_path, plan, stitched_subbed_path, video_width=aspect_ratio_width)

    final_path = f"{WORK_DIR}/final_video.mp4"
    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    generate_soundtrack_and_mux(stitched_subbed_path, total_duration, final_path)

    send_telegram_preview(final_path, plan)
    print("🐾 30종 무중복 정석 후가공 자막 25초 영상 제작 완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
