import streamlit as st
import pandas as pd
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ─────────────────────
# Google Sheet 연결 함수
# ─────────────────────
def connect_to_sheet():
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open("theater_reviews").sheet1
    return sheet

# ─────────────────────
# 리뷰 작성 탭
# ─────────────────────
st.set_page_config(page_title="연극 리뷰 저장소", page_icon="🎭", layout="wide")
tab1, tab2, tab3 = st.tabs(["✍️ 리뷰 작성", "📖 연극별 리뷰 보기", "🛠 리뷰 수정/삭제"])

with tab1:
    st.header("✍️ 연극 리뷰 남기기")
    with st.form("리뷰폼"):
        nickname = st.text_input("닉네임", max_chars=15)
        title = st.text_input("공연 제목")
        watch_date = st.date_input("관람일", value=date.today())
        rating = st.slider("별점 (0~5)", min_value=0.0, max_value=5.0, value=0.0, step=0.5)

        q1 = st.text_area("1. 한줄평 - 공연을 한 문장으로 표현한다면?")
        q2 = st.text_area("2. 기억에 남는 장면이나 인물은?")
        q3 = st.text_area("3. 배우들의 연기는 어땠나요?")
        q4 = st.text_area("4. 무대 연출/조명/음악 등 시각·청각적 요소는 어땠나요?")
        q5 = st.text_area("5. 스토리 구성과 대본은 어땠나요?")
        q6 = st.text_area("6. 이 공연이 전하려는 메시지나 주제를 어떻게 느꼈나요?")
        q7 = st.text_area("7. 전체적인 감상 소감")

        submitted = st.form_submit_button("저장하기")

        if submitted:
            if not nickname or not title:
                st.warning("닉네임과 공연 제목은 필수입니다!")
            else:
                try:
                    sheet = connect_to_sheet()
                    sheet.append_row([
                        nickname, title, str(watch_date), rating,
                        q1, q2, q3, q4, q5, q6, q7
                    ])
                    st.success("✅ 리뷰가 저장소에 저장되었습니다!")
                except Exception as e:
                    st.error(f"❌ 저장 중 오류 발생: {e}")

# ─────────────────────
# 연극별 리뷰 보기 탭
# ─────────────────────
with tab2:
    st.header("🎭 연극별 리뷰 보기")
    try:
        sheet = connect_to_sheet()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        # 좋아요 열이 없으면 0으로 채움
        if "좋아요" not in df.columns:
            df["좋아요"] = 0

        play_titles = df["공연 제목"].dropna().unique()
        selected_title = st.selectbox("공연을 선택하세요", play_titles)

        filtered = df[df["공연 제목"] == selected_title].copy()
        st.markdown(f"### 📄 '{selected_title}'에 대한 리뷰 ({len(filtered)}개)")
        st.markdown(f"⭐ **평균 별점:** `{filtered['별점'].mean():.2f}` / 5")

        for idx, row in filtered.iterrows():
            expander_title = f"⭐ {row['별점']} | **{row['닉네임']}** | {row['관람일']}  \n👉 **_{row['한줄평']}_**"
            with st.expander(expander_title):
                st.markdown(f"**1. 한줄평**\n{row['한줄평']}")
                st.markdown(f"**2. 기억에 남는 장면/인물**\n{row['기억에 남는 장면/인물']}")
                st.markdown(f"**3. 배우 연기**\n{row['배우 연기']}")
                st.markdown(f"**4. 무대/연출/음향**\n{row['무대/연출/음향']}")
                st.markdown(f"**5. 스토리/대본**\n{row['스토리/대본']}")
                st.markdown(f"**6. 메시지/주제**\n{row['메시지/주제']}")
                st.markdown(f"**7. 전체 소감**\n{row['전체 소감']}")

                # 현재 좋아요 수 표시 및 버튼
                like_col, count_col = st.columns([1, 5])
                with like_col:
                    if st.button("❤️ 좋아요", key=f"like_{idx}"):
                        try:
                            sheet_row = df.index.get_loc(idx) + 2
                            current_likes = int(row.get("좋아요", 0) or 0)
                            sheet.update_cell(sheet_row, df.columns.get_loc("좋아요") + 1, current_likes + 1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"좋아요 실패: {e}")
                
                with count_col:
                    st.markdown(
                        f"<div style='text-align:left; font-size:20px;'>👍 <b>{int(row.get('좋아요', 0) or 0)}</b>명 공감했어요</div>",
                        unsafe_allow_html=True
                    )


    except Exception as e:
        st.error(f"❌ 리뷰 불러오기 실패: {e}")

# ─────────────────────
# 탭 3: Google Sheet 기반 수정/삭제
# ─────────────────────
with tab3:
    st.header("🛠 리뷰 수정 또는 삭제")

    try:
        sheet = connect_to_sheet()
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        nickname = st.text_input("닉네임 입력 (수정/삭제용)", key="edit_nick")

        if nickname:
            user_reviews = df[df["닉네임"] == nickname]

            if user_reviews.empty:
                st.warning("해당 닉네임으로 작성된 리뷰가 없습니다.")
            else:
                selected_idx = st.selectbox(
                    "수정 또는 삭제할 리뷰 선택",
                    user_reviews.index,
                    format_func=lambda i: f"{user_reviews.loc[i, '공연 제목']} | {user_reviews.loc[i, '관람일']}"
                )

                selected_review = user_reviews.loc[selected_idx]
                # 행 번호는 get_all_records() 기준으로 +2 (헤더 제외 + 1-index)
                sheet_row_num = selected_idx + 2

                # 기존 값 입력 폼에 채우기
                new_title = st.text_input("공연 제목", value=selected_review["공연 제목"])
                new_date = st.date_input("관람일", value=pd.to_datetime(selected_review["관람일"]))
                new_rating = st.slider("별점", min_value=0.0, max_value=5.0,value=float(selected_review["별점"]),step=0.5)

                q1 = st.text_area("1. 한줄평 - 공연을 한 문장으로 표현한다면?", value=selected_review["한줄평"])
                q2 = st.text_area("2. 기억에 남는 장면이나 인물은?", value=selected_review["기억에 남는 장면/인물"])
                q3 = st.text_area("3. 배우들의 연기는 어땠나요?", value=selected_review["배우 연기"])
                q4 = st.text_area("4. 무대 연출/조명/음악 등 시각·청각적 요소는 어땠나요?", value=selected_review["무대/연출/음향"])
                q5 = st.text_area("5. 스토리 구성과 대본은 어땠나요?", value=selected_review["스토리/대본"])
                q6 = st.text_area("6. 이 공연이 전하려는 메시지나 주제를 어떻게 느꼈나요?", value=selected_review["메시지/주제"])
                q7 = st.text_area("7. 전체적인 감상 소감", value=selected_review["전체 소감"])

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 리뷰 수정 저장"):
                        try:
                            sheet.update(
                                f"A{sheet_row_num}:K{sheet_row_num}",
                                [[nickname, new_title, str(new_date), new_rating,
                                  q1, q2, q3, q4, q5, q6, q7]]
                            )
                            st.success("✅ 저장소에 리뷰 수정 완료!")
                        except Exception as e:
                            st.error(f"수정 실패: {e}")

                with col2:
                    if st.button("🗑️ 리뷰 삭제"):
                        try:
                            sheet.delete_rows(sheet_row_num)
                            st.success("❌ 리뷰가 저장소에서 삭제되었습니다!")
                        except Exception as e:
                            st.error(f"삭제 실패: {e}")

    except Exception as e:
        st.error(f"❌ 저장소 접근 실패: {e}")
