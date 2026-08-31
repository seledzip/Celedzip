import os
import json
import base64
import time
import streamlit as st
from PIL import Image
from automation.ad_creator_engine import (
    generate_ad_script,
    generate_ad_visual,
    generate_ad_visual_with_product,
    generate_ad_motion,
    overlay_ad_typography,
    generate_voiceover,
    get_audio_duration,
    pick_scene_video_duration,
    stitch_ad_clips,
    mix_voiceover_and_bgm,
    WORK_DIR
)

st.set_page_config(page_title="AI 커머스 광고 제작 스튜디오", page_icon="🎬", layout="wide")

st.title("🎬 AI 20초 커머스 광고 원클릭 제작 스튜디오")
st.markdown("제품 사진 1장과 핵심 셀링포인트만 넣으면 **실제 제품 합성 + 전문 쇼호스트 더빙 + 20초 전환형 광고**를 자동 렌더링합니다.")

os.makedirs(WORK_DIR, exist_ok=True)

# Session State 기본값 초기화
default_values = {
    "h1": "단 3일 만에 피부 톤업?", "s1": "거울 볼 때마다 놀라는 변화", "n1": "단 3일 만에 피부 톤업, 거울 볼 때마다 놀라실 거예요",
    "vp1": "Extreme macro close-up of gorgeous glowing glass skin, golden sunlight caressing cheekbones", "mp1": "Slow cinematic camera pan across radiant glowing dewy skin",
    "h2": "푸석하고 칙칙한 피부 고민", "s2": "아침마다 화장이 뜬다면?", "n2": "푸석하고 칙칙한 피부, 아침마다 화장 뜨시나요?",
    "vp2": "Cinematic close-up of dry dull textured skin with visible imperfections under harsh light", "mp2": "Slow subtle zoom in on skin texture with emotional mood",
    "h3": "순수 글루타치온 500mg", "s3": "입안에 닿자마자 싹 흡수", "n3": "순수 글루타치온 필름으로 속부터 맑고 투명하게 채워보세요",
    "vp3": "Macro shot of a glowing translucent glutathione oral dissolving film melting with golden light particles", "mp3": "Ultra slow-motion fluid glow melting effect with radiant sparkle",
    "h4": "런칭 기념 1+1 한정 특가", "s4": "프로필 링크에서 지금 확인", "n4": "런칭 기념 1+1 특가, 지금 바로 프로필 링크를 확인하세요",
    "vp4": "Luxury product packaging on clean reflective marble podium, golden ambient light", "mp4": "360 degree slow cinematic orbit around the luxury product box"
}

