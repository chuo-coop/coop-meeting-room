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
if "page" not in st.session_state:
    st.session_state["page"] = "calendar"

if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.now().date()

if "reservations" not in st.session_state:
    st.session_state["reservations"] = {r: [] for r in ["前方区画", "後方区画"]}

ROOMS = ["前方区画", "後方区画", "全面"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

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

    if room == "全面":
        targets = ["前方区画", "後方区画"]
    else:
        targets = [room]

    # 重複チェック
    for t in targets:
        for r in st.session_state["reservations"][t]:
            if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
                st.warning(f"{t} はこの時間帯に既に予約があります。")
                return False

    # 登録
    for t in targets:
        st.session_state["reservations"][t].append(new_res.copy())
    return True

def cancel_reservation(room, user, start, end, date):
    targets = ["前方区画", "後方区画"] if room == "全面" else [room]
    for t in targets:
        st.session_state["reservations"][t] = [
            r for r in st.session_state["reservations"][t]
            if not (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date)
        ]
    st.success("予約を取り消しました。")
    st.experimental_rerun()

def merge_reservations(date):
    """全面予約統合（前方・後方で同一内容を1行にまとめる）"""
    merged, seen = [], set()
    f_list = st.session_state["reservations"]["前方区画"]
    b_list = st.session_state["reservations"]["後方区画"]

    for f in f_list:
        if f["date"] != date:
            continue
        for b in b_list:
            if (b["date"] == date and f["start"] == b["start"] and f["end"] == b["end"]
                and f["user"] == b["user"]):
                key = (f["start"], f["end"], f["user"])
                seen.add(key)
                merged.append({"room": "全面", **f})
    for f in f_list:
        key = (f["start"], f["end"], f["user"])
        if f["date"] == date and key not in seen:
            merged.append({"room": "前方区画", **f})
    for b in b_list:
        key = (b["start"], b["end"], b["user"])
        if b["date"] == date and key not in seen:
            merged.append({"room": "後方区画", **b})
    return sorted(merged, key=lambda x: x["start"])

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
# 日別画面
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    selected_date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {selected_date} の利用状況")

    st.markdown("""
    <div style='display:flex;gap:24px;align-items:center;margin:6px 0 14px 2px;font-size:14px;'>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ccffcc;border:1px solid #999;'></span>空室</div>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ffcccc;border:1px solid #999;'></span>予約済</div>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ff6666;border:1px solid #999;'></span>全面利用</div>
    </div>
    """, unsafe_allow_html=True)

    for room in ["前方区画", "後方区画"]:
        st.markdown(f"### 🏢 {room}")
        res_list = st.session_state["reservations"][room]
        cells = []
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color = "#ccffcc"
            for r in res_list:
                if (r["date"] == selected_date) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0):
                    color = "#ffcccc"
                    break
            cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;font-size:10px;text-align:center;padding:3px;'>{slot}</div>")
        st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;'>{''.join(cells)}</div>", unsafe_allow_html=True)

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
        elif register_reservation(room_sel, selected_date, start_sel, end_sel, user, purpose, extension):
            st.success("登録が完了しました。")
            st.experimental_rerun()

    st.divider()
    st.subheader("🗑️ 予約を取り消す")
    all_res = merge_reservations(selected_date)
    if all_res:
        df_cancel = pd.DataFrame(all_res)
        df_cancel["display"] = df_cancel.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1)
        sel = st.selectbox("削除する予約を選択", df_cancel["display"])
        if st.button("選択した予約を取り消す"):
            room, user, se = sel.split(" | ")
            start, end = se.split("〜")
            cancel_reservation(room, user, start, end, selected_date)
    else:
        st.caption("当日の予約はありません。")

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v3.4.4+ 機能追加固定版）")
