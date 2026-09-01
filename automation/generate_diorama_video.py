"""
아기 환상종 보호소 무중단 자동화 엔진 (v35 - Extended Replicate Polling & Scene Auto-Retry)
- [Replicate 타임아웃 10분 연장] 360초 -> 600초 확장으로 대기 시간 초과 에러 해결
- [씬 단위 자동 재시도] API 지연/네트워크 순단 시 씬별 1회 자동 복구 재시도
- [FFmpeg 100% 방탄 병합] filter_complex 기반 1080x1920 30fps 규격 정규화
- [YouTube 실제 업로드] videos.insert(unlisted) 연동 및 실시간 시청 링크 텔레그램 발송
"""

import os
import re
import json
import time
import base64
import random
import subprocess
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

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
    2: ["gentle_lift_rustle", "soft_fabric_towel"],
    3: ["soft_fabric_towel", "gentle_taps"],
    4: ["crisp_chewing_asmr", "sparkle_chimes"],
    5: ["soft_blanket_tuck", "peaceful_sleep_purr"],
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
    {"name": "Baby Sun Lion", "desc": "miniature baby lion cub with a warm radiant sunbeam golden mane"},
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
    os.makedirs(BGM_LIBRARY_DIR, exist_ok=True)
    bgm_target = os.path.join(BGM_LIBRARY_DIR, "lullaby_ambient.wav")
    if not os.path.exists(bgm_target) or os.path.getsize(bgm_target) < 1000:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi",
             "-i", "sine=f=432:r=44100:d=25,volume=0.02,afade=t=in:st=0:d=2,afade=t=out:st=22:d=3",
             "-c:a", "pcm_s16le", bgm_target],
            check=True, capture_output=True
        )

    crisp_chew_filter = (
        "aevalsrc='if(between(mod(t,0.8),0.05,0.22)+between(mod(t,0.8),0.32,0.48),"
        "0.6*sin(2*PI*950*t)*exp(-25*mod(t,0.4))+0.4*sin(2*PI*1800*t)*exp(-35*mod(t,0.4)),0)':d=5,"
        "volume=2.2,highpass=f=400,lowpass=f=3500"
    )

    sfx_synth_map = {
        "wind_cold_ambient": "anoisesrc=c=pink:r=44100:a=0.04:d=5,lowpass=f=800,volume=0.3",
        "soft_whimper_rustle": "sine=f=520:r=44100:d=5,volume=0.02,afade=t=in:st=0:d=1",
        "gentle_lift_rustle": "anoisesrc=c=brown:r=44100:a=0.05:d=5,highpass=f=200,volume=0.3",
        "soft_fabric_towel": "anoisesrc=c=pink:r=44100:a=0.03:d=5,volume=0.3,afade=t=in:st=0:d=0.5",
        "gentle_taps": "anoisesrc=c=brown:r=44100:a=0.06:d=5,volume=0.25",
        "crisp_chewing_asmr": crisp_chew_filter,
        "sparkle_chimes": "sine=f=1400:r=44100:d=5,tremolo=f=5:d=0.8,volume=0.025,afade=t=in:st=0.5:d=0.8",
        "soft_blanket_tuck": "anoisesrc=c=pink:r=44100:a=0.04:d=5,lowpass=f=600,volume=0.25",
        "peaceful_sleep_purr": "sine=f=160:r=44100:d=5,volume=0.035,afade=t=in:st=0:d=1,afade=t=out:st=4:d=1",
    }

    for cat, lavfi_filter in sfx_synth_map.items():
        cat_dir = os.path.join(SFX_LIBRARY_DIR, cat)
        os.makedirs(cat_dir, exist_ok=True)
        target_wav = os.path.join(cat_dir, f"{cat}.wav")
        if not os.path.exists(target_wav) or os.path.getsize(target_wav) < 1000:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", lavfi_filter, "-c:a", "pcm_s16le", target_wav],
                check=True, capture_output=True
            )


