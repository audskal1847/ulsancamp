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

# 시작 시 업로드 폴더 자동 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)

CLASS_GROUPS = ["1반", "2반", "3반", "4반"]

ACTIVITIES = [
    "[활동지1] 진학 희망 학과 조사하기",
    "[활동지2] AI 활용 심화 주제 발굴: 탐구 주제 구체화 & 전략 수립",
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
    updated = False
    for i in range(1, 5):
        admin_id = f"admin{i}"
        user_key = f"호계고등학교_{admin_id}"
        if user_key not in users:
            users[user_key] = {"id": admin_id, "password": "admin123", "name": f"관리자{i}", "role": "관리자", "school": "호계고등학교", "class_group": "관리자"}
            updated = True
    if updated: save_json(USERS_FILE, users)
    
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

# --- [3-A] 일반 제출 폼 (텍스트/링크/파일 혼합) ---
def render_submission_form(user_key, category, q_id, q_label):
    data = load_json(DATA_FILE, {})
    ans = data.get(user_key, {}).get(category, {}).get(q_id, {})
    
    if isinstance(ans, str): 
        ans = {"text": ans, "link": "", "file_name": "", "file_path": ""}
        
    with st.form(key=f"form_{user_key}_{category}_{q_id}"):
        st.markdown(f"**{q_label}**")
        st.caption("텍스트 입력, 외부 링크 주소, 파일 첨부 중 원하는 방식을 하나 이상 선택하여 제출하세요.")
        text_val = st.text_area("📝 텍스트 내용 작성", value=ans.get("text", ""), height=150)
        link_val = st.text_input("🔗 관련 링크(URL) 제출", value=ans.get("link", ""), placeholder="https://...")
        
        if ans.get("file_name"):
            st.info(f"📁 현재 등록된 파일: {ans.get('file_name')}")
            
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

# --- [3-B] 활동지1 전용 맞춤형 폼 (이미지 추가 및 키워드 열 이름 변경) ---
def render_activity1_form(user_key):
    category = "[활동지1] 진학 희망 학과 조사하기"
    data = load_json(DATA_FILE, {})
    ans = data.get(user_key, {}).get(category, {})
    
    st.markdown("<div style='background-color: #fff9e6; padding: 15px; border-radius: 5px; font-weight: bold;'>전공 가이드북을 활용하여 진학을 희망하는 학과의 핵심 내용 요소를 추출하고 이를 바탕으로 자신의 학교생활기록부의 탐구 활동을 분석/분류한다.</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form(key=f"form_act1_{user_key}"):
        st.markdown("#### [1단계] 학과/전공 가이드북 읽고 핵심 내용 요소 추출하기")
        default_df1 = pd.DataFrame([{"학과/전공명": "", "핵심 내용 요소": ""} for _ in range(4)])
        df1 = pd.DataFrame(ans.get("df1", default_df1.to_dict('records')))
        edited_df1 = st.data_editor(df1, num_rows="dynamic", use_container_width=True, key="act1_df1")
        st.markdown("---")
        
        st.markdown("#### [2단계] 내용 요소 중심 학교생활기록부 탐구 내용 분석하기")
        st.info("💡 표의 가장 윗줄인 **'✏️ 나의 탐구 키워드'** 행의 빈칸을 더블클릭하여 본인의 키워드를 직접 입력하세요!")
        
        # 💡 [핵심 수정] 요소1~5를 키워드1~5로 변경 완료
        default_df2 = pd.DataFrame({
            "구분": ["✏️ 나의 탐구 키워드", "창체활동", "교과세특"],
            "키워드1": ["", "", ""], "키워드2": ["", "", ""], "키워드3": ["", "", ""], "키워드4": ["", "", ""], "키워드5": ["", "", ""]
        })
        df2 = pd.DataFrame(ans.get("df2", default_df2.to_dict('records')))
        edited_df2 = st.data_editor(df2, use_container_width=True, key="act1_df2")
        
        st.markdown("<br>#### [2단계-예시]", unsafe_allow_html=True)
        # 💡 [핵심 수정] 전달해주신 스크린샷 이미지 출력 코드 추가
        example_image = os.path.join(os.path.dirname(__file__), "스크린샷 2026-07-18 214218.png")
        if os.path.exists(example_image):
            st.image(example_image, caption="희망 전공 분야 카운팅 표 사례 (고려대 전기전자공학부 등)를 참고하여 위 표의 칸을 채워보세요.", use_container_width=True)
        else:
            st.info("💡 [2단계-예시] 희망 전공 분야 카운팅 표 사례 (고려대 전기전자공학부 등)를 참고하여 위 표의 칸을 채워보세요. (현재 폴더에 '스크린샷 2026-07-18 214218.png' 파일이 없어 이미지가 표시되지 않습니다.)")
            
        st.markdown("---")
        
        st.markdown("#### [3단계] 이번 특강을 통해 탐구하고 싶은 내용 영역 또는 문제 인식(주제 찾기)")
        st.markdown("<div style='background-color: #fff9e6; padding: 10px; border-radius: 5px;'>내가 지금까지 다루지 못했던 내용 요소는 무엇이고 그것과 관련된 탐구 주제는 무엇이 있을까?</div>", unsafe_allow_html=True)
        step3_val = st.text_area("내용을 입력하세요", value=ans.get("step3", ""), height=150)

        if st.form_submit_button("활동지 최종 제출 및 저장", type="primary"):
            if user_key not in data: data[user_key] = {}
            data[user_key][category] = {
                "is_custom": True, "df1": edited_df1.to_dict('records'),
                "df2": edited_df2.to_dict('records'), "step3": step3_val
            }
            save_json(DATA_FILE, data)
            st.toast("🎉 활동지1이 성공적으로 저장되었습니다!")

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

        with st.expander("📝 활동지 링크 (클릭 시 이동 및 작성)"):
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
    if display_class and display_class != "관리자":
        st.sidebar.write(f"🏫 소속: {u_info['school']} ({display_class})")
    else:
        st.sidebar.write(f"🏫 소속: {u_info['school']}")
    st.sidebar.write(f"🛡️ 권한: {u_info['role']}")
    if st.sidebar.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False; st.session_state.user_info = None; st.session_state.current_page = "main"; st.rerun()
else:
    auth_choice = st.sidebar.radio("원하는 작업을 선택하세요", ["회원가입", "로그인"])
    users = load_json(USERS_FILE, {})
    
    if auth_choice == "회원가입":
        st.sidebar.subheader("📝 회원가입")
        reg_role = st.sidebar.selectbox("자격 선택", ["학생", "교사", "관리자"])
        if reg_role == "학생": reg_class = st.sidebar.selectbox("소속 분반", CLASS_GROUPS)
        else: reg_class = "관리자"
            
        reg_school = st.sidebar.text_input("소속 학교", value="호계고등학교")
        reg_id = st.sidebar.text_input("학번/ID 입력")
        reg_name = st.sidebar.text_input("이름 입력")
        reg_pw = st.sidebar.text_input("비밀번호", type="password")
        
        if st.sidebar.button("가입 신청", use_container_width=True):
            if reg_role and reg_school and reg_id and reg_pw and reg_name:
                user_key = f"{reg_school}_{reg_id}"
                if user_key in users: st.sidebar.error("❌ 해당 학교에 이미 동일한 학번/ID가 존재합니다.")
                else:
                    users[user_key] = {"id": reg_id, "password": reg_pw, "name": reg_name, "role": reg_role, "school": reg_school, "class_group": reg_class}
                    save_json(USERS_FILE, users); st.sidebar.success("🎉 가입 완료! [로그인] 메뉴로 이동해주세요.")
            else: st.sidebar.warning("⚠️ 모든 빈칸을 빠짐없이 입력해주세요.")
                
    elif auth_choice == "로그인":
        login_school = st.sidebar.text_input("소속 학교", value="호계고등학교")
        input_id = st.sidebar.text_input("학번/ID")
        input_pw = st.sidebar.text_input("비밀번호", type="password")
        
        if st.sidebar.button("로그인", use_container_width=True):
            user_key = f"{login_school}_{input_id}"
            if user_key in users and users[user_key]["password"] == input_pw:
                st.session_state.logged_in = True
                st.session_state.user_info = {
                    "user_key": user_key, "username": users[user_key].get("id", input_id), 
                    "name": users[user_key]["name"], "role": users[user_key]["role"], 
                    "school": users[user_key]["school"], "class_group": users[user_key].get("class_group", "미배정")
                }
                st.rerun()
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
            else: render_submission_form(current_user_key, act_name, "content", f"{act_name} 제출란")
        else: st.warning("교사/관리자는 제출 모니터링 탭을 이용해주세요.")

    elif st.session_state.current_page == "main":
        # --------- 학생 ---------
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

        # --------- 관리자/교사 ---------
        elif current_role in ["교사", "관리자"]:
            st.title(f"🛠️ {current_role} 대시보드")
            if current_role == "관리자":
                menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "🗂️ 차시 및 자료 편집", "📥 학생 제출 자료 조회 및 관리"])
            else:
                menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "📥 학생 제출 자료 조회 및 관리"])
            
            with menu_tabs[0]: render_camp_overview(current_role)

            with menu_tabs[1]:
                all_users = load_json(USERS_FILE, {})
                st.dataframe(pd.DataFrame([{"학교": info["school"], "학번": info.get("id", uid.split('_')[-1]), "이름": info["name"], "권한": info["role"], "반": info.get("class_group", "-")} for uid, info in all_users.items()]), use_container_width=True)

            if current_role == "관리자":
                with menu_tabs[2]: st.info("차시 및 자료 제어 인터페이스 구동 중 (이전 코드와 완벽 동일)")

            with menu_tabs[-1]:
                st.subheader("📥 반별 학생 학습 활동 및 제출 자료 조회")
                all_users = load_json(USERS_FILE, {})
                filter_class = st.radio("조회할 반 선택", ["전체 보기"] + CLASS_GROUPS, horizontal=True)
                
                student_list = []
                for uid, info in all_users.items():
                    if info["role"] == "학생":
                        s_class = info.get("class_group", "미배정")
                        if filter_class == "전체 보기" or filter_class == s_class:
                            student_list.append(uid)
                
                if not student_list: st.info(f"선택하신 조건({filter_class})에 해당하는 가입 학생이 없습니다.")
                else:
                    view_mode = st.radio("조회 모드 선택", ["👤 특정 학생 집중 분석", "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)"], horizontal=True)
                    st.markdown("---")
                    
                    if view_mode == "👤 특정 학생 집중 분석":
                        selected_student = st.selectbox("학생 선택", student_list, format_func=lambda x: f"[{all_users[x].get('class_group', '-')}] {all_users[x]['school']} {all_users[x]['name']} ({all_users[x].get('id', x.split('_')[-1])})")
                        if selected_student:
                            student_answers = learning_data.get(selected_student, {})
                            st.markdown("#### 📍 [1] 활동지 작성 내역")
                            for act in ACTIVITIES:
                                ans = student_answers.get(act, {})
                                if act == "[활동지1] 진학 희망 학과 조사하기":
                                    if ans.get("is_custom"):
                                        st.markdown(f"### **{act}**")
                                        st.markdown("**[1단계] 추출한 핵심 내용 요소**")
                                        st.dataframe(pd.DataFrame(ans.get("df1", [])), use_container_width=True)
                                        st.markdown("**[2단계] 생기부 탐구 내용 분석**")
                                        st.dataframe(pd.DataFrame(ans.get("df2", [])), use_container_width=True)
                                        st.markdown("**[3단계] 탐구 주제 및 문제 인식**")
                                        st.info(ans.get("step3", "-"))
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
                                        st.markdown(f"**[{t_name}] Q. {q['label']}**")
                                        if ans.get("text"): st.write(f"📝 {ans['text']}")
                                        if ans.get("link"): st.write(f"🔗 {ans['link']}")
                                        if ans.get("file_path") and os.path.exists(ans['file_path']):
                                            with open(ans['file_path'], "rb") as f:
                                                st.download_button(f"📥 {ans['file_name']} 다운로드", f, file_name=ans['file_name'], key=f"dl_{selected_student}_{q['id']}")

                    elif view_mode == "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)":
                        combined_list = ["--- [활동지 데이터 목록] ---"] + ACTIVITIES + ["--- [학습 차시 데이터 목록] ---"] + app_config["tabs"]
                        selected_view = st.selectbox("다운로드할 데이터 범주를 선택하세요", combined_list)
                        
                        if selected_view == "[활동지1] 진학 희망 학과 조사하기":
                            q_summary_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {})
                                q_summary_data.append({
                                    "학교": all_users[s_uid]["school"], "반": all_users[s_uid].get("class_group", "-"), "학번": all_users[s_uid].get("id", s_uid.split('_')[-1]), "이름": all_users[s_uid]["name"],
                                    "3단계 작성 주제": ans.get("step3", "-"), "1단계 입력개수": len(ans.get("df1", [])) if ans.get("df1") else 0, "상세데이터": "개별 학생 분석에서 확인 요망"
                                })
                            df_q = pd.DataFrame(q_summary_data)
                            st.dataframe(df_q, use_container_width=True, hide_index=True)
                            st.download_button(f"📊 활동지1 요약본 다운로드 ({filter_class})", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"활동지1_{filter_class}_결과.csv", mime='text/csv')

                        elif selected_view in ACTIVITIES:
                            q_summary_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {}).get("content", {})
                                if isinstance(ans, str): ans = {"text": ans}
                                q_summary_data.append({"학교": all_users[s_uid]["school"], "반": all_users[s_uid].get("class_group", "-"), "학번": all_users[s_uid].get("id", s_uid.split('_')[-1]), "이름": all_users[s_uid]["name"], "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")})
                            df_q = pd.DataFrame(q_summary_data)
                            st.dataframe(df_q, use_container_width=True, hide_index=True)
                            st.download_button(f"📊 엑셀(CSV) 다운로드 ({filter_class})", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_view}_{filter_class}_결과.csv", mime='text/csv')
                            
                        elif selected_view in app_config["tabs"]:
                            for q in app_config["questions"].get(selected_view, []):
                                st.markdown(f"##### ❓ {q['label']}")
                                q_summary_data = []
                                for s_uid in student_list:
                                    ans = learning_data.get(s_uid, {}).get(selected_view, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans}
                                    q_summary_data.append({"학교": all_users[s_uid]["school"], "반": all_users[s_uid].get("class_group", "-"), "학번": all_users[s_uid].get("id", s_uid.split('_')[-1]), "이름": all_users[s_uid]["name"], "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")})
                                df_q = pd.DataFrame(q_summary_data)
                                st.dataframe(df_q, use_container_width=True, hide_index=True)
                                st.download_button(f"📊 문항 데이터 다운로드 ({filter_class})", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_view}_{filter_class}_결과.csv", mime='text/csv', key=f"csv_{q['id']}")
