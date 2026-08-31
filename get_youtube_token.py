import json
from google_auth_oauthlib.flow import InstalledAppFlow

print("=" * 60)
print("🔑 [YouTube OAuth Refresh Token 재발급]")
print("=" * 60)

client_id = input("1. Google Client ID를 입력하세요: ").strip()
client_secret = input("2. Google Client Secret을 입력하세요: ").strip()

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8080/"]
    }
}

scopes = ["https://www.googleapis.com/auth/youtube.upload"]
flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)

print("\n🌐 웹 브라우저가 열리면 유튜브 채널이 연결된 Google 계정으로 로그인하고 권한을 승인해 주세요...")
creds = flow.run_local_server(port=8080, prompt='consent', access_type='offline')

print("\n" + "=" * 60)
print("🎉 [새로 발급된 YOUTUBE_REFRESH_TOKEN]")
print(creds.refresh_token)
print("=" * 60)
