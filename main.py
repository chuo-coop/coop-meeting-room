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
    st.session_state["reservations"] = {r: [] for r in ["前側", "奥側"]}

ROOMS = ["前側", "奥側"]
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
    new_res = {
        "date": date,
        "start": start,
        "end": end,
        "user": user,
        "purpose": purpose,
        "extension": extension,
        "status": "active",
        "cancelled_by": None,
    }

    # 競合チェック
    for r in st.session_state["reservations"][room]:
        if (r["date"] == date) and (r["status"] == "active") and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning(f"{room} のこの時間帯はすでに予約があります。")
            return False

    st.session_state["reservations"][room].append(new_res)
    return True

def cancel_reservation(room, user, start, end, date, cancelled_by):
    for r in st.session_state["reservations"][room]:
        if (
            r["user"] == user
            and r["start"] == start
            and r["end"] == end
            and r["date"] == date
            and r["status"] == "active"
        ):
            r["status"] = "cancelled"
            r["cancelled_by"] = cancelled_by
            st.success("予約を取り消しました。")
            st.experimental_rerun()
            return
    st.error("一致する予約が見つかりませんでした。")

def is_full(selected_date):
    """前側と奥側の両方が同時間帯で予約されている場合に「満」を返す"""
    res_a = st.session_state["reservations"]["前側"]
    res_b = st.session_state["reservations"]["奥側"]
    for a in res_a:
        if a["date"] != selected_date or a["status"] != "active":
            continue
        for b in res_b:
            if b["date"] != selected_date or b["status"] != "active":
                continue
            if overlap(parse_time(a["start"]), parse_time(a["end"]), parse_time(b["start"]), parse_time(b["end"])):
                return True
    return False

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
# 日別表示（登録・取消含む）
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    selected_date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {selected_date} の利用状況")

    # 満インジケーター
    if is_full(selected_date):
        st.markdown("<div style='font-size:18px;color:#d00;font-weight:bold;'>□満</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size:18px;color:#666;'>□空</div>", unsafe_allow_html=True)

    # 利用状況（現）
    st.divider()
    st.subheader("🔸 現在の利用状況")

    any_active = False
    for room in ROOMS:
        res_list = [r for r in st.session_state["reservations"][room] if r["date"] == selected_date]
        if res_list:
            st.markdown(f"### 🏢 {room}")
            for r in sorted(res_list, key=lambda x: x["start"]):
                text = f"{r['start']}〜{r['end']}　{r['user']}"
                if r["purpose"]:
                    text += f"　{r['purpose']}"
                if r["extension"]:
                    text += f"（内線 {r['extension']}）"

                if r["status"] == "cancelled":
                    text = f"<span style='text-decoration:line-through;color:#777;'>{text}</span>"
                st.markdown(text, unsafe_allow_html=True)
                any_active = True
    if not any_active:
        st.caption("当日の予約はありません。")

    # 新規登録
    st.divider()
    st.subheader("📝 新しい予約を登録")

    c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,2,1])
    with c1:
        room_sel = st.selectbox("区分", ROOMS)
    with c2:
        start_sel = st.selectbox("開始", TIME_SLOTS)
    with c3:
        end_sel = st.selectbox("終了", TIME_SLOTS)
    with c4:
        user = st.text_input("担当者（苗字）", max_chars=16)
    with c5:
        purpose = st.text_input("目的（任意）", placeholder="例：打合せ")
    with c6:
        extension = st.text_input("内線（任意）", placeholder="例：1234")

    if st.button("登録"):
        s = parse_time(start_sel)
        e = parse_time(end_sel)
        if e <= s:
            st.error("終了時刻は開始より後にしてください。")
        elif not user:
            st.error("担当者名（苗字）は必須です。")
        else:
            if register_reservation(room_sel, selected_date, start_sel, end_sel, user, purpose, extension):
                st.success("登録が完了しました。")
                st.experimental_rerun()

    # 取消登録
    st.divider()
    st.subheader("🗑️ 予約を取り消す（履歴保持）")

    all_res = []
    for rname, items in st.session_state["reservations"].items():
        for it in items:
            if it["date"] == selected_date and it["status"] == "active":
                all_res.append({"room": rname, **it})

    if all_res:
        df_cancel = pd.DataFrame(all_res)
        sel = st.selectbox(
            "取り消す予約を選択",
            df_cancel.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1),
        )
        cancel_by = st.text_input("取り消し担当者（苗字）", max_chars=16)
        if st.button("取消を登録"):
            if not cancel_by:
                st.error("取り消し担当者の入力は必須です。")
            else:
                room, user, se = sel.split(" | ")
                start, end = se.split("〜")
                cancel_reservation(room, user, start, end, selected_date, cancel_by)
    else:
        st.caption("取り消し可能な予約はありません。")

    # 戻るボタン
    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（改良版：満表示＋現利用＋取消履歴）")
