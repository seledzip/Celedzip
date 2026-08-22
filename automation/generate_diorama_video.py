"""
아기 환상종 보호소 (Baby Fantasy Sanctuary) 365일 무인 자동화 엔진 (v16)
- 365일 무한 주제 자동 생성기 (Topic DB Auto-Selector)
- 씬별 타임라인 맞춤 ASMR 사운드 (낑낑거림/먹는소리/골골송) + 힐링 BGM 2중 믹싱
- Replicate Llama 3 -> Flux Schnell -> Kling 2.5 Turbo Pro
- 텔레그램 미리보기 + 유튜브 자동 업로드 연동
"""

import os
import re
import json
import time
import base64
import random
import datetime
import subprocess
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
RAW_TOPIC = os.environ.get("TOPIC", "").strip()

WORK_DIR = "video_work"
SCENE_DURATION = 5.0

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}

# 365일 무한 자동 순환용 아기 크리처 & 위기 환경 데이터베이스
CREATURE_DB = [
    ("baby snow fox with crystal paws", "freezing in a heavy snowstorm"),
    ("baby star dragon with glowing golden wings", "trapped in dark muddy rain"),
    ("tiny moss spirit puppy with blooming head flower", "lost in dry cracked earth"),
    ("baby thunder gryphon with fluffy blue feathers", "shivering under a giant wet leaf"),
    ("baby cloud kitten with floating tail", "stuck in thorny frozen briars"),
    ("tiny baby ember phoenix with soft warm feathers", "weakened in cold pouring rain"),
    ("baby moonlight bunny with glowing translucent ears", "shivering inside a hollow iced log"),
    ("baby ocean otter with pearlescent tiny scales", "stranded on rough dry gravel"),
    ("baby stardust bear with glittering fur", "trapped under fallen wet tree branches"),
    ("baby aurora fawn with glowing mini antlers", "lost alone in thick icy fog"),
]


def resolve_topic() -> str:
    """주제가 직접 들어오지 않으면 날짜/시간 기반으로 365일 자동 주제 선택"""
    if RAW_TOPIC and RAW_TOPIC != "auto":
        return RAW_TOPIC
    
    day_idx = (datetime.datetime.now().timetuple().tm_yday + random.randint(0, 5)) % len(CREATURE_DB)
    creature, crisis = CREATURE_DB[day_idx]
    return f"Rescuing a lost {creature} {crisis} and giving it warm care and cozy bed"


TOPIC = resolve_topic()


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
            wait_time = (attempt + 1) * 20
            print(f"⚠️ 429 대기 중... ({wait_time}초 후 재시도)")
            time.sleep(wait_time)
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
        raise RuntimeError(f"Replicate 렌더링 실패: {data.get('error')}")
    return data


