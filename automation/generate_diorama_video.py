"""
미니어처/디오라마 시네마틱 영상 자동화 스크립트 (v4)
- 주제 입력 → Claude API로 씬 구성(JSON) 생성 (개성 요소 + 훅 문구 + 씬별 자막 + 배경음 프롬프트 포함)
- 1번 씬만 Flux-schnell로 이미지 생성, 2번 씬부터는 이전 씬 영상의 마지막 프레임을 이어서 사용
- 씬마다 Kling 2.5 Turbo Pro로 이미지->영상 변환
- ffmpeg로 씬 영상 이어붙이기 + 훅 문구 + 씬별 자막 삽입
- MusicGen으로 전체 길이에 맞는 배경음 생성 후 최종 믹싱
- 완성된 영상을 텔레그램으로 전송 (유튜브 메타데이터 캡션 포함)
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
FONT_PATH = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"  # fonts-nanum 패키지에 실제 존재하는 파일명
SCENE_DURATION = 5.0
client = Anthropic(api_key=ANTHROPIC_API_KEY)

REPLICATE_HEADERS = {
    "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
    "Content-Type": "application/json",
}


def generate_scene_plan(topic: str) -> dict:
    system_prompt = """당신은 AI 영상 제작 플랫폼(Higgsfield Seedance 2.0 / Runway / Kling 등)과
유튜브 쇼츠 최적화를 동시에 다루는 자동화 엔지니어입니다.
사용자가 주제를 입력하면, 연속성 있는 하나의 스토리로 이어지는 미니어처/디오라마
시네마틱 숏폼 영상을 설계합니다.

[가장 중요한 원칙 - 개성]
단순히 사실적인 미니어처를 재현하는 것으로는 부족합니다. 사람들이 저장하고 공유하고 싶어할
만큼 귀엽거나, 유머러스하거나, 독특한 "시그니처 요소"가 반드시 하나 있어야 합니다.
예: 표정이 있는 작은 피규어, 엉뚱한 소품, 과장된 색감의 마스코트 오브젝트 등.
이 시그니처 요소는 iconic_element_en 필드에 명확히 정의하고, 모든 씬에 계속 등장시킵니다.

[연속성 원칙 - 매우 중요]
이 영상은 하나의 연속된 롱테이크처럼 느껴져야 합니다. 각 씬은 별개의 장면이 아니라,
카메라가 계속 움직이거나 파고들면서 같은 공간/피사체를 탐험하는 하나의 흐름입니다.
- 1번 씬에서 설정한 공간과 시그니처 요소가 마지막 씬까지 시각적으로 계속 이어져야 합니다.
- 각 씬의 visual_prompt_en은 "완전히 새로운 장면"이 아니라 "직전 장면에서 카메라가
  이동/확대/회전한 결과"로 이어지는 자연스러운 다음 컷이어야 합니다.
- 스토리는 명확한 기승전결(호기심 유발 → 세부 탐험 → 반전/클라이맥스 → 마무리)을 가져야 합니다.

[온스크린 자막 원칙]
- hook_text_ko: 영상 시작 2.5초 동안 화면에 나올 짧고 강렬한 한국어 문구 (15자 이내)
- 각 씬의 caption_ko: 그 씬이 재생되는 5초 동안 화면 하단에 나올 짧은 한국어 자막 (12자 이내)

