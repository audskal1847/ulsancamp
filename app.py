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

# 관리자 4명의 계정을 절대값으로 지정
ADMIN_ACCOUNTS = {
    "admin1": "admin11",
    "admin2": "admin22",
    "admin3": "admin33",
    "admin4": "admin44"
}

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

# --- [3-B] 활동지1 전용 맞춤형 폼 ---
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
        
        default_df2 = pd.DataFrame({
            "구분": ["✏️ 나의 탐구 키워드", "창체활동", "교과세특"],
            "키워드1": ["", "", ""], "키워드2": ["", "", ""], "키워드3": ["", "", ""], "키워드4": ["", "", ""], "키워드5": ["", "", ""]
        })
        df2 = pd.DataFrame(ans.get("df2", default_df2.to_dict('records')))
        edited_df2 = st.data_editor(df2, use_container_width=True, key="act1_df2")
        
        st.markdown("<br>#### [2단계-예시]", unsafe_allow_html=True)
        example_image = os.path.join(os.path.dirname(__file__), "example.png")
        if os.path.exists(example_image):
            st.image(example_image, caption="희망 전공 분야 카운팅 표 사례 (고려대 전기전자공학부 등)를 참고하여 위 표의 칸을 채워보세요.", use_container_width=True)
        else:
            st.info("💡 [2단계-예시] 희망 전공 분야 카운팅 표 사례 (고려대 전기전자공학부 등)를 참고하여 위 표의 칸을 채워보세요.")
            
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
        st.sidebar.write(f"🏫 소속: {u_info.get('school', '소속없음')} ({display_class})")
    else:
        st.sidebar.write(f"🏫 소속: {u_info.get('school', '소속없음')}")
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
            reg_school = "교사소속"
            reg_class = "교사"
            
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
        
        if login_type == "학생":
            login_school = st.sidebar.text_input("소속 학교", value="호계고등학교")
        else:
            login_school = ""
            
        input_id = st.sidebar.text_input("학번/ID")
        input_pw = st.sidebar.text_input("비밀번호", type="password")
        
        if st.sidebar.button("로그인", use_container_width=True):
            if input_id in ADMIN_ACCOUNTS and input_pw == ADMIN_ACCOUNTS[input_id]:
                st.session_state.logged_in = True
                st.session_state.user_info = {
                    "user_key": input_id, "username": input_id, 
                    "name": f"총괄운영자({input_id})", "role": "관리자", 
                    "school": "운영본부", "class_group": "관리자"
                }
                st.rerun()
            else:
                user_key = f"{login_school}_{input_id}" if login_type == "학생" else f"teacher_{input_id}"
                
                if user_key in users and users[user_key].get("password") == input_pw:
                    if users[user_key].get("role") == login_type:
                        st.session_state.logged_in = True
                        st.session_state.user_info = {
                            "user_key": user_key, "username": users[user_key].get("id", input_id), 
                            "name": users[user_key].get("name", "이름없음"), "role": users[user_key].get("role", login_type), 
                            "school": users[user_key].get("school", "소속없음"), "class_group": users[user_key].get("class_group", "미배정")
                        }
                        st.rerun()
                    else:
                        st.sidebar.error("❌ 가입하신 계정 유형(학생/교사)이 다릅니다.")
                else: 
                    st.sidebar.error("❌ 학교, 학번/ID 또는 비밀번호가 틀렸습니다.")

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
            if current_role == "관리자":
                menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "🗂️ 차시 및 자료 편집", "📥 학생 제출 자료 조회 및 관리"])
            else:
                menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "📥 학생 제출 자료 조회 및 관리"])
            
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
                                del all_users[delete_target]
                                save_json(USERS_FILE, all_users); st.success("삭제 완료"); st.rerun()

                    with col2:
                        st.write("🔑 **학생/교사 비밀번호 강제 변경**")
                        pw_target = st.selectbox("비밀번호를 변경할 회원을 선택하세요", ["선택"] + editable_users, format_func=lambda x: x if x == "선택" else f"[{all_users[x].get('school', '소속없음')}] {all_users[x].get('name', '이름없음')} ({all_users[x].get('id', x.split('_')[-1])})")
                        new_pw = st.text_input("새로운 비밀번호 입력", type="password")
                        if pw_target != "선택":
                            if st.button("비밀번호 변경 적용") and new_pw:
                                all_users[pw_target]["password"] = new_pw
                                save_json(USERS_FILE, all_users); st.success("비밀번호 성공적으로 변경"); st.rerun()

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
                                if mat_type == "외부 링크 (Notion, Google Docs 등)":
                                    new_mat["type"] = "link"
                                    new_mat["content"] = mat_link
                                else:
                                    if mat_file is not None:
                                        safe_filename = mat_file.name.replace("/", "_").replace("\\", "_")
                                        file_path = os.path.join(UPLOAD_DIR, f"lecture_{safe_filename}")
                                        with open(file_path, "wb") as f: f.write(mat_file.getvalue())
                                        new_mat["type"] = "file"; new_mat["content"] = file_path; new_mat["filename"] = mat_file.name
                                    else:
                                        st.error("파일을 선택해주세요."); st.stop()
                                app_config["materials"].append(new_mat)
                                save_json(CONFIG_FILE, app_config); st.success("등록 완료!"); st.rerun()

                    current_materials = app_config.get("materials", [])
                    if current_materials:
                        st.write("🗑️ **등록된 강의 자료 삭제**")
                        del_mat_target = st.selectbox("삭제할 자료를 선택하세요", options=current_materials, format_func=lambda x: x.get("title", "제목없음"))
                        if st.button("선택한 자료 삭제하기"):
                            app_config["materials"].remove(del_mat_target)
                            save_json(CONFIG_FILE, app_config); st.success("삭제 완료!"); st.rerun()
                    
                    st.markdown("---")
                    st.subheader("⚙️ 차시(Tab) 동적 제어 (5차시 이상 무한 생성 가능)")
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
                                app_config["questions"][target_q_tab] = current_qs
                                save_json(CONFIG_FILE, app_config); st.success("문항 추가 완료."); st.rerun()
                        with q_col2:
                            if current_qs:
                                del_q_target = st.selectbox("삭제할 문항을 고르세요", options=current_qs, format_func=lambda x: x.get("label", ""))
                                if st.button("선택한 문항 삭제", type="primary"):
                                    current_qs.remove(del_q_target); app_config["questions"][target_q_tab] = current_qs
                                    save_json(CONFIG_FILE, app_config); st.success("삭제 완료."); st.rerun()

            with menu_tabs[-1]:
                st.subheader("📥 반별 학생 학습 활동 및 제출 자료 조회")
                all_users = load_json(USERS_FILE, {})
                filter_class = st.radio("조회할 반 선택", ["전체 보기"] + CLASS_GROUPS, horizontal=True)
                
                student_list = []
                for uid, info in all_users.items():
                    if info.get("role") == "학생":
                        s_class = info.get("class_group", "미배정")
                        if filter_class == "전체 보기" or filter_class == s_class:
                            student_list.append(uid)
                
                if not student_list: st.info(f"선택하신 조건({filter_class})에 해당하는 가입 학생이 없습니다.")
                else:
                    view_mode = st.radio("조회 모드 선택", ["👤 특정 학생 집중 분석", "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)"], horizontal=True)
                    st.markdown("---")
                    
                    if view_mode == "👤 특정 학생 집중 분석":
                        selected_student = st.selectbox("학생 선택", student_list, format_func=lambda x: f"[{all_users[x].get('class_group', '-')}] {all_users[x].get('school', '-')} {all_users[x].get('name', '이름없음')} ({all_users[x].get('id', x.split('_')[-1])})")
                        if selected_student:
                            student_answers = learning_data.get(selected_student, {})
                            
                            # 💡 [핵심 추가 2] 특정 학생 전체 포트폴리오 텍스트 추출 및 다운로드 버튼 생성
                            report_content = f"[{all_users[selected_student].get('school', '')}] {all_users[selected_student].get('class_group', '')} {all_users[selected_student].get('name', '')} ({all_users[selected_student].get('id', '')}) 학습 포트폴리오\n\n"
                            report_content += "==== [1] 활동지 작성 내역 ====\n\n"
                            
                            for act in ACTIVITIES:
                                ans = student_answers.get(act, {})
                                if act == "[활동지1] 진학 희망 학과 조사하기":
                                    if ans.get("is_custom"):
                                        report_content += f"▶ {act}\n[1단계] 추출한 핵심 내용 요소\n"
                                        for row in ans.get("df1", []):
                                            report_content += f" - {row.get('학과/전공명', '')} : {row.get('핵심 내용 요소', '')}\n"
                                        report_content += "\n[2단계] 생기부 탐구 내용 분석\n"
                                        for row in ans.get("df2", []):
                                            report_content += f" - {row.get('구분', '')} | {row.get('키워드1','')} | {row.get('키워드2','')} | {row.get('키워드3','')} | {row.get('키워드4','')} | {row.get('키워드5','')}\n"
                                        report_content += f"\n[3단계] 탐구 주제 및 문제 인식\n{ans.get('step3', '')}\n\n"
                                    continue
                                ans_content = ans.get("content", {})
                                if isinstance(ans_content, str): ans_content = {"text": ans_content}
                                if ans_content.get("text") or ans_content.get("link"):
                                    report_content += f"▶ {act}\n"
                                    if ans_content.get("text"): report_content += f"📝 텍스트: {ans_content['text']}\n"
                                    if ans_content.get("link"): report_content += f"🔗 링크: {ans_content['link']}\n"
                                    report_content += "\n"
                            
                            report_content += "==== [2] 차시별 제출 자료 ====\n\n"
                            for t_name in app_config["tabs"]:
                                for q in app_config["questions"].get(t_name, []):
                                    ans = student_answers.get(t_name, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans} 
                                    if ans.get("text") or ans.get("link"):
                                        report_content += f"▶ [{t_name}] {q.get('label', '')}\n"
                                        if ans.get("text"): report_content += f"📝 텍스트: {ans['text']}\n"
                                        if ans.get("link"): report_content += f"🔗 링크: {ans['link']}\n"
                                        report_content += "\n"
                                        
                            st.download_button(
                                label=f"📄 {all_users[selected_student].get('name', '학생')}의 전체 활동 데이터 텍스트(.txt) 파일로 다운로드",
                                data=report_content,
                                file_name=f"{all_users[selected_student].get('name', '학생')}_학습포트폴리오.txt",
                                mime="text/plain",
                                type="primary"
                            )
                            st.markdown("---")
                            
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
                                        st.markdown(f"**[{t_name}] Q. {q.get('label', '')}**")
                                        if ans.get("text"): st.write(f"📝 {ans['text']}")
                                        if ans.get("link"): st.write(f"🔗 {ans['link']}")
                                        if ans.get("file_path") and os.path.exists(ans['file_path']):
                                            with open(ans['file_path'], "rb") as f:
                                                st.download_button(f"📥 {ans['file_name']} 다운로드", f, file_name=ans['file_name'], key=f"dl_{selected_student}_{q['id']}")

                    elif view_mode == "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)":
                        combined_list = ["--- [활동지 데이터 목록] ---"] + ACTIVITIES + ["--- [학습 차시 데이터 목록] ---"] + app_config["tabs"]
                        selected_view = st.selectbox("다운로드할 데이터 범주를 선택하세요", combined_list)
                        
                        # 💡 [핵심 추가 1] 활동지1의 표 데이터를 모두 Flatten(가로로 전개) 처리하여 출력
                        if selected_view == "[활동지1] 진학 희망 학과 조사하기":
                            q_summary_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {})
                                df1_data = ans.get("df1", [])
                                df2_data = ans.get("df2", [])
                                
                                row_data = {
                                    "학교": all_users[s_uid].get("school", "-"), "반": all_users[s_uid].get("class_group", "-"),
                                    "학번": all_users[s_uid].get("id", s_uid.split('_')[-1]), "이름": all_users[s_uid].get("name", "")
                                }
                                
                                # 1단계(df1) 데이터 전개 (4줄)
                                for i in range(4):
                                    if i < len(df1_data):
                                        row_data[f"[1단계] 전공명{i+1}"] = df1_data[i].get("학과/전공명", "")
                                        row_data[f"[1단계] 핵심요소{i+1}"] = df1_data[i].get("핵심 내용 요소", "")
                                    else:
                                        row_data[f"[1단계] 전공명{i+1}"] = ""
                                        row_data[f"[1단계] 핵심요소{i+1}"] = ""
                                        
                                # 2단계(df2) 데이터 전개 (탐구키워드, 창체, 세특)
                                labels = ["탐구키워드", "창체활동", "교과세특"]
                                for i, label in enumerate(labels):
                                    if i < len(df2_data):
                                        for k in range(1, 6):
                                            row_data[f"[2단계] {label}_{k}"] = df2_data[i].get(f"키워드{k}", "")
                                    else:
                                        for k in range(1, 6):
                                            row_data[f"[2단계] {label}_{k}"] = ""
                                            
                                # 3단계 텍스트 추가
                                row_data["[3단계] 탐구주제"] = ans.get("step3", "")
                                q_summary_data.append(row_data)
                                
                            df_q = pd.DataFrame(q_summary_data)
                            st.dataframe(df_q, use_container_width=True, hide_index=True)
                            st.download_button(f"📊 활동지1 상세 데이터 엑셀 다운로드 ({filter_class})", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"활동지1_상세_{filter_class}_결과.csv", mime='text/csv')

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
