# =========================================================
# 中大生協 会議室予約システム v3.3（確認ポップアップ安定版）
# =========================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# -------------------------------------------------------------
# ページ設定
# -------------------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")

# -------------------------------------------------------------
# ログイン認証
# -------------------------------------------------------------
PASSWORD = "coop"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align:center;'>🔒 会議室予約システム</h2>", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        pw = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pw == PASSWORD:
                st.session_state["authenticated"] = True
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
if "pending_register" not in st.session_state:
    st.session_state["pending_register"] = None
if "pending_cancel" not in st.session_state:
    st.session_state["pending_cancel"] = None

ROOMS = ["前側", "奥側"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 補助関数
# -------------------------------------------------------------
def parse_time(tstr):
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def register_reservation(room, date, start, end, user, purpose, ext):
    new = {"date": date, "start": start, "end": end, "user": user,
           "purpose": purpose, "ext": ext, "status": "active", "cancel": ""}
    st.session_state["reservations"][room].append(new)
    st.session_state["pending_register"] = None
    st.experimental_rerun()

def cancel_reservation(room, user, start, end, date):
    for r in st.session_state["reservations"][room]:
        if r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date:
            r["status"] = "cancel"
            r["cancel"] = datetime.now().strftime("%Y-%m-%d")
    st.session_state["pending_cancel"] = None
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    selected = st.date_input("日付を選択", datetime.now().date())
    st.session_state["selected_date"] = selected
    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示画面
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {date} の利用状況")

    # === インジケータ ===
    st.markdown("### 🏢 利用インジケータ（凡例付き）")

    for idx, layer in enumerate(["前側", "奥側", "満"]):
        label = ["前側", "奥側", "満"][idx]
        row = []
        row.append(f"<div style='width:60px;text-align:center;font-weight:bold;border:1px solid #999;background:#f9f9f9;'>{label}</div>")
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color, text = "#ffffff", ""
            if layer in ["前側", "奥側"]:
                active = any(
                    r["date"] == date and r["status"] == "active" and
                    overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"][layer]
                )
                color = "#ffcccc" if active else "#ccffcc"
                text = slot
            else:  # 満
                front_busy = any(r["date"] == date and r["status"] == "active" and
                                 overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                                 for r in st.session_state["reservations"]["前側"])
                back_busy = any(r["date"] == date and r["status"] == "active" and
                                overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                                for r in st.session_state["reservations"]["奥側"])
                if front_busy and back_busy:
                    color = "#ff6666"
                    text = "満"
            row.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;font-size:10px;text-align:center;padding:2px;'>{text}</div>")
        st.markdown(f"<div style='display:flex;'>{''.join(row)}</div>", unsafe_allow_html=True)

    # === 使用状況一覧 ===
    st.divider()
    st.markdown("### 📋 使用状況一覧（時間順）")
    records = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if r["date"] == date:
                records.append({
                    "区画": room,
                    "時間": f"{r['start']}〜{r['end']}",
                    "担当者": r["user"],
                    "目的": r["purpose"],
                    "内線": r["ext"],
                    "状態": "取消" if r["status"] == "cancel" else "有効",
                    "取消日": r["cancel"]
                })
    if records:
        df = pd.DataFrame(records).sort_values(by="時間")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("当日の予約はありません。")

    # === 予約登録 ===
    st.divider()
    st.subheader("📝 新しい予約を登録")

    cols = st.columns([1, 1, 1, 1, 2, 1, 1])
    room = cols[0].selectbox("区画", ROOMS)
    start = cols[1].selectbox("開始", TIME_SLOTS)
    end = cols[2].selectbox("終了", TIME_SLOTS)
    user = cols[3].text_input("担当者", "")
    purpose = cols[4].text_input("目的（任意）", "")
    ext = cols[5].text_input("内線（任意）", "")
    if cols[6].button("登録"):
        if not user:
            st.error("担当者名を入力してください。")
        elif parse_time(end) <= parse_time(start):
            st.error("終了時刻は開始より後にしてください。")
        else:
            st.session_state["pending_register"] = {"room": room, "date": date, "start": start, "end": end, "user": user, "purpose": purpose, "ext": ext}
            st.experimental_rerun()

    if st.session_state["pending_register"]:
        d = st.session_state["pending_register"]
        with st.container():
            st.markdown("<div style='border:2px solid #666;padding:10px;background:#f0f0f0;text-align:center;'>"
                        f"<b>登録内容確認：</b><br>{d['room']}　{d['start']}〜{d['end']}　{d['user']}<br>これで登録しますか？</div>",
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("はい、登録する"):
                    register_reservation(**d)
            with c2:
                if st.button("戻る"):
                    st.session_state["pending_register"] = None
                    st.experimental_rerun()

    # === 予約取消 ===
    st.divider()
    st.subheader("🗑️ 予約取消")

    cancel_targets = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if r["date"] == date and r["status"] == "active":
                cancel_targets.append(f"{room} | {r['user']} | {r['start']}〜{r['end']}")

    if cancel_targets:
        sel = st.selectbox("取消対象を選択", cancel_targets)
        if st.button("取消"):
            room, user, t = sel.split(" | ")
            start, end = t.split("〜")
            st.session_state["pending_cancel"] = {"room": room, "user": user, "start": start, "end": end, "date": date}
            st.experimental_rerun()

    if st.session_state["pending_cancel"]:
        d = st.session_state["pending_cancel"]
        with st.container():
            st.markdown("<div style='border:2px solid #900;padding:10px;background:#fff0f0;text-align:center;'>"
                        f"<b>取消確認：</b><br>{d['room']}　{d['start']}〜{d['end']}　{d['user']}<br>本当に取り消しますか？</div>",
                        unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("はい、取消する"):
                    cancel_reservation(**d)
            with c2:
                if st.button("戻る"):
                    st.session_state["pending_cancel"] = None
                    st.experimental_rerun()

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v3.3確認ポップアップ安定版）")
