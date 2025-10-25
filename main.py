import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time
from dotenv import load_dotenv

# -------------------------------------------------------------
# 環境設定
# -------------------------------------------------------------
load_dotenv("env/.env")
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")

DATA_PATH = "data/reservations.csv"
os.makedirs("data", exist_ok=True)

# -------------------------------------------------------------
# ログイン認証
# -------------------------------------------------------------
PASSWORD = os.getenv("SYSTEM_PASSWORD", "coop")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 会議室予約システム ログイン")
    input_pw = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
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

ROOMS = ["前方区画", "後方区画", "全体利用"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.now().date()

if "reservations" not in st.session_state:
    st.session_state["reservations"] = {r: [] for r in ROOMS}

# -------------------------------------------------------------
# 保存・読み込み関数
# -------------------------------------------------------------
def save_reservations():
    all_res = []
    for room, items in st.session_state["reservations"].items():
        for it in items:
            all_res.append({"room": room, **it})
    pd.DataFrame(all_res).to_csv(DATA_PATH, index=False)

def load_reservations():
    if os.path.exists(DATA_PATH):
        df_saved = pd.read_csv(DATA_PATH)
        for _, row in df_saved.iterrows():
            r = row.to_dict()
            room = r.pop("room")
            if room in st.session_state["reservations"]:
                st.session_state["reservations"][room].append(r)

load_reservations()

# -------------------------------------------------------------
# 基本関数
# -------------------------------------------------------------
def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def parse_time(tstr: str) -> time:
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def register_reservation(room, date, start, end, user, purpose, extension):
    new_res = {"date": date, "start": start, "end": end,
               "user": user, "purpose": purpose, "extension": extension}

    # 全体利用チェック
    if room == "全体利用":
        for rname in ["前方区画", "後方区画"]:
            for r in st.session_state["reservations"][rname]:
                if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                                  parse_time(start), parse_time(end)):
                    st.warning(f"{rname} に既に予約があります。全体利用はできません。")
                    return False
        st.session_state["reservations"][room].append(new_res)
        for rname in ["前方区画", "後方区画"]:
            st.session_state["reservations"][rname].append(new_res.copy())
        save_reservations()
        return True

    # 半面予約時：全体利用と衝突チェック
    for r in st.session_state["reservations"]["全体利用"]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                           parse_time(start), parse_time(end)):
            st.warning("この時間帯は全体利用で予約済みです。")
            return False

    # 半面登録
    st.session_state["reservations"][room].append(new_res)
    other = "後方区画" if room == "前方区画" else "前方区画"
    overlap_found = any(
        (r["date"] == date)
        and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end))
        for r in st.session_state["reservations"][other]
    )
    if overlap_found:
        st.session_state["reservations"]["全体利用"].append(new_res.copy())

    save_reservations()
    return True

def cancel_reservation(room, user, start, end, date):
    for rlist in st.session_state["reservations"].values():
        rlist[:] = [r for r in rlist if not (
            r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date)]
    save_reservations()
    st.success("予約を取り消しました。")
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    st.caption("利用希望日を選んでください。詳細画面で予約登録ができます。")

    selected = st.date_input("日付を選択", st.session_state["selected_date"])
    st.session_state["selected_date"] = selected

    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示（登録・取消含む）
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    selected_date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {selected_date} の利用状況")

    # 凡例
    st.markdown("""
    <div style='display:flex;gap:24px;align-items:center;margin:6px 0 14px 2px;font-size:14px;'>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ccffcc;border:1px solid #999;'></span>空室</div>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ffcccc;border:1px solid #999;'></span>予約済</div>
    </div>
    """, unsafe_allow_html=True)

    # スケジュール表
    for room in ROOMS:
        st.markdown(f"### 🏢 {room}
