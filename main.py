# =========================================================
# ChuoCoop_MeetingRoom_UI_v2.py
# 中央大学生協 会議室予約システム（前側＋奥側＋満 表示版）
# =========================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# -------------------------------------------------------------
# ページ設定
# -------------------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")

# -------------------------------------------------------------
# ログイン認証　# === 改修ポイント ===
# -------------------------------------------------------------
PASSWORD = "coop"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align:center;'>🔒 会議室予約システム</h2>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;width:300px;margin:auto;'>", unsafe_allow_html=True)
    input_pw = st.text_input("パスワードを入力してください", type="password", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("ログイン", use_container_width=True):
        if input_pw == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("ログイン成功。システムを開きます。")
            st.experimental_rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# -------------------------------------------------------------
# 初期化
# -------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "calendar"

if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.now().date()

if "reservations" not in st.session_state:
    st.session_state["reservations"] = {"前側": [], "奥側": []}

ROOMS = ["前側", "奥側"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 関数群
# -------------------------------------------------------------
def parse_time(tstr: str) -> time:
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def register_reservation(room, date, start, end, user, purpose, extension):
    new_res = {"date": date, "start": start, "end": end, "user": user, "purpose": purpose, "extension": extension, "status": "active", "cancelled_at": None}
    st.session_state["reservations"][room].append(new_res)
    return True

def cancel_reservation(room, user, start, end, date):
    for r in st.session_state["reservations"][room]:
        if (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date):
            r["status"] = "cancelled"
            r["cancelled_at"] = datetime.now().strftime("%Y-%m-%d")
    st.success("予約を取り消しました。")
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    selected = st.date_input("日付を選択", value=datetime.now().date())
    st.session_state["selected_date"] = selected
    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示画面（A→B→C→D）
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    selected_date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {selected_date} の利用状況")

    # === A：インジケーター部 ===
    st.markdown("### ⏱ 利用状況マップ（前側・奥側・満）")

    for layer in ["前側", "奥側", "満"]:
        row_cells = []
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color = "transparent"
            text = slot if layer != "満" else ""
            if layer != "満":
                for r in st.session_state["reservations"][layer]:
                    if (r["date"] == selected_date and r["status"] == "active" and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)):
                        color = "#ffcccc"
                        break
            else:
                front_busy = any(r["date"] == selected_date and r["status"] == "active" and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0) for r in st.session_state["reservations"]["前側"])
                back_busy = any(r["date"] == selected_date and r["status"] == "active" and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0) for r in st.session_state["reservations"]["奥側"])
                if front_busy and back_busy:
                    color = "#ff6666"
                    text = "満"
            row_cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;height:26px;display:flex;align-items:center;justify-content:center;font-size:10px;'>{text}</div>")
        st.markdown(f"<div style='display:flex;gap:1px;'>{''.join(row_cells)}</div>", unsafe_allow_html=True)

    # === B：使用状況一覧 ===
    st.markdown("### 📋 使用状況一覧（時間順）")
    all_res = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if r["date"] == selected_date:
                all_res.append({"区画": room, "開始": r["start"], "終了": r["end"], "担当者": r["user"], "目的": r["purpose"], "内線": r["extension"], "状態": "取消済" if r["status"] == "cancelled" else "有効", "取消日": r["cancelled_at"]})
    if all_res:
        df = pd.DataFrame(all_res).sort_values(by=["開始"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("この日の予約はありません。")

    # === C：予約登録 ===
    st.divider()
    st.subheader("📝 新しい予約を登録")
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    with c1:
        room_sel = st.selectbox("区画", ROOMS)
    with c2:
        start_sel = st.selectbox("開始", TIME_SLOTS)
    with c3:
        end_sel = st.selectbox("終了", TIME_SLOTS)
    with c4:
        user = st.text_input("担当者", max_chars=16)
    purpose = st.text_input("目的（任意）", "")
    extension = st.text_input("内線（任意）", "")

    if st.button("登録"):
        if not (room_sel and user and start_sel and end_sel):
            st.error("必須項目が入力されていません。")
        else:
            with st.modal("予約内容を確認"):
                st.write(f"区画：{room_sel}")
                st.write(f"時間：{start_sel}〜{end_sel}")
                st.write(f"担当者：{user}")
                if st.button("はい、登録する"):
                    register_reservation(room_sel, selected_date, start_sel, end_sel, user, purpose, extension)
                    st.success("登録が完了しました。")
                    st.experimental_rerun()
                st.button("もどる")

    # === D：予約取消 ===
    st.divider()
    st.subheader("🗑️ 予約取消")
    cancel_list = [f"{r['区画']} | {r['担当者']} | {r['開始']}〜{r['終了']}" for r in all_res if r["状態"] == "有効"]
    if cancel_list:
        sel_cancel = st.selectbox("取消対象を選択", cancel_list)
        cancel_user = st.text_input("担当者名（確認用）", "")
        if st.button("取り消す"):
            room, user, times = sel_cancel.split(" | ")
            start, end = times.split("〜")
            with st.modal("取消内容を確認"):
                st.write(f"区画：{room}")
                st.write(f"時間：{start}〜{end}")
                st.write(f"担当者：{user}")
                if st.button("はい、取消する"):
                    cancel_reservation(room, cancel_user, start, end, selected_date)
                st.button("もどる")
    else:
        st.caption("有効な予約はありません。")

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v2統合版）")
