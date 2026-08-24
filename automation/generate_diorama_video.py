"""
아기 환상종 보호소 무중단 자동화 엔진 (v27.1 - Safer Zero-Duplication Count)
- [FIX] channels().list(statistics).videoCount 대신 'uploads' 재생목록의
        실제 아이템 개수를 셉니다. videoCount는 공개(Public) 영상만 집계할
        가능성이 있고, 이 파이프라인은 안전을 위해 '일부공개'로 업로드하므로
        그 경우 카운트가 실제보다 훨씬 낮게 나와 중복 위험이 커질 수 있습니다.
- [FIX] YouTube API 카운트 조회가 실패해서 로컬 히스토리로 폴백할 경우,
        콘솔 로그뿐 아니라 텔레그램으로도 명시적 경고를 보냅니다. GitHub
        Actions는 매번 새 환경이라 로컬 히스토리가 비어있을 수 있어, 이
        폴백이 조용히 반복되면 중복 배정 위험이 누적됩니다.
- [3단계 공간 전환] 야외 구조 -> 실내 보호소 케어 -> 따뜻한 요정 침대 수면 완결
- 텍스트 폭 자동 측정 후가공 자막 & ASMR 믹싱
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
    3: ["water_drops", "sparkle_chimes"],
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


def send_telegram_message(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        except Exception:
            pass


def fetch_youtube_uploaded_count() -> int:
    """
    videoCount 대신 'uploads' 재생목록의 실제 등록 개수를 조회합니다.
    """
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        return -1
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

        pl_resp = youtube.playlistItems().list(
            playlistId=uploads_id, part="id", maxResults=1
        ).execute()
        count = pl_resp.get("pageInfo", {}).get("totalResults", 0)
        print(f"📊 YouTube 'uploads' 재생목록 기준 실제 업로드 영상 수: {count}개 확인")
        return count
    except Exception as e:
        print(f"⚠️ YouTube API 카운트 조회 실패 ({e}). 로컬 히스토리로 폴백합니다.")
        return -1


def resolve_unique_topic() -> tuple:
    if RAW_TOPIC and RAW_TOPIC.lower() not in ("auto", "none", ""):
        return RAW_TOPIC, "Baby Fantasy Creature", 1

    yt_count = fetch_youtube_uploaded_count()
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    if yt_count >= 0:
        current_episode = yt_count + 1
    else:
        current_episode = len(history) + 1
        send_telegram_message(
            "⚠️ [경고] YouTube API로 업로드 개수를 조회하지 못해 로컬 히스토리로 "
            "폴백했습니다. GitHub Actions 환경에서는 로컬 히스토리가 매번 초기화될 "
            "수 있어 크리처 중복 배정 위험이 있습니다. YOUTUBE_CLIENT_ID/SECRET/"
            "REFRESH_TOKEN 설정을 확인해주세요."
        )

    target_idx = (current_episode - 1) % len(CREATURE_POOL)
    selected_creature = CREATURE_POOL[target_idx]
    season = 1 if current_episode <= 30 else 2

    if current_episode == 28:
        alert_msg = (
            "🔔 [보호소 세계관 알림] 아기 환상종 시즌 1이 28회차에 도달했습니다!\n\n"
            "• 시즌 1(구조 & 수면): 앞으로 2회 남음 (총 30회 완결)\n"
            "• 31회차부터 [시즌 2: 모닝 루틴 & 힐링 스파 케어]로 전환 준비가 완료되었습니다.\n"
            "• 30회 완료 후 1시간 수면용 롱폼 컴필레이션 제작을 추천합니다."
        )
        send_telegram_message(alert_msg)

    history.append(selected_creature["name"])
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    full_topic = f"Rescuing a lost {selected_creature['desc']} and tucking it into a cozy bed"
    print(f"✅ [에피소드 {current_episode}화 / 시즌 {season}] 배정 크리처 ({target_idx+1}/30): {selected_creature['name']}")
    return full_topic, selected_creature["name"], current_episode


TOPIC, CREATURE_NAME, CURRENT_EPISODE = resolve_unique_topic()


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


def build_structured_rescue_plan(creature_name: str) -> dict:
    return {
        "project_title": f"Rescuing a Lost {creature_name}",
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_number": 1,
                "stage": "wild",
                "story_subtitle": f"Found a tiny {creature_name} shivering alone...",
                "visual_prompt_en": f"Cinematic extreme macro of a tiny adorable shivering {creature_name} with big teary eyes trapped in cold thorny snow, volumetric winter lighting, 8k octane render, no text",
                "motion_prompt": "Slow gentle camera zoom in on the shivering creature with blinking teary eyes in cold wind",
                "negative_prompt_en": "blurry, dark dirt, mud on face, adult animal, human face, text, letters"
            },
            {
                "scene_number": 2,
                "stage": "shelter_warm",
                "story_subtitle": "Step 1: Gentle rescue to warm nursery",
                "visual_prompt_en": f"INDOOR warm cozy wooden sanctuary nursery interior, wooden walls and warm fireplace glow visible, NO snow NO branches NO outdoor elements, gentle caring human hands wrapping the clean cute {creature_name} in a soft fluffy warm white towel, soft golden fairy lights in background, 8k octane render",
                "motion_prompt": "Gentle hands softly wrapping and patting the happy creature with a warm white towel, creature smiles",
                "negative_prompt_en": "mud, dirt, brown paint, messy brush, paintbrush, outdoor, snow, branches, forest, winter, scary, text"
            },
            {
                "scene_number": 3,
                "stage": "shelter_warm",
                "story_subtitle": "Step 2: Feeding glowing starlight treat",
                "visual_prompt_en": f"Inside warm cozy nursery, feeding the clean happy fluffy {creature_name} a sparkling magical glowing crystal starlight berry candy, joyful sparkling eyes, magical fairy dust floating",
                "motion_prompt": "Creature happily nibbling the glowing crystal starlight treat with joyful glowing eyes and happy wagging tail",
                "negative_prompt_en": "mud, brown goo, dirty bottle, outdoor, snow, branches, text, watermark"
            },
            {
                "scene_number": 4,
                "stage": "bed",
                "story_subtitle": "Step 3: Tucking into cozy miniature bed",
                "visual_prompt_en": f"INDOOR bedroom scene, NO snow NO branches NO outdoor elements, gentle caring hands slowly lowering the clean sleepy fluffy {creature_name} into a miniature cozy wooden cradle bed lined with glowing magical moss and soft velvet pillow, warm golden fairy lights, indoor wooden nursery walls in background",
                "motion_prompt": "Slow cinematic camera lowering the sleepy creature under a tiny warm knitted blanket, creature yawns softly",
                "negative_prompt_en": "mud, dirt, snow, forest branches, outdoor, winter, dark, text"
            },
            {
                "scene_number": 5,
                "stage": "bed",
                "story_subtitle": "Safe and sound asleep. Goodnight little one...",
                "visual_prompt_en": f"Extreme macro close-up of the clean fluffy {creature_name} sound asleep and breathing peacefully inside its glowing miniature bed, smiling in sweet dreams, soft warm glowing bokeh",
                "motion_prompt": "Ultra-slow macro cinematic zoom on the sleeping creature breathing gently with tiny glowing fairy sparkles",
                "negative_prompt_en": "mud on face, snow, forest, outdoor, dirty, human hands, text"
            }
        ],
        "youtube_metadata": {
            "title": f"Found a Shivering Baby {creature_name}! 🥺 Rescue & Bedtime ASMR",
            "description": f"Rescuing a lost {creature_name} and giving it a warm cozy bed! 🌿✨\n\n🐾 Welcome to Pocket Creature Rescue. What should we name this little one?\n\n#Shorts #BabyCreature #{creature_name.replace(' ', '')} #Cute #ASMR #Bedtime",
            "tags": ["babycreature", "fantasyrescue", creature_name.lower().replace(" ", ""), "cutemonster", "asmr", "satisfying", "shorts", "healing"]
        }
    }


def generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> str:
    quality_enhancer = "masterpiece, sharp focus, hyper-detailed 3D octane render, studio lighting, clean composition, no text, no watermark"
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
    return output[0] if isinstance(output, list) else output


def generate_video_clip(image_source: str, motion_prompt: str, negative_prompt: str,
                         aspect_ratio: str, index: int) -> str:
    time.sleep(15)
    data = post_with_retry(
        "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
        {
            "input": {
                "prompt": motion_prompt,
                "negative_prompt": f"{negative_prompt}, text, letters, subtitles, watermark, blur, brown mud, paintbrush",
                "image": image_source,
                "duration": 5,
                "aspect_ratio": aspect_ratio,
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=360)
    video_url = data.get("output")[0] if isinstance(data.get("output"), list) else data.get("output")

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
    print("✍️ 25초 완성본 위에 시간대별 감성 동화 자막 오버레이 중...")
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
            ["ffmpeg", "-y", "-i", stitched_video, "-vf", vf_chain, "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
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
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.15[bgm]"
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
            f"{mix_inputs}amix=inputs={1 + len(sfx_labels)}:duration=first:normalize=0,alimiter=limit=0.95[aout]"
        )
    else:
        filter_parts.append("[bgm]alimiter=limit=0.95[aout]")

    try:
        subprocess.run(
            ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filter_parts),
             "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path],
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
        ["ffmpeg", "-y", "-i", video_path, "-filter_complex", filter_complex,
         "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path],
        check=True,
        capture_output=True,
    )


def send_telegram_preview(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🐾 *[{plan['project_title']}] 구조 영상 완성 (v27.1)!*\n\n"
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
    send_telegram_message(f"🐾 아기 환상종 숏폼(v27.1) 제작 시작!\n크리처: '{CREATURE_NAME}' (에피소드 {CURRENT_EPISODE}화)")

    plan = build_structured_rescue_plan(CREATURE_NAME)

    with open(f"{WORK_DIR}/metadata.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    clip_paths = []

    for i, scene in enumerate(plan["scenes"]):
        idx = scene["scene_number"]
        print(f"\n🎬 [씬 {idx}/5 - 공간: {scene['stage']}] 렌더링 중...")

        if idx in (1, 2, 4):
            print(f"✨ 새로운 공간 키프레임 생성 중 (Flux 1.1 Pro Ultra)...")
            image_source = generate_image(scene["visual_prompt_en"], scene["negative_prompt_en"], aspect_ratio)
        else:
            frame_path = extract_last_frame(clip_paths[-1], idx)
            image_source = image_to_data_uri(frame_path)

        raw_clip = generate_video_clip(
            image_source=image_source,
            motion_prompt=scene["motion_prompt"],
            negative_prompt=scene["negative_prompt_en"],
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
    print("🐾 v27.1 영상 제작 및 텔레그램 발송 완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