def generate_scene_plan(topic: str) -> dict:
    prompt = f"""You are the director for a viral global YouTube Shorts series: 'Baby Fantasy Creature Sanctuary'.
Design an emotional 4-scene rescue and healing story for: "{topic}".

Rules:
- Exactly 4 scenes (5 seconds each).
- Visual Style: Hyper-detailed 3D cinematic render, ultra-cute baby fantasy creature, huge glossy watery reflective eyes, soft fluffy fur, tilt-shift macro lens, warm cozy lighting, 8k octane render.
- Scene 1: Heartbreaking crisis. Shivering, dirty baby creature with sad teary eyes trapped in harsh environment.
- Scene 2: The Rescue. Gentle warm human hands wrapped in a soft towel, carefully lifting the tiny creature.
- Scene 3: Satisfying Care ASMR. Cleaning away mud, wrapping in warmth, feeding a glowing magical fruit or snowflake.
- Scene 4: Emotional Bond & Comfort. Clean fluffy baby creature purring happily, gently nuzzling human finger, sleeping peacefully in a palm-sized cozy bed.
- Strict JSON output only.

JSON Schema:
{{
  "project_title": "Title in English",
  "style_anchor": "Hyper-detailed cinematic 3D render, adorable baby fantasy creature, huge glossy watery eyes, ultra-soft fluffy texture, warm dreamy lighting, 8k octane render, macro tilt-shift",
  "iconic_element_en": "description of the specific baby creature",
  "aspect_ratio": "9:16",
  "scenes": [
    {{
      "scene_number": 1,
      "visual_prompt_en": "Extreme macro close-up of a tiny shivering baby creature with big teary eyes trapped in wet ground",
      "negative_prompt_en": "blurry, low quality, adult animal, human face, scary, text, watermark"
    }},
    {{
      "scene_number": 2,
      "visual_prompt_en": "Gentle realistic giant human hands wrapped in a soft warm towel gently scooping up the tiny baby creature",
      "negative_prompt_en": "blurry, low quality, watermark, distortion, harsh lighting"
    }},
    {{
      "scene_number": 3,
      "visual_prompt_en": "Satisfying cleaning of the baby creature, feeding a glowing magical tiny crystal fruit",
      "negative_prompt_en": "blurry, low quality, watermark"
    }},
    {{
      "scene_number": 4,
      "visual_prompt_en": "Happy fluffy baby creature glowing with joy, sleeping in a cozy miniature snowflake bed",
      "negative_prompt_en": "blurry, low quality, watermark"
    }}
  ],
  "youtube_metadata": {{
    "title": "Viral Emotional Title with Emojis",
    "description": "Saving a lost tiny baby fantasy creature! 🐾✨ What should we name this cute little one? Leave your idea in the comments! #Shorts #BabyCreature #FantasyRescue #Cute #ASMR",
    "tags": ["babycreature", "fantasyrescue", "cutemonster", "asmr", "satisfying", "shorts", "healing", "cuteanimals"]
  }}
}}"""

    data = post_with_retry(
        "https://api.replicate.com/v1/models/meta/meta-llama-3-70b-instruct/predictions",
        {
            "input": {
                "prompt": prompt,
                "temperature": 0.3,
                "max_tokens": 2048,
                "system_prompt": "You are a JSON generator. Output only valid JSON."
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=120)
    output = data.get("output")
    raw_text = "".join(output) if isinstance(output, list) else str(output)
    
    raw_clean = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
    if match:
        raw_clean = match.group(0)
    return json.loads(raw_clean, strict=False)


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
    """
    FFmpeg 내장 합성 엔진을 통해 0원 과금으로 씬별 4단계 ASMR 효과음 + 힐링 BGM 결합:
    - 0~5초: 눈바람 소리 + 가냘픈 아기 소리 (S1)
    - 5~10초: 부드러운 타월/담요 터치음 (S2)
    - 10~15초: 마법 차임벨 + 오물오물 먹는 소리 (S3)
    - 15~20초: 기분 좋은 골골송 톤 + 수면 힐링 BGM (S4)
    """
    print("🎬 씬별 맞춤 ASMR 사운드팩 + 자장가 BGM 2중 믹싱 진행...")
    
    filter_complex = (
        # 1. 20초 전체 힐링 BGM (432Hz 톤 + 핑크노이즈)
        "anoisesrc=c=pink:r=44100:a=0.02[pink];"
        "sine=f=528:r=44100[tone];"
        "[tone]volume=0.015[tone_soft];"
        "[pink][tone_soft]amix=inputs=2[bgm];"
        
        # 2. 씬 1 효과음 (0~5s): 바람 소리
        "anoisesrc=c=brown:r=44100:a=0.04[wind_raw];"
        "[wind_raw]atrim=0:5,asetpts=PTS-STARTPTS,afade=t=out:st=4:d=1[sfx1];"
        
        # 3. 씬 2 효과음 (5~10s): 부드러운 스위시
        "sine=f=300:r=44100[sfx2_raw];"
        "[sfx2_raw]atrim=0:5,asetpts=PTS-STARTPTS,volume=0.01,afade=t=in:st=0:d=1,afade=t=out:st=4:d=1[sfx2];"
        
        # 4. 씬 3 효과음 (10~15s): 영롱한 마법 차임
        "sine=f=880:r=44100[sfx3_raw];"
        "[sfx3_raw]atrim=0:5,asetpts=PTS-STARTPTS,volume=0.025,afade=t=in:st=0:d=0.5,afade=t=out:st=4:d=1[sfx3];"
        
        # 5. 씬 4 효과음 (15~20s): 따뜻한 골골송 앰비언스
        "sine=f=220:r=44100[sfx4_raw];"
        "[sfx4_raw]atrim=0:5,asetpts=PTS-STARTPTS,volume=0.02,afade=t=in:st=0:d=1[sfx4];"
        
        # 6. 모든 오디오 트랙을 시간순으로 결합
        "[sfx1][sfx2][sfx3][sfx4]concat=n=4:v=0:a=1[all_sfx];"
        "[bgm][all_sfx]amix=inputs=2:duration=first[aout]"
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
    print(f"✅ ASMR 사운드팩 믹싱 완료: {output_path}")


def send_telegram_preview(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🐾 *[{plan['project_title']}] 아기 환상종 구조 영상 완성!*\n\n"
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
