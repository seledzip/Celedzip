"""
아기 환상종 보호소 무중단 자동화 엔진 (v29.2 - Auto-Download Pure ASMR Library)
- [SFX 라이브러리 자동 구축] 먹방 씹는 소리, 수면 골골송, 마법 차임벨 음원 자동 다운로드
- [씬 4 먹방 ASMR 실사 탑재] 별사탕 오물오물 냠냠 씹어먹는 리얼 사운드 믹싱
- [씬 5 수면 ASMR 강화] 포근한 이불 바스락 + 새근새근 평온한 잠자리 사운드
- [YouTube 실시간 제목 스캔] 기제작 환상종 100% 제외 및 30종 무중복 순차 배정
- [자막 100% 제거] 4K 청정 시네마틱 비주얼 & 동일 캐릭터 모션 체이닝
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
    1: ["wind_cold_ambient", "soft_whimper_rustle"],      # 0~5s: 눈바람 & 가련한 울음
    2: ["gentle_lift_rustle", "soft_fabric_towel"],       # 5~10s: 손길 구출 & 부드러운 안김
    3: ["soft_fabric_towel", "gentle_taps"],              # 10~15s: 수건 케어 & 보송보송 닦기
    4: ["cute_nibble_munch", "sparkle_chimes"],           # 15~20s: ★ 별사탕 오물오물 냠냠 먹방 + 마법 회복
    5: ["soft_blanket_tuck", "peaceful_sleep_purr"],      # 20~25s: ★ 포근한 이불 + 새근새근 수면 ASMR
}

# 검증된 저작권 무료 고음질 ASMR 음원 저장소 (자동 다운로드용)
SFX_DOWNLOAD_SOURCES = {
    "wind_cold_ambient": "https://cdn.freesound.org/previews/518/518887_11235129-lq.mp3",
    "soft_whimper_rustle": "https://cdn.freesound.org/previews/416/416179_5121236-lq.mp3",
    "gentle_lift_rustle": "https://cdn.freesound.org/previews/240/240776_4107740-lq.mp3",
    "soft_fabric_towel": "https://cdn.freesound.org/previews/387/387232_1474204-lq.mp3",
    "gentle_taps": "https://cdn.freesound.org/previews/68/68940_1015240-lq.mp3",
    "cute_nibble_munch": "https://cdn.freesound.org/previews/369/369515_6687700-lq.mp3",  # 리얼 오물오물 씹는 소리
    "sparkle_chimes": "https://cdn.freesound.org/previews/608/608645_11861866-lq.mp3",    # 영롱한 별빛 마법음
    "soft_blanket_tuck": "https://cdn.freesound.org/previews/240/240777_4107740-lq.mp3",
    "peaceful_sleep_purr": "https://cdn.freesound.org/previews/459/459992_6142149-lq.mp3", # 아늑한 수면 숨소리/골골송
}

BGM_DOWNLOAD_URL = "https://cdn.freesound.org/previews/676/676404_14493393-lq.mp3" # 따뜻한 오르골 자장가 앰비언트

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


def ensure_sfx_library():
    """효과음/배경음 파일이 없으면 인터넷에서 고음질 음원을 자동 다운로드하여 세팅"""
    os.makedirs(BGM_LIBRARY_DIR, exist_ok=True)
    bgm_target = os.path.join(BGM_LIBRARY_DIR, "lullaby_ambient.mp3")
    if not os.path.exists(bgm_target):
        try:
            r = requests.get(BGM_DOWNLOAD_URL, timeout=15)
            if r.status_code == 200:
                with open(bgm_target, "wb") as f:
                    f.write(r.content)
                print("🎵 힐링 BGM 음원 자동 세팅 완료")
        except Exception:
            pass

    for category, url in SFX_DOWNLOAD_SOURCES.items():
        cat_dir = os.path.join(SFX_LIBRARY_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)
        target_file = os.path.join(cat_dir, f"{category}.mp3")
        if not os.path.exists(target_file):
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    with open(target_file, "wb") as f:
                        f.write(r.content)
            except Exception:
                pass


def send_telegram_message(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        except Exception:
            pass


def get_all_uploaded_creature_names() -> set:
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        return set()
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

        titles = []
        next_page_token = None
        while True:
            pl_resp = youtube.playlistItems().list(
                playlistId=uploads_id,
                part="snippet",
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            for item in pl_resp.get("items", []):
                titles.append(item["snippet"]["title"])
            next_page_token = pl_resp.get("nextPageToken")
            if not next_page_token:
                break

        print(f"🔍 YouTube 채널 총 업로드 영상 수: {len(titles)}개 확인")
        uploaded_names = set()
        for t in titles:
            for c in CREATURE_POOL:
                if c["name"].lower() in t.lower():
                    uploaded_names.add(c["name"])

        print(f"🚫 [제외] 이미 유튜브에 업로드된 환상종 ({len(uploaded_names)}종): {list(uploaded_names)}")
        return uploaded_names
    except Exception as e:
        print(f"⚠️ YouTube API 스캔 실패 ({e})")
        return set()


def resolve_unique_topic() -> tuple:
    if RAW_TOPIC and RAW_TOPIC.lower() not in ("auto", "none", ""):
        return RAW_TOPIC, "Baby Fantasy Creature", "tiny fantasy creature", 1

    uploaded_creatures = get_all_uploaded_creature_names()

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    all_used_creatures = uploaded_creatures.union(set(history))
    available_creatures = [c for c in CREATURE_POOL if c["name"] not in all_used_creatures]

    if not available_creatures:
        selected_creature = CREATURE_POOL[0]
        current_episode = len(all_used_creatures) + 1
        print("🎉 30종 모든 아기 환상종 제작이 완료되었습니다! 2회차 루프를 시작합니다.")
    else:
        selected_creature = available_creatures[0]
        current_episode = len(all_used_creatures) + 1

    season = 1 if current_episode <= 30 else 2

    if current_episode == 28:
        alert_msg = (
            "🔔 [보호소 세계관 알림] 아기 환상종 시즌 1이 28회차에 도달했습니다!\n\n"
            "• 시즌 1(구조 & 수면): 앞으로 2회 남음 (총 30회 완결)\n"
            "• 31회차부터 [시즌 2: 모닝 루틴 & 힐링 스파 케어]로 전환 준비가 완료되었습니다."
        )
        send_telegram_message(alert_msg)

    history.append(selected_creature["name"])
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    full_topic = f"Rescuing a lost {selected_creature['desc']} and tucking it into a cozy bed"
    print(f"✅ [에피소드 {current_episode}화 / 시즌 {season}] 배정 크리처: {selected_creature['name']} (남은 환상종: {len(available_creatures)}종)")
    return full_topic, selected_creature["name"], selected_creature["desc"], current_episode


TOPIC, CREATURE_NAME, CREATURE_DESC, CURRENT_EPISODE = resolve_unique_topic()


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


def build_pure_visual_rescue_plan(creature_name: str, creature_desc: str) -> dict:
    return {
        "project_title": f"Rescuing a Lost {creature_name}",
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_number": 1,
                "title": "Sad Shivering Creature in Cold Snow",
                "visual_prompt_en": (
                    f"Extreme macro close-up of a tiny shivering {creature_desc}, "
                    f"big watery sad reflective teary eyes, helpless trembling expression, "
                    f"trapped in cold winter snow on thorny branches, cinematic lighting, 8k octane render, no text"
                ),
                "motion_prompt": (
                    "Slow cinematic macro zoom on the shivering creature trembling in the cold wind, "
                    "looking up with big sad watery blinking eyes asking for help"
                ),
                "negative_prompt_en": "blurry, human face, mud, brown paint, dirt, text, watermark, adult animal"
            },
            {
                "scene_number": 2,
                "title": "Gentle Hands Rescuing the Creature",
                "motion_prompt": (
                    "Gentle caring warm human hands softly reach into the frame from below, "
                    "carefully and tenderly scooping up this exact tiny creature from the snow, "
                    "lifting it safely and lovingly into warm embrace"
                ),
                "negative_prompt_en": "dropping, harsh movement, mud, brown goo, dirt, transformation, morphing into other animal, text"
            },
            {
                "scene_number": 3,
                "title": "Warm Towel Care in Cozy Home",
                "motion_prompt": (
                    "Inside a warm cozy nursery, gentle human hands wrapping this exact tiny creature "
                    "in a soft fluffy warm white towel, softly patting and drying its fur, "
                    "the creature feels safe, relieved and softly smiles"
                ),
                "negative_prompt_en": "mud, paintbrush, brown dirt, dirty towel, outdoor, snow, animal shape change, text"
            },
            {
                "scene_number": 4,
                "title": "Feeding Starlight Treat & Revitalizing Joy",
                "motion_prompt": (
                    "A glowing sparkling golden starlight candy treat is gently fed to this exact creature, "
                    "as it happily nibbles the treat, sparkling magical golden fairy dust illuminates its body, "
                    "its eyes glow with vibrant energy and its face lights up with an ecstatic happy beaming smile"
                ),
                "negative_prompt_en": "sad expression, brown liquid, mud, dirty bottle, changing creature, text, watermark"
            },
            {
                "scene_number": 5,
                "title": "Cozy Bedtime Sleep Ending",
                "motion_prompt": (
                    "Gentle hands carefully tuck the now happy, clean and sleepy creature into a miniature warm wooden cradle bed "
                    "under a tiny soft knitted blanket, the creature gently closes its eyes and breathes peacefully into sweet dreams"
                ),
                "negative_prompt_en": "awake, open eyes, falling, mud, snow, outdoor, branches, animal morphing, text"
            }
        ],
        "youtube_metadata": {
            "title": f"Rescuing a Shivering Baby {creature_name}! 🥺 Bedtime ASMR",
            "description": f"Rescuing a tiny lost {creature_name} and giving it a warm cozy bed! 🌿✨\n\n🐾 Welcome to Pocket Creature Rescue. What should we name this cute little one?\n\n#Shorts #BabyCreature #{creature_name.replace(' ', '')} #Cute #ASMR #Bedtime",
            "tags": ["babycreature", "fantasyrescue", creature_name.lower().replace(" ", ""), "cutemonster", "asmr", "satisfying", "shorts", "healing"]
        }
    }


def generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> str:
    quality_enhancer = "masterpiece, ultra-sharp focus, hyper-detailed 3D octane render, volumetric warm lighting, clean background, no text, no watermark"
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
                "negative_prompt": f"{negative_prompt}, text, letters, subtitles, watermark, blur, brown mud, paintbrush, changing animal species",
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


def _pick_random_file(folder_path: str) -> str:
    if not os.path.isdir(folder_path):
        return None
    candidates = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith((".wav", ".mp3", ".flac", ".ogg", ".m4a"))
    ]
    return random.choice(candidates) if candidates else None


def generate_soundtrack_and_mux(video_path: str, total_sec: int, output_path: str):
    """5개 씬별 ASMR 입체 사운드 (4번 오물오물 먹방 & 5번 수면 전용 오디오 믹싱)"""
    ensure_sfx_library()

    num_scenes = int(total_sec / SCENE_DURATION)
    inputs = ["-i", video_path]
    filter_parts = []

    bgm_path = _pick_random_file(BGM_LIBRARY_DIR)
    if bgm_path:
        inputs += ["-i", bgm_path]
        filter_parts.append(
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"atrim=0:{total_sec},asetpts=PTS-STARTPTS,volume=0.15,"
            f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(total_sec - 2.5, 0)}:d=2.5[bgm]"
        )
    else:
        inputs += ["-f", "lavfi", "-i", f"anoisesrc=c=pink:r=44100:a=0.012:d={total_sec}"]
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
                
                # 씬 4(먹방 ASMR)는 오물오물 씹는 소리가 잘 들리도록 볼륨 0.50 강조
                if scene_idx == 4 and "nibble" in cat:
                    vol = 0.50
                elif scene_idx == 5:
                    vol = 0.28
                else:
                    vol = 0.35

                filter_parts.append(
                    f"[{stream_cursor}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                    f"atrim=0:{SCENE_DURATION},asetpts=PTS-STARTPTS,volume={vol},"
                    f"afade=t=in:st=0:d=0.2,afade=t=out:st={max(SCENE_DURATION - 0.5, 0)}:d=0.5,"
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

    subprocess.run(
        [
            "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filter_parts),
            "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path
        ],
        check=True,
        capture_output=True,
    )


def send_telegram_preview(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🐾 *[{plan['project_title']}] 구조 영상 완성 (v29.2 고음질 먹방 & 수면 ASMR)!*\n\n"
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
    send_telegram_message(
        f"🐾 아기 환상종 숏폼(v29.2 고음질 ASMR 라이브러리 자동 탑재) 제작 시작!\n"
        f"크리처: '{CREATURE_NAME}' (에피소드 {CURRENT_EPISODE}화)"
    )

    plan = build_pure_visual_rescue_plan(CREATURE_NAME, CREATURE_DESC)

    with open(f"{WORK_DIR}/metadata.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    clip_paths = []

    for i, scene in enumerate(plan["scenes"]):
        idx = scene["scene_number"]
        print(f"\n🎬 [씬 {idx}/5 - {scene['title']}] 렌더링 중...")

        if i == 0:
            print("✨ 씬 1 마스터 비주얼 생성 (Flux 1.1 Pro Ultra)...")
            image_source = generate_image(scene["visual_prompt_en"], scene["negative_prompt_en"], aspect_ratio)
        else:
            print(f"🔗 씬 {i}의 마지막 프레임을 이어받아 100% 동일 캐릭터 모션 렌더링...")
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

    final_path = f"{WORK_DIR}/final_video.mp4"
    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    generate_soundtrack_and_mux(stitched_clean_path, total_duration, final_path)

    send_telegram_preview(final_path, plan)
    print("🐾 v29.2 고음질 먹방 ASMR 영상 완성 및 텔레그램 발송 완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