for k, v in default_values.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 사이드바: 제품 정보 입력
with st.sidebar:
    st.header("📌 제품 정보 입력")
    product_name = st.text_input("제품명", value="글루타치온 필름")
    usps_input = st.text_area("핵심 셀링 포인트 (USP)", value="구강용해 필름, 직접 흡수, 순수 글루타치온 500mg, 칙칙한 안색 개선", height=80)
    target_audience = st.text_input("타깃 고객층", value="2030 직장인 여성")
    tone_mood = st.selectbox("광고 무드 & 톤", ["트렌디 & 에너제틱", "럭셔리 & 감성 뷰티", "신뢰감 있는 전문가 톤"])
    
    st.markdown("---")
    if st.button("🪄 AI 카피 & 프롬프트 자동 기획", type="primary"):
        with st.spinner("🤖 Llama-3 AI가 4단 전환형 스토리보드를 기획 중입니다..."):
            try:
                usps_list = [u.strip() for u in usps_input.split(",") if u.strip()]
                script_data = generate_ad_script(product_name, usps_list, target_audience, tone_mood)
                scenes = script_data.get("scenes", [])
                for sc in scenes:
                    num = sc["scene_number"]
                    st.session_state[f"h{num}"] = sc.get("hook_text", "")
                    st.session_state[f"s{num}"] = sc.get("sub_text", "")
                    st.session_state[f"n{num}"] = sc.get("narration", "")
                    st.session_state[f"vp{num}"] = sc.get("visual_prompt", "")
                    st.session_state[f"mp{num}"] = sc.get("motion_prompt", "")
                st.success("✅ 제품 맞춤 4단 카피 및 프롬프트 기획 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"기획 생성 실패: {e}")

    st.subheader("📷 실제 제품 사진 업로드")
    uploaded_file = st.file_uploader("제품 사진 (JPG/PNG)", type=["jpg", "jpeg", "png"])
    
    product_image_url = None
    if uploaded_file is not None:
        local_prod_path = os.path.join(WORK_DIR, "uploaded_product.png")
        image = Image.open(uploaded_file)
        image.save(local_prod_path)
        st.image(image, caption="업로드된 제품 사진")
        with open(local_prod_path, "rb") as f:
            b64_str = base64.b64encode(f.read()).decode("utf-8")
            product_image_url = f"data:image/png;base64,{b64_str}"

# 메인 화면: 4개 씬 구성
st.subheader("📝 4단 전환형 스토리보드 & 카피 세팅 (20초 완결)")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 씬 1: 후킹 (Hook / 0~5초)")
    h1 = st.text_input("씬 1 훅 자막", value=st.session_state["h1"], key="in_h1")
    s1 = st.text_input("씬 1 서브 자막", value=st.session_state["s1"], key="in_s1")
    n1 = st.text_area("씬 1 쇼호스트 내레이션", value=st.session_state["n1"], key="in_n1", height=70)
    vp1 = st.text_input("씬 1 비주얼 프롬프트 (영문)", value=st.session_state["vp1"], key="in_vp1")
    mp1 = st.text_input("씬 1 카메라 모션 (영문)", value=st.session_state["mp1"], key="in_mp1")

    st.markdown("### 씬 2: 결핍 자극 (Agitation / 5~10초)")
    h2 = st.text_input("씬 2 훅 자막", value=st.session_state["h2"], key="in_h2")
    s2 = st.text_input("씬 2 서브 자막", value=st.session_state["s2"], key="in_s2")
    n2 = st.text_area("씬 2 쇼호스트 내레이션", value=st.session_state["n2"], key="in_n2", height=70)
    vp2 = st.text_input("씬 2 비주얼 프롬프트 (영문)", value=st.session_state["vp2"], key="in_vp2")
    mp2 = st.text_input("씬 2 카메라 모션 (영문)", value=st.session_state["mp2"], key="in_mp2")

with col2:
    st.markdown("### 씬 3: 솔루션 (Solution / 10~15초)")
    h3 = st.text_input("씬 3 훅 자막", value=st.session_state["h3"], key="in_h3")
    s3 = st.text_input("씬 3 서브 자막", value=st.session_state["s3"], key="in_s3")
    n3 = st.text_area("씬 3 쇼호스트 내레이션", value=st.session_state["n3"], key="in_n3", height=70)
    vp3 = st.text_input("씬 3 비주얼 프롬프트 (영문)", value=st.session_state["vp3"], key="in_vp3")
    mp3 = st.text_input("씬 3 카메라 모션 (영문)", value=st.session_state["mp3"], key="in_mp3")

    st.markdown("### 씬 4: 행동 유도 (CTA / 15~20초)")
    h4 = st.text_input("씬 4 훅 자막", value=st.session_state["h4"], key="in_h4")
    s4 = st.text_input("씬 4 서브 자막", value=st.session_state["s4"], key="in_s4")
    n4 = st.text_area("씬 4 쇼호스트 내레이션", value=st.session_state["n4"], key="in_n4", height=70)
    vp4 = st.text_input("씬 4 비주얼 프롬프트 (영문)", value=st.session_state["vp4"], key="in_vp4")
    mp4 = st.text_input("씬 4 카메라 모션 (영문)", value=st.session_state["mp4"], key="in_mp4")

st.divider()

# 제작 버튼
if st.button("🚀 20초 AI 상업 광고 영상 원클릭 렌더링 시작", type="primary"):
    scenes_data = [
        {"idx": 1, "hook": h1, "sub": s1, "narr": n1, "vp": vp1, "mp": mp1},
        {"idx": 2, "hook": h2, "sub": s2, "narr": n2, "vp": vp2, "mp": mp2},
        {"idx": 3, "hook": h3, "sub": s3, "narr": n3, "vp": vp3, "mp": mp3},
        {"idx": 4, "hook": h4, "sub": s4, "narr": n4, "vp": vp4, "mp": mp4},
    ]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_clips = []
    voice_paths = []
    scene_durations = []
    start_time = time.time()
    
    try:
        for i, sc in enumerate(scenes_data):
            idx = sc["idx"]
            status_text.info(f"🎙️ **[씬 {idx}/4] 쇼호스트 보이스 생성 중...**")
            v_path = os.path.join(WORK_DIR, f"ui_voice_scene_{idx}.mp3")
            generate_voiceover(sc["narr"], v_path)
            voice_paths.append(v_path)
            
            v_sec = get_audio_duration(v_path)
            chosen_dur = pick_scene_video_duration(v_sec)
            scene_durations.append(chosen_dur)
            
            is_product_scene = (product_image_url and idx in (3, 4))
            status_text.info(f"🎨 **[씬 {idx}/4] 4K 비주얼 생성 중...** (제품 합성: {'적용' if is_product_scene else '일반'})")
            if is_product_scene:
                img_url = generate_ad_visual_with_product(product_image_url, sc["vp"], idx, "9:16")
            else:
                img_url = generate_ad_visual(sc["vp"], idx, "9:16")
                
            status_text.info(f"🎬 **[씬 {idx}/4] Kling 모션 비디오 렌더링 중 ({chosen_dur}초 분량)... 약 1분 소요**")
            raw_clip = generate_ad_motion(img_url, sc["mp"], "9:16", idx, duration=chosen_dur)
            
            status_text.info(f"✍️ **[씬 {idx}/4] 하이라이트 박스 자막 오버레이 중...**")
            txt_clip = os.path.join(WORK_DIR, f"ui_typed_scene_{idx}.mp4")
            overlay_ad_typography(raw_clip, sc["hook"], sc["sub"], txt_clip, "9:16")
            processed_clips.append(txt_clip)
            
            progress_bar.progress(int((i + 1) * 20))
            
        status_text.info("🎞️ **비디오 4개 씬 20초 병합 중...**")
        stitched_video = os.path.join(WORK_DIR, "ui_stitched_clean.mp4")
        stitch_ad_clips(processed_clips, stitched_video)
        progress_bar.progress(90)
        
        status_text.info("🎵 **쇼호스트 음성 & BGM 사운드 최종 믹싱 중...**")
        final_output = os.path.join(WORK_DIR, "ui_final_commercial_ad.mp4")
        mix_voiceover_and_bgm(stitched_video, voice_paths, scene_durations, final_output)
        progress_bar.progress(100)
        
        elapsed = int(time.time() - start_time)
        status_text.success(f"🎉 20초 커머스 광고 영상 제작 완료! (총 소요 시간: {elapsed}초)")
        
        st.video(final_output)
        with open(final_output, "rb") as f:
            st.download_button(
                label="📥 완성본 MP4 비디오 다운로드",
                data=f,
                file_name=f"{product_name}_20s_Ad.mp4",
                mime="video/mp4"
            )
    except Exception as e:
        status_text.error(f"❌ 렌더링 중 오류 발생: {e}")
        st.exception(e)
