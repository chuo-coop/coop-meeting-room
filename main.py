import streamlit as st
import calendar
from datetime import date, datetime

# --------------------------------------------------
# 🧭 ページ設定
# --------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約カレンダー", layout="wide")

# --------------------------------------------------
# 🔐 パスワード認証ブロック
# --------------------------------------------------
PASSWORD = "chuo2025"  # ← ここを好きなパスワードに変更可能

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("## 🔐 パスワード認証")
    pw_input = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if pw_input == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("認証に成功しました。")
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# --------------------------------------------------
# 📅 認証済みユーザー向け：カレンダー画面
# --------------------------------------------------
st.markdown("## 🗓️ 会議室利用カレンダー")

today = datetime.now()
display_year = st.session_state.get("year", today.year)
display_month = st.session_state.get("month", today.month)

cal = calendar.Calendar(firstweekday=6).monthdayscalendar(display_year, display_month)

col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("← 前月"):
        if display_month == 1:
            st.session_state["year"] = display_year - 1
            st.session_state["month"] = 12
        else:
            st.session_state["month"] = display_month - 1
        st.rerun()
with col3:
    if st.button("次月 →"):
        if display_month == 12:
            st.session_state["year"] = display_year + 1
            st.session_state["month"] = 1
        else:
            st.session_state["month"] = display_month + 1
        st.rerun()

st.markdown(f"### {display_year}年 {display_month}月")
st.caption("利用したい日をクリックしてください。")

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
                st.rerun()

st.divider()
st.caption("中央大学生活協同組合　情報通信チーム（パスワード認証対応版）")

# ページ遷移制御
if st.session_state.get("page") == "weekview":
    import pages.meeting_room_weekview
    st.stop()
