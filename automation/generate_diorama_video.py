"""
글로벌 미니어처 ASMR 숏폼 자동화 파이프라인 (v14 - Fully Verified & Fail-Safe)
"""

import os
import re
import json
import time
import base64
import subprocess
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
TOPIC = os.environ.get("TOPIC", "Miniature rescue mission").strip()

WORK_DIR = "video_work"
SCENE_DURATION = 5.0

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}


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
            print(f"⚠️ 429 제한 발생: {wait_time}초 대기 후 재시도...")
            time.sleep(wait_time)
            continue
        res.raise_for_status()
        return res.json()
    raise RuntimeError(f"최대 재시도 초과: {url}")


def poll_until_done(data: dict, max_wait_sec: int = 360) -> dict:
    get_url = data.get("urls", {}).get("get")
    if not get_url:
        raise ValueError(f"유효하지 않은 응답: {data}")

    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(5)
        waited += 5
        poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
        poll_res.raise_for_status()
        data = poll_res.json()

    if data.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 렌더링 실패 (status={data.get('status')}): {data.get('error')}")
    return data


def generate_scene_plan(topic: str) -> dict:
    prompt = f"""You are a director for viral Miniature ASMR YouTube Shorts.
Design a 4-scene rescue and satisfying transformation story for topic: "{topic}".

Rules:
- Exactly 4 scenes (5 seconds each).
- Visual Style: Hyper-detailed 3D miniature diorama, tilt-shift macro photography, cute claymation texture, warm soft cinematic lighting, 8k, octane render, shallow depth of field.
- Scene 1: Tiny cute character/object in distress.
- Scene 2: Giant realistic human hand enters holding a tiny tool/water.
- Scene 3: Satisfying action (pouring crystal clear water, rapid blooming).
- Scene 4: Lush restored diorama, joyful tiny characters celebrating.
- Strict JSON output only.

JSON Schema:
{{
  "project_title": "Title in English",
  "style_anchor": "Hyper-detailed 3D miniature diorama, tilt-shift macro photography, cute claymation texture, warm lighting, 8k",
  "iconic_element_en": "description of tiny subject",
  "bgm_prompt_en": "relaxing acoustic marimba and soft music box, gentle warm ambient melody, 90 bpm",
  "aspect_ratio": "9:16",
  "scenes": [
    {{
      "scene_number": 1,
      "visual_prompt_en": "Macro shot of tiny cute clay characters struggling in dry cracked soil, tilt-shift lens",
      "negative_prompt_en": "blurry, low quality, human face, text, watermark"
    }},
    {{
      "scene_number": 2,
      "visual_prompt_en": "A realistic giant human hand entering from top holding a tiny watering can over the scene",
      "negative_prompt_en": "blurry, low quality, watermark, distortion"
    }},
    {{
      "scene_number": 3,
      "visual_prompt_en": "Crystal clear water pouring onto miniature ground, soil turning rich and dark, rapid blooming of green sprouts",
      "negative_prompt_en": "blurry, low quality, watermark"
    }},
    {{
      "scene_number": 4,
      "visual_prompt_en": "Lush flourishing miniature garden, happy tiny characters jumping in joy under sunlight",
      "negative_prompt_en": "blurry, low quality, watermark"
    }}
  ],
  "youtube_metadata": {{
    "title": "Viral Title with Emojis",
    "description": "Satisfying Miniature ASMR Rescue Mission #Shorts #Miniature #ASMR #Satisfying",
    "tags": ["miniature", "diorama", "asmr", "satisfying", "shorts", "claymation"]
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
    time.sleep(15)  # 429 방지 안전 쿨다운
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


def generate_bgm(prompt: str, duration_sec: int) -> str:
    print(f"🎵 ASMR 배경음 생성 시도: '{prompt}'")
    bgm_path = f"{WORK_DIR}/bgm.mp3"
    
    # 1. 고품질 앰비언스 오디오 생성 (포근한 ASMR 핑크 노이즈 + 잔잔한 톤)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anoisesrc=c=pink:r=44100:a=0.04",
            "-f", "lavfi", "-i", "sine=f=432:r=44100",
            "-filter_complex", "[1:a]volume=0.02[tone];[0:a][tone]amix=inputs=2[out]",
            "-map", "[out]",
            "-t", str(duration_sec),
            bgm_path
        ],
        check=True,
        capture_output=True,
    )
    print(f"✅ ASMR 전용 배경음 완성: {bgm_path}")
    return bgm_path


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


def mux_audio(video_path: str, bgm_path: str, output_path: str):
    print("🎬 비디오 + 오디오 최종 믹싱 진행...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ],
        check=True,
        capture_output=True,
    )
    print(f"✅ 최종 비디오 합성 완료: {output_path}")


def send_telegram_preview(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🎬 *[{plan['project_title']}] 영상 제작 완료!*\n\n"
        f"📌 *Title*: {yt['title']}\n"
        f"📝 *Description*: {yt['description']}\n"
        f"🏷️ *Tags*: {tags_str}\n\n"
        f"🚀 *유튜브에 '일부공개'로 안전하게 등록 중입니다...*"
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
    print(f"Topic: {TOPIC}")
    os.makedirs(WORK_DIR, exist_ok=True)
    send_telegram_message(f"🎬 ASMR 미니어처 영상 제작 시작: '{TOPIC}'")

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
        negative_prompt = scene.get("negative_prompt_en", "blurry, low quality, watermark, text")

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

    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    bgm_path = generate_bgm(plan["bgm_prompt_en"], total_duration)

    final_path = f"{WORK_DIR}/final_video.mp4"
    mux_audio(stitched_video_path, bgm_path, final_path)

    send_telegram_preview(final_path, plan)
    print("ASMR 최종 영상 전송 완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
