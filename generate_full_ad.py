import os
import time
import subprocess
import requests
from automation.ad_creator_engine import (
    generate_ad_visual,
    generate_ad_motion,
    overlay_ad_typography,
    stitch_ad_clips,
    WORK_DIR
)

SCENES = [
    {
        "index": 1,
        "hook_text": "단 3일 만에 피부 톤업?",
        "sub_text": "거울 볼 때마다 놀라는 변화",
        "visual_prompt": "Extreme macro close-up of gorgeous glowing glass skin, natural golden sunlight caressing cheekbones, hydrated dewy texture, luxury beauty editorial",
        "motion_prompt": "Slow cinematic camera pan across radiant glowing dewy skin, gentle lighting shift"
    },
    {
        "index": 2,
        "hook_text": "푸석하고 칙칙한 피부 고민",
        "sub_text": "아침마다 화장이 뜬다면?",
        "visual_prompt": "Cinematic close-up of dry dull skin with subtle textured pores in soft dramatic studio lighting, emotional mood",
        "motion_prompt": "Slow subtle zoom in on skin texture with soft atmospheric lighting"
    },
    {
        "index": 3,
        "hook_text": "초미세 히알루론산 10,000ppm",
        "sub_text": "피부 속까지 촘촘한 수분 충전",
        "visual_prompt": "Macro slow motion of luminous crystal serum droplet splashing into glowing water surface, micro moisture capsules bursting with radiant light, 8k octane render",
        "motion_prompt": "Ultra slow-motion fluid splash of serum droplet bursting into micro moisture particles, glowing sparkles"
    },
    {
        "index": 4,
        "hook_text": "런칭 기념 1+1 한정 특가",
        "sub_text": "프로필 링크에서 지금 확인",
        "visual_prompt": "Luxury skincare serum glass bottle standing elegantly on wet reflective marble podium, soft golden studio rim lighting, dewy mist, floating water pearls, ultra sharp commercial photography",
        "motion_prompt": "360 degree slow cinematic orbit around the luxury serum bottle on reflective marble"
    }
]

os.makedirs(WORK_DIR, exist_ok=True)
processed_clips = []

print("🚀 [15초 풀 광고 제작 파이프라인 가동]")

for sc in SCENES:
    idx = sc["index"]
    raw_clip = f"{WORK_DIR}/raw_scene_{idx}.mp4"
    txt_clip = f"{WORK_DIR}/scene_{idx}_with_typo.mp4"
    
    # 이미 생성된 씬은 자동 재사용 (비용/시간 절약)
    if os.path.exists(raw_clip) and os.path.getsize(raw_clip) > 50000:
        print(f"\n⚡ [씬 {idx}/4] 기존 렌더링 영상 감지! 재사용합니다.")
    else:
        print(f"\n🎨 [씬 {idx}/4] 비주얼 이미지 생성 중 (Flux Pro Ultra)...")
        img_url = generate_ad_visual(sc["visual_prompt"], aspect_ratio="9:16")
        
        print(f"🎬 [씬 {idx}/4] 다이내믹 모션 렌더링 중 (Kling Turbo)...")
        generate_ad_motion(img_url, sc["motion_prompt"], aspect_ratio="9:16", index=idx)
    
    print(f"✍️ [씬 {idx}/4] 고전환 타이포그래피 자막 각인 중...")
    overlay_ad_typography(raw_clip, sc["hook_text"], sc["sub_text"], txt_clip, aspect_ratio="9:16")
    processed_clips.append(txt_clip)

stitched_path = f"{WORK_DIR}/stitched_ad.mp4"
print("\n🎞️ 4개 씬 15초 영상 병합 중...")
stitch_ad_clips(processed_clips, stitched_path)

final_ad_path = f"{WORK_DIR}/final_commercial_ad.mp4"
print("🎵 뷰티 커머스 사운드트랙 믹싱 중...")

bgm_filter = (
    "anoisesrc=c=pink:r=44100:a=0.015,atrim=0:20,asetpts=PTS-STARTPTS[pink];"
    "sine=f=440:r=44100,atrim=0:20,asetpts=PTS-STARTPTS,volume=0.01[s1];"
    "sine=f=880:r=44100,atrim=0:20,asetpts=PTS-STARTPTS,volume=0.008[s2];"
    "[pink][s1][s2]amix=inputs=3[bgm];"
    "[bgm]afade=t=in:st=0:d=1.0,afade=t=out:st=18.0:d=2.0[aout]"
)

subprocess.run(
    [
        "ffmpeg", "-y",
        "-i", stitched_path,
        "-filter_complex", bgm_filter,
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_ad_path
    ],
    check=True,
    capture_output=True
)

print(f"\n🎉 [완성] 15초 B2B 포트폴리오 광고 영상이 완성되었습니다!")
print(f"📁 저장 위치: {os.path.abspath(final_ad_path)}")
