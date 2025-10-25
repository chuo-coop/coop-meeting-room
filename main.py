import streamlit as st
import calendar
from datetime import date, datetime

st.set_page_config(page_title="中大生協 会議室予約カレンダー", layout="wide")

# --- パスワード認証 ---
PASSWORD = "coop"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 会議室予約システム ログイン")
    pw_input = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pw_input == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("ログインしました。")
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# --- カレンダー表示 ---
st.markdown("## 📅 会議室利用カレンダー")

today = datetime.now()
year = today.year
month = today.month
cal = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

st.write(f"### {year}年 {month}月")
st.caption("利用したい日をクリックしてください。")

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].markdown(" ")
        else:
            if cols[i].button(str(day)):
                st.session_state["selected_date"] = date(year, month, day)
                # ✅ ページ遷移（この1行が重要）
                st.switch_page("meeting_room_weekview")

st.caption("中央大学生活協同組合　会議室予約システム（安定版）")

