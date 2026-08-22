"""
미니어처/디오라마 시네마틱 영상 자동화 스크립트 (v5)
- Claude API로 바이럴 미니어처 서사(위기 -> 거인의 손 등장 -> 극적 해결 -> 해피엔딩) 생성
- Flux-schnell 첫 씬 생성 -> Kling 2.5 I2V -> 마지막 프레임 루프
- ffmpeg 자막 + MusicGen BGM 믹싱
- 유튜브 업로드용 메타데이터 JSON 저장
- 텔레그램으로 영상과 인라인 승인 버튼 전송
"""

import os
import re
import json
import time
import base64
import subprocess
import requests
from anthropic import Anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"].strip()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"].strip()
TOPIC = os.environ["TOPIC"].strip()

WORK_DIR = "video_work"
FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
SCENE_DURATION = 5.0
client = Anthropic(api_key=ANTHROPIC_API_KEY)

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}


def generate_scene_plan(topic: str) -> dict:
    system_prompt = """당신은 수백만 조회수를 기록하는 미니어처 ASMR 숏폼(Miniature Rescue / Satisfying Diorama) 전문 크리에이터입니다.
사용자가 주제를 입력하면, 틱톡/유튜브 쇼츠에서 바이럴되는 '귀여운 미니어처 캐릭터의 위기 극복 및 힐링 스토리'를 설계합니다.

[스토리텔링 필수 4단계 공식 - Rescue & Satisfying Structure]
1. 씬 1 (위기/곤경): 아주 작고 귀여운 미니어처 캐릭터가 곤경에 처함 (가뭄, 추위, 고장, 배고픔 등).
2. 씬 2 (도움의 손길 등장): 거대한 사람의 손(Realistic giant human hand)이나 신비한 도구가 나타나 도움을 주기 시작함.
3. 씬 3 (극적인 변화/카타르시스): 물이 쏟아지거나 마법처럼 문제가 해결되며 폭발적인 시각적 만족감(Satisfying growth, clean up)을 줌.
4. 씬 4 (행복한 결말): 풍요롭고 완벽해진 미니어처 세상에서 캐릭터들이 기뻐하며 마무리.

[스타일 앵커 원칙 (style_anchor)]
반드시 아래 키워드를 기본으로 조합하세요:
"Hyper-detailed 3D miniature diorama, tilt-shift macro photography, cute claymation texture, miniature scale, warm soft cinematic lighting, 8k render, octane render, shallow depth of field"

[씬 설계 원칙]
- 정확히 4개 씬으로 분할 (씬당 정확히 5초)
- 1번 씬의 디오라마 환경이 4번 씬까지 연속적으로 유지되어야 합니다.
- 2~3번 씬에는 'giant human hand'의 물리적 상호작용(물 붓기, 씨앗 심기, 수리 등)을 명시하세요.

[온스크린 자막 원칙]
- hook_text_ko: 1번 씬의 위기를 강조하는 한국어 훅 (15자 이내, 예: "말라죽기 직전의 미니 농장?!")
- caption_ko: 각 씬의 상황을 직관적으로 보여주는 짧은 문구 (10자 이내)

[배경음 원칙]
- bgm_prompt_en: ASMR에 어울리는 경쾌하고 따뜻한 피치카토/어쿠스틱 무드 ("whimsical playful pizzicato strings, light marimba, cheerful cozy acoustic feeling, satisfying ASMR rhythm, 110 bpm")

반드시 아래 JSON 구조로만 응답하세요 (JSON 마크다운 외 다른 설명 금지):
{
  "project_title": "주제명",
  "style_anchor": "전체 영상 공통 미니어처 스타일 문구 (영문)",
  "iconic_element_en": "구조 대상이 되는 귀여운 미니어처 캐릭터/사물 묘사 (영문)",
  "hook_text_ko": "영상 시작 2.5초 자막용 한국어 훅 (15자 이내)",
  "bgm_prompt_en": "ASMR/경쾌한 배경음 설명 (영문)",
  "aspect_ratio": "9:16",
  "scenes": [
    {
      "scene_number": 1,
      "story_ko": "곤경에 처한 상황",
      "caption_ko": "자막 1",
      "visual_prompt_en": "Macro shot of tiny cute clay characters struggling in dry cracked soil farm, tilt-shift, cute expressive faces, miniature props",
      "negative_prompt_en": "blurry, low quality, real human full body, realistic face, watermark"
    },
    {
      "scene_number": 2,
      "story_ko": "거인의 손 등장",
      "caption_ko": "자막 2",
      "visual_prompt_en": "A realistic giant human hand entering from top holding a watering can, preparing to pour water over the dry diorama",
      "negative_prompt_en": "blurry, low quality, watermark, distortion"
    },
    {
      "scene_number": 3,
      "story_ko": "극적인 변화와 만족감",
      "caption_ko": "자막 3",
      "visual_prompt_en": "Crystal clear water pouring from watering can onto miniature crops, soil turning rich and moist, rapid magical plant growth",
      "negative_prompt_en": "blurry, low quality, watermark"
    },
    {
      "scene_number": 4,
      "story_ko": "행복한 결말",
      "caption_ko": "자막 4",
      "visual_prompt_en": "Vibrant flourishing miniature green farm full of ripe tiny vegetables, tiny happy characters celebrating under warm sunlight, macro shot",
      "negative_prompt_en": "blurry, low quality, watermark"
    }
  ],
  "youtube_metadata": {
    "title": "후킹 제목",
    "description": "영상 요약",
    "tags": ["miniature", "diorama", "asmr", "satisfying", "shorts"],
    "shorts_hook": "첫 3초 후킹 나레이션"
  }
}"""

    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": f"주제 입력: {topic}"}],
    )
    text_block = next((b for b in response.content if b.type == "text"), None)
    if text_block is None:
        raise RuntimeError("Claude 응답에서 텍스트 블록을 찾지 못했습니다.")
    raw = text_block.text.strip()
    raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return json.loads(raw, strict=False)


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
        raise RuntimeError(f"이미지 생성 실패: {data}")
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
        raise RuntimeError(f"영상 생성 실패: {data}")

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
            raise RuntimeError(f"배경음 생성 실패: {data}")

        audio_res = requests.get(audio_url, timeout=60)
        audio_res.raise_for_status()
        bgm_path = f"{WORK_DIR}/bgm.mp3"
        with open(bgm_path, "wb") as f:
            f.write(audio_res.content)
        print(f"배경음 생성 완료: {bgm_path}")
        return bgm_path
    except Exception as e:
        print(f"배경음 생성 건너뜀: {e}")
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


