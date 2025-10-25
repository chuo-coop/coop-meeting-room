# -------------------------------------------------------------
# 中央大学生活協同組合 会議室予約システム
# ver.2025.09（完全安定統合版）
# -------------------------------------------------------------

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time

# -------------------------------------------------------------
# ページ設定
# -------------------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")
DATA_PATH = "data/reservations.csv"
os.makedirs("data", exist_ok=True)

PASSWORD = "coop"
ROOMS = ["前方区画", "後方区画", "全体利用"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# ログイン処理
# -------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 会議室予約システム ログイン")
    pw = st.text_input("パスワードを入力してください", type="password")
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
    st.session_state["reservations"] = {r: [] for r in ROOMS}

# -------------------------------------------------------------
# 保存・読み込み
# -------------------------------------------------------------
def save_reservations():
    all_res = []
    for room, items in st.session_state["reservations"].items():
        for it in items:
            d = it.copy()
            if isinstance(d["date"], datetime):
                d["date"] = d["date"].date().isoformat()
            elif not isinstance(d["date"], str):
                d["date"] = str(d["date"])
            all_res.append({"room": room, **d})
    pd.DataFrame(all_res).to_csv(DATA_PATH, index=False)

def load_reservations():
    if not os.path.exists(DATA_PATH):
        return
    df = pd.read_csv(DATA_PATH)
    for _, row in df.iterrows():
        d = row.to_dict()
        r = d.pop("room")
        if "date" in d and isinstance(d["date"], str):
            try:
                d["date"] = datetime.strptime(d["date"], "%Y-%m-%d").date()
            except Exception:
                pass
        st.session_state["reservations"][r].append(d)

load_reservations()

# -------------------------------------------------------------
# 共通関数
# -------------------------------------------------------------
def parse_time(t): 
    h, m = map(int, t.split(":"))
    return time(h, m)

def overlap(s1, e1, s2, e2):
    return s1 < e2 and s2 < e1

def sync_full_room(date):
    fwd = st.session_state["reservations"]["前方区画"]
    bwd = st.session_state["reservations"]["後方区画"]
    full_new = []
    for f in fwd:
        for b in bwd:
            if f["date"] == b["date"] == date and overlap(
                parse_time(f["start"]), parse_time(f["end"]),
                parse_time(b["start"]), parse_time(b["end"])
            ):
                full_new.append({
                    "date": date,
                    "start": min(f["start"], b["start"]),
                    "end": max(f["end"], b["end"]),
                    "user": f.get("user", ""),
                    "purpose": f.get("purpose", ""),
                    "extension": f.get("extension", "")
                })
    st.session_state["reservations"]["全体利用"] = [
        r for r in st.session_state["reservations"]["全体利用"] if r["date"] != date
    ] + full_new

def register_reservation(room, date, start, end, user, purpose, ext):
    new = {"date": date, "start": start, "end": end,
           "user": user, "purpose": purpose, "extension": ext}

    if room == "全体利用":
        for rname in ["前方区画", "後方区画"]:
            for r in st.session_state["reservations"][rname]:
                if r["date"] == date and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                                parse_time(start), parse_time(end)):
                    st.warning(f"{rname} に既に予約があります。")
                    return False
        for rname in ROOMS:
            st.session_state["reservations"][rname].append(new.copy())
        save_reservations()
        st.experimental_rerun()
        return True

    for r in st.session_state["reservations"]["全体利用"]:
        if r["date"] == date and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                         parse_time(start), parse_time(end)):
            st.warning("この時間帯は全体利用で予約済みです。")
            return False

    st.session_state["reservations"][room].append(new)
    sync_full_room(date)
    save_reservations()
    st.experimental_rerun()
    return True

def cancel_reservation(room, user, start, end, date):
    for rname in ROOMS:
        st.session_state["reservations"][rname] = [
            r for r in st.session_state["reservations"][rname]
            if not (r["date"] == date and r["user"] == user and r["start"] == start and r["end"] == end)
        ]
    sync_full_room(date)
    save_reservations()
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    selected = st.date_input("日付を選択", st.session_state["selected_date"])
    st.session_state["selected_date"] = selected
    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別画面
# -------------------------------------------------------------
elif st.session_state["page"] == "day":
    date = st.session_state["selected_date"]
    sync_full_room(date)
    st.markdown(f"## 🗓️ {date} の利用状況")

    for room in ROOMS:
        st.markdown(f"### 🏢 {room}")
        cells = []
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color = "#ccffcc"
            for r in st.session_state["reservations"][room]:
                if r["date"] == date and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0):
                    color = "#ffcccc"
                    break
            cells.append(
                f"<div style='flex:1;background:{color};border:1px solid #aaa;"
                f"text-align:center;font-size:10px;padding:2px;'>{slot}</div>"
            )
        st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:6px;'>{''.join(cells)}</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📝 新しい予約を登録")
    with st.form("add_reservation"):
        c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 2, 1])
        with c1:
            room = st.selectbox("区画", ROOMS)
        with c2:
            start = st.select_slider("開始", options=TIME_SLOTS, value="12:00")
        with c3:
            end = st.select_slider("終了", options=TIME_SLOTS, value="13:00")
        with c4:
            user = st.text_input("氏名", max_chars=16)
        with c5:
            purpose = st.text_input("目的", placeholder="任意")
        with c6:
            ext = st.text_input("内線", placeholder="例：1234")
        submitted = st.form_submit_button("登録")

        if submitted:
            s = parse_time(start)
            e = parse_time(end)
            if e <= s:
                st.error("終了時刻は開始より後にしてください。")
            elif not user.strip():
                st.warning("氏名を入力してください。")
            else:
                register_reservation(room, date, start, end, user, purpose, ext)

    st.divider()
    st.subheader("🗑️ 予約を取り消す")

    all_res = []
    for rname, items in st.session_state["reservations"].items():
        for it in items:
            if it["date"] == date:
                all_res.append({"room": rname, **it})

    if all_res:
        df = pd.DataFrame(all_res)
        sel = st.selectbox(
            "削除対象",
            df.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1)
        )
        if st.button("選択した予約を取り消す"):
            room, user, se = sel.split(" | ")
            start, end = se.split("〜")
            cancel_reservation(room, user, start, end, date)
    else:
        st.caption("当日の予約はありません。")

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム　ver.2025.09（完全安定統合版）")
