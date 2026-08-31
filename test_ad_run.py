import os
from automation.ad_creator_engine import (
    generate_ad_script,
    generate_ad_visual,
    generate_ad_motion,
    overlay_ad_typography,
    WORK_DIR
)

PRODUCT = {
    "name": "루미너스 글래스 스킨 세럼 (Luminous Glow Serum)",
    "usps": ["단 3일 만에 피부 톤업", "초미세 캡슐 히알루론산 10,000ppm", "런칭 기념 1+1 한정 특가"],
    "target": "칙칙한 피부 톤과 건조함이 고민인 2535 여성",
    "tone": "프리미엄 럭셔리 스튜디오, 시원하고 촉촉한 텍스처 강조",
    "format": "9:16"
}

print("🚀 AI 기업 광고 제작 파이프라인 가동...")
os.makedirs(WORK_DIR, exist_ok=True)

plan = generate_ad_script(
    PRODUCT["name"], PRODUCT["usps"], PRODUCT["target"], PRODUCT["tone"], PRODUCT["format"]
)
print("📋 기획된 씬 정보:")
for sc in plan["scenes"]:
    print(f"  [씬 {sc['scene_number']}] 훅: {sc['hook_text']} / 설명: {sc.get('sub_text', '')}")

s1 = plan["scenes"][0]
print("\n🎨 씬 1 비주얼 렌더링 중 (Flux Pro Ultra)...")
img_url = generate_ad_visual(s1["visual_prompt"], PRODUCT["format"])

print("🎬 씬 1 모션 비디오 생성 중 (Kling Turbo)...")
raw_clip = generate_ad_motion(img_url, s1["motion_prompt"], PRODUCT["format"], index=1)

print("✍️ 전환 최적화 훅 타이포그래피 자막 각인 중...")
final_scene1 = f"{WORK_DIR}/scene1_with_typography.mp4"
overlay_ad_typography(raw_clip, s1["hook_text"], s1.get("sub_text", ""), final_scene1, PRODUCT["format"])

print(f"\n🎉 [완성] 씬 1 광고 영상 생성 완료: {final_scene1}")