def send_telegram_message(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        except Exception:
            pass


def resolve_unique_topic() -> tuple:
    if RAW_TOPIC and RAW_TOPIC.lower() not in ("auto", "none", ""):
        return RAW_TOPIC, "Baby Fantasy Creature", "tiny fantasy creature", 1

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8-sig") as f:
                history = json.load(f)
        except Exception:
            history = []

    used_set = set(history)
    available = [c for c in CREATURE_POOL if c["name"] not in used_set]

    if not available:
        selected_creature = CREATURE_POOL[0]
        history = [selected_creature["name"]]
        current_episode = 1
    else:
        selected_creature = available[0]
        history.append(selected_creature["name"])
        current_episode = len(history)

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    season = 1 if current_episode <= 30 else 2
    full_topic = f"Rescuing a lost {selected_creature['desc']} and tucking it into a cozy bed"
    print(f"\n🎯 [배정] 에피소드 {current_episode}화 (시즌 {season}): {selected_creature['name']}")
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


def poll_until_done(data: dict, max_wait_sec: int = 600) -> dict:
    get_url = data.get("urls", {}).get("get")
    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(5)
        waited += 5
        if waited % 20 == 0:
            print(f"   ⏳ 렌더링 진행 중... ({waited}초 경과, 현재 상태: {data.get('status')})")
        try:
            poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
            poll_res.raise_for_status()
            data = poll_res.json()
        except requests.exceptions.RequestException:
            continue

    if data.get("status") != "succeeded":
        error_detail = data.get("error") or f"상태({data.get('status')}), {max_wait_sec}초 타임아웃 경과"
        raise RuntimeError(f"Replicate 오류: {error_detail}")
    return data


def build_pure_visual_rescue_plan(creature_name: str, creature_desc: str) -> dict:
    t_name = creature_name.replace(" ", "")
    return {
        "project_title": "Rescuing " + creature_name,
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_number": 1,
                "title": "Shivering in Blizzard",
                "visual_prompt_en": "Extreme macro close-up of tiny baby " + creature_desc + ", big tearful eyes trembling in snowstorm, cinematic, 8k",
                "motion_prompt": "Slow zoom into tiny creature shivering violently in snow, crying with big watery eyes",
                "negative_prompt_en": "blurry, text, watermark"
            },
            {
                "scene_number": 2,
                "title": "Rescue Care",
                "motion_prompt": "Gentle hands scooping up the tiny creature from snow into a warm embrace",
                "negative_prompt_en": "text, watermark"
            },
            {
                "scene_number": 3,
                "title": "Warm Towel",
                "motion_prompt": "Hands wrapping the tiny creature in a soft fluffy warm towel in a cozy room",
                "negative_prompt_en": "text, watermark"
            },
            {
                "scene_number": 4,
                "title": "Magic Treat",
                "motion_prompt": "Feeding a glowing star candy to the tiny creature as it happily smiles",
                "negative_prompt_en": "text, watermark"
            },
            {
                "scene_number": 5,
                "title": "Sleep",
                "motion_prompt": "Tucking the happy creature into a warm wooden cradle bed to sleep",
                "negative_prompt_en": "text, watermark"
            }
        ],
        "youtube_metadata": {
            "title": "Rescuing a Shivering Baby " + creature_name + "! #Shorts",
            "description": "Rescue and healing ASMR for baby " + creature_name + "! Subscribe for more. #Shorts #" + t_name,
            "tags": ["babycreature", "shorts", t_name.lower()]
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
    data = poll_until_done(data, max_wait_sec=180)
    output = data.get("output")
    return output[0] if isinstance(output, list) else output


def generate_video_clip(image_source: str, motion_prompt: str, negative_prompt: str,
                         aspect_ratio: str, index: int, retry_count: int = 1) -> str:
    for attempt in range(retry_count + 1):
        try:
            time.sleep(10)
            data = post_with_retry(
                "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
                {
                    "input": {
                        "prompt": motion_prompt,
                        "negative_prompt": f"{negative_prompt}, text, letters, subtitles, watermark, blur, brown mud, paintbrush, changing animal species, laser eyes, glowing eyes, flashlight eyes",
                        "image": image_source,
                        "duration": 5,
                        "aspect_ratio": aspect_ratio,
                    }
                }
            )
            data = poll_until_done(data, max_wait_sec=600)
            video_url = data.get("output")[0] if isinstance(data.get("output"), list) else data.get("output")

            video_res = requests.get(video_url, timeout=60)
            video_res.raise_for_status()
            os.makedirs(WORK_DIR, exist_ok=True)
            clip_path = f"{WORK_DIR}/scene_{index}.mp4"
            with open(clip_path, "wb") as f:
                f.write(video_res.content)
            return clip_path
        except Exception as e:
            if attempt < retry_count:
                print(f"⚠️ [씬 {index}] 렌더링 지연/에러 발생 ({e}). 10초 후 재시도합니다...")
                time.sleep(10)
                continue
            raise


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
    inputs = []
    filter_chains = []
    concat_inputs = []

    for i, p in enumerate(clip_paths):
        inputs += ["-i", p]
        filter_chains.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v{i}]"
        )
        concat_inputs.append(f"[v{i}]")

    concat_filter = f"{''.join(concat_inputs)}concat=n={len(clip_paths)}:v=1:a=0[vout]"
    full_filter_complex = ";".join(filter_chains) + ";" + concat_filter

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", full_filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg Concat 실패: {result.stderr[-300:]}")


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
    ensure_sfx_library()

    num_scenes = int(total_sec / SCENE_DURATION)
    inputs = ["-i", video_path]
    filter_parts = []

    bgm_path = _pick_random_file(BGM_LIBRARY_DIR)
    if bgm_path:
        inputs += ["-i", bgm_path]
        filter_parts.append(
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
            f"atrim=0:{total_sec},asetpts=PTS-STARTPTS,volume=0.08,"
            f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(total_sec - 2.5, 0)}:d=2.5[bgm]"
        )
    else:
        inputs += ["-f", "lavfi", "-i", f"anoisesrc=c=pink:r=44100:a=0.012:d={total_sec}"]
        filter_parts.append(
            f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.08[bgm]"
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

                if scene_idx == 4 and "chewing" in cat:
                    vol = 2.20
                elif scene_idx == 4 and "sparkle" in cat:
                    vol = 0.35
                elif scene_idx == 5:
                    vol = 0.35
                else:
                    vol = 0.40

                filter_parts.append(
                    f"[{stream_cursor}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                    f"atrim=0:{SCENE_DURATION},asetpts=PTS-STARTPTS,volume={vol},"
                    f"afade=t=in:st=0:d=0.1,afade=t=out:st={max(SCENE_DURATION - 0.3, 0)}:d=0.3,"
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
            [
                "ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filter_parts),
                "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        _generate_emergency_fallback_soundtrack(video_path, total_sec, output_path)


def _generate_emergency_fallback_soundtrack(video_path: str, total_sec: int, output_path: str):
    filter_complex = (
        f"anoisesrc=c=pink:r=44100:a=0.02,atrim=0:{total_sec},asetpts=PTS-STARTPTS[bgm];"
        f"[bgm]alimiter=limit=0.95[aout]"
    )
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-filter_complex", filter_complex,
             "-map", "0:v:0", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", output_path],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError:
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-c", "copy", output_path], check=True, capture_output=True)


def upload_video_to_youtube(video_path: str, plan: dict) -> str:
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        print("⚠️ YouTube API 인증 정보가 없어 업로드를 건너뜁니다.")
        return None
    try:
        print("🚀 YouTube API로 일부공개 업로드를 진행합니다...")
        creds = Credentials(
            None,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = build("youtube", "v3", credentials=creds)
        yt = plan["youtube_metadata"]

        body = {
            "snippet": {
                "title": yt["title"],
                "description": yt["description"],
                "tags": yt.get("tags", []),
                "categoryId": "15"
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   • 업로드 진행률: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        print(f"✅ YouTube 업로드 성공: {video_url}")
        return video_url
    except Exception as e:
        print(f"❌ YouTube 업로드 실패: {e}")
        return None


def send_telegram_preview(video_path: str, plan: dict, yt_url: str = None):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    upload_status = f"🔗 *YouTube 링크*: {yt_url}\n(일부공개로 등록되었습니다)" if yt_url else "⚠️ *유튜브 업로드 실패*"

    caption = (
        f"🐾 *[{plan['project_title']}] 구조 영상 완성 (v35 롱 타임아웃 & 방탄 렌더링)!*\n\n"
        f"📌 *Title*: {yt['title']}\n"
        f"📝 *Description*: {yt['description']}\n"
        f"🏷️ *Tags*: {tags_str}\n\n"
        f"🚀 {upload_status}"
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
        f"🐾 아기 환상종 숏폼(v35 방탄 롱타임아웃 엔진) 제작 시작!\n"
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

    yt_url = upload_video_to_youtube(final_path, plan)
    send_telegram_preview(final_path, plan, yt_url)
    print(f"🐾 v35 제작 및 업로드 완료! (URL: {yt_url})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise



def upload_to_youtube(video_path: str, plan: dict):
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        print("?? YouTube API ?? ??? ?? ???? ?????.")
        return
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials(
            None,
            refresh_token=REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        youtube = build("youtube", "v3", credentials=creds)
        
        yt = plan["youtube_metadata"]
        body = {
            "snippet": {
                "title": yt["title"],
                "description": yt["description"],
                "tags": yt.get("tags", []),
                "categoryId": "22"
            },
            "status": {
                "privacyStatus": "unlisted",
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%.")
        
        print(f"? YouTube ??? ??! ?? ID: {response.get('id')}")
    except Exception as e:
        print(f"? YouTube ??? ? ?? ??: {e}")
        raise e
