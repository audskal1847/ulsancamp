import streamlit as st
import json
import os
import base64
import pandas as pd
import datetime

# --- [1] 파일 경로 설정 및 상수 정의 ---
USERS_FILE = "users.json"
DATA_FILE = "learning_data.json"
CONFIG_FILE = "config.json"
UPLOAD_DIR = "uploads" 

os.makedirs(UPLOAD_DIR, exist_ok=True)

CLASS_GROUPS = ["1반", "2반", "3반", "4반"]

ADMIN_ACCOUNTS = {
    "admin1": "admin11",
    "admin2": "admin22",
    "admin3": "admin33",
    "admin4": "admin44"
}

ACTIVITIES = [
    "[활동지1] 진학 희망 학과 조사하기",
    "[활동지2] 나만의 탐구 설계하기",
    "[활동지2 예시] 모둠별 예시 8개",
    "[활동지3] 참고 자료 조사",
    "[활동지4] 주제 탐구 보고서 설계도 (생략 가능 - 보고서 양식으로 대체)",
    "[활동지5] 주제 탐구 보고서 양식",
    "[활동지6] 발표 피드백에 따른 보완",
    "[활동지7] 자기평가서 (수정본)",
    "[활동지8] 심화탐구 후속 활동 계획: 독서 연계 & 대입 로드맵"
]

# --- [2] 데이터 입출력 및 초기화 함수 ---
def load_json(file_path, default_value):
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_value, f, ensure_ascii=False, indent=4)
        return default_value
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default_value

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_system():
    users = load_json(USERS_FILE, {})
    load_json(DATA_FILE, {})
    
    default_config = {
        "tabs": ["1일차_1차시", "2일차_1차시"],
        "pdfs": {"1일차_1차시": "session1_1.pdf", "2일차_1차시": "session2_1.pdf"},
        "questions": {
            "1일차_1차시": [{"id": "q1", "label": "탐구 주제 및 목차 설계 (텍스트, 파일, 링크 중 자유 제출)"}],
            "2일차_1차시": [{"id": "q1", "label": "보고서 초안 제출"}]
        },
        "materials": [] 
    }
    current_config = load_json(CONFIG_FILE, default_config)
    if "materials" not in current_config:
        current_config["materials"] = []
        save_json(CONFIG_FILE, current_config)

