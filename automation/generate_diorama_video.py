"""
글로벌 미니어처 ASMR 숏폼 자동화 스크립트 (v7 - Replicate LLM Engine)
- Anthropic 의존성 제거 -> Replicate Meta Llama 3.3 70B로 씬 기획 생성
- 화면 자막 없이 100% 비주얼 및 ASMR 중심 렌더링
- Flux -> Kling 2.5 Turbo -> 마지막 프레임 연결
- 무자막 영상 병합 + MusicGen ASMR 앰비언스 믹싱
- 텔레그램 승인 메시지 전송 및 metadata.json 저장
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


def poll_until_done(data: dict, max_wait_sec: int = 180) -> dict:
    get_url = data["urls"]["get"]
    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(4)
        waited += 4
        poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
        poll_res.raise_for_status()
        data = poll_res.json()

    if data.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 작업 실패 (status={data.get('status')}): {data.get('error')}")
    return data


def generate_scene_plan(topic: str) -> dict:
    prompt = f"""You are a director for viral Miniature ASMR YouTube Shorts.
Design a 4-scene rescue and satisfying transformation story for topic: "{topic}".

Rules:
- Exactly 4 scenes (5 seconds each).
- Visual Style: Hyper-detailed 3D miniature diorama, tilt-shift macro photography, cute claymation texture, warm soft cinematic lighting, 8k, octane render, shallow depth of field.
- Scene 1: Tiny cute character/object in distress.
- Scene 2: Giant realistic human hand enters holding a tiny tool/water.
- Scene 3: Satisfying action (pouring water, magic repair, rapid blooming).
- Scene 4: Lush restored diorama, joyful tiny characters celebrating.
- Strict JSON output only. No conversational text.

JSON Schema:
{{
  "project_title": "Title in English",
  "style_anchor": "Hyper-detailed 3D miniature diorama, tilt-shift macro photography, cute claymation texture, warm lighting, 8k",
  "iconic_element_en": "description of tiny subject",
  "bgm_prompt_en": "whimsical playful pizzicato strings, light marimba, cheerful cozy acoustic feeling, satisfying ASMR rhythm, 110 bpm",
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
      "visual_prompt_en": "Crystal clear water pouring onto miniature ground, soil turning dark, rapid blooming of green sprouts",
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
    "description": "Engaging description with #Shorts #Miniature #ASMR",
    "tags": ["miniature", "diorama", "asmr", "satisfying", "shorts", "claymation"]
  }}
}}"""

    res = requests.post(
        "https://api.replicate.com/v1/models/meta/meta-llama-3-70b-instruct/predictions",
        headers=REPLICATE_HEADERS,
        json={
            "input": {
                "prompt": prompt,
                "temperature": 0.3,
                "max_tokens": 2048,
                "system_prompt": "You are a specialized JSON generator. You only output valid parseable JSON objects without markdown fences."
            }
        },
        timeout=30,
    )
    res.raise_for_status()
    data = poll_until_done(res.json(), max_wait_sec=120)
    output = data.get("output")
    raw_text = "".join(output) if isinstance(output, list) else str(output)
    
    # JSON 추출 및 파싱
    raw_clean = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
    if match:
        raw_clean = match.group(0)
    return json.loads(raw_clean, strict=False)


def generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> str:
    res = requests.post(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        headers=REPLICATE_HEADERS,
        json={"input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "output_format": "jpg"}},
        timeout=30,
    )
    res.raise_for_status()
    data = poll_until_done(res.json(), max_wait_sec=90)
    output = data.get("output")
    image_url = output[0] if isinstance(output, list) else output
    if not image_url:
        raise RuntimeError(f"Image generation failed: {data}")
    return image_url


def generate_video_clip(image_source: str, motion_prompt: str, negative_prompt: str,
                         aspect_ratio: str, index: int) -> str:
    res = requests.post(
        "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
        headers=REPLICATE_HEADERS,
        json={
            "input": {
                "prompt": motion_prompt,
                "negative_prompt": negative_prompt,
                "image": image_source,
                "duration": 5,
                "aspect_ratio": aspect_ratio,
            }
        },
        timeout=30,
    )
    res.raise_for_status()
    data = poll_until_done(res.json(), max_wait_sec=300)

    output = data.get("output")
    video_url = output[0] if isinstance(output, list) else output
    if not video_url:
        raise RuntimeError(f"Video generation failed: {data}")

    video_res = requests.get(video_url, timeout=60)
    video_res.raise_for_status()
    os.makedirs(WORK_DIR, exist_ok=True)
    clip_path = f"{WORK_DIR}/scene_{index}.mp4"
    with open(clip_path, "wb") as f:
        f.write(video_res.content)
    return clip_path


def generate_bgm(prompt: str, duration_sec: int) -> str:
    try:
        res = requests.post(
            "https://api.replicate.com/v1/models/meta/musicgen/predictions",
            headers=REPLICATE_HEADERS,
            json={
                "input": {
                    "prompt": prompt,
                    "model_version": "stereo-large",
                    "duration": min(duration_sec, 30),
                    "output_format": "mp3",
                    "normalization_strategy": "peak",
                }
            },
            timeout=30,
        )
        res.raise_for_status()
        data = poll_until_done(res.json(), max_wait_sec=180)
        output = data.get("output")
        audio_url = output[0] if isinstance(output, list) else output
        if not audio_url:
            raise RuntimeError(f"BGM generation failed: {data}")

        audio_res = requests.get(audio_url, timeout=60)
        audio_res.raise_for_status()
        bgm_path = f"{WORK_DIR}/bgm.mp3"
        with open(bgm_path, "wb") as f:
            f.write(audio_res.content)
        print(f"BGM 생성 완료: {bgm_path}")
        return bgm_path
    except Exception as e:
        print(f"BGM 생성 건너뜀: {e}")
        return None


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
    if not bgm_path:
        subprocess.run(["cp", video_path, output_path], check=True)
        return

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def send_telegram_video(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags_str = " ".join([f"#{t.replace('#', '')}" for t in yt.get("tags", [])])
    caption = (
        f"🎬 *[{plan['project_title']}] Global Video Created!*\n\n"
        f"📌 *Title*: {yt['title']}\n"
        f"📝 *Description*: {yt['description']}\n"
        f"🏷️ *Tags*: {tags_str}\n\n"
        f"👇 *영상을 확인하시고 아래 버튼을 눌러 발행하세요.*"
    )
    if len(caption) > 1000:
        caption = caption[:1000] + "..."

    reply_markup = {
        "inline_keyboard": [
            [{"text": "🚀 Publish to YouTube Shorts", "callback_data": "approve_upload"}],
            [{"text": "❌ Discard", "callback_data": "cancel_upload"}]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(reply_markup)
            },
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
    send_telegram_message(f"🎬 Creating global ASMR miniature video for: '{TOPIC}' (Takes ~3-4 mins)")

    plan = generate_scene_plan(TOPIC)
    print("Plan generated successfully:", json.dumps(plan, ensure_ascii=False, indent=2))
    
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

    send_telegram_video(final_path, plan)
    print("완료: 텔레그램 전송 성공!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ Video generation failed: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