[배경음 원칙]
- bgm_prompt_en: 영상 전체에 깔릴 배경 음악/분위기를 설명하는 영문 프롬프트.
  장르, 악기, 템포, 무드를 구체적으로 명시 (예: "playful pizzicato strings, light percussion,
  whimsical and cinematic, mid-tempo, family-friendly adventure feel"). 스토리의 기승전결에
  어울리는 분위기로 만들되, 특정 저작권 있는 곡을 연상시키지 않는 오리지널한 설명으로 작성.

[씬 설계 원칙]
- 3~4개 씬으로 분할 (씬당 정확히 5초 - Kling 모델 제약)
- 각 씬마다 dynamic camera move 중 하나를 명시: dolly in / dolly out / orbit / whip pan / slow push
- 4K resolution, hyper-realistic 3D render 등 렌더 품질 키워드 포함
- 네거티브 프롬프트(blurry, low quality, watermark, text, extra limbs, realistic human face 등) 별도 명시

반드시 아래 JSON 구조로만 응답하세요 (다른 텍스트 없이 JSON만, 모든 문자열은 줄바꿈 없이 한 줄로):

{
  "project_title": "주제명",
  "style_anchor": "전체 영상 공통 스타일 문구 (영문, 렌더/조명/색보정/렌즈)",
  "iconic_element_en": "모든 씬에 반복 등장할 귀엽고 개성있는 시그니처 요소 묘사 (영문)",
  "hook_text_ko": "영상 시작 2.5초 자막용 짧은 한국어 훅 문구 (15자 이내)",
  "bgm_prompt_en": "영상 전체 배경음 설명 (영문)",
  "aspect_ratio": "9:16",
  "scenes": [
    {
      "scene_number": 1,
      "story_ko": "씬 스토리 설명 (한국어)",
      "caption_ko": "이 씬 재생 중 화면에 나올 짧은 자막 (12자 이내, 한국어)",
      "visual_prompt_en": "1번 씬은 전체 장면을 설정하는 와이드 샷. 시각 묘사 + 카메라 워크 + 조명 + iconic_element 포함 (영문)",
      "negative_prompt_en": "제외할 요소 (영문)"
    },
    {
      "scene_number": 2,
      "story_ko": "1번 씬에서 카메라가 이동한 결과 이어지는 다음 컷 설명 (한국어)",
      "caption_ko": "이 씬 재생 중 화면에 나올 짧은 자막 (12자 이내, 한국어)",
      "visual_prompt_en": "직전 프레임에서 카메라가 어떻게 움직여 무엇을 보여주는지 (영문, 카메라 워크 필수 포함)",
      "negative_prompt_en": "제외할 요소 (영문)"
    }
  ],
  "youtube_metadata": {
    "title": "후킹 제목 (60자 이내)",
    "description": "영상 요약 2~3줄 + 주요 타임라인",
    "tags": ["#태그1", "#태그2", "#쇼츠", "#AI영상"],
    "shorts_hook": "첫 3초 시청자를 사로잡을 나레이션 문구"
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
    data = poll_until_done(res.json(), max_wait_sec=240)

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
    """MusicGen으로 배경음 생성, mp3 로컬 경로 반환. 실패해도 예외를 위로 던지지 않고 None 반환."""
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
        print(f"배경음 생성 실패 (무시하고 무음으로 계속 진행): {e}")
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
    """씬 영상 이어붙이기 + 자막 삽입 (아직 무음 상태의 영상)"""
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
            f"fontcolor=white:fontsize=58:box=1:boxcolor=black@0.55:boxborderw=22:"
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
    """자막 입힌 무음 영상 + 배경음을 하나로 합치기"""
    if not bgm_path:
        # 배경음 생성 실패 시 무음 영상 그대로 사용
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
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
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
    send_telegram_message(f"🎬 '{TOPIC}' 영상 제작을 시작합니다. 자막+배경음까지 포함해서 3~5분 정도 걸려요...")

    plan = generate_scene_plan(TOPIC)
    print("씬 구성 완료:", json.dumps(plan, ensure_ascii=False, indent=2))

    aspect_ratio = plan.get("aspect_ratio", "9:16")
    style_anchor = plan["style_anchor"]
    iconic_element = plan["iconic_element_en"]
    clip_paths = []

    for i, scene in enumerate(plan["scenes"]):
        idx = scene["scene_number"]
        print(f"--- 씬 {idx} 처리 시작 ---")

        full_prompt = f"{style_anchor}, featuring {iconic_element}, {scene['visual_prompt_en']}"
        negative_prompt = scene.get("negative_prompt_en", "blurry, low quality, watermark, text")

        if i == 0:
            image_source = generate_image(full_prompt, negative_prompt, aspect_ratio)
            print(f"씬 {idx} 이미지 생성 완료 (Flux)")
        else:
            frame_path = extract_last_frame(clip_paths[-1], idx)
            image_source = image_to_data_uri(frame_path)
            print(f"씬 {idx} 시작 이미지 = 이전 씬 마지막 프레임")

        clip_path = generate_video_clip(
            image_source=image_source,
            motion_prompt=scene["visual_prompt_en"],
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            index=idx,
        )
        print(f"씬 {idx} 영상 생성 완료: {clip_path}")
        clip_paths.append(clip_path)

    captioned_path = f"{WORK_DIR}/captioned_video.mp4"
    stitch_clips_with_captions(clip_paths, plan, captioned_path)
    print("자막 삽입 완료")

    total_duration = int(len(plan["scenes"]) * SCENE_DURATION)
    bgm_path = generate_bgm(plan["bgm_prompt_en"], total_duration)

    final_path = f"{WORK_DIR}/final_video.mp4"
    mux_audio(captioned_path, bgm_path, final_path)
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
