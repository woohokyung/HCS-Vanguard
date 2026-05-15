import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="HCS 뱅가드 통합 대시보드", page_icon="🏆", layout="wide")

st.title("🏆 HCS 뱅가드 선발제 계산 시스템")

# --- 2. 사이드바: 데이터 소스 선택 ---
st.sidebar.header("📁 데이터 불러오기")
data_source = st.sidebar.radio("데이터 소스를 선택하세요:", ["구글 시트 주소 입력", "파일 직접 업로드(CSV/Excel)"])

df = pd.DataFrame() # 빈 데이터프레임 초기화

if data_source == "구글 시트 주소 입력":
    sheet_url_input = st.sidebar.text_input("구글 시트 공유 URL을 붙여넣으세요:", placeholder="https://docs.google.com/...")
    if sheet_url_input:
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(spreadsheet=sheet_url_input, ttl="1m")
            st.sidebar.success("✅ 시트 연결 성공!")
        except Exception as e:
            st.sidebar.error(f"❌ 시트 연결 실패: {e}")
    else:
        st.info("왼쪽 사이드바에 구글 시트 링크를 넣어주세요.")

else:
    uploaded_file = st.sidebar.file_uploader("엑셀이나 CSV 파일을 선택하세요", type=["csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            st.sidebar.success("✅ 파일 업로드 성공!")
        except Exception as e:
            st.sidebar.error(f"❌ 파일 읽기 실패: {e}")

# --- 3. 메인 로직 (데이터가 있을 때만 실행) ---
if not df.empty:
    # 컬럼 매핑 로직 (구글 폼 형식에 맞춤)
    form_mapping = {"팀명": "팀명", "선봉": "멤버1", "중견": "멤버2", "대장": "멤버3"}
    df = df.rename(columns=form_mapping)

    # 기본 컬럼 추가
    for col in ['승', '패']:
        if col not in df.columns: df[col] = 0
    if '기권' not in df.columns: df['기권'] = False

    # 선발 룰 설정
    st.sidebar.divider()
    st.sidebar.header("⚙️ 선발 조건")
    base_win = st.sidebar.number_input("🥇 기준 그룹 승수", value=3)
    target_win = st.sidebar.number_input("🥈 대상 그룹 승수", value=2)
    pick_count = st.sidebar.number_input("🎯 선발 팀 수", value=2)

    # 데이터 입력 및 수정
    st.subheader("📊 대회 데이터 관리")
    display_df = df[['팀명', '멤버1', '멤버2', '멤버3', '승', '패', '기권']].rename(
        columns={"멤버1": "선봉", "멤버2": "중견", "멤버3": "대장"}
    )
    
    edited_df = st.data_editor(display_df, use_container_width=True)

    # 계산 버튼
    if st.button("🚀 결과 계산하기", type="primary"):
        active_df = edited_df[~edited_df['기권']]
        
        # 기준 그룹 멤버
        base_df = active_df[active_df['승'] >= base_win]
        base_members = set()
        for _, row in base_df.iterrows():
            base_members.update([str(row['선봉']), str(row['중견']), str(row['대장'])])
            
        # 대상 그룹 분석
        target_df = active_df[active_df['승'] == target_win]
        results = []
        for _, row in target_df.iterrows():
            team_deck = [str(row['선봉']), str(row['중견']), str(row['대장'])]
            unique_deck = [m for m in team_deck if m not in base_members]
            results.append({
                "팀명": row['팀명'], "승패": f"{row['승']}승 {row['패']}패",
                "고유수": len(unique_deck), "Rogue": ", ".join(unique_deck)
            })

        # 결과 출력
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.write(f"### 🥇 기준 ({base_win}승+)")
            st.dataframe(base_df[['팀명', '승']], hide_index=True)
        with res_col2:
            st.write(f"### 🥈 순위 ({target_win}승)")
            if results:
                res_df = pd.DataFrame(results).sort_values(by="고유수", ascending=False)
                st.dataframe(res_df, hide_index=True)
            else:
                st.write("대상 없음")
else:
    st.warning("데이터를 먼저 입력해주세요. (왼쪽 사이드바 이용)")