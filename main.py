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
    input_pw = st.text_input("パスワードを入力してください", type="password", key="pw_input", max_chars=16)
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
    st.session_state["reservations"] = {r: [] for r in ["前側", "奥側"]}

ROOMS = ["前側", "奥側", "全面"]
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
    """全面予約時は前側＋奥側を同時登録"""
    if room == "全面":
        ok1 = register_reservation("前側", date, start, end, user, purpose, extension)
        ok2 = register_reservation("奥側", date, start, end, user, purpose, extension)
        if ok1 and ok2:
            return True
        return False

    # 全面利用との重複チェック
    other = "奥側" if room == "前側" else "前側"
    for r in st.session_state["reservations"][other]:
        if (r["date"] == date) and (r["user"] == user) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning("同一時間帯に他区画で予約があります。")
            return False

    for r in st.session_state["reservations"][room]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning(f"{room} はこの時間帯に既に予約があります。")
            return False

    st.session_state["reservations"][room].append({
        "date": date, "start": start, "end": end,
        "user": user, "purpose": purpose, "extension": extension
    })
    return True

def cancel_reservation(room, user, start, end, date):
    """全面取消対応"""
    if room == "全面":
        cancel_reservation("前側", user, start, end, date)
        cancel_reservation("奥側", user, start, end, date)
        return
    st.session_state["reservations"][room] = [
        r for r in st.session_state["reservations"][room]
        if not (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date)
    ]
    st.success("予約を取り消しました。")
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")

    selected = st.date_input("日付を選択", st.session_state["selected_date"])
    st.session_state["selected_date"] = selected

    if st.button("この日の予約状況を見る", use_container_width=True):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別画面
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    selected_date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {selected_date} の利用状況")

    # 凡例
    st.markdown("""
    <div style='display:flex;gap:24px;align-items:center;margin:6px 0 14px 2px;font-size:14px;'>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ccffcc;border:1px solid #999;'></span>空室</div>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ffcccc;border:1px solid #999;'></span>予約済</div>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ff6666;border:1px solid #999;'></span>満室（全面）</div>
    </div>
    """, unsafe_allow_html=True)

    # スケジュール表示
    for room in ["前側", "奥側"]:
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
            cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;font-size:11px;text-align:center;padding:3px;'>{slot}</div>")
        st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;'>{''.join(cells)}</div>", unsafe_allow_html=True)

    # 満室表示（全面）
    front_used = any(r["date"] == selected_date for r in st.session_state["reservations"]["前側"])
    back_used = any(r["date"] == selected_date for r in st.session_state["reservations"]["奥側"])
    if front_used and back_used:
        st.markdown("<div style='background:#ff6666;color:white;text-align:center;padding:6px;font-weight:bold;'>全面利用中（満室）</div>", unsafe_allow_html=True)

    st.divider()

    # 📝 新しい予約登録
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

    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    if st.button("登録", use_container_width=False):
        s = parse_time(start_sel)
        e = parse_time(end_sel)
        if e <= s:
            st.error("終了時刻は開始より後にしてください。")
        elif not user:
            st.error("氏名は必須です。")
        else:
            if register_reservation(room_sel, selected_date, start_sel, end_sel, user, purpose, extension):
                st.success("登録が完了しました。")
                st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # 🗑️ 予約取消
    st.subheader("🗑️ 予約を取り消す")

    all_res = []
    for rname, items in st.session_state["reservations"].items():
        for it in items:
            if it["date"] == selected_date:
                all_res.append({"room": rname, **it})

    if all_res:
        df_cancel = pd.DataFrame(all_res)
        df_cancel = df_cancel.sort_values(by="start")
        df_cancel["display"] = df_cancel.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1)
        sel = st.selectbox("削除する予約を選択", df_cancel["display"])
        if st.button("選択した予約を取り消す", use_container_width=False):
            room, user, se = sel.split(" | ")
            start, end = se.split("〜")
            cancel_reservation(room, user, start, end, selected_date)
    else:
        st.caption("当日の予約はありません。")

    if st.button("⬅ カレンダーへ戻る", use_container_width=True):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v3.5 最終固定版）")
