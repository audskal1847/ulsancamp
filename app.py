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
UPLOAD_DIR = "uploads" # 파일이 저장될 폴더명

# 시작 시 업로드 폴더 자동 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 활동지 목록 정의
ACTIVITIES = [
    "[활동지1] 진학 희망 학과 조사하기",
    "[활동지1] 진학 희망 학과 조사하기 (1)",
    "[활동지2] AI 활용 심화 주제 발굴: 탐구 주제 구체화 & 전략 수립",
    "[활동지2 예시] 모둠별 예시 8개",
    "[활동지3] 참고 자료 조사",
    "[활동지4] 주제 탐구 보고서 설계도",
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
        if admin_id not in users:
            users[admin_id] = {"password": "admin123", "name": f"관리자{i}", "role": "관리자", "school": "호계고등학교"}
            updated = True
    if updated: save_json(USERS_FILE, users)
    
    load_json(DATA_FILE, {})
    
    default_config = {
        "tabs": ["1일차_1차시", "2일차_1차시"],
        "pdfs": {"1일차_1차시": "session1_1.pdf", "2일차_1차시": "session2_1.pdf"},
        "questions": {
            "1일차_1차시": [{"id": "q1", "label": "탐구 주제 및 목차 설계 (텍스트, 파일, 링크 중 자유 제출)"}],
            "2일차_1차시": [{"id": "q1", "label": "보고서 초안 제출"}]
        }
    }
    load_json(CONFIG_FILE, default_config)

# PDF 임베드 출력 함수
def display_pdf(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="450" type="application/pdf"></iframe>', unsafe_allow_html=True)
    else:
        st.info(f"💡 교재 파일('{file_path}')이 없습니다.")

# --- [3] 복합 제출(텍스트/링크/파일) 폼 렌더링 함수 ---
def render_submission_form(username, category, q_id, q_label):
    data = load_json(DATA_FILE, {})
    ans = data.get(username, {}).get(category, {}).get(q_id, {})
    
    # 이전 버전(단순 텍스트)과의 호환성 유지
    if isinstance(ans, str): 
        ans = {"text": ans, "link": "", "file_name": "", "file_path": ""}
        
    with st.form(key=f"form_{username}_{category}_{q_id}"):
        st.markdown(f"**{q_label}**")
        st.caption("텍스트 입력, 외부 링크 주소, 파일 첨부 중 원하는 방식을 하나 이상 선택하여 제출하세요.")
        
        text_val = st.text_area("📝 텍스트 내용 작성", value=ans.get("text", ""), height=150)
        link_val = st.text_input("🔗 관련 링크(URL) 제출", value=ans.get("link", ""), placeholder="https://...")
        
        if ans.get("file_name"):
            st.info(f"📁 현재 등록된 파일: {ans.get('file_name')}")
            
        file_val = st.file_uploader("📂 첨부 파일 업로드 (새 파일을 올리면 기존 파일이 대체됩니다)")
        
        if st.form_submit_button("제출 및 저장하기"):
            if username not in data: data[username] = {}
            if category not in data[username]: data[username][category] = {}
            
            new_data = {
                "text": text_val,
                "link": link_val,
                "file_path": ans.get("file_path", ""),
                "file_name": ans.get("file_name", "")
            }
            
            # 새 파일이 업로드된 경우 로컬 폴더에 저장
            if file_val is not None:
                safe_filename = f"{username}_{category}_{q_id}_{file_val.name}".replace("/", "_").replace("\\", "_")
                file_path = os.path.join(UPLOAD_DIR, safe_filename)
                with open(file_path, "wb") as f:
                    f.write(file_val.getvalue())
                new_data["file_path"] = file_path
                new_data["file_name"] = file_val.name
                
            data[username][category][q_id] = new_data
            save_json(DATA_FILE, data)
            st.toast("💾 제출 자료가 성공적으로 저장되었습니다!")

# --- 캠프 종합 공지 렌더링 ---
def render_camp_overview():
    st.header("🎯 [학생-호계고-거점학교] 주제 탐구 캠프 (26-하계방학)")
    st.markdown("---")
    st.subheader("🔗 캠프 필수 링크 및 자료실")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("👥 모둠 구성 및 사전 설문"):
            st.markdown("- [호계고 모둠 구성 확인하기](#)")
        with st.expander("📝 활동지 링크 모음 (클릭 시 입력 화면으로 이동)"):
            st.caption("아래 버튼을 클릭하여 활동지를 작성하세요.")
            for act in ACTIVITIES:
                if st.button(f"📄 {act}", use_container_width=True):
                    st.session_state.current_page = act
                    st.rerun()

    with col2:
        with st.expander("📚 전공 가이드 및 교과 자료"):
            st.markdown("- [📁 대학 전공 가이드북 폴더 링크](#)")
        with st.expander("🔍 자료 탐색 추천 사이트"):
            st.markdown("- ▶ [검색 엔진](#)")

# --- [4] 메인 프로그램 세팅 및 사이드바 ---
st.set_page_config(page_title="주제 탐구 캠프 시스템", layout="wide")
init_system()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "메인"

st.sidebar.title("🔒 인증 센터")
if st.session_state.logged_in:
    u_info = st.session_state.user_info
    st.sidebar.success(f"🟢 {u_info['name']} 님 로그인 중")
    st.sidebar.write(f"🏫 소속: {u_info['school']} | 🛡️ {u_info['role']}")
    if st.sidebar.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False; st.session_state.user_info = None; st.session_state.current_page = "메인"; st.rerun()
else:
    auth_choice = st.sidebar.radio("원하는 작업을 선택하세요", ["회원가입", "로그인"])
    users = load_json(USERS_FILE, {})
    if auth_choice == "회원가입":
        st.sidebar.subheader("📝 회원가입")
        reg_role = st.sidebar.selectbox("자격 선택", ["학생", "교사", "관리자"])
        reg_id = st.sidebar.text_input("학번/ID 입력"); reg_name = st.sidebar.text_input("이름 입력"); reg_pw = st.sidebar.text_input("비밀번호", type="password")
        if st.sidebar.button("가입 신청", use_container_width=True):
            if reg_id and reg_pw and reg_name:
                if reg_id in users: st.sidebar.error("❌ 이미 존재하는 ID입니다.")
                else:
                    users[reg_id] = {"password": reg_pw, "name": reg_name, "role": reg_role, "school": "호계고등학교"}
                    save_json(USERS_FILE, users); st.sidebar.success("🎉 가입 완료! 로그인해주세요.")
    elif auth_choice == "로그인":
        input_id = st.sidebar.text_input("학번/ID"); input_pw = st.sidebar.text_input("비밀번호", type="password")
        if st.sidebar.button("로그인", use_container_width=True):
            if input_id in users and users[input_id]["password"] == input_pw:
                st.session_state.logged_in = True
                st.session_state.user_info = {"username": input_id, "name": users[input_id]["name"], "role": users[input_id]["role"], "school": users[input_id]["school"]}
                st.rerun()
            else: st.sidebar.error("❌ 정보가 틀렸습니다.")

# --- [5] 화면 분기 로직 ---
if not st.session_state.logged_in:
    st.title("🏫 주제 탐구 캠프 학습 시스템")
    st.info("왼쪽 사이드바를 이용해 로그인해주세요.")

else:
    current_role = st.session_state.user_info["role"]
    current_user = st.session_state.user_info["username"]
    app_config = load_json(CONFIG_FILE, {})
    learning_data = load_json(DATA_FILE, {})

    # [화면 A] 활동지 개별 입력 화면 (학생/관리자 공통)
    if st.session_state.current_page in ACTIVITIES:
        act_name = st.session_state.current_page
        st.title(f"📄 {act_name}")
        if st.button("⬅️ 메인 대시보드로 돌아가기"):
            st.session_state.current_page = "메인"; st.rerun()
        st.markdown("---")
        
        if current_role == "학생":
            render_submission_form(current_user, act_name, "content", "아래 입력란에 활동지 결과물을 제출하세요.")
        else:
            st.warning("교사/관리자는 제출 모니터링 탭을 이용해주세요.")

    # [화면 B] 메인 대시보드
    elif st.session_state.current_page == "메인":
        # --------- 학생 ---------
        if current_role == "학생":
            tabs_list = ["📌 캠프 공지 및 자료실"] + app_config["tabs"]
            tabs_objects = st.tabs(tabs_list)
            with tabs_objects[0]: render_camp_overview()
                
            for index, tab_name in enumerate(app_config["tabs"]):
                with tabs_objects[index + 1]:
                    st.subheader(f"📘 {tab_name} 활동 및 자료 제출")
                    display_pdf(app_config["pdfs"].get(tab_name, f"{tab_name}.pdf"))
                    st.markdown("---")
                    questions = app_config["questions"].get(tab_name, [])
                    for q in questions:
                        render_submission_form(current_user, tab_name, q["id"], q["label"])

        # --------- 관리자/교사 ---------
        elif current_role in ["교사", "관리자"]:
            st.title(f"🛠️ {current_role} 대시보드")
            menu_tabs = st.tabs(["👥 회원 관리", "🗂️ 차시 편집", "📥 학생 제출 자료 조회(다운로드)"]) if current_role == "관리자" else st.tabs(["👥 회원 관리", "📥 학생 제출 자료 조회(다운로드)"])
            
            with menu_tabs[0]:
                all_users = load_json(USERS_FILE, {})
                st.dataframe(pd.DataFrame([{"학번": uid, "이름": info["name"], "권한": info["role"]} for uid, info in all_users.items()]), use_container_width=True)
                
            if current_role == "관리자":
                with menu_tabs[1]:
                    st.info("차시 및 문항 동적 제어 기능 (이전 코드와 동일)")
                    # (차시 추가/삭제 생략 - 필요시 이전 코드 블럭 삽입)

            # 핵심 추가: 멀티미디어 조회 및 데이터 다운로드
            with menu_tabs[-1]:
                st.subheader("📥 학생 학습 활동 및 제출 자료 통합 조회")
                student_list = [uid for uid, info in all_users.items() if info["role"] == "학생"]
                
                if not student_list: st.info("가입된 학생이 없습니다.")
                else:
                    view_mode = st.radio("조회 모드 선택", ["👤 특정 학생 집중 분석", "📅 차시/활동지별 전체 현황 (엑셀 다운로드)"], horizontal=True)
                    st.markdown("---")
                    
                    # 모드 1: 특정 학생 조회 (첨부파일 개별 다운로드 지원)
                    if view_mode == "👤 특정 학생 집중 분석":
                        selected_student = st.selectbox("학생 선택", student_list, format_func=lambda x: f"{all_users[x]['name']} ({x})")
                        if selected_student:
                            st.markdown(f"### 📑 {all_users[selected_student]['name']} 학생의 제출 포트폴리오")
                            student_answers = learning_data.get(selected_student, {})
                            
                            st.markdown("#### 📍 [1] 차시별 질문 답변 및 첨부파일")
                            for t_name in app_config["tabs"]:
                                for q in app_config["questions"].get(t_name, []):
                                    ans = student_answers.get(t_name, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans} # 호환성 보정
                                    
                                    st.markdown(f"**[{t_name}] Q. {q['label']}**")
                                    if ans.get("text"): st.write(f"📝 텍스트: {ans['text']}")
                                    if ans.get("link"): st.write(f"🔗 링크: {ans['link']}")
                                    if ans.get("file_path") and os.path.exists(ans['file_path']):
                                        with open(ans['file_path'], "rb") as f:
                                            st.download_button(f"📥 {ans['file_name']} 파일 다운로드", f, file_name=ans['file_name'], key=f"dl_{selected_student}_{q['id']}")
                                    st.write("---")
                            
                            st.markdown("#### 📍 [2] 활동지 작성 내역")
                            for act in ACTIVITIES:
                                ans = student_answers.get(act, {}).get("content", {})
                                if isinstance(ans, str): ans = {"text": ans}
                                if ans.get("text") or ans.get("link") or ans.get("file_name"):
                                    st.markdown(f"**{act}**")
                                    if ans.get("text"): st.write(f"📝 {ans['text']}")
                                    if ans.get("link"): st.write(f"🔗 {ans['link']}")
                                    if ans.get("file_path") and os.path.exists(ans['file_path']):
                                        with open(ans['file_path'], "rb") as f:
                                            st.download_button("📥 첨부파일 다운로드", f, file_name=ans['file_name'], key=f"dl_{selected_student}_{act}")

                    # 모드 2: 전체 현황 모아보기 및 CSV 엑셀 다운로드
                    elif view_mode == "📅 차시/활동지별 전체 현황 (엑셀 다운로드)":
                        combined_list = ["--- [활동지 데이터 목록] ---"] + ACTIVITIES + ["--- [학습 차시 데이터 목록] ---"] + app_config["tabs"]
                        selected_view = st.selectbox("다운로드할 데이터 범주를 선택하세요", combined_list)
                        
                        if selected_view in ACTIVITIES:
                            q_summary_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {}).get("content", {})
                                if isinstance(ans, str): ans = {"text": ans}
                                q_summary_data.append({
                                    "학번": s_uid, "이름": all_users[s_uid]["name"],
                                    "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")
                                })
                            
                            df_q = pd.DataFrame(q_summary_data)
                            st.dataframe(df_q, use_container_width=True, hide_index=True)
                            
                            # CSV 데이터 다운로드 버튼
                            csv = df_q.to_csv(index=False).encode('utf-8-sig') # 한글 깨짐 방지용 utf-8-sig
                            st.download_button(f"📊 {selected_view} 엑셀(CSV) 데이터 전체 다운로드", data=csv, file_name=f"{selected_view}_결과.csv", mime='text/csv')
                            
                        elif selected_view in app_config["tabs"]:
                            for q in app_config["questions"].get(selected_view, []):
                                st.markdown(f"##### ❓ {q['label']}")
                                q_summary_data = []
                                for s_uid in student_list:
                                    ans = learning_data.get(s_uid, {}).get(selected_view, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans}
                                    q_summary_data.append({
                                        "학번": s_uid, "이름": all_users[s_uid]["name"],
                                        "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")
                                    })
                                
                                df_q = pd.DataFrame(q_summary_data)
                                st.dataframe(df_q, use_container_width=True, hide_index=True)
                                csv = df_q.to_csv(index=False).encode('utf-8-sig')
                                st.download_button(f"📊 문항 데이터 다운로드", data=csv, file_name=f"{selected_view}_문항_결과.csv", mime='text/csv', key=f"csv_{q['id']}")