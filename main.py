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

# -------------------------------------------------------------
# ログイン認証
# -------------------------------------------------------------
PASSWORD = "coop"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 会議室予約システム ログイン")
    input_pw = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if input_pw == PASSWORD:
            st.session_state["authenticated"] = True
            st.experimental_rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# -------------------------------------------------------------
# 初期化
# -------------------------------------------------------------
ROOMS = ["前方区画", "後方区画", "全体利用"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

if "page" not in st.session_state:
    st.session_state["page"] = "calendar"
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.now().date()
if "reservations" not in st.session_state:
    st.session_state["reservations"] = {r: [] for r in ROOMS}

# -------------------------------------------------------------
# CSV 永続化
# -------------------------------------------------------------
def save_reservations():
    all_res = []
    for room, items in st.session_state["reservations"].items():
        for it in items:
            all_res.append({"room": room, **it})
    pd.DataFrame(all_res).to_csv(DATA_PATH, index=False)

def load_reservations():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        for _, row in df.iterrows():
            d = row.to_dict()
            room = d.pop("room")
            # 日付をdatetime.dateに変換
            if isinstance(d["date"], str):
                try:
                    d["date"] = datetime.strptime(d["date"], "%Y-%m-%d").date()
                except ValueError:
                    pass
            if room in st.session_state["reservations"]:
                st.session_state["reservations"][room].append(d)

load_reservations()

# -------------------------------------------------------------
# 共通関数
# -------------------------------------------------------------
def parse_time(tstr): h, m = map(int, tstr.split(":")); return time(h, m)
def overlap(s1, e1, s2, e2): return s1 < e2 and s2 < e1

def to_date(d):
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    return d

# -------------------------------------------------------------
# 整合処理（前後半面が重なる場合に全体利用を生成）
# -------------------------------------------------------------
def sync_full_room(date):
    front = st.session_state["reservations"]["前方区画"]
    back = st.session_state["reservations"]["後方区画"]
    full_new = []

    for f in front:
        for b in back:
            if (
                to_date(f["date"]) == to_date(b["date"]) == date
                and overlap(parse_time(f["start"]), parse_time(f["end"]),
                            parse_time(b["start"]), parse_time(b["end"]))
            ):
                full_new.append({
                    "date": date,
                    "start": min(f["start"], b["start"]),
                    "end": max(f["end"], b["end"]),
                    "user": f["user"],
                    "purpose": f.get("purpose", ""),
                    "extension": f.get("extension", "")
                })

    # 対象日だけ置き換え
    st.session_state["reservations"]["全体利用"] = [
        r for r in st.session_state["reservations"]["全体利用"] if to_date(r["date"]) != date
    ] + full_new

# -------------------------------------------------------------
# 登録処理
# -------------------------------------------------------------
def register_reservation(room, date, start, end, user, purpose, extension):
    new = {"date": date, "start": start, "end": end,
           "user": user, "purpose": purpose, "extension": extension}

    # 全体予約の場合
    if room == "全体利用":
        for rname in ["前方区画", "後方区画"]:
            for r in st.session_state["reservations"][rname]:
                if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                                  parse_time(start), parse_time(end)):
                    st.warning(f"{rname} に既に予約があります。全体利用はできません。")
                    return False
        for rname in ROOMS:
            st.session_state["reservations"][rname].append(new.copy())
        save_reservations()
        return True

    # 半面予約
    for r in st.session_state["reservations"]["全体利用"]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                           parse_time(start), parse_time(end)):
            st.warning("この時間帯は全体利用で予約済みです。")
            return False

    st.session_state["reservations"][room].append(new)
    sync_full_room(date)
    save_reservations()
    return True

# -------------------------------------------------------------
# 取消処理
# -------------------------------------------------------------
def cancel_reservation(room, user, start, end, date):
    for rname in ROOMS:
        st.session_state["reservations"][rname] = [
            r for r in st.session_state["reservations"][rname]
            if not (r["date"] == date and r["start"] == start and r["end"] == end and r["user"] == user and
                    (room == "全体利用" or rname == room))
        ]
    sync_full_room(date)
    save_reservations()
    st.success("予約を取り消しました。")
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    selected = st.date_input("日付を選択", st.session_state["selected_date"])
    st.session_state["selected_date"] = selected
    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {date} の利用状況")
    st.markdown("<div style='display:flex;gap:20px;'><div>🟩空室</div><div>🟥予約済</div></div>", unsafe_allow_html=True)

    for room in ROOMS:
        st.markdown(f"### 🏢 {room}")
        cells = []
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color = "#ccffcc"
            for r in st.session_state["reservations"][room]:
                if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0):
                    color = "#ffcccc"; break
            cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;font-size:10px;padding:2px;'>{slot}</div>")
        st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;overflow-x:auto'>{''.join(cells)}</div>", unsafe_allow_html=True)

    # 登録フォーム
    st.divider()
    st.subheader("📝 新しい予約を登録")
    with st.form("add_reservation"):
        c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,2,1])
        with c1: room_sel = st.selectbox("区画", ROOMS)
        with c2: start_sel = st.select_slider("開始", options=TIME_SLOTS, value="12:00")
        with c3: end_sel = st.select_slider("終了", options=TIME_SLOTS, value="13:00")
        with c4: user = st.text_input("氏名", max_chars=16)
        with c5: purpose = st.text_input("目的", placeholder="任意")
        with c6: ext = st.text_input("内線", placeholder="例：1234")
        sub = st.form_submit_button("登録")

        if sub:
            s, e = parse_time(start_sel), parse_time(end_sel)
            if e <= s: st.error("終了時刻は開始より後にしてください。")
            elif not user.strip(): st.warning("氏名を入力してください。")
            else:
                if register_reservation(room_sel, date, start_sel, end_sel, user, purpose, ext):
                    st.success("登録完了。")
                    st.experimental_rerun()

    # 削除フォーム
    st.divider()
    st.subheader("🗑️ 予約を取り消す")
    all_res = []
    for rname, items in st.session_state["reservations"].items():
        for it in items:
            if it["date"] == date:
                all_res.append({"room": rname, **it})

    if all_res:
        df = pd.DataFrame(all_res)
        sel = st.selectbox("削除する予約を選択",
                           df.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1))
        if st.button("選択した予約を取り消す"):
            room, user, se = sel.split(" | "); start, end = se.split("〜")
            cancel_reservation(room, user, start, end, date)
    else:
        st.caption("当日の予約はありません。")

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム　ver.2025.08d（統合安定＋型整合完全版）")
