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
if "reservations" not in st.session_state:
    st.session_state["reservations"] = {r: [] for r in ["前側", "奥側"]}

ROOMS = ["前側", "奥側"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]
today = datetime.now().date()

# -------------------------------------------------------------
# 関数定義
# -------------------------------------------------------------
def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def parse_time(tstr: str) -> time:
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def register_reservation(room, date, start, end, user, purpose, extension):
    new_res = {"date": date, "start": start, "end": end, "user": user, "purpose": purpose, "extension": extension}
    for r in st.session_state["reservations"][room]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning(f"{room} に既に予約があります。")
            return False
    st.session_state["reservations"][room].append(new_res)
    return True

def cancel_reservation(room, user, start, end, date):
    for rlist in st.session_state["reservations"].values():
        rlist[:] = [r for r in rlist if not (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date)]
    st.success("予約を取り消しました。")
    st.experimental_rerun()

# -------------------------------------------------------------
# ページ構成
# -------------------------------------------------------------
st.title("🏢 中央大学生協 会議室予約システム")
st.markdown(f"### 📅 本日：{today.strftime('%Y年%m月%d日（%a）')}")

# -------------------------------------------------------------
# インジケーター表示
# -------------------------------------------------------------
st.markdown("#### 利用状況（前側・奥側・満）")

for room in ROOMS:
    st.markdown(f"### {room}")
    res_list = st.session_state["reservations"][room]
    cells = []
    for slot in TIME_SLOTS:
        s0 = parse_time(slot)
        e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
        color = "#ccffcc"
        for r in res_list:
            if (r["date"] == today) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0):
                color = "#ffcccc"
                break
        cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;font-size:10px;text-align:center;padding:3px;'></div>")
    st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;'>{''.join(cells)}</div>", unsafe_allow_html=True)

# 満ブロック（常時表示）
st.markdown("### □満（前側・奥側 両方利用中）")
cells_full = []
for slot in TIME_SLOTS:
    s0 = parse_time(slot)
    e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
    front_used = any(
        (r["date"] == today) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
        for r in st.session_state["reservations"]["前側"]
    )
    back_used = any(
        (r["date"] == today) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
        for r in st.session_state["reservations"]["奥側"]
    )
    color = "#ff9999" if (front_used and back_used) else "#eeeeee"
    label = "満" if (front_used and back_used) else ""
    cells_full.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;font-size:10px;text-align:center;padding:3px;'>{label}</div>")
st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:20px;'>{''.join(cells_full)}</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# 使用状況一覧（常時表示）
# -------------------------------------------------------------
st.subheader("📋 使用状況一覧（当日）")

all_res = []
for rname, items in st.session_state["reservations"].items():
    for it in items:
        if it["date"] == today:
            all_res.append({"区画": rname, "開始": it["start"], "終了": it["end"], "氏名": it["user"], "目的": it["purpose"], "内線": it["extension"]})

if len(all_res) == 0:
    df_view = pd.DataFrame(columns=["区画", "開始", "終了", "氏名", "目的", "内線"])
else:
    df_view = pd.DataFrame(all_res).sort_values(by=["区画", "開始"])

st.data_editor(df_view, use_container_width=True, hide_index=True, num_rows="dynamic")

# -------------------------------------------------------------
# 登録フォーム
# -------------------------------------------------------------
st.divider()
st.subheader("📝 新しい予約を登録")

c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,2,1])
with c1:
    room_sel = st.selectbox("区画", ROOMS)
with c2:
    start_sel = st.selectbox("開始", TIME_SLOTS)
with c3:
    end_sel = st.selectbox("終了", TIME_SLOTS)
with c4:
    user = st.text_input("氏名", max_chars=16)
with c5:
    purpose = st.text_input("目的", placeholder="任意")
with c6:
    extension = st.text_input("内線", placeholder="例：1234")

if st.button("登録"):
    s = parse_time(start_sel)
    e = parse_time(end_sel)
    if e <= s:
        st.error("終了時刻は開始より後にしてください。")
    elif not user:
        st.error("氏名は必須です。")
    else:
        if register_reservation(room_sel, today, start_sel, end_sel, user, purpose, extension):
            st.success("登録が完了しました。")
            st.experimental_rerun()

# -------------------------------------------------------------
# 取消フォーム
# -------------------------------------------------------------
st.divider()
st.subheader("🗑️ 予約を取り消す")

all_res_cancel = []
for rname, items in st.session_state["reservations"].items():
    for it in items:
        if it["date"] == today:
            all_res_cancel.append({"room": rname, **it})

if all_res_cancel:
    df_cancel = pd.DataFrame(all_res_cancel)
    sel = st.selectbox("取消対象を選択", df_cancel.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1))
    if st.button("選択した予約を取り消す"):
        room, user, se = sel.split(" | ")
        start, end = se.split("〜")
        cancel_reservation(room, user, start, end, today)
else:
    st.caption("当日の予約はありません。")

st.caption("中央大学生活協同組合　情報通信チーム（v9：自動日付＋常時一覧＋前側・奥側・満 完全版）")
