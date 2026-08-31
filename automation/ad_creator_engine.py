import os
import re
import json
import time
import asyncio
import subprocess
import requests
import edge_tts

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
WORK_DIR = "ad_work"
TTS_VOICE = "ko-KR-SunHiNeural"

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}

SCENE_TYPE_BY_NUMBER = {
    1: "hook",
    2: "agitation",
    3: "solution",
    4: "cta",
}

SCENE_ENHANCERS = {
    "hook": "cinematic beauty commercial, natural lighting, ultra-detailed, 8k octane render, sharp focus",
    "agitation": "raw close-up, dramatic lighting, tired skin or problem state, realistic, 8k",
    "solution": "masterpiece, commercial product photography, 8k octane render, volumetric lighting, luxury clean background",
    "cta": "masterpiece, luxury commercial presentation, 8k, golden hour studio lighting, premium clean background",
}

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

def generate_ad_script(product_name: str, usps: list, target_audience: str, tone: str, format_type: str = "9:16") -> dict:
    """Llama-3를 통한 4단 고전환율 광고 기획 및 프롬프트 실시간 생성"""
    usp_str = ", ".join(usps) if usps else product_name
    prompt = f"""You are a top-tier performance ad director for Meta/TikTok ads.
Create a high-converting 4-scene (15-20s total) commercial video script for:
- Product Name: {product_name}
- Key USPs: {usp_str}
- Target Audience: {target_audience}
- Tone & Mood: {tone}
- Format: {format_type}

Scene Structure:
- Scene 1 (Hook / 0-5s): Shocking question or problem statement to stop scrolling.
- Scene 2 (Agitation / 5-10s): Emphasizing the pain point, fatigue, or need.
- Scene 3 (Product Solution / 10-15s): Luxurious showcase of the product solving the problem with key ingredients.
- Scene 4 (CTA / 15-20s): Compelling limited offer, 1+1 event, or call to action.

Output strict JSON only with this schema:
{{
  "campaign_title": "{product_name} Performance Ad",
  "scenes": [
    {{
      "scene_number": 1,
      "hook_text": "짧고 강렬한 훅 자막 (한글 15자 내외)",
      "sub_text": "보조 설명 자막",
      "narration": "쇼호스트가 자연스럽게 말할 15자 내외 내레이션 대사",
      "visual_prompt": "Cinematic commercial shot, detailed prompt for Flux 1.1 Pro Ultra",
      "motion_prompt": "Camera motion prompt for Kling video"
    }},
    {{
      "scene_number": 2,
      "hook_text": "핵심 결핍 자극 자막",
      "sub_text": "보조 설명 자막",
      "narration": "결핍을 공감해주는 쇼호스트 내레이션 대사",
      "visual_prompt": "Cinematic close-up showing the problem or fatigue state",
      "motion_prompt": "Camera motion prompt"
    }},
    {{
      "scene_number": 3,
      "hook_text": "제품의 핵심 성분 및 효능 자막",
      "sub_text": "보조 설명 자막",
      "narration": "제품의 놀라운 효과를 설명하는 내레이션 대사",
      "visual_prompt": "Luxury commercial product macro showcase with glowing liquid or capsules",
      "motion_prompt": "Camera motion prompt"
    }},
    {{
      "scene_number": 4,
      "hook_text": "지금 구매 시 한정 혜택",
      "sub_text": "프로필 링크 클릭",
      "narration": "지금 바로 구매하도록 유도하는 클로징 대사",
      "visual_prompt": "Luxury product packaging on clean podium with studio lighting",
      "motion_prompt": "Camera motion prompt"
    }}
  ]
}}"""

    data = post_with_retry(
        "https://api.replicate.com/v1/models/meta/meta-llama-3-70b-instruct/predictions",
        {
            "input": {
                "prompt": prompt,
                "temperature": 0.6,
                "max_tokens": 2048,
                "system_prompt": "You are a professional performance ad copywriter. Output only valid JSON."
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=60)
    raw_text = "".join(data.get("output", []))
    raw_clean = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", raw_clean, re.DOTALL)
    if match:
        raw_clean = match.group(0)
    return json.loads(raw_clean, strict=False)

async def _generate_tts_async(text: str, output_path: str, voice: str = TTS_VOICE, rate: str = "+5%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def generate_voiceover(text: str, output_path: str, voice: str = TTS_VOICE):
    clean_text = re.sub(r"[^\w\s.,!?]", "", text).strip()
    asyncio.run(_generate_tts_async(clean_text, output_path, voice))

def get_audio_duration(audio_path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 4.0

def pick_scene_video_duration(voice_sec: float) -> int:
    return 5 if voice_sec <= 4.8 else 10

def generate_ad_visual(prompt: str, scene_number: int, aspect_ratio: str = "9:16") -> str:
    scene_type = SCENE_TYPE_BY_NUMBER.get(scene_number, "solution")
    enhancer = SCENE_ENHANCERS[scene_type]
    full_prompt = f"{prompt}, {enhancer}"

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

def generate_ad_visual_with_product(product_image_url: str, scene_prompt: str,
                                     scene_number: int, aspect_ratio: str = "9:16") -> str:
    scene_type = SCENE_TYPE_BY_NUMBER.get(scene_number, "solution")
    enhancer = SCENE_ENHANCERS[scene_type]
    edit_instruction = (
        f"Keep the product bottle, shape, label, and branding exactly as in the "
        f"original photo — do not alter the product itself. Place it in this new scene: "
        f"{scene_prompt}, {enhancer}"
    )

    data = post_with_retry(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-kontext-pro/predictions",
        {
            "input": {
                "prompt": edit_instruction,
                "input_image": product_image_url,
                "aspect_ratio": aspect_ratio,
                "output_format": "jpg",
                "safety_tolerance": 2,
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=120)
    output = data.get("output")
    return output[0] if isinstance(output, list) else output

def generate_ad_motion(image_source: str, motion_prompt: str, aspect_ratio: str = "9:16", index: int = 1, duration: int = 5) -> str:
    time.sleep(10)
    data = post_with_retry(
        "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
        {
            "input": {
                "prompt": motion_prompt,
                "negative_prompt": "blurry, distortion, low quality, jitter, text, watermark",
                "image": image_source,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }
        }
    )
    data = poll_until_done(data, max_wait_sec=360)
    video_url = data.get("output")[0] if isinstance(data.get("output"), list) else data.get("output")

    os.makedirs(WORK_DIR, exist_ok=True)
    clip_path = f"{WORK_DIR}/raw_scene_{index}.mp4"
    res = requests.get(video_url, timeout=60)
    with open(clip_path, "wb") as f:
        f.write(res.content)
    return clip_path

def _resolve_korean_font_path() -> str:
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf" if os.name == "nt" else None,
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None

def overlay_ad_typography(input_clip: str, hook_text: str, sub_text: str, output_clip: str, aspect_ratio: str = "9:16"):
    font_file = _resolve_korean_font_path()
    font_escaped = font_file.replace("\\", "/").replace(":", "\\:") if font_file else None

    if aspect_ratio == "9:16":
        main_size = 52
        sub_size = 30
        main_y = "h*0.12"
        sub_y = "h*0.12+70"
    else:
        main_size = 64
        sub_size = 36
        main_y = "h*0.10"
        sub_y = "h*0.10+80"

    clean_hook = hook_text.replace("'", "").replace(":", "").replace("\\", "")
    clean_sub = sub_text.replace("'", "").replace(":", "").replace("\\", "")

    fontfile_clause = f"fontfile='{font_escaped}':" if font_escaped else ""
    draw_filter = (
        f"drawtext={fontfile_clause}text='{clean_hook}':"
        f"fontcolor=yellow:fontsize={main_size}:box=1:boxcolor=black@0.75:boxborderw=16:"
        f"x=(w-text_w)/2:y={main_y},"
        f"drawtext={fontfile_clause}text='{clean_sub}':"
        f"fontcolor=white:fontsize={sub_size}:box=1:boxcolor=black@0.6:boxborderw=10:"
        f"x=(w-text_w)/2:y={sub_y}"
    )

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_clip, "-vf", draw_filter, "-c:v", "libx264", "-pix_fmt", "yuv420p", output_clip],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        subprocess.run(["ffmpeg", "-y", "-i", input_clip, "-c", "copy", output_clip], check=True, capture_output=True)

def stitch_ad_clips(clip_paths: list, output_path: str):
    concat_list = f"{WORK_DIR}/concat_ad.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_paths:
            f.write(f"file '{os.path.abspath(c).replace(chr(92), '/')}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", output_path],
        check=True,
        capture_output=True,
    )

def mix_voiceover_and_bgm(video_path: str, voice_audio_paths: list, scene_durations: list, output_path: str):
    total_sec = sum(scene_durations)
    inputs = ["-i", video_path]
    filter_parts = []
    
    inputs += ["-f", "lavfi", "-i", f"anoisesrc=c=pink:r=44100:a=0.012:d={total_sec}"]
    filter_parts.append(
        f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
        f"volume=0.12,afade=t=in:st=0:d=1.0,afade=t=out:st={max(total_sec - 2, 0)}:d=2.0[bgm]"
    )

    voice_labels = []
    stream_idx = 2
    cumulative_delay = 0.0
    for i, audio_file in enumerate(voice_audio_paths):
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 1000:
            inputs += ["-i", audio_file]
            delay_ms = int((cumulative_delay + 0.2) * 1000)
            v_label = f"v{stream_idx}"
            filter_parts.append(
                f"[{stream_idx}:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,"
                f"volume=1.2,adelay={delay_ms}|{delay_ms}[{v_label}]"
            )
            voice_labels.append(f"[{v_label}]")
            stream_idx += 1
        cumulative_delay += scene_durations[i]

    all_inputs = "[bgm]" + "".join(voice_labels)
    filter_parts.append(
        f"{all_inputs}amix=inputs={1 + len(voice_labels)}:duration=first:normalize=0,"
        f"alimiter=limit=0.95[aout]"
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(filter_parts),
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
