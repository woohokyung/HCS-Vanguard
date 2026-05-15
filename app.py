import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="HCS 뱅가드 선발제 시스템", page_icon="🏆", layout="wide")

st.title("🏆 HCS 뱅가드 선발제 계산 프로그램 (구글 폼 연동형)")
st.markdown("""
구글 폼 응답 시트에서 데이터를 실시간으로 불러옵니다. 
**승/패/기권** 정보를 입력한 뒤 하단의 계산 버튼을 눌러주세요.
""")

# --- 2. 구글 시트 연결 설정 ---
# TODO: 구글 폼 응답이 쌓이는 스프레드시트의 공유 URL을 넣으세요.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uG3yvzqbjayYZUXXSwPG04m11SbYSIyWJ1mIAkvi_Ug/edit?resourcekey=&gid=1473131751#gid=1473131751"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 데이터 읽기 (1분마다 새로고침)
    raw_df = conn.read(spreadsheet=SHEET_URL, ttl="1m")
    
    
    if not raw_df.empty:
        # 구글 폼 시트의 컬럼을 프로그램에 맞게 자동 연결 (매핑)
        form_mapping = {
            "팀명": "팀명",
            "선봉": "멤버1",
            "중견": "멤버2",
            "대장": "멤버3"
        }
        
        raw_df = raw_df.rename(columns=form_mapping)
        
        # 승, 패, 기권 컬럼이 없다면 생성
        if '승' not in raw_df.columns: raw_df['승'] = 0
        if '패' not in raw_df.columns: raw_df['패'] = 0
        if '기권' not in raw_df.columns: raw_df['기권'] = False
        
        # 화면에 표시할 필수 컬럼만 추출
        target_cols = ['팀명', '멤버1', '멤버2', '멤버3', '승', '패', '기권']
        available_cols = [c for c in target_cols if c in raw_df.columns]
        df = raw_df[available_cols]
        
    else:
        st.error("시트가 비어있거나 데이터를 가져올 수 없습니다.")
        st.stop()
except Exception as e:
    st.error(f"시트 연결 중 오류 발생: {e}")
    st.info("구글 시트 URL이 올바른지, '링크가 있는 모든 사용자(뷰어)' 권한이 있는지 확인하세요.")
    st.stop()

# --- 3. 선발 룰 설정 ---
st.sidebar.header("⚙️ 선발 조건 설정")
base_win = st.sidebar.number_input("🥇 라이드라인 선발 그룹 승수", min_value=1, max_value=10, value=3)
target_win = st.sidebar.number_input("🥈 선발제 대상 그룹 승수", min_value=0, max_value=10, value=2)
pick_count = st.sidebar.number_input("🎯 선발할 팀 수 (TOP N)", min_value=1, max_value=10, value=2)

# --- 4. 데이터 입력 섹션 ---
st.subheader("📊 대회 결과 입력")
st.caption("구글 폼 참가자 명단을 바탕으로 최종 승패를 기록하세요.")

# 사용자가 입력하기 편하게 컬럼 이름을 다시 예쁘게 보여줍니다.
display_df = df.rename(columns={"멤버1": "선봉", "멤버2": "중견", "멤버3": "대장"})

edited_df = st.data_editor(
    display_df, 
    use_container_width=True, 
    num_rows="fixed",
    column_config={
        "승": st.column_config.NumberColumn("승리", min_value=0, step=1),
        "패": st.column_config.NumberColumn("패배", min_value=0, step=1),
        "기권": st.column_config.CheckboxColumn("기권 여부")
    }
)

# --- 5. 계산 로직 ---
st.divider()
if st.button("🚀 최종 선발팀 계산하기", type="primary"):
    
    # 필수 컬럼 확인
    if not all(col in edited_df.columns for col in ['선봉', '중견', '대장']):
        st.error("⚠️ 구글 시트에서 '선봉', '중견', '대장' 컬럼을 찾을 수 없습니다.")
        st.stop()
        
    # 기권 팀 제외
    active_df = edited_df[~edited_df['기권']]
    
    # 1. 기준 그룹 멤버 수집
    base_df = active_df[active_df['승'] >= base_win]
    base_members = set()
    for _, row in base_df.iterrows():
        base_members.update([str(row['선봉']), str(row['중견']), str(row['대장'])])
        
    # 2. 선발 대상 그룹 분석
    target_df = active_df[active_df['승'] == target_win]
    
    results = []
    for _, row in target_df.iterrows():
        team_deck = [str(row['선봉']), str(row['중견']), str(row['대장'])]
        unique_deck = [m for m in team_deck if m not in base_members]
        
        results.append({
            "팀명": row['팀명'],
            "승패": f"{row['승']}승 {row['패']}패",
            "고유 멤버 수": len(unique_deck),
            "고유 멤버(Rogue)": ", ".join(unique_deck) if unique_deck else "없음",
            "전체 라인업": ", ".join(team_deck)
        })
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🥇 기준 그룹 ({base_win}승 이상)")
        if not base_df.empty:
            st.dataframe(base_df[['팀명', '승', '패']], hide_index=True)
            st.success(f"📌 기준 메타 라인업 (총 {len(base_members)}명): {', '.join(base_members)}")
        else:
            st.warning("조건을 만족하는 기준 팀이 없습니다.")

    with col2:
        st.subheader(f"🥈 선발 랭킹 ({target_win}승 팀 중)")
        if results:
            results_df = pd.DataFrame(results).sort_values(by="고유 멤버 수", ascending=False).reset_index(drop=True)
            st.dataframe(results_df, hide_index=True, use_container_width=True)
            
            st.markdown(f"### 🎯 최종 추천 TOP {pick_count}")
            if len(results_df) > 0:
                cutoff_idx = min(int(pick_count)-1, len(results_df)-1)
                cutoff_score = results_df.iloc[cutoff_idx]["고유 멤버 수"]
                top_teams = results_df[results_df["고유 멤버 수"] >= cutoff_score]
                
                for i, (_, row) in enumerate(top_teams.iterrows(), 1):
                    st.info(f"**{i}위. {row['팀명']}** (고유 {row['고유 멤버 수']}명)  \n👉 {row['고유 멤버(Rogue)']}")
        else:
            st.warning("선발 대상 팀이 없습니다.")