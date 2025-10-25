import streamlit as st
import calendar
from datetime import date

# -----------------------------
# ページ設定
# -----------------------------
st.set_page_config(page_title="中大生協 会議室予約カレンダー", layout="centered")

# -----------------------------
# パスワード認証
# -----------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 会議室予約システム ログイン")
    password = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if password == st.secrets.get("PASSWORD", "coop"):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# -----------------------------
# カレンダー生成（月単位）
# -----------------------------
st.title("📅 会議室利用カレンダー")

if "month_offset" not in st.session_state:
    st.session_state["month_offset"] = 0

today = date.today()
display_month = today.month + st.session_state["month_offset"]
display_year = today.year + (display_month - 1) // 12
display_month = (display_month - 1) % 12 + 1

st.subheader(f"{display_year}年 {display_month}月")

col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.button("← 前月"):
        st.session_state["month_offset"] -= 1
        st.rerun()
with col3:
    if st.button("次月 →"):
        st.session_state["month_offset"] += 1
        st.rerun()

# -----------------------------
# カレンダー表示
# -----------------------------
cal = calendar.monthcalendar(display_year, display_month)
st.write("利用したい日をクリックしてください。")

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].markdown(" ")
        else:
            btn = cols[i].button(str(day))
            if btn:
                st.session_state["selected_date"] = date(display_year, display_month, day)
                st.switch_page("meeting_room_weekview.py")
