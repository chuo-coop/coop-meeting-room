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
    st.session_state["reservations"] = {r: [] for r in ["前方区画", "後方区画", "全体利用"]}

ROOMS = ["前方区画", "後方区画", "全体利用"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 関数定義
# -------------------------------------------------------------
def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def parse_time(tstr: str) -> time:
    h, m = map(int, tstr.split(":"))
    return time(h, m)

# -------------------------------------------------------------
# 予約登録ロジック（時間完全一致で全体化）
# -------------------------------------------------------------
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
        return True

    # 半面予約時：全体利用との衝突防止
    for r in st.session_state["reservations"]["全体利用"]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]),
                                           parse_time(start), parse_time(end)):
            st.warning("この時間帯は全体利用で予約済みです。")
            return False

    # 半面登録
    st.session_state["reservations"][room].append(new_res)

    # 🔽 修正版：もう一方の区画と時間が「完全一致」した場合のみ全体化
    other = "後方区画" if room == "前方区画" else "前方区画"
    match_found = any(
        (r["date"] == date)
        and (r["start"] == start)
        and (r["end"] == end)
        for r in st.session_state["reservations"][other]
    )
    if match_found:
        st.session_state["reservations"]["全体利用"].append(new_res.copy())

    return True

# -------------------------------------------------------------
# 予約取消ロジック（全体連動）
# -------------------------------------------------------------
def cancel_reservation(room, user, start, end, date):
    # ---- 全体利用キャンセルなら3区画削除 ----
    if room == "全体利用":
        for target in ["全体利用", "前方区画", "後方区画"]:
            st.session_state["reservations"][target][:] = [
                r for r in st.session_state["reservations"][target]
                if not (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date)
            ]
        st.success("全体利用を取り消しました。")
        st.experimental_rerun()
        return

    # ---- 半面キャンセル時：全体との整合を取る ----
    other = "後方区画" if room == "前方区画" else "前方区画"

    # 自区画削除
    st.session_state["reservations"][room][:] = [
        r for r in st.session_state["reservations"][room]
        if not (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == date)
    ]

    # 他区画が同一時間で残っているか確認
    both_used = any(
        (r["date"] == date and r["start"] == start and r["end"] == end)
        for r in st.session_state["reservations"][other]
    )

    # 両方消えたら全体予約も削除
    if not both_used:
        st.session_state["reservations"]["全体利用"][:] = [
            r for r in st.session_state["reservations"]["全体利用"]
            if not (r["start"] == start and r["end"] == end and r["date"] == date)
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

    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示
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
        st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;overflow-x:auto;width:100%;'>{''.join(cells)}</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 登録フォーム（select_slider対応）
    # -------------------------------------------------------------
    st.divider()
    st.subheader("📝 新しい予約を登録")

    with st.form("add_reservation"):
        c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,2,1])
        with c1:
            room_sel = st.selectbox("区画", ROOMS)
        with c2:
            start_sel = st.select_slider("開始", options=TIME_SLOTS, value="12:00")
        with c3:
            end_sel = st.select_slider("終了", options=TIME_SLOTS, value="13:00")
        with c4:
            user = st.text_input("氏名", max_chars=16)
        with c5:
            purpose = st.text_input("目的", placeholder="任意")
        with c6:
            extension = st.text_input("内線", placeholder="例：1234")

        submitted = st.form_submit_button("登録")
        if submitted:
            s = parse_time(start_sel)
            e = parse_time(end_sel)
            if e <= s:
                st.error("終了時刻は開始より後にしてください。")
            elif not user.strip():
                st.warning("氏名を入力してください。")
            else:
                if register_reservation(room_sel, selected_date, start_sel, end_sel, user, purpose, extension):
                    st.success("登録が完了しました。")
                    st.experimental_rerun()

    # -------------------------------------------------------------
    # 取消ブロック
    # -------------------------------------------------------------
    st.divider()
    st.subheader("🗑️ 予約を取り消す")

    all_res = []
    for rname, items in st.session_state["reservations"].items():
        for it in items:
            if it["date"] == selected_date:
                all_res.append({"room": rname, **it})

    if all_res:
        df_cancel = pd.DataFrame(all_res)
        sel = st.selectbox(
            "削除する予約を選択",
            df_cancel.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1)
        )
        if st.button("選択した予約を取り消す"):
            room, user, se = sel.split(" | ")
            start, end = se.split("〜")
            cancel_reservation(room, user, start, end, selected_date)
    else:
        st.caption("当日の予約はありません。")

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（ver.2025.02：完全安定統合版）")
