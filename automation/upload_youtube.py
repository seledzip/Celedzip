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
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text})


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

    yt = plan["youtube_metadata"]
    title = yt.get("title", plan.get("project_title", "Miniature Shorts"))
    description = f"{yt.get('description', '')}\n\n#Shorts #Miniature #Diorama #ASMR"
    tags = yt.get("tags", ["shorts", "miniature", "asmr"])

    youtube = get_youtube_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(VIDEO_PATH, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"Upload success: {video_url}")
    
    send_telegram(f"🎉 *YouTube Shorts Uploaded Successfully!*\n\n🔗 [Watch Video]({video_url})")


if __name__ == "__main__":
    try:
        upload_to_youtube()
    except Exception as e:
        msg = f"❌ YouTube upload failed: {e}"
        print(msg)
        send_telegram(msg)
        raise
