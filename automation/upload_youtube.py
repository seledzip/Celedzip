"""
유튜브 쇼츠 안전 자동 업로드 모듈 (v2 - Policy Safe & Direct Link)
"""

import os
import json
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

WORK_DIR = "video_work"
VIDEO_PATH = f"{WORK_DIR}/final_video.mp4"
METADATA_PATH = f"{WORK_DIR}/metadata.json"

YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def send_telegram(text: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})


def get_youtube_service():
    credentials = Credentials(
        None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=credentials)


def upload_to_youtube():
    if not os.path.exists(VIDEO_PATH) or not os.path.exists(METADATA_PATH):
        raise FileNotFoundError("업로드할 영상 또는 메타데이터 파일이 없습니다.")

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        plan = json.load(f)

    yt = plan.get("youtube_metadata", {})
    title = yt.get("title", plan.get("project_title", "Miniature Shorts"))
    raw_desc = yt.get("description", "")
    
    description = (
        f"{raw_desc}\n\n"
        f"✨ Altered/Synthetic Content: This video contains AI-generated visuals and sound design.\n\n"
        f"#Shorts #Miniature #Diorama #ASMR #Satisfying"
    )
    tags = yt.get("tags", ["shorts", "miniature", "asmr", "diorama"])

    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "24",  # Entertainment
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "unlisted",  # 안전 가이드 준수: 일부공개
            "selfDeclaredMadeForKids": False,
            "embeddable": True,
        },
    }

    media = MediaFileUpload(VIDEO_PATH, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("유튜브 업로드 시작...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"업로드 진행률: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    video_url = f"https://youtube.com/shorts/{video_id}"
    studio_edit_url = f"https://studio.youtube.com/video/{video_id}/edit"
    
    print(f"업로드 완료: {video_url}")
    
    success_msg = (
        f"🎉 *유튜브 자동 업로드 완료 (일부공개 상태)*\n\n"
        f"📌 *제목*: {title}\n"
        f"🔗 *미리보기 링크*: [YouTube Shorts 바로가기]({video_url})\n\n"
        f"⚙️ 영상을 확인하시고 마음에 드시면 스튜디오에서 **'공개(Public)'**로 전환해 주세요!\n"
        f"👉 [유튜브 스튜디오에서 공개로 변경하기]({studio_edit_url})"
    )
    send_telegram(success_msg)


if __name__ == "__main__":
    try:
        upload_to_youtube()
    except Exception as e:
        msg = f"❌ 유튜브 자동 업로드 중 오류 발생: {e}"
        print(msg)
        send_telegram(msg)
        raise