def build_caption_segments(plan: dict) -> list:
    segments = [(plan["hook_text_ko"], 0.0, 2.5)]
    for i, scene in enumerate(plan["scenes"]):
        start = i * SCENE_DURATION
        end = start + SCENE_DURATION
        if i == 0:
            start = 2.5
        text = scene.get("caption_ko", "")
        if text:
            segments.append((text, start, end))
    return segments


def stitch_clips_with_captions(clip_paths: list, plan: dict, output_path: str):
    concat_list_path = f"{WORK_DIR}/concat_list.txt"
    with open(concat_list_path, "w") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    concatenated_path = f"{WORK_DIR}/concatenated.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
         "-c", "copy", concatenated_path],
        check=True,
    )

    segments = build_caption_segments(plan)
    filters = []
    for idx, (text, start, end) in enumerate(segments):
        text_path = f"{WORK_DIR}/caption_{idx}.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
        filters.append(
            f"drawtext=fontfile={FONT_PATH}:textfile={text_path}:reload=1:"
            f"fontcolor=white:fontsize=56:box=1:boxcolor=black@0.55:boxborderw=20:"
            f"x=(w-text_w)/2:y=140:enable='between(t,{start},{end})'"
        )
    vf = ",".join(filters)

    subprocess.run(
        ["ffmpeg", "-y", "-i", concatenated_path, "-vf", vf,
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
        f"🎬 *[{plan['project_title']}] 영상 생성 완료!*\n\n"
        f"📌 *유튜브 제목*: {yt['title']}\n"
        f"📝 *설명*: {yt['description']}\n"
        f"🏷️ *태그*: {tags_str}\n\n"
        f"👇 *영상을 확인하시고 발행을 승인해 주세요.*"
    )
    if len(caption) > 1000:
        caption = caption[:1000] + "..."

    # 유튜브 발행 승인 인라인 키보드
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🚀 유튜브 즉시 업로드 (발행)", "callback_data": "approve_upload"}],
            [{"text": "❌ 발행 취소", "callback_data": "cancel_upload"}]
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
    print(f"주제: {TOPIC}")
    os.makedirs(WORK_DIR, exist_ok=True)
    send_telegram_message(f"🎬 '{TOPIC}' 미니어처 영상 제작을 시작합니다! (약 3~4분 소요)")

    plan = generate_scene_plan(TOPIC)
    
    # 유튜브 업로드 모듈에서 사용할 메타데이터 저장
    with open(f"{WORK_DIR}/metadata.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    style_anchor = plan["style_anchor"]
    iconic_element = plan["iconic_element_en"]
    clip_paths = []

    for i, scene in enumerate(plan["scenes"]):
        idx = scene["scene_number"]
        print(f"--- 씬 {idx} 생성 시작 ---")

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

    captioned_path = f"{WORK_DIR}/captioned_video.mp4"
    stitch_clips_with_captions(clip_paths, plan, captioned_path)

    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    bgm_path = generate_bgm(plan["bgm_prompt_en"], total_duration)

    final_path = f"{WORK_DIR}/final_video.mp4"
    mux_audio(captioned_path, bgm_path, final_path)

    send_telegram_video(final_path, plan)
    print("텔레그램 전송 완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ 영상 제작 중 오류 발생: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
