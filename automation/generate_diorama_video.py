"""
글로벌 미니어처 ASMR 숏폼 자동화 파이프라인 (v11 - Rate-Limit Safe Edition)
"""

import os
import re
import json
import time
import base64
import subprocess
import requests

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"].strip()
TOPIC = os.environ["TOPIC"].strip()

WORK_DIR = "video_work"
SCENE_DURATION = 5.0

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}


def post_with_retry(url: str, json_data: dict, max_retries: int = 5) -> dict:
    """429 Rate Limit 방지용 자동 재시도 함수"""
    for attempt in range(max_retries):
        res = requests.post(url, headers=REPLICATE_HEADERS, json=json_data, timeout=30)
        if res.status_code == 429:
            wait_time = (attempt + 1) * 15
            print(f"⚠️ 429 대기 중... ({wait_time}초 후 재시도)")
            time.sleep(wait_time)
            continue
        res.raise_for_status()
        return res.json()
    raise RuntimeError(f"최대 재시도 초과: {url}")


def poll_until_done(data: dict, max_wait_sec: int = 300) -> dict:
    get_url = data["urls"]["get"]
    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(5)
        waited += 5
        poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
        poll_res.raise_for_status()
        data = poll_res.json()

    if data.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 작업 실패 (status={data.get('status')}): {data.get('error')}")
    return data


def generate_scene_plan(topic: str) -> dict:
    prompt = f"""You are an elite sound designer & director for viral Miniature ASMR YouTube Shorts.
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
  "bgm_prompt_en": "whimsical soft cozy acoustic pizzicato strings, relaxing lo-fi ASMR background music, 90 bpm",
  "aspect_ratio": "9:16",
  "scenes": [
    {{
      "scene_number": 1,
      "visual_prompt_en": "Macro shot of tiny cute clay characters struggling in dry cracked soil, tilt-shift lens",
      "negative_prompt_en": "blurry, low quality, human face, text, watermark",
      "sfx_prompt_en": "dry cracked earth, desert wind blowing"
    }},
    {{
      "scene_number": 2,
      "visual_prompt_en": "A realistic giant human hand entering from top holding a tiny watering can over the scene",
      "negative_prompt_en": "blurry, low quality, watermark, distortion",
      "sfx_prompt_en": "gentle tool movement, soft air swoosh"
    }},
    {{
      "scene_number": 3,
      "visual_prompt_en": "Crystal clear water pouring onto miniature ground, soil turning rich and dark, rapid blooming of green sprouts",
      "negative_prompt_en": "blurry, low quality, watermark",
      "sfx_prompt_en": "crisp refreshing water pouring, liquid splash, water bubbles ASMR"
    }},
    {{
      "scene_number": 4,
      "visual_prompt_en": "Lush flourishing miniature garden, happy tiny characters jumping in joy under sunlight",
      "negative_prompt_en": "blurry, low quality, watermark",
      "sfx_prompt_en": "sparkling magic chime, fairy dust sound"
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
                "system_prompt": "You are a specialized JSON generator. You only output valid parseable JSON objects."
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
    # 요청 전 안전 딜레이
    time.sleep(10)
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
    data = poll_until_done(data, max_wait_sec=300)

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
    print(f"🎵 ASMR 배경음악 생성: '{prompt}'")
    time.sleep(5)
    data = post_with_retry(
        "https://api.replicate.com/v1/models/meta/musicgen/predictions",
        {
            "input": {
                "prompt": prompt,
                "duration": int(min(duration_sec, 30)),
                "output_format": "mp3",
                "normalization_strategy": "loudness",
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=180)
    output = data.get("output")
    audio_url = output if isinstance(output, str) else (output[0] if isinstance(output, list) else None)
    
    if not audio_url:
        raise RuntimeError(f"BGM 생성 실패: {data}")

    audio_res = requests.get(audio_url, timeout=60)
    audio_res.raise_for_status()
    bgm_path = f"{WORK_DIR}/bgm.mp3"
    with open(bgm_path, "wb") as f:
        f.write(audio_res.content)
    return bgm_path


def generate_sfx_clip(prompt: str, index: int) -> str:
    """AudioLDM 안정화 호출 및 실패 시 고주파 ASMR 노이즈/무음 자동 폴백"""
    print(f"🔊 씬 {index} 효과음 생성: '{prompt}'")
    sfx_path = f"{WORK_DIR}/sfx_scene_{index}.wav"
    try:
        time.sleep(3)
        data = post_with_retry(
            "https://api.replicate.com/v1/models/lucataco/audioldm/predictions",
            {"input": {"prompt": prompt, "duration": "5.0"}}
        )
        data = poll_until_done(data, max_wait_sec=90)
        output = data.get("output")
        sfx_url = output if isinstance(output, str) else (output[0] if isinstance(output, list) else None)
        if sfx_url:
            res = requests.get(sfx_url, timeout=60)
            res.raise_for_status()
            with open(sfx_path, "wb") as f:
                f.write(res.content)
            return sfx_path
    except Exception as e:
        print(f"⚠️ 씬 {index} 효과음 폴백 적용: {e}")

    # 생성 실패 시 5초 무음 파일 생성하여 믹싱 유지
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "5", sfx_path],
        check=True,
        capture_output=True,
    )
    return sfx_path


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


def stitch_sfx_tracks(sfx_paths: list, output_sfx_path: str):
    sfx_list_path = f"{WORK_DIR}/sfx_concat_list.txt"
    with open(sfx_list_path, "w") as f:
        for path in sfx_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", sfx_list_path,
         "-c:a", "pcm_s16le", output_sfx_path],
        check=True,
        capture_output=True,
    )


def mux_multi_layer_audio(video_path: str, bgm_path: str, sfx_path: str, output_path: str):
    filter_complex = (
        "[1:a]volume=0.35[bgm];"
        "[2:a]volume=1.2[sfx];"
        "[bgm][sfx]amix=inputs=2:duration=longest[aout]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-i", sfx_path,
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
        f"🎬 *[{plan['project_title']}] ASMR 영상 제작 완료!*\n\n"
        f"📌 *Title*: {yt['title']}\n"
        f"📝 *Description*: {yt['description']}\n"
        f"🏷️ *Tags*: {tags_str}\n\n"
        f"🚀 *유튜브에 '일부공개'로 등록 중입니다...*"
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


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})


def main():
    print(f"Topic: {TOPIC}")
    os.makedirs(WORK_DIR, exist_ok=True)
    send_telegram_message(f"🎬 ASMR 미니어처 영상 제작 시작: '{TOPIC}' (예상 소요시간: ~6분)")

    plan = generate_scene_plan(TOPIC)
    
    with open(f"{WORK_DIR}/metadata.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    style_anchor = plan["style_anchor"]
    iconic_element = plan["iconic_element_en"]
    clip_paths = []
    sfx_paths = []

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

        sfx_prompt = scene.get("sfx_prompt_en", "satisfying water pouring asmr sound")
        sfx_clip = generate_sfx_clip(sfx_prompt, idx)
        sfx_paths.append(sfx_clip)

    stitched_video_path = f"{WORK_DIR}/stitched_video.mp4"
    stitch_clips_clean(clip_paths, stitched_video_path)

    stitched_sfx_path = f"{WORK_DIR}/stitched_sfx.wav"
    stitch_sfx_tracks(sfx_paths, stitched_sfx_path)

    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    bgm_path = generate_bgm(plan["bgm_prompt_en"], total_duration)

    final_path = f"{WORK_DIR}/final_video.mp4"
    mux_multi_layer_audio(stitched_video_path, bgm_path, stitched_sfx_path, final_path)

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
