"""
미니어처/디오라마 시네마틱 영상 자동화 스크립트
- 주제 입력 → Claude API로 씬 구성(JSON) 생성
- 씬마다 Flux-schnell로 이미지 생성
- 씬마다 Kling 2.5 Turbo Pro로 이미지->영상 변환
- ffmpeg로 씬 영상 이어붙이기
- 완성된 영상을 텔레그램으로 전송 (유튜브 메타데이터 캡션 포함)
"""

import os
import re
import json
import time
import subprocess
import requests
from anthropic import Anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"].strip()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"].strip()
TOPIC = os.environ["TOPIC"].strip()

WORK_DIR = "video_work"
client = Anthropic(api_key=ANTHROPIC_API_KEY)

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}


def generate_scene_plan(topic: str) -> dict:
    system_prompt = """당신은 AI 영상 제작 플랫폼(Higgsfield Seedance 2.0 / Runway / Kling 등)과
유튜브 쇼츠 최적화를 동시에 다루는 자동화 엔지니어입니다.
사용자가 주제를 입력하면, 멀티씬 영상 제작에 필요한 전체 프롬프트 세트와
유튜브 업로드 메타데이터를 하나의 JSON으로 생성합니다.

[일관성 원칙]
- 전체 영상에 걸쳐 통일할 스타일 앵커(렌더 스타일, 조명, 색보정, 카메라 렌즈감)를
  먼저 정의하고, 모든 씬의 visual_prompt에 동일하게 포함시킨다.
- 씬 간 연결은 카메라 워크나 피사체의 연속성으로 자연스럽게 이어지게 설계한다.

[씬 설계 원칙]
- 3~5개 씬으로 분할 (숏폼 15~25초 기준, 씬당 5초 또는 10초 - Kling 모델 제약)
- 각 씬마다 dynamic multi-shot 요소 중 하나를 명시: pan / dolly in / dolly out / orbit / static
- 미니어처·디오라마 스타일은 피사체 움직임을 1~2가지로 제한 (과한 동작은 정지감을 해침)
- 4K resolution, hyper-realistic 또는 3D animation style 등 렌더 품질 키워드 포함
- 네거티브 프롬프트(blurry, low quality, watermark, text, extra limbs, realistic human face 등) 별도 명시
- visual_prompt_en에는 카메라 워크 문구(예: slow dolly in, orbit, static push in)를 반드시 포함할 것
  (이 문구가 이미지 생성과 영상 모션 생성 양쪽에 다 쓰입니다)

반드시 아래 JSON 구조로만 응답하세요 (다른 텍스트 없이 JSON만, 모든 문자열은 줄바꿈 없이 한 줄로):

{
  "project_title": "주제명",
  "style_anchor": "전체 영상 공통 스타일 문구 (영문)",
  "aspect_ratio": "9:16",
  "total_duration_sec": 20,
  "scenes": [
    {
      "scene_number": 1,
      "story_ko": "씬 스토리 설명 (한국어)",
      "duration_sec": 5,
      "visual_prompt_en": "상세 시각 묘사 + 카메라 워크 + 조명 + 텍스처 (영문)",
      "negative_prompt_en": "제외할 요소 (영문)",
      "sound_vibe_en": "분위기 음악 및 SFX 키워드 (영문)",
      "transition_to_next": "다음 씬 전환 방식"
    }
  ],
  "youtube_metadata": {
    "title": "후킹 제목 (60자 이내)",
    "description": "영상 요약 2~3줄 + 주요 타임라인",
    "tags": ["#태그1", "#태그2", "#쇼츠", "#AI영상"],
    "shorts_hook": "첫 3초 시청자를 사로잡을 나레이션/자막 문구"
  }
}"""

    response = client.messages.create(
        model="claude-sonnet-5",
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


def poll_until_done(data: dict, max_wait_sec: int = 90) -> dict:
    """Replicate 예측(prediction) 완료까지 폴링"""
    get_url = data["urls"]["get"]
    waited = 0
    while data.get("status") not in ("succeeded", "failed", "canceled") and waited < max_wait_sec:
        time.sleep(3)
        waited += 3
        poll_res = requests.get(get_url, headers=REPLICATE_HEADERS, timeout=30)
        poll_res.raise_for_status()
        data = poll_res.json()

    if data.get("status") != "succeeded":
        raise RuntimeError(f"Replicate 작업 실패 (status={data.get('status')}): {data.get('error')}")
    return data


def generate_image(prompt: str, negative_prompt: str, aspect_ratio: str) -> str:
    """Flux-schnell로 이미지 생성, 완료까지 폴링 후 이미지 URL 반환"""
    res = requests.post(
        "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        headers=REPLICATE_HEADERS,
        json={
            "input": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "output_format": "jpg",
            }
        },
        timeout=30,
    )
    res.raise_for_status()
    data = poll_until_done(res.json(), max_wait_sec=90)
    output = data.get("output")
    image_url = output[0] if isinstance(output, list) else output
    if not image_url:
        raise RuntimeError(f"이미지 생성 실패: {data}")
    return image_url


