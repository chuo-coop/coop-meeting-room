import streamlit as st
import calendar
from datetime import date, datetime

# ページ設定
st.set_page_config(page_title="中大生協 会議室予約（カレンダー）", layout="wide")

# --- ページ遷移制御 ---
if st.session_state.get("page") == "weekview":
    import pages.meeting_room_weekview
    st.stop()

# --- タイトル ---
st.markdown("## 🗓️ 会議室利用カレンダー")

# 今日の日付から年と月を取得
today = datetime.now()
display_year = st.session_state.get("year", today.year)
display_month = st.session_state.get("month", today.month)

# カレンダー生成
cal = calendar.Calendar(firstweekday=6).monthdayscalendar(display_year, display_month)

# --- 月切り替えボタン ---
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("← 前月"):
        if display_month == 1:
            st.session_state["year"] = display_year - 1
            st.session_state["month"] = 12
        else:
            st.session_state["month"] = display_month - 1
        st.experimental_rerun()
with col3:
    if st.button("次月 →"):
        if display_month == 12:
            st.session_state["year"] = display_year + 1
            st.session_state["month"] = 1
        else:
            st.session_state["month"] = display_month + 1
        st.experimental_rerun()

st.markdown(f"### {display_year}年 {display_month}月")
st.caption("利用したい日をクリックしてください。")

# --- カレンダー描画 ---
for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].markdown(" ")
        else:
            btn = cols[i].button(str(day))
            if btn:
                st.session_state["selected_date"] = date(display_year, display_month, day)
                st.session_state["page"] = "weekview"
                st.experimental_rerun()

# --- フッター ---
st.divider()
st.caption("中央大学生活協同組合　情報通信チーム")
