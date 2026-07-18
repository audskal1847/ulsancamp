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

# 활동지 목록 정의
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
        },
        "materials": [] # 교사용 강의 자료(PPT, 링크 등) 저장 공간
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

# --- [3] 복합 제출 폼 렌더링 함수 ---
def render_submission_form(username, category, q_id, q_label):
    data = load_json(DATA_FILE, {})
    ans = data.get(username, {}).get(category, {}).get(q_id, {})
    
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
            new_data = {"text": text_val, "link": link_val, "file_path": ans.get("file_path", ""), "file_name": ans.get("file_name", "")}
            
            if file_val is not None:
                safe_filename = f"{username}_{category}_{q_id}_{file_val.name}".replace("/", "_").replace("\\", "_")
                file_path = os.path.join(UPLOAD_DIR, safe_filename)
                with open(file_path, "wb") as f: f.write(file_val.getvalue())
                new_data["file_path"] = file_path; new_data["file_name"] = file_val.name
                
            data[username][category][q_id] = new_data
            save_json(DATA_FILE, data)
            st.toast("💾 제출 자료가 성공적으로 저장되었습니다!")

# --- 캠프 종합 공지 렌더링 (권한별 다운로드 제한 포함) ---
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
    
    # 강사용 PPT 및 링크 자료실 표시 영역 (학생 다운로드 제한 처리)
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
        with st.expander("👥 호계고 모둠 구성 및 사전 안내"):
            st.markdown("[🔗 호계고 모둠 구성 확인하기 (구글 문서)](#)")
            st.markdown("[🔗 호계고 캠프 사전 안내 노션 사이트](https://app.notion.com/p/26-3a1b5d2009278095b09cd44692be6056?pvs=11)")

        with st.expander("📝 활동지 링크 (클릭 시 제출 화면으로 이동)"):
            st.caption("아래 버튼을 누르면 해당 활동지 제출 양식으로 화면이 전환됩니다.")
            for act in ACTIVITIES:
                if st.button(f"📄 {act}", use_container_width=True):
                    st.session_state.current_page = act
                    st.rerun()
            st.markdown("---")
            st.markdown("[🔗 [참고] 사전 설문 조사 (구글 폼)](#)")
            
    with col2:
        with st.expander("📚 대학 전공 가이드북 링크"):
            st.markdown("[📁 대학 전공 가이드북 구글 드라이브 폴더 열기](#)")

        with st.expander("🔍 교과 키워드 추출 링크"):
            st.markdown("- 📗 `[고3] 2015 선택과목 안내서.pdf` (49.1 MiB)\n- 📘 `[고1,2] 2022 선택과목 안내서.pdf` (21.8 MiB)")

        with st.expander("🌐 자료 탐색 사이트 목록"):
            st.markdown("- ▶ 검색 엔진\n- ▶ 대학 웹사이트 (연구 소개)\n- ▶ 논문 사이트\n- ▶ 포털\n- ▶ 분야별 간행지\n- ▶ 영상 자료")

        with st.expander("📁 차시별 강의 pdf"):
            st.markdown("[🔗 차시별 강의 PDF 드라이브 모음 열기](#)")

        with st.expander("📊 만족도 조사 설문 링크 (QR 포함)", expanded=True):
            st.markdown("[🔗 캠프 만족도 조사 참여하기 (Google Forms)](https://forms.gle/kqjWnsTE65Jf8QCS6)")
            qr_image = "image_e1cca7.png"
            if os.path.exists(qr_image):
                st.image(qr_image, caption="스마트폰 카메라로 스캔하여 만족도 조사에 참여해주세요.", width=300)
            else:
                st.info(f"💡 현재 폴더에 '{qr_image}' 파일이 없습니다. 폴더에 이미지를 넣으면 QR코드가 나타납니다.")

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
        
        # [수정됨] 회원가입 폼 순서 완벽 조정 (자격 - 학교 - 학번 - 이름 - 비번)
        reg_role = st.sidebar.selectbox("유형", ["학생", "교사", "관리자"])
        reg_school = st.sidebar.text_input("소속 학교")
        reg_id = st.sidebar.text_input("학번")
        reg_name = st.sidebar.text_input("이름")
        reg_pw = st.sidebar.text_input("비밀번호", type="password")
        
        if st.sidebar.button("가입 신청", use_container_width=True):
            if reg_role and reg_school and reg_id and reg_pw and reg_name:
                if reg_id in users: st.sidebar.error("❌ 이미 존재하는 ID입니다.")
                else:
                    users[reg_id] = {"password": reg_pw, "name": reg_name, "role": reg_role, "school": reg_school}
                    save_json(USERS_FILE, users); st.sidebar.success("🎉 가입 완료! 로그인해주세요.")
            else:
                st.sidebar.warning("⚠️ 모든 빈칸을 빠짐없이 입력해주세요.")
                
    elif auth_choice == "로그인":
        input_id = st.sidebar.text_input("학번"); input_pw = st.sidebar.text_input("비밀번호", type="password")
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

    if st.session_state.current_page in ACTIVITIES:
        act_name = st.session_state.current_page
        st.title(f"📄 {act_name}")
        if st.button("⬅️ 메인 화면으로 돌아가기"):
            st.session_state.current_page = "메인"; st.rerun()
        st.markdown("---")
        if current_role == "학생": render_submission_form(current_user, act_name, "content", "아래 입력란에 활동지 결과물을 제출하세요.")
        else: st.warning("교사/관리자는 제출 모니터링 탭을 이용해주세요.")

    elif st.session_state.current_page == "메인":
        # --------- 학생 ---------
        if current_role == "학생":
            tabs_list = ["📌 캠프 공지 및 자료실"] + app_config["tabs"]
            tabs_objects = st.tabs(tabs_list)
            
            with tabs_objects[0]: 
                render_camp_overview(current_role) # 현재 권한 전달 (학생)
                
            for index, tab_name in enumerate(app_config["tabs"]):
                with tabs_objects[index + 1]:
                    st.subheader(f"📘 {tab_name} 활동 및 자료 제출")
                    display_pdf(app_config["pdfs"].get(tab_name, f"{tab_name}.pdf"))
                    st.markdown("---")
                    questions = app_config["questions"].get(tab_name, [])
                    for q in questions: render_submission_form(current_user, tab_name, q["id"], q["label"])

        # --------- 관리자/교사 ---------
        elif current_role in ["교사", "관리자"]:
            st.title(f"🛠️ {current_role} 대시보드")
            if current_role == "관리자":
                menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "🗂️ 차시 및 자료 편집", "📥 학생 제출 자료 조회(다운로드)"])
            else:
                menu_tabs = st.tabs(["📌 캠프 공지(미리보기)", "👥 회원 관리", "📥 학생 제출 자료 조회(다운로드)"])
            
            with menu_tabs[0]:
                st.info("학생들의 첫 화면(첫 번째 탭)으로 표시되는 메인 대시보드입니다.")
                render_camp_overview(current_role) # 현재 권한 전달 (관리자/교사)

            with menu_tabs[1]:
                all_users = load_json(USERS_FILE, {})
                st.dataframe(pd.DataFrame([{"학번": uid, "이름": info["name"], "권한": info["role"], "학교": info["school"]} for uid, info in all_users.items()]), use_container_width=True)
                if current_role == "관리자":
                    st.markdown("---")
                    delete_target = st.selectbox("삭제할 사용자의 학번/ID를 선택하세요", ["선택"] + list(all_users.keys()))
                    if delete_target != "선택" and not delete_target.startswith("admin"):
                        if st.button(f"⚠️ {delete_target} 계정 영구 삭제", type="primary"):
                            del all_users[delete_target]
                            save_json(USERS_FILE, all_users); st.success(f"{delete_target} 삭제 완료"); st.rerun()

            if current_role == "관리자":
                with menu_tabs[2]:
                    # 강의 자료 업로드 기능
                    st.subheader("👨‍🏫 교사용 특강 자료 업로드 (PPT, PDF, 외부 링크)")
                    with st.form("upload_lecture_material"):
                        mat_title = st.text_input("자료 제목 (예: 1일차 오리엔테이션 PPT)")
                        mat_type = st.radio("자료 유형 선택", ["파일 업로드 (PPT, PDF 등)", "외부 링크 (Notion, Google Docs 등)"])
                        mat_link = st.text_input("외부 링크인 경우 URL을 입력하세요", placeholder="https://...")
                        mat_file = st.file_uploader("파일인 경우 이곳에 업로드하세요")
                        
                        if st.form_submit_button("자료 등록하여 공지사항에 올리기"):
                            if not mat_title:
                                st.error("자료 제목을 입력해주세요.")
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
                                        new_mat["type"] = "file"
                                        new_mat["content"] = file_path
                                        new_mat["filename"] = mat_file.name
                                    else:
                                        st.error("파일을 선택해주세요."); st.stop()
                                
                                app_config["materials"].append(new_mat)
                                save_json(CONFIG_FILE, app_config)
                                st.success("성공적으로 등록되었습니다! 메인 화면의 '특강 및 강의 자료실'에 표시됩니다.")
                                st.rerun()

                    current_materials = app_config.get("materials", [])
                    if current_materials:
                        st.write("🗑️ **등록된 강의 자료 삭제**")
                        del_mat_target = st.selectbox("삭제할 자료를 선택하세요", options=current_materials, format_func=lambda x: x["title"])
                        if st.button("선택한 자료 삭제하기"):
                            app_config["materials"].remove(del_mat_target)
                            save_json(CONFIG_FILE, app_config); st.success("삭제 완료!"); st.rerun()
                    
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
                            else: st.error("입력값이 올바르지 않거나 중복입니다.")
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
                        for q in current_qs: st.text(f" - [{q['id']}] {q['label']}")
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
                                del_q_target = st.selectbox("삭제할 문항을 고르세요", options=current_qs, format_func=lambda x: x["label"])
                                if st.button("선택한 문항 삭제", type="primary"):
                                    current_qs.remove(del_q_target); app_config["questions"][target_q_tab] = current_qs
                                    save_json(CONFIG_FILE, app_config); st.success("삭제 완료."); st.rerun()

            with menu_tabs[-1]:
                st.subheader("📥 학생 학습 활동 및 제출 자료 통합 조회")
                student_list = [uid for uid, info in all_users.items() if info["role"] == "학생"]
                if not student_list: st.info("가입된 학생이 없습니다.")
                else:
                    view_mode = st.radio("조회 모드 선택", ["👤 특정 학생 집중 분석", "📅 항목별(활동지/차시) 전체 현황 (엑셀 다운로드)"], horizontal=True)
                    st.markdown("---")
                    
                    if view_mode == "👤 특정 학생 집중 분석":
                        selected_student = st.selectbox("학생 선택", student_list, format_func=lambda x: f"{all_users[x]['name']} ({x})")
                        if selected_student:
                            student_answers = learning_data.get(selected_student, {})
                            st.markdown("#### 📍 [1] 활동지 작성 내역")
                            for act in ACTIVITIES:
                                ans = student_answers.get(act, {})
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
                        
                        if selected_view in ACTIVITIES:
                            q_summary_data = []
                            for s_uid in student_list:
                                ans = learning_data.get(s_uid, {}).get(selected_view, {}).get("content", {})
                                if isinstance(ans, str): ans = {"text": ans}
                                q_summary_data.append({"학번": s_uid, "이름": all_users[s_uid]["name"], "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")})
                            df_q = pd.DataFrame(q_summary_data)
                            st.dataframe(df_q, use_container_width=True, hide_index=True)
                            st.download_button("📊 엑셀(CSV) 다운로드", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_view}_결과.csv", mime='text/csv')
                            
                        elif selected_view in app_config["tabs"]:
                            for q in app_config["questions"].get(selected_view, []):
                                st.markdown(f"##### ❓ {q['label']}")
                                q_summary_data = []
                                for s_uid in student_list:
                                    ans = learning_data.get(s_uid, {}).get(selected_view, {}).get(q["id"], {})
                                    if isinstance(ans, str): ans = {"text": ans}
                                    q_summary_data.append({"학번": s_uid, "이름": all_users[s_uid]["name"], "입력 텍스트": ans.get("text", "-"), "제출 링크": ans.get("link", "-"), "첨부 파일명": ans.get("file_name", "-")})
                                df_q = pd.DataFrame(q_summary_data)
                                st.dataframe(df_q, use_container_width=True, hide_index=True)
                                st.download_button("📊 문항 데이터 다운로드", data=df_q.to_csv(index=False).encode('utf-8-sig'), file_name=f"{selected_view}_문항_결과.csv", mime='text/csv', key=f"csv_{q['id']}")