def display_pdf(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="450" type="application/pdf"></iframe>', unsafe_allow_html=True)
    else:
        st.info(f"💡 교재 파일('{file_path}')이 폴더에 없습니다. 파일을 업로드하면 이곳에 표시됩니다.")

# --- [3-A] 일반 제출 폼 ---
def render_submission_form(user_key, category, q_id, q_label):
    data = load_json(DATA_FILE, {})
    ans = data.get(user_key, {}).get(category, {}).get(q_id, {})
    if isinstance(ans, str): ans = {"text": ans, "link": "", "file_name": "", "file_path": ""}
        
    with st.form(key=f"form_{user_key}_{category}_{q_id}"):
        st.markdown(f"**{q_label}**")
        st.caption("텍스트 입력, 외부 링크 주소, 파일 첨부 중 원하는 방식을 하나 이상 선택하여 제출하세요.")
        text_val = st.text_area("📝 텍스트 내용 작성", value=ans.get("text", ""), height=150)
        link_val = st.text_input("🔗 관련 링크(URL) 제출", value=ans.get("link", ""), placeholder="https://...")
        if ans.get("file_name"): st.info(f"📁 현재 등록된 파일: {ans.get('file_name')}")
        file_val = st.file_uploader("📂 첨부 파일 업로드 (새 파일을 올리면 기존 파일이 대체됩니다)")
        
        if st.form_submit_button("제출 및 저장하기"):
            if user_key not in data: data[user_key] = {}
            if category not in data[user_key]: data[user_key][category] = {}
            new_data = {"text": text_val, "link": link_val, "file_path": ans.get("file_path", ""), "file_name": ans.get("file_name", "")}
            if file_val is not None:
                safe_filename = f"{user_key}_{category}_{q_id}_{file_val.name}".replace("/", "_").replace("\\", "_")
                file_path = os.path.join(UPLOAD_DIR, safe_filename)
                with open(file_path, "wb") as f: f.write(file_val.getvalue())
                new_data["file_path"] = file_path; new_data["file_name"] = file_val.name
            data[user_key][category][q_id] = new_data
            save_json(DATA_FILE, data)
            st.toast("💾 제출 자료가 성공적으로 저장되었습니다!")

# --- [3-B] 활동지1 전용 맞춤형 폼 ---
def render_activity1_form(user_key):
    category = "[활동지1] 진학 희망 학과 조사하기"
    data = load_json(DATA_FILE, {})
    ans = data.get(user_key, {}).get(category, {})
    
    st.markdown("<div style='background-color: #fff9e6; padding: 15px; border-radius: 5px; font-weight: bold;'>전공 가이드북을 활용하여 진학을 희망하는 학과의 핵심 내용 요소를 추출하고 이를 바탕으로 자신의 학교생활기록부의 탐구 활동을 분석/분류한다.</div><br>", unsafe_allow_html=True)
    with st.form(key=f"form_act1_{user_key}"):
        st.markdown("#### [1단계] 학과/전공 가이드북 읽고 핵심 내용 요소 추출하기")
        default_df1 = pd.DataFrame([{"학과/전공명": "", "핵심 내용 요소": ""} for _ in range(4)])
        df1 = pd.DataFrame(ans.get("df1", default_df1.to_dict('records')))
        edited_df1 = st.data_editor(df1, num_rows="dynamic", use_container_width=True, key="act1_df1")
        st.markdown("---")
        
        st.markdown("#### [2단계] 내용 요소 중심 학교생활기록부 탐구 내용 분석하기")
        st.info("💡 표의 가장 윗줄인 **'✏️ 나의 탐구 키워드'** 행의 빈칸을 더블클릭하여 본인의 키워드를 직접 입력하세요!")
        default_df2 = pd.DataFrame({
            "구분": ["✏️ 나의 탐구 키워드", "창체활동", "교과세특"],
            "키워드1": ["", "", ""], "키워드2": ["", "", ""], "키워드3": ["", "", ""], "키워드4": ["", "", ""], "키워드5": ["", "", ""]
        })
        df2 = pd.DataFrame(ans.get("df2", default_df2.to_dict('records')))
        edited_df2 = st.data_editor(df2, use_container_width=True, key="act1_df2")
        
        st.markdown("<br>#### [2단계-예시]", unsafe_allow_html=True)
        example_image = os.path.join(os.path.dirname(__file__), "example.png")
        if os.path.exists(example_image): st.image(example_image, caption="희망 전공 분야 카운팅 표 사례", use_container_width=True)
        else: st.info("💡 [2단계-예시] 희망 전공 분야 카운팅 표 사례 (고려대 전기전자공학부 등)를 참고하여 위 표의 칸을 채워보세요.")
        st.markdown("---")
        
        st.markdown("#### [3단계] 이번 특강을 통해 탐구하고 싶은 내용 영역 또는 문제 인식(주제 찾기)")
        st.markdown("<div style='background-color: #fff9e6; padding: 10px; border-radius: 5px;'>내가 지금까지 다루지 못했던 내용 요소는 무엇이고 그것과 관련된 탐구 주제는 무엇이 있을까?</div>", unsafe_allow_html=True)
        step3_val = st.text_area("내용을 입력하세요", value=ans.get("step3", ""), height=150)

        if st.form_submit_button("활동지 최종 제출 및 저장", type="primary"):
            if user_key not in data: data[user_key] = {}
            data[user_key][category] = {"is_custom": True, "df1": edited_df1.to_dict('records'), "df2": edited_df2.to_dict('records'), "step3": step3_val}
            save_json(DATA_FILE, data); st.toast("🎉 활동지1이 성공적으로 저장되었습니다!")

# --- [3-C] 💡 새로운 활동지2 전용 맞춤형 폼 (나만의 탐구 설계하기) ---
def render_activity2_form(user_key):
    category = "[활동지2] 나만의 탐구 설계하기"
    data = load_json(DATA_FILE, {})
    ans = data.get(user_key, {}).get(category, {})
    
    st.markdown("### 교과서 속 지식을 세상의 해답으로 바꾸는 나만의 탐구 여정")
    st.markdown("<div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px;'><i>이 활동지는 여러 주제를 나열하는 것이 아니라, <b>하나의 탐구 주제를 스스로 만들어 완성</b>하기 위한 것입니다. 1단계부터 순서대로 채워 나가면 마지막에 나만의 탐구 계획서가 완성됩니다. 각 단계는 앞 단계의 답을 이어받아 점점 구체화되도록 설계되어 있으니, 건너뛰지 말고 차례대로 작성해 보세요.</i></div><br>", unsafe_allow_html=True)
    
    with st.form(key=f"form_act2_{user_key}"):
        
        st.markdown("#### [1단계] 관심에서 출발하기")
        st.markdown("<i>최근 궁금했던 것, 불편함을 느꼈던 것, 또는 수업이나 독서 중 더 알고 싶었던 것을 자유롭게 적어 봅니다.</i>", unsafe_allow_html=True)
        step1_1 = st.text_input("(1) 내가 관심 있는 것 / 궁금했던 현상:", value=ans.get("step1_1", ""))
        
        opts1_2 = [
            "수업이나 책을 보다가 생긴 의문을 파고들고 싶어서 (지적호기심)", 
            "배운 원리를 실생활 문제(사회 문제) 해결에 직접 적용해 보고 싶어서 (문제해결)", 
            "이전에 했던 탐구에서 남은 궁금증이나 한계를 더 발전시키고 싶어서 (연계 및 심화)"
        ]
        step1_2 = st.radio("(2) 이 관심이 생긴 계기 (하나만 선택)", opts1_2, index=opts1_2.index(ans.get("step1_2", opts1_2[0])))
        
        st.markdown("**이전에 했던 탐구의 확장을 선택했다면 아래도 함께 채우세요.**")
        default_df1 = pd.DataFrame([
            {"구분": "이전에 했던 탐구 주제", "내용": ""},
            {"구분": "그때 알아낸 것 (결론)", "내용": ""},
            {"구분": "풀지 못했거나 아쉬웠던 점", "내용": ""},
            {"구분": "이번에 발전시키고 싶은 방향", "내용": "(예: 대상 확대, 조건 변경, 다른 관점 적용, 해결책 제시 등)"}
        ])
        df1 = pd.DataFrame(ans.get("df1", default_df1.to_dict('records')))
        edited_df1 = st.data_editor(df1, hide_index=True, use_container_width=True, disabled=["구분"], key="act2_df1")
        st.markdown("---")
        
        st.markdown("#### [2단계] 교과 개념에 닻 내리기: 내 관심사를 수업에서 배운 원리와 연결하기")
        st.markdown("<div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px;'><i>좋은 탐구는 단순한 검색이 아니라 배운 개념 위에서 출발합니다. 과목 이름만 적지 말고, 배운 핵심 개념 하나를 구체적으로 적는 것이 중요합니다.</i></div>", unsafe_allow_html=True)
        default_df2 = pd.DataFrame([
            {"구분": "관련 교과목, 단원", "내용": "(예: 확률과 통계 - 통계적 추정)"},
            {"구분": "수업에서 배운 핵심 개념", "내용": "(예: 표본 조사에서의 신뢰구간과 오차)"},
            {"구분": "이 개념이 내 관심사와 연결되는 지점", "내용": ""}
        ])
        df2 = pd.DataFrame(ans.get("df2", default_df2.to_dict('records')))
        edited_df2 = st.data_editor(df2, hide_index=True, use_container_width=True, disabled=["구분"], key="act2_df2")
        step2_dir = st.text_input("**이 시점의 잠정적인 탐구 방향 (한 문장으로):**", value=ans.get("step2_dir", ""))
        st.markdown("---")
        
        st.markdown("#### [3단계] 주제 적절성 자가 진단: 주제가 고등학생 수준에 맞는지 점검")
        default_df3 = pd.DataFrame([
            {"점검 항목": "1. 교과 개념 연계", "점검 질문": "교과서의 원리 없이 인터넷 검색만으로 알 수 있는 상식적인 내용인가?", "좋은 예": "(나쁜 예) 비타민을 많이 먹으면 좋은지 조사 → (좋은 예) 생명과학 I '방어 작용'을 바탕으로 면역 결핍과 자가면역이 일어나는 기작의 차이 비교", "판단 (O/X)": ""},
            {"점검 항목": "2. 시의성 (트렌드)", "점검 질문": "너무 유행을 타거나(정치적 이슈 등), 이미 결론이 난 철 지난 주제는 아닌가?", "좋은 예": "(나쁜 예) 특정 정치인을 화자로 시 쓰기 → (좋은 예) 현대 시 한 편을 문학 사조별 대표 시인의 화법으로 다시 쓰기...", "판단 (O/X)": ""},
            {"점검 항목": "3. 수행 가능성", "점검 질문": "고등학생의 시간·장비·비용으로 실제 조사나 실험이 가능한가?", "좋은 예": "(나쁜 예) 층간소음을 완벽히 없애는 신소재 발명 → (좋은 예) 물-시멘트 배합 비율 및 첨가제 유무에 따른 콘크리트 압축 강도 변화 측정", "판단 (O/X)": ""},
            {"점검 항목": "4. 동기의 진정성", "점검 질문": "억지로 끼워 맞춘 것이 아니라 1단계의 계기에서 자연스럽게 이어지는가?", "좋은 예": "1단계에 적은 관심·계기와 흐름이 연결되는지 확인", "판단 (O/X)": ""}
        ])
        df3 = pd.DataFrame(ans.get("df3", default_df3.to_dict('records')))
        edited_df3 = st.data_editor(df3, hide_index=True, use_container_width=True, disabled=["점검 항목", "점검 질문", "좋은 예"], key="act2_df3")
        st.info("자가 진단 결과: 모든 항목이 O라면 다음 단계로 넘어가세요. 하나라도 X라면 주제를 수정해야 합니다.")
        st.markdown("---")
        
        st.markdown("#### [4단계] 막연한 주제를 학술적 질문으로 바꾸기")
        st.markdown("<div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px;'><i>좋은 탐구는 좋은 질문에서 시작합니다. 아래 여섯 개의 질문 렌즈 중 딱 하나를 골라, 내 주제를 탐구 가능한 질문으로 바꿔 봅니다.</i></div>", unsafe_allow_html=True)
        ref_df4 = pd.DataFrame([
            {"질문 렌즈": "1. 원인과 결과", "질문 형태 예시": "~은 ~에 어떤 메커니즘으로 영향을 미치는가?"},
            {"질문 렌즈": "2. 비교와 대조", "질문 형태 예시": "A와 B는 어떻게 다르며, 그 차이는 왜 생기는가?"},
            {"질문 렌즈": "3. 평가와 가치", "질문 형태 예시": "~은 지금 시점에서 어떤 사회적 의미를 갖는가?"},
            {"질문 렌즈": "4. 분류와 특징", "질문 형태 예시": "~에는 어떤 유형이 있고, 각각 어떤 구조적 특징이 있는가?"},
            {"질문 렌즈": "5. 변화 과정", "질문 형태 예시": "~은 시대나 기술의 흐름에 따라 어떻게 변해 왔는가?"},
            {"질문 렌즈": "6. 기타", "질문 형태 예시": "위에 없는 나만의 형태"}
        ])
        st.dataframe(ref_df4, hide_index=True, use_container_width=True)
        opts4_1 = ["1. 원인과 결과", "2. 비교와 대조", "3. 평가와 가치", "4. 분류와 특징", "5. 변화 과정", "6. 기타"]
        step4_1 = st.selectbox("1) 선택한 렌즈:", opts4_1, index=opts4_1.index(ans.get("step4_1", opts4_1[0])))
        step4_2 = st.text_input("2) 완성한 나의 핵심 탐구 질문:", value=ans.get("step4_2", ""))
        st.markdown("---")
        
        st.markdown("#### [5단계] 탐구 전략 하나 정하기")
        st.markdown("<i>질문에 답하기에 가장 알맞은 접근법을 고르세요.</i>", unsafe_allow_html=True)
        st.markdown("- **현미경 (원리 분석)** — 결과 이면에 숨은 원리와 메커니즘을 파고든다.\n- **벤치마킹 (비교 탐구)** — 다른 사례·국가·조건과 비교해 시사점을 끌어낸다.\n- **색안경 (관점 적용)** — 특정 이론이나 학문의 관점으로 현상을 해석·비평한다.\n- **의사 (문제 해결)** — 분석을 바탕으로 실질적 대안이나 처방을 제시한다.")
        opts5_1 = ["현미경 (원리 분석)", "벤치마킹 (비교 탐구)", "색안경 (관점 적용)", "의사 (문제 해결)"]
        step5_1 = st.selectbox("2) 내가 선택한 전략은?", opts5_1, index=opts5_1.index(ans.get("step5_1", opts5_1[0])))
        step5_2 = st.text_area("3) 이 전략으로 질문에 접근하는 구체적인 방법 (2~3문장)", value=ans.get("step5_2", ""))
        st.markdown("---")
        
        st.markdown("#### [6단계] AI 멘토에게 점검받기")
        st.markdown("<div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px;'><i>내가 세운 전략이 논리적이고 고등학생 수준에서 수행 가능한지 AI에게 물어보고 부족한 점을 보완하세요.</i></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background-color: #f4f4f4; padding: 15px; border-radius: 5px; color: #555;'>
        나는 <b>[관련 교과목]</b>의 <b>[핵심 개념]</b>을 바탕으로 <b>[나의 탐구 질문]</b>을 탐구하려고 해. 접근 전략은 <b>[탐구 전략]</b>이야.<br><br>
        이 질문이 명확하고 탐구할 가치가 있는지 평가해 줘.<br>
        고등학생이 실제로 조사·실험할 수 있는 범위인지, 줄이거나 보완할 점이 있으면 알려 줘.<br>
        참고할 만한 개념이나 자료의 방향을 추천해 줘.
        </div>
        """, unsafe_allow_html=True)
        step6 = st.text_area("2) AI의 조언 중 내가 반영할 점:", value=ans.get("step6", ""))
        st.markdown("---")
        
        st.markdown("#### [7단계] 나의 탐구 계획 완성하기")
        st.markdown("<i>지금까지의 답을 모아 하나의 계획서로 정리한다.</i>", unsafe_allow_html=True)
        default_df7 = pd.DataFrame([
            {"항목": "탐구 주제 (제목)", "내용": ""},
            {"항목": "핵심 탐구 질문", "내용": ""},
            {"항목": "연계 교과 개념", "내용": ""},
            {"항목": "탐구 전략", "내용": ""},
            {"항목": "탐구 방법 (자료, 조사, 실험 등)", "내용": ""},
            {"항목": "기대하는 결론, 알아낼 점", "내용": ""}
        ])
        df7 = pd.DataFrame(ans.get("df7", default_df7.to_dict('records')))
        edited_df7 = st.data_editor(df7, hide_index=True, use_container_width=True, disabled=["항목"], key="act2_df7")
        
        st.markdown("<br>**한 문장으로 요약한 나의 탐구**", unsafe_allow_html=True)
        col1, col2, col3, col4, col5, col6, col7 = st.columns([0.5, 2, 1.2, 2, 0.8, 2, 1.5])
        with col1: st.write("나는 (")
        with col2: step7_s1 = st.text_input("개념", value=ans.get("step7_s1", ""), label_visibility="collapsed")
        with col3: st.write(") 개념을 활용해, (")
        with col4: step7_s2 = st.text_input("전략", value=ans.get("step7_s2", ""), label_visibility="collapsed")
        with col5: st.write(") 전략으로 (")
        with col6: step7_s3 = st.text_input("밝힐점", value=ans.get("step7_s3", ""), label_visibility="collapsed")
        with col7: st.write(")을(를) 밝히려 한다.")

        if st.form_submit_button("활동지 최종 제출 및 저장", type="primary"):
            if user_key not in data: data[user_key] = {}
            data[user_key][category] = {
                "is_custom_act2": True, "step1_1": step1_1, "step1_2": step1_2,
                "df1": edited_df1.to_dict('records'), "df2": edited_df2.to_dict('records'),
                "step2_dir": step2_dir, "df3": edited_df3.to_dict('records'),
                "step4_1": step4_1, "step4_2": step4_2, "step5_1": step5_1, "step5_2": step5_2,
                "step6": step6, "df7": edited_df7.to_dict('records'),
                "step7_s1": step7_s1, "step7_s2": step7_s2, "step7_s3": step7_s3
            }
            save_json(DATA_FILE, data)
            st.toast("🎉 활동지2가 성공적으로 저장되었습니다!")

# --- 캠프 종합 공지 렌더링 ---
def render_camp_overview(current_role):
    st.header("🎯 [학생-호계고-거점학교] 주제 탐구 캠프 (26-하계방학)")
    st.markdown("---")
    
    st.subheader("🗓️ 7/23(목) ~ 7/24(금) 일정")
    schedule_data = [
        ["1일차", "1 (09:00~10:40)", "학생부 종합 전형과 탐구 역량의 이해", "우수 기록 사례 분석 및 인공지능 탐색 툴 활용법 익히기"],
        ["1일차", "2 (11:00~12:40)", "학과 안내서(가이드북)를 활용한 나의 학생부 분석", "학과별 요구 역량 파악 및 개인별 학생부 강점·보완점 분석 활동"],
        ["1일차", "점심 (12:40~13:30)", "점심식사", "점심식사"],
        ["1일차", "3 (13:30~15:10)", "탐구 주제 선정 및 보고서 개요(목차) 작성법", "인공지능을 활용한 개인별 맞춤형 탐구 주제 및 목차 설계"],
        ["1일차", "4 (15:30~17:10)", "탐구 보고서 설계도 작성 및 자료 수집", "논문, 해외 원문, 도서, 기사 등 다각적 자료 수집 및 개요 구체화"],
        ["2일차", "1 (09:00~10:40)", "탐구 보고서 본문 작성 및 내용 보완", "수집한 자료를 바탕으로 보고서 초안 작성 및 자체 점검"],
        ["2일차", "2 (11:00~12:40)", "탐구 결과 요약 및 시각화 자료 구성", "보고서 핵심 내용 요약 및 인포그래픽, 시각 자료 제작 활동"],
        ["2일차", "점심 (12:40~13:30)", "점심식사", "점심식사"],
        ["2일차", "3 (13:30~15:10)", "탐구 보고서 최종 수정 및 고도화", "작성된 보고서의 논리 구조 점검 및 문장 다듬기 완성 활동"],
        ["2일차", "4 (15:30~17:10)", "후속 탐구 활동 계획 및 학년별 실천 로드맵 수립", "연계 독서 활동 계획 수립 및 교과 학습 실천 로드맵 정리"]
    ]
    st.dataframe(pd.DataFrame(schedule_data, columns=["일자", "차시(시간)", "수업내용", "활동내용"]), use_container_width=True, hide_index=True)
    st.markdown("---")
    
    app_config = load_json(CONFIG_FILE, {})
    materials = app_config.get("materials", [])
    if materials:
        st.subheader("👨‍🏫 캠프 특강 및 강의 자료실")
        for mat in materials:
            if mat["type"] == "link":
                st.markdown(f"🔗 **[{mat['title']}]({mat['content']})**")
            elif mat["type"] == "file":
                if os.path.exists(mat["content"]):
                    if current_role in ["관리자", "교사"]:
                        with open(mat["content"], "rb") as f:
                            st.download_button(f"📥 {mat['title']} ({mat['filename']}) 다운로드", f, file_name=mat['filename'], key=f"mat_dl_{mat['id']}")
                    else:
                        st.markdown(f"🔒 **{mat['title']}** (학생 다운로드 제한 자료)")
        st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("👥 모둠 구성 및 사전 안내", expanded=True):
            st.markdown("- [🔗 모둠 구성 확인하기 (구글 문서)](#)")
            st.markdown("- [🔗 캠프 사전 안내 노션 사이트](https://app.notion.com/p/26-3a1b5d2009278095b09cd44692be6056?pvs=11)")
            st.markdown("- [🔗 사전 설문조사 [구글 폼]](https://forms.gle/4Co5GLdD3M6KEVcs8)")

        with st.expander("📝 활동지 링크 (클릭 시 이동 및 작성)", expanded=True):
            st.caption("아래 버튼을 누르면 프로그램 내 제출 화면으로 전환됩니다.")
            for act in ACTIVITIES:
                if st.button(f"📄 {act}", use_container_width=True):
                    st.session_state.current_page = act
                    st.rerun()
            
    with col2:
        with st.expander("📚 대학 전공 가이드북 링크", expanded=True):
            st.markdown("[📁 대학 전공 가이드북 구글 드라이브 폴더 열기](https://drive.google.com/drive/folders/18TOhHc0kVvQBa5UcbwlvkQkglOYax8xZ?usp=sharing)")

        with st.expander("📊 만족도 조사 설문 링크 (QR 포함)", expanded=True):
            st.markdown("[🔗 캠프 만족도 조사 참여하기 (Google Forms)](https://forms.gle/kqjWnsTE65Jf8QCS6)")
            qr_image = os.path.join(os.path.dirname(__file__), "image (11).png")
            if os.path.exists(qr_image):
                st.image(qr_image, caption="스마트폰 카메라로 스캔하여 만족도 조사에 참여해주세요.", width=300)

# --- [4] 메인 프로그램 세팅 및 사이드바 ---
st.set_page_config(page_title="주제 탐구 캠프 시스템", layout="wide")
init_system()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "main"

if st.session_state.current_page == "메인": st.session_state.current_page = "main"

st.sidebar.title("🔒 인증 센터")
if st.session_state.logged_in:
    u_info = st.session_state.user_info
    st.sidebar.success(f"🟢 {u_info['name']} 님 로그인 중")
    display_class = u_info.get('class_group', '')
    if display_class and display_class != "관리자": st.sidebar.write(f"🏫 소속: {u_info.get('school', '소속없음')} ({display_class})")
    else: st.sidebar.write(f"🏫 소속: {u_info.get('school', '소속없음')}")
    st.sidebar.write(f"🛡️ 권한: {u_info['role']}")
    if st.sidebar.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False; st.session_state.user_info = None; st.session_state.current_page = "main"; st.rerun()
else:
    auth_choice = st.sidebar.radio("원하는 작업을 선택하세요", ["회원가입", "로그인"])
    users = load_json(USERS_FILE, {})
    
    if auth_choice == "회원가입":
        st.sidebar.subheader("📝 회원가입")
        reg_role = st.sidebar.selectbox("자격 선택", ["학생", "교사"])
        if reg_role == "학생": 
            reg_school = st.sidebar.text_input("소속 학교", value="호계고등학교")
            reg_class = st.sidebar.selectbox("소속 분반", CLASS_GROUPS)
        else: 
            reg_school = "교사소속"; reg_class = "교사"
            
        reg_id = st.sidebar.text_input("학번/ID 입력")
        reg_name = st.sidebar.text_input("이름 입력")
        reg_pw = st.sidebar.text_input("비밀번호", type="password")
        
        if st.sidebar.button("가입 신청", use_container_width=True):
            if reg_role and reg_id and reg_pw and reg_name:
                user_key = f"{reg_school}_{reg_id}" if reg_role == "학생" else f"teacher_{reg_id}"
                if user_key in users: st.sidebar.error("❌ 해당 학번/ID가 이미 존재합니다.")
                else:
                    users[user_key] = {"id": reg_id, "password": reg_pw, "name": reg_name, "role": reg_role, "school": reg_school if reg_role == "학생" else "소속없음", "class_group": reg_class}
                    save_json(USERS_FILE, users); st.sidebar.success("🎉 가입 완료! [로그인] 메뉴로 이동해주세요.")
            else: st.sidebar.warning("⚠️ 모든 빈칸을 빠짐없이 입력해주세요.")
                
    elif auth_choice == "로그인":
        login_type = st.sidebar.radio("로그인 계정 유형", ["학생", "교사"])
        if login_type == "학생": login_school = st.sidebar.text_input("소속 학교", value="호계고등학교")
        else: login_school = ""
            
        input_id = st.sidebar.text_input("학번/ID")
        input_pw = st.sidebar.text_input("비밀번호", type="password")
        
        if st.sidebar.button("로그인", use_container_width=True):
            if input_id in ADMIN_ACCOUNTS and input_pw == ADMIN_ACCOUNTS[input_id]:
                st.session_state.logged_in = True
                st.session_state.user_info = {"user_key": input_id, "username": input_id, "name": f"총괄운영자({input_id})", "role": "관리자", "school": "운영본부", "class_group": "관리자"}
                st.rerun()
            else:
                user_key = f"{login_school}_{input_id}" if login_type == "학생" else f"teacher_{input_id}"
                if user_key in users and users[user_key].get("password") == input_pw:
                    if users[user_key].get("role") == login_type:
                        st.session_state.logged_in = True
                        st.session_state.user_info = {"user_key": user_key, "username": users[user_key].get("id", input_id), "name": users[user_key].get("name", "이름없음"), "role": users[user_key].get("role", login_type), "school": users[user_key].get("school", "소속없음"), "class_group": users[user_key].get("class_group", "미배정")}
                        st.rerun()
                    else: st.sidebar.error("❌ 가입하신 계정 유형(학생/교사)이 다릅니다.")
                else: st.sidebar.error("❌ 학교, 학번/ID 또는 비밀번호가 틀렸습니다.")

# --- [5] 화면 분기 로직 ---
if not st.session_state.logged_in:
    st.title("🏫 주제 탐구 캠프 학습 시스템")
    st.info("왼쪽 사이드바를 이용해 로그인해주세요.")

else:
    current_role = st.session_state.user_info["role"]
    current_user_key = st.session_state.user_info["user_key"]
    app_config = load_json(CONFIG_FILE, {})
    learning_data = load_json(DATA_FILE, {})

    if st.session_state.current_page in ACTIVITIES:
        act_name = st.session_state.current_page
        st.title(f"📄 {act_name}")
        if st.button("⬅️ 메인 화면으로 돌아가기"):
            st.session_state.current_page = "main"; st.rerun()
        st.markdown("---")
        
        if current_role == "학생":
            if act_name == "[활동지1] 진학 희망 학과 조사하기": render_activity1_form(current_user_key)
            elif act_name == "[활동지2] 나만의 탐구 설계하기": render_activity2_form(current_user_key)
            else: render_submission_form(current_user_key, act_name, "content", f"{act_name} 제출란")
        else: st.warning("교사/관리자는 제출 모니터링 탭을 이용해주세요.")

    elif st.session_state.current_page == "main":
        if current_role == "학생":
            tabs_list = ["📌 캠프 공지 및 자료실"] + app_config["tabs"]
            tabs_objects = st.tabs(tabs_list)
            with tabs_objects[0]: render_camp_overview(current_role)
            for index, tab_name in enumerate(app_config["tabs"]):
                with tabs_objects[index + 1]:
                    st.subheader(f"📘 {tab_name} 활동 및 자료 제출")
                    display_pdf(app_config["pdfs"].get(tab_name, f"{tab_name}.pdf"))
                    st.markdown("---")
                    questions = app_config["questions"].get(tab_name, [])
                    for q in questions: render_submission_form(current_user_key, tab_name, q["id"], q["label"])

        elif current_role in ["교사", "관리자"]:
            st.title(f"🛠️ {current_role} 대시보드")
            if current_role == "관리자": menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "🗂️ 차시 및 자료 편집", "📥 학생 제출 자료 조회 및 관리"])
            else: menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "📥 학생 제출 자료 조회 및 관리"])
            
            with menu_tabs[0]: render_camp_overview(current_role)

            with menu_tabs[1]:
                st.subheader("👥 가입 회원 목록 및 관리")
                all_users = load_json(USERS_FILE, {})
                df_users = pd.DataFrame([{
                    "학교": info.get("school", "-"), "학번/ID": info.get("id", uid.split('_')[-1]), 
                    "이름": info.get("name", "이름없음"), "권한": info.get("role", "-"), 
                    "반": info.get("class_group", "-"), "비밀번호": info.get("password", "-")
                } for uid, info in all_users.items()])
                st.dataframe(df_users, use_container_width=True)

                if current_role == "관리자":
                    st.markdown("---")
                    st.subheader("⚙️ 개별 회원 제어")
                    col1, col2 = st.columns(2)
                    editable_users = [u for u in all_users.keys() if u not in ADMIN_ACCOUNTS]
                    with col1:
                        st.write("❌ **회원 강제 탈퇴(삭제)**")
                        delete_target = st.selectbox("삭제할 회원을 선택하세요", ["선택"] + editable_users, format_func=lambda x: x if x == "선택" else f"[{all_users[x].get('school', '소속없음')}] {all_users[x].get('name', '이름없음')} ({all_users[x].get('id', x.split('_')[-1])})")
                        if delete_target != "선택":
                            if st.button(f"⚠️ {all_users[delete_target].get('name', '해당 사용자')} 회원 데이터 영구 삭제", type="primary"):
                                del all_users[delete_target]; save_json(USERS_FILE, all_users); st.success("삭제 완료"); st.rerun()
                    with col2:
                        st.write("🔑 **학생/교사 비밀번호 강제 변경**")
                        pw_target = st.selectbox("비밀번호를 변경할 회원을 선택하세요", ["선택"] + editable_users, format_func=lambda x: x if x == "선택" else f"[{all_users[x].get('school', '소속없음')}] {all_users[x].get('name', '이름없음')} ({all_users[x].get('id', x.split('_')[-1])})")
                        new_pw = st.text_input("새로운 비밀번호 입력", type="password")
                        if pw_target != "선택":
                            if st.button("비밀번호 변경 적용") and new_pw:
                                all_users[pw_target]["password"] = new_pw; save_json(USERS_FILE, all_users); st.success("비밀번호 성공적으로 변경"); st.rerun()

            if current_role == "관리자":
                with menu_tabs[2]:
                    st.subheader("👨‍🏫 교사용 특강 자료 업로드 (PPT, PDF, 외부 링크)")
                    with st.form("upload_lecture_material"):
                        mat_title = st.text_input("자료 제목 (예: 1일차 오리엔테이션 PPT)")
                        mat_type = st.radio("자료 유형 선택", ["파일 업로드 (PPT, PDF 등)", "외부 링크 (Notion, Google Docs 등)"])
                        mat_link = st.text_input("외부 링크인 경우 URL을 입력하세요", placeholder="https://...")
                        mat_file = st.file_uploader("파일인 경우 이곳에 업로드하세요")
                        if st.form_submit_button("자료 등록하여 공지사항에 올리기"):
                            if not mat_title: st.error("자료 제목을 입력해주세요.")
                            else:
                                new_mat = {"id": f"mat_{datetime.datetime.now().strftime('%d%H%M%S')}", "title": mat_title}
                                if mat_type == "외부 링크 (Notion, Google Docs 등)": new_mat["type"] = "link"; new_mat["content"] = mat_link
                                else:
                                    if mat_file is not None:
                                        safe_filename = mat_file.name.replace("/", "_").replace("\\", "_")
                                        file_path = os.path.join(UPLOAD_DIR, f"lecture_{safe_filename}")
                                        with open(file_path, "wb") as f: f.write(mat_file.getvalue())
                                        new_mat["type"] = "file"; new_mat["content"] = file_path; new_mat["filename"] = mat_file.name
                                    else: st.error("파일을 선택해주세요."); st.stop()
                                app_config["materials"].append(new_mat); save_json(CONFIG_FILE, app_config); st.success("등록 완료!"); st.rerun()
                    current_materials = app_config.get("materials", [])
                    if current_materials:
                        st.write("🗑️ **등록된 강의 자료 삭제**")
                        del_mat_target = st.selectbox("삭제할 자료를 선택하세요", options=current_materials, format_func=lambda x: x.get("title", "제목없음"))
                        if st.button("선택한 자료 삭제하기"):
                            app_config["materials"].remove(del_mat_target); save_json(CONFIG_FILE, app_config); st.success("삭제 완료!"); st.rerun()
                    
                    st.markdown("---")
                    st.subheader("⚙️ 차시(Tab) 동적 제어")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("➕ **새로운 학습 차시 추가**")
                        new_tab_name = st.text_input("추가할 차시 이름 입력")
                        new_pdf_name = st.text_input("연결할 PDF 파일명", value="session_new.pdf")
                        if st.button("차시 개설하기"):
                            if new_tab_name and new_tab_name not in app_config["tabs"]:
                                app_config["tabs"].append(new_tab_name); app_config["pdfs"][new_tab_name] = new_pdf_name; app_config["questions"][new_tab_name] = []
                                save_json(CONFIG_FILE, app_config); st.success(f"🎉 {new_tab_name} 개설 완료."); st.rerun()
                    with col2:
                        st.write("❌ **기존 학습 차시 폐쇄**")
                        del_tab_target = st.selectbox("삭제할 차시를 지정하세요", ["선택"] + app_config["tabs"])
                        if del_tab_target != "선택":
                            if st.button(f"🔥 {del_tab_target} 세션 및 질문 전체 삭제", type="primary"):
                                app_config["tabs"].remove(del_tab_target); app_config["pdfs"].pop(del_tab_target, None); app_config["questions"].pop(del_tab_target, None)
                                save_json(CONFIG_FILE, app_config); st.success(f"삭제 완료."); st.rerun()
                                
                    st.markdown("---")
                    st.subheader("📝 차시별 제출 텍스트 상자(질문 문항) 동적 가변 설정")
                    target_q_tab = st.selectbox("문항을 편집할 차시 선택", app_config["tabs"])
                    if target_q_tab:
                        current_qs = app_config["questions"].get(target_q_tab, [])
                        for q in current_qs: st.text(f" - [{q['id']}] {q.get('label', '')}")
                        q_col1, q_col2 = st.columns(2)
                        with q_col1:
                            add_q_label = st.text_input("질문 설명(라벨) 문구 입력")
                            if st.button("질문 추가") and add_q_label:
                                new_id = f"q_{datetime.datetime.now().strftime('%d%H%M%S')}"
                                current_qs.append({"id": new_id, "label": add_q_label})
                                app_config["questions"][target_q_tab] = current_qs; save_json(CONFIG_FILE, app_config); st.success("문항 추가 완료."); st.rerun()
                        with q_col2:
                            if current_qs:
                                del_q_target = st.selectbox("삭제할 문항을 고르세요", options=current_qs, format_func=lambda x: x.get("label", ""))
                                if st.button("선택한 문항 삭제", type="primary"):
                                    current_qs.remove(del_q_target); app_config["questions"][target_q_tab] = current_qs; save_json(CONFIG_FILE, app_config); st.success("삭제 완료."); st.rerun()

            with menu_tabs[-1]:
                st.subheader("📥 반별 학생 학습 활동 및 제출 자료 조회")
                all_users = load_json(USERS_FILE, {})
                filter_class = st.radio("조회할 반 선택", ["전체 보기"] + CLASS_GROUPS, horizontal=True)
                
                student_list = [uid for uid, info in all_users.items() if info.get("role") == "학생" and (filter_class == "전체 보기" or filter_class == info.get("class_group", "미배정"))]
                
                if not student_list: st.info(f"선택하신 조건({filter_class})에 해당하는 가입 학생이 없습니다.")
                else:
                    view_mode = st.radio("조회 모드 선택", ["👤 특정 학생 집중 분석", "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)"], horizontal=True)
                    st.markdown("---")
                    
                    if view_mode == "👤 특정 학생 집중 분석":
                        selected_student = st.selectbox("학생 선택", student_list, format_func=lambda x: f"[{all_users[x].get('class_group', '-')}] {all_users[x].get('school', '-')} {all_users[x].get('name', '이름없음')} ({all_users[x].get('id', x.split('_')[-1])})")
                        if selected_student:
                            student_answers = learning_data.get(selected_student, {})
                            st.info("💡 다운로드한 파일을 더블클릭하여 인터넷 창으로 연 뒤, **[우클릭] -> [인쇄] -> [PDF로 저장]**을 누르시면 화면 깨짐 없이 완벽한 PDF 문서가 만들어집니다.")
                            
                            html_content = f"""<!DOCTYPE html>
                            <html lang="ko">
                            <head>
                            <meta charset="UTF-8">
                            <title>학습 포트폴리오</title>
                            <style>
                                body {{ font-family: 'Malgun Gothic', dotum, sans-serif; padding: 40px; line-height: 1.6; color: #333; }}
                                h1 {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 40px; }}
                                h2 {{ color: #2c3e50; border-left: 5px solid #3498db; padding-left: 10px; margin-top: 40px; }}
                                h3 {{ color: #2980b9; margin-top: 20px; }}
                                h4 {{ color: #34495e; margin-top: 15px; border-bottom: 1px dashed #ccc; padding-bottom: 5px; }}
                                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; font-size: 14px; }}
                                th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: left; }}
                                th {{ background-color: #ecf0f1; font-weight: bold; text-align: center; }}
                                .content-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; border: 1px solid #e9ecef; margin-bottom: 20px; white-space: pre-wrap; }}
                                .link-text {{ color: #e74c3c; font-weight: bold; text-decoration: none; }}
                            </style>
                            </head>
                            <body>
                                <h1>📚 학습 포트폴리오</h1>
                                <div style="text-align: right; margin-bottom: 30px; font-size: 16px;">
                                    <strong>학교:</strong> {all_users[selected_student].get('school', '')}<br>
                                    <strong>소속:</strong> {all_users[selected_student].get('class_group', '')}<br>
                                    <strong>이름:</strong> {all_users[selected_student].get('name', '')} ({all_users[selected_student].get('id', '')})
                                </div>
                            """

                            html_content += "<h2>📑 [1] 활동지 작성 내역</h2>"
                            for act in ACTIVITIES:
                                ans = student_answers.get(act, {})
                                if act == "[활동지1] 진학 희망 학과 조사하기" and ans.get("is_custom"):
                                    html_content += f"<h3>▶ {act}</h3>"
                                    html_content += "<h4>[1단계] 추출한 핵심 내용 요소</h4>"
                                    html_content += "<table><tr><th>학과/전공명</th><th>핵심 내용 요소</th></tr>"
                                    for row in ans.get("df1", []): html_content += f"<tr><td>{row.get('학과/전공명', '')}</td><td>{row.get('핵심 내용 요소', '')}</td></tr>"
                                    html_content += "</table>"
                                    html_content += "<h4>[2단계] 생기부 탐구 내용 분석</h4>"
                                    html_content += "<table><tr><th>구분</th><th>키워드1</th><th>키워드2</th><th>키워드3</th><th>키워드4</th><th>키워드5</th></tr>"
                                    for row in ans.get("df2", []): html_content += f"<tr><td><b>{row.get('구분', '')}</b></td><td>{row.get('키워드1','')}</td><td>{row.get('키워드2','')}</td><td>{row.get('키워드3','')}</td><td>{row.get('키워드4','')}</td><td>{row.get('키워드5','')}</td></tr>"
                                    html_content += "</table>"
                                    html_content += "<h4>[3단계] 탐구 주제 및 문제 인식</h4>"
                                    html_content += f"<div class='content-box'>{ans.get('step3', '')}</div>"
                                    continue
                                
                                # 💡 활동지2 HTML 출력 연동
                                if act == "[활동지2] 나만의 탐구 설계하기" and ans.get("is_custom_act2"):
                                    html_content += f"<h3>▶ {act}</h3>"
                                    html_content += "<h4>[1단계] 관심에서 출발하기</h4>"
                                    html_content += f"<p><b>관심 있는 것:</b> {ans.get('step1_1', '')}</p>"
                                    html_content += f"<p><b>계기:</b> {ans.get('step1_2', '')}</p>"
                                    html_content += "<table><tr><th>구분</th><th>내용</th></tr>"
                                    for row in ans.get("df1", []): html_content += f"<tr><td>{row.get('구분', '')}</td><td>{row.get('내용', '')}</td></tr>"
                                    html_content += "</table>"
                                    html_content += "<h4>[2단계] 교과 개념에 닻 내리기</h4>"
                                    html_content += "<table><tr><th>구분</th><th>내용</th></tr>"
                                    for row in ans.get("df2", []): html_content += f"<tr><td>{row.get('구분', '')}</td><td>{row.get('내용', '')}</td></tr>"
                                    html_content += "</table>"
                                    html_content += f"<p><b>잠정적 탐구 방향:</b> {ans.get('step2_dir', '')}</p>"
                                    html_content += "<h4>[3단계] 주제 적절성 자가 진단</h4>"
                                    html_content += "<table><tr><th>점검 항목</th><th>점검 질문</th><th>좋은 예</th><th>판단 (O/X)</th></tr>"
                                    for row in ans.get("df3", []): html_content += f"<tr><td>{row.get('점검 항목', '')}</td><td>{row.get('점검 질문', '')}</td><td>{row.get('좋은 예', '')}</td><td>{row.get('판단 (O/X)', '')}</td></tr>"
                                    html_content += "</table>"
                                    html_content += "<h4>[4단계] 막연한 주제를 학술적 질문으로 바꾸기</h4>"
                                    html_content += f"<p><b>선택한 렌즈:</b> {ans.get('step4_1', '')}</p>"
                                    html_content += f"<p><b>핵심 탐구 질문:</b> {ans.get('step4_2', '')}</p>"
                                    html_content += "<h4>[5단계] 탐구 전략 하나 정하기</h4>"
                                    html_content += f"<p><b>선택한 전략:</b> {ans.get('step5_1', '')}</p>"
                                    html_content += f"<p><b>구체적인 접근 방법:</b> {ans.get('step5_2', '')}</p>"
                                    html_content += "<h4>[6단계] AI 멘토에게 점검받기</h4>"
                                    html_content += f"<div class='content-box'><b>반영할 점:</b><br>{ans.get('step6', '')}</div>"
                                    html_content += "<h4>[7단계] 나의 탐구 계획 완성하기</h4>"
                                    html_content += "<table><tr><th>항목</th><th>내용</th></tr>"
                                    for row in ans.get("df7", []): html_content += f"<tr><td>{row.get('항목', '')}</td><td>{row.get('내용', '')}</td></tr>"
                                    html_content += "</table>"
                                    html_content += f"<p><b>요약:</b> 나는 <b>({ans.get('step7_s1', '')})</b> 개념을 활용해, <b>({ans.get('step7_s2', '')})</b> 전략으로 <b>({ans.get('step7_s3', '')})</b>을(를) 밝히려 한다.</p>"
                                    continue
                                    
                                ans_content = ans.get("content", {})
                                if isinstance(ans_content, str): ans_content = {"text": ans_content}
                                if ans_content.get("text") or ans_content.get("link"):
                                    html_content += f"<h3>▶ {act}</h3>"
                                    if ans_content.get("text"): html_content += f"<b>[텍스트 작성 내용]</b><div class='content-box'>{ans_content['text']}</div>"
                                    if ans_content.get("link"): html_content += f"<b>[제출 링크]</b> <a href='{ans_content['link']}' target='_blank' class='link-text'>{ans_content['link']}</a><br><br>"

                            html_content += "<h2>📝 [2] 차시별 제출 자료</h2>"
                            for t_name in app_config["tabs"]:
                                for q in app_config["questions"].get(t_name, []):
                                    ans = student_answers.get(t_name, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans} 
                                    if ans.get("text") or ans.get("link"):
                                        html_content += f"<h3>▶ [{t_name}] {q.get('label', '')}</h3>"
                                        if ans.get("text"): html_content += f"<b>[텍스트 작성 내용]</b><div class='content-box'>{ans['text']}</div>"
                                        if ans.get("link"): html_content += f"<b>[제출 링크]</b> <a href='{ans['link']}' target='_blank' class='link-text'>{ans['link']}</a><br><br>"

                            html_content += "</body></html>"
                            
                            st.download_button(
                                label=f"📄 {all_users[selected_student].get('name', '학생')}의 포트폴리오 다운로드 (웹문서/PDF 변환용)",
                                data=html_content.encode('utf-8-sig'), file_name=f"{all_users[selected_student].get('name', '학생')}_학습포트폴리오.html", mime="text/html", type="primary"
                            )
                            
                            st.markdown("---")
                            st.markdown("#### 📍 [1] 활동지 작성 내역")
                            for act in ACTIVITIES:
                                ans = student_answers.get(act, {})
                                if act == "[활동지1] 진학 희망 학과 조사하기" and ans.get("is_custom"):
                                    st.markdown(f"### **{act}**")
                                    st.markdown("**[1단계] 추출한 핵심 내용 요소**")
                                    st.dataframe(pd.DataFrame(ans.get("df1", [])), use_container_width=True)
                                    st.markdown("**[2단계] 생기부 탐구 내용 분석**")
                                    st.dataframe(pd.DataFrame(ans.get("df2", [])), use_container_width=True)
                                    st.markdown("**[3단계] 탐구 주제 및 문제 인식**")
                                    st.info(ans.get("step3", "-"))
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    continue
                                
                                # 💡 활동지2 스크린 렌더링
                                if act == "[활동지2] 나만의 탐구 설계하기" and ans.get("is_custom_act2"):
                                    st.markdown(f"### **{act}**")
                                    st.markdown("**[1단계] 관심에서 출발하기**")
                                    st.write(f"- 관심 현상: {ans.get('step1_1', '')}")
                                    st.write(f"- 계기: {ans.get('step1_2', '')}")
                                    st.dataframe(pd.DataFrame(ans.get("df1", [])), use_container_width=True)
                                    st.markdown("**[2단계] 교과 개념에 닻 내리기**")
                                    st.dataframe(pd.DataFrame(ans.get("df2", [])), use_container_width=True)
                                    st.write(f"- 잠정적 탐구 방향: {ans.get('step2_dir', '')}")
                                    st.markdown("**[3단계] 주제 적절성 자가 진단**")
                                    st.dataframe(pd.DataFrame(ans.get("df3", [])), use_container_width=True)
                                    st.markdown("**[4단계] 학술적 질문으로 바꾸기**")
                                    st.write(f"- 선택 렌즈: {ans.get('step4_1', '')}")
                                    st.write(f"- 탐구 질문: {ans.get('step4_2', '')}")
                                    st.markdown("**[5단계] 탐구 전략 하나 정하기**")
                                    st.write(f"- 선택 전략: {ans.get('step5_1', '')}")
                                    st.write(f"- 구체적 방법: {ans.get('step5_2', '')}")
                                    st.markdown("**[6단계] AI 멘토에게 점검받기**")
                                    st.info(f"반영할 점: {ans.get('step6', '')}")
                                    st.markdown("**[7단계] 나의 탐구 계획 완성하기**")
                                    st.dataframe(pd.DataFrame(ans.get("df7", [])), use_container_width=True)
                                    st.write(f"**요약:** 나는 ({ans.get('step7_s1', '')}) 개념을 활용해, ({ans.get('step7_s2', '')}) 전략으로 ({ans.get('step7_s3', '')})을(를) 밝히려 한다.")
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    continue
                                
                                ans_content = ans.get("content", {})
                                if isinstance(ans_content, str): ans_content = {"text": ans_content}
                                if ans_content.get("text") or ans_content.get("link") or ans_content.get("file_name"):
                                    st.markdown(f"**{act}**")
                                    if ans_content.get("text"): st.write(f"📝 {ans_content['text']}")
                                    if ans_content.get("link"): st.write(f"🔗 {ans_content['link']}")
                                    if ans_content.get("file_path") and os.path.exists(ans_content['file_path']):
                                        with open(ans_content['file_path'], "rb") as f:
                                            st.download_button("📥 첨부파일 다운로드", f, file_name=ans_content['file_name'], key=f"dl_{selected_student}_{act}")
                            
                            st.markdown("---")
                            st.markdown("#### 📍 [2] 차시별 제출 자료")
                            for t_name in app_config["tabs"]:
                                for q in app_config["questions"].get(t_name, []):
                                    ans = student_answers.get(t_name, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans} 
                                    if ans.get("text") or ans.get("link") or ans.get("file_name"):
                                        st.markdown(f"**[{t_name}] Q. {q.get('label', '')}**")
                                        if ans.get("text"): st.write(f"📝 {ans['text']}")
                                        if ans.get("link"): st.write(f"🔗 {ans['link']}")
                                        if ans.get("file_path") and os.path.exists(ans['file_path']):
                                            with open(ans['file_path'], "rb") as f:
                                                st.download_button(f"📥 {ans['file_name']} 다운로드", f, file_name=ans['file_name'], key=f"dl_{selected_student}_{q['id']}")

                    elif view_mode == "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)":
                        combined_list = ["--- [활동지 데이터 목록] ---"] + ACTIVITIES + ["--- [학습 차시 데이터 목록] ---"] + app_config["tabs"]
                        selected_view = st.selectbox("다운로드할 데이터 범주를 선택하세요", combined_list)
                        
                        if selected_view == "[활동지1] 진학 희망 학과 조사하기":
                            st.info("💡 아래 화면은 입력 형식 그대로 렌더링된 모습이며, 하단의 엑셀 다운로드 버튼을 누르면 세로 형식의 데이터로 깔끔하게 정리된 엑셀(CSV) 파일을 받을 수 있습니다.")
                            csv_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {})
                                u_info = all_users[s_uid]
                                st.markdown(f"#### 👤 [{u_info.get('school', '')}] {u_info.get('class_group', '')} - {u_info.get('name', '')} ({u_info.get('id', s_uid.split('_')[-1])})")
                                st.markdown("**[1단계] 학과/전공 가이드북 읽고 핵심 내용 요소 추출하기**")
                                st.dataframe(pd.DataFrame(ans.get("df1", [])), use_container_width=True)
                                st.markdown("**[2단계] 내용 요소 중심 학교생활기록부 탐구 내용 분석하기**")
                                st.dataframe(pd.DataFrame(ans.get("df2", [])), use_container_width=True)
                                st.markdown("**[3단계] 탐구 주제 및 문제 인식**")
                                st.info(ans.get("step3", "-")); st.markdown("---")
                                
                                csv_data.append([f"■ [{u_info.get('school', '')}] {u_info.get('class_group', '')} - {u_info.get('name', '')} ({u_info.get('id', s_uid.split('_')[-1])})", "", "", "", "", ""])
                                csv_data.append(["[1단계] 학과/전공 가이드북 읽고 핵심 내용 요소 추출하기", "", "", "", "", ""])
                                csv_data.append(["학과/전공명", "핵심 내용 요소", "", "", "", ""])
                                for row in ans.get("df1", []): csv_data.append([row.get("학과/전공명", ""), row.get("핵심 내용 요소", ""), "", "", "", ""])
                                csv_data.append(["", "", "", "", "", ""])
                                csv_data.append(["[2단계] 내용 요소 중심 학교생활기록부 탐구 내용 분석하기", "", "", "", "", ""])
                                csv_data.append(["구분", "키워드1", "키워드2", "키워드3", "키워드4", "키워드5"])
                                for row in ans.get("df2", []): csv_data.append([row.get("구분", ""), row.get("키워드1", ""), row.get("키워드2", ""), row.get("키워드3", ""), row.get("키워드4", ""), row.get("키워드5", "")])
                                csv_data.append(["", "", "", "", "", ""])
                                csv_data.append(["[3단계] 이번 특강을 통해 탐구하고 싶은 내용 영역 또는 문제 인식", "", "", "", "", ""])
                                csv_data.append([ans.get("step3", ""), "", "", "", "", ""])
                                csv_data.append(["==================================================", "", "", "", "", ""])
                                csv_data.append(["", "", "", "", "", ""])
                            df_csv = pd.DataFrame(csv_data)
                            st.download_button(f"📊 활동지1 원본 폼 형식 엑셀 다운로드 ({filter_class})", data=df_csv.to_csv(index=False, header=False).encode('utf-8-sig'), file_name=f"활동지1_원본포맷_{filter_class}_결과.csv", mime='text/csv', type="primary")

                        elif selected_view == "[활동지2] 나만의 탐구 설계하기":
                            st.info("💡 아래 화면은 입력 형식 그대로 렌더링된 모습이며, 하단의 엑셀 다운로드 버튼을 누르면 세로 형식의 데이터로 깔끔하게 정리된 엑셀(CSV) 파일을 받을 수 있습니다.")
                            csv_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {})
                                u_info = all_users[s_uid]
                                st.markdown(f"#### 👤 [{u_info.get('school', '')}] {u_info.get('class_group', '')} - {u_info.get('name', '')} ({u_info.get('id', s_uid.split('_')[-1])})")
                                st.markdown("**[1단계] 관심에서 출발하기**")
                                st.write(f"- 관심 현상: {ans.get('step1_1', '')}\n- 계기: {ans.get('step1_2', '')}")
                                st.dataframe(pd.DataFrame(ans.get("df1", [])), use_container_width=True)
                                st.markdown("**[2단계] 교과 개념에 닻 내리기**")
                                st.dataframe(pd.DataFrame(ans.get("df2", [])), use_container_width=True)
                                st.write(f"- 잠정적 탐구 방향: {ans.get('step2_dir', '')}")
                                st.markdown("**[3단계] 주제 적절성 자가 진단**")
                                st.dataframe(pd.DataFrame(ans.get("df3", [])), use_container_width=True)
                                st.markdown("**[4단계] 학술적 질문으로 바꾸기**")
                                st.write(f"- 선택 렌즈: {ans.get('step4_1', '')}\n- 탐구 질문: {ans.get('step4_2', '')}")
                                st.markdown("**[5단계] 탐구 전략 하나 정하기**")
                                st.write(f"- 선택 전략: {ans.get('step5_1', '')}\n- 구체적 방법: {ans.get('step5_2', '')}")
                                st.markdown("**[6단계] AI 멘토에게 점검받기**")
                                st.info(f"반영할 점: {ans.get('step6', '')}")
                                st.markdown("**[7단계] 나의 탐구 계획 완성하기**")
                                st.dataframe(pd.DataFrame(ans.get("df7", [])), use_container_width=True)
                                st.write(f"**요약:** 나는 ({ans.get('step7_s1', '')}) 개념을 활용해, ({ans.get('step7_s2', '')}) 전략으로 ({ans.get('step7_s3', '')})을(를) 밝히려 한다.")
                                st.markdown("---")
                                
                                csv_data.append([f"■ [{u_info.get('school', '')}] {u_info.get('class_group', '')} - {u_info.get('name', '')} ({u_info.get('id', s_uid.split('_')[-1])})", "", "", ""])
                                csv_data.append(["[1단계] 관심에서 출발하기", "", "", ""])
                                csv_data.append([f"관심사: {ans.get('step1_1', '')}", f"계기: {ans.get('step1_2', '')}", "", ""])
                                csv_data.append(["이전 탐구 확장 시", "내용", "", ""])
                                for row in ans.get("df1", []): csv_data.append([row.get("구분", ""), row.get("내용", ""), "", ""])
                                csv_data.append(["", "", "", ""])
                                csv_data.append(["[2단계] 교과 개념에 닻 내리기", "", "", ""])
                                csv_data.append(["구분", "내용", "", ""])
                                for row in ans.get("df2", []): csv_data.append([row.get("구분", ""), row.get("내용", ""), "", ""])
                                csv_data.append([f"잠정적 탐구 방향: {ans.get('step2_dir', '')}", "", "", ""])
                                csv_data.append(["", "", "", ""])
                                csv_data.append(["[3단계] 주제 적절성 자가 진단", "", "", ""])
                                csv_data.append(["점검 항목", "점검 질문", "좋은 예", "판단 (O/X)"])
                                for row in ans.get("df3", []): csv_data.append([row.get("점검 항목", ""), row.get("점검 질문", ""), row.get("좋은 예", ""), row.get("판단 (O/X)", "")])
                                csv_data.append(["", "", "", ""])
                                csv_data.append(["[4단계] 학술적 질문으로 바꾸기", "", "", ""])
                                csv_data.append([f"선택 렌즈: {ans.get('step4_1', '')}", f"핵심 탐구 질문: {ans.get('step4_2', '')}", "", ""])
                                csv_data.append(["", "", "", ""])
                                csv_data.append(["[5단계] 탐구 전략 하나 정하기", "", "", ""])
                                csv_data.append([f"선택 전략: {ans.get('step5_1', '')}", f"접근 방법: {ans.get('step5_2', '')}", "", ""])
                                csv_data.append(["", "", "", ""])
                                csv_data.append(["[6단계] AI 멘토에게 점검받기", "", "", ""])
                                csv_data.append([f"반영할 점: {ans.get('step6', '')}", "", "", ""])
                                csv_data.append(["", "", "", ""])
                                csv_data.append(["[7단계] 나의 탐구 계획 완성하기", "", "", ""])
                                csv_data.append(["항목", "내용", "", ""])
                                for row in ans.get("df7", []): csv_data.append([row.get("항목", ""), row.get("내용", ""), "", ""])
                                csv_data.append([f"요약: 나는 ({ans.get('step7_s1', '')}) 개념을 활용해, ({ans.get('step7_s2', '')}) 전략으로 ({ans.get('step7_s3', '')})을(를) 밝히려 한다.", "", "", ""])
                                csv_data.append(["==================================================", "", "", ""])
                                csv_data.append(["", "", "", ""])
                            df_csv = pd.DataFrame(csv_data)
                            st.download_button(f"📊 활동지2 원본 폼 형식 엑셀 다운로드 ({filter_class})", data=df_csv.to_csv(index=False, header=False).encode('utf-8-sig'), file_name=f"활동지2_원본포맷_{filter_class}_결과.csv", mime='text/csv', type="primary")

                        elif selected_view in ACTIVITIES:
                            q_summary_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {}).get("content", {})
                                if isinstance(ans, str): ans = {"text": ans}
                                q_summary_data.append({"학교": all_users[s_uid].get("school", "-"), "반": all_users[s_uid].get("class_group", "-"), "학번": all_users[s_uid].get("id", s_uid.split('_')[-1]), "이름": all_users[s_uid].get("name", ""), "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")})
                            df_q = pd.DataFrame(q_summary_data)
                            st.dataframe(df_q, use_container_width=True, hide_index=True)
                            st.download_button(f"📊 엑셀(CSV) 다운로드 ({filter_class})", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_view}_{filter_class}_결과.csv", mime='text/csv')
                            
                        elif selected_view in app_config["tabs"]:
                            for q in app_config["questions"].get(selected_view, []):
                                st.markdown(f"##### ❓ {q.get('label', '')}")
                                q_summary_data = []
                                for s_uid in student_list:
                                    ans = learning_data.get(s_uid, {}).get(selected_view, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans}
                                    q_summary_data.append({"학교": all_users[s_uid].get("school", "-"), "반": all_users[s_uid].get("class_group", "-"), "학번": all_users[s_uid].get("id", s_uid.split('_')[-1]), "이름": all_users[s_uid].get("name", ""), "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")})
                                df_q = pd.DataFrame(q_summary_data)
                                st.dataframe(df_q, use_container_width=True, hide_index=True)
                                st.download_button(f"📊 문항 데이터 다운로드 ({filter_class})", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_view}_{filter_class}_결과.csv", mime='text/csv', key=f"csv_{q['id']}")