def generate_video_clip(image_url: str, motion_prompt: str, negative_prompt: str,
                         duration: int, aspect_ratio: str, index: int) -> str:
    """Kling 2.5 Turbo Pro로 이미지->영상 변환, 완료까지 폴링 후 mp4 로컬 경로 반환"""
    duration = 5 if duration <= 5 else 10  # Kling은 5초 또는 10초만 지원

    res = requests.post(
        "https://api.replicate.com/v1/models/kwaivgi/kling-v2.5-turbo-pro/predictions",
        headers=REPLICATE_HEADERS,
        json={
            "input": {
                "prompt": motion_prompt,
                "negative_prompt": negative_prompt,
                "image": image_url,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }
        },
        timeout=30,
    )
    res.raise_for_status()
    data = poll_until_done(res.json(), max_wait_sec=240)  # 영상은 이미지보다 오래 걸림

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


def stitch_clips(clip_paths: list, output_path: str):
    """ffmpeg로 여러 영상 클립을 하나로 이어붙이기"""
    concat_list_path = f"{WORK_DIR}/concat_list.txt"
    with open(concat_list_path, "w") as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            output_path,
        ],
        check=True,
    )


def send_telegram_video(video_path: str, plan: dict):
    yt = plan["youtube_metadata"]
    tags = " ".join(yt.get("tags", []))
    caption = (
        f"🎬 *{plan['project_title']}*\n\n"
        f"*유튜브 제목*: {yt['title']}\n\n"
        f"*설명*:\n{yt['description']}\n\n"
        f"*훅 문구*: {yt['shorts_hook']}\n\n"
        f"*태그*: {tags}"
    )
    if len(caption) > 1000:
        caption = caption[:1000] + "..."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown",
            },
            files={"video": f},
            timeout=120,
        )
    resp.raise_for_status()
    result = resp.json()
    print("텔레그램 전송 결과:", result)
    if not result.get("ok"):
        raise RuntimeError(f"텔레그램 전송 실패: {result}")


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})


def main():
    print(f"주제: {TOPIC}")
    send_telegram_message(f"🎬 '{TOPIC}' 영상 제작을 시작합니다. 1~2분 정도 걸려요...")

    plan = generate_scene_plan(TOPIC)
    print("씬 구성 완료:", json.dumps(plan, ensure_ascii=False, indent=2))

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    clip_paths = []

    for scene in plan["scenes"]:
        idx = scene["scene_number"]
        print(f"--- 씬 {idx} 처리 시작 ---")

        full_visual_prompt = f"{plan['style_anchor']}, {scene['visual_prompt_en']}"
        negative_prompt = scene.get("negative_prompt_en", "blurry, low quality, watermark, text")

        image_url = generate_image(full_visual_prompt, negative_prompt, aspect_ratio)
        print(f"씬 {idx} 이미지 생성 완료: {image_url}")

        clip_path = generate_video_clip(
            image_url=image_url,
            motion_prompt=scene["visual_prompt_en"],
            negative_prompt=negative_prompt,
            duration=scene.get("duration_sec", 5),
            aspect_ratio=aspect_ratio,
            index=idx,
        )
        print(f"씬 {idx} 영상 생성 완료: {clip_path}")
        clip_paths.append(clip_path)

    final_path = f"{WORK_DIR}/final_video.mp4"
    stitch_clips(clip_paths, final_path)
    print(f"최종 영상 완성: {final_path}")

    send_telegram_video(final_path, plan)
    print("완료!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"⚠️ 영상 제작 중 오류 발생: {e}"
        print(error_msg)
        send_telegram_message(error_msg)
        raise
