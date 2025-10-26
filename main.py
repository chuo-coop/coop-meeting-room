# =========================================================
# 中大生協 会議室予約システム v3.4.6（安定修正版）
# （全面利用対応版：登録・一覧統合・一括取消）
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

ROOMS = ["前側", "奥側", "全面"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 関数定義
# -------------------------------------------------------------
def parse_time(tstr):
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def has_conflict(room, date, start, end):
    date_str = str(date)
    for subroom in ["前側", "奥側"]:
        for r in st.session_state["reservations"][subroom]:
            if str(r.get("date")) == date_str and r.get("status") == "active" and r["user"].endswith("(全面)"):
                if overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
                    return True
    targets = ["前側", "奥側"] if room == "全面" else [room]
    for sub in targets:
        for r in st.session_state["reservations"][sub]:
            if str(r.get("date")) == date_str and r.get("status", "active") == "active":
                s1, e1 = parse_time(r["start"]), parse_time(r["end"])
                s2, e2 = parse_time(start), parse_time(end)
                if overlap(s1, e1, s2, e2):
                    return True
    return False

def register_reservation(room, date, start, end, user, purpose, ext):
    if room == "全面":
        for subroom in ["前側", "奥側"]:
            if has_conflict(subroom, date, start, end):
                st.warning(f"{subroom}に既存の予約があります。全面予約できません。")
                return
        for subroom in ["前側", "奥側"]:
            new = {
                "date": str(date),
                "start": start,
                "end": end,
                "user": f"{user}(全面)",
                "purpose": purpose,
                "ext": ext,
                "status": "active",
                "cancel": "",
            }
            st.session_state["reservations"][subroom].append(new)
        st.session_state["pending_register"] = None
        st.success("✅ 全面予約を登録しました。")
        st.experimental_rerun()
    else:
        new = {
            "date": str(date),
            "start": start,
            "end": end,
            "user": user,
            "purpose": purpose,
            "ext": ext,
            "status": "active",
            "cancel": "",
        }
        st.session_state["reservations"][room].append(new)
        st.session_state["pending_register"] = None
        st.success("✅ 登録が完了しました。")
        st.experimental_rerun()

def cancel_reservation(room, user, start, end, date):
    for r in st.session_state["reservations"][room]:
        if r["user"] == user and r["start"] == start and r["end"] == end and str(r["date"]) == str(date):
            r["status"] = "cancel"
            r["cancel"] = datetime.now().strftime("%Y-%m-%d")
    st.session_state["pending_cancel"] = None
    st.success("🗑️ 予約を取り消しました。")
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
# 日別表示
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {date} の利用状況")

    # --- 取消処理 ---
    st.divider()
    st.subheader("🗑️ 予約取消")

    cancels = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if str(r["date"]) == str(date) and r["status"] == "active":
                cancels.append(f"{room} | {r['user']} | {r['start']}〜{r['end']}")

    pairs = []
    for r in st.session_state["reservations"]["前側"]:
        for s in st.session_state["reservations"]["奥側"]:
            if (r["user"] == s["user"]
                and r["start"] == s["start"]
                and r["end"] == s["end"]
                and str(r["date"]) == str(s["date"])
                and r["status"] == "active"
                and s["status"] == "active"):
                pairs.append(f"全面 | {r['user']} | {r['start']}〜{r['end']}")

    cancels = list(dict.fromkeys(cancels + pairs))

    if cancels:
        sel = st.selectbox("取消対象を選択", cancels, key=f"cancel_sel_{date}")
        if st.button("取消"):
            room, user, t = sel.split(" | ")
            start, end = t.split("〜")
            st.session_state["pending_cancel"] = {"room": room, "user": user, "start": start, "end": end, "date": date}

    if st.session_state["pending_cancel"]:
        d = st.session_state["pending_cancel"]
        st.markdown(f"<div style='border:2px solid #900;padding:10px;background:#fff0f0;text-align:center;'>"
                    f"<b>取消確認：</b><br>{d['room']}　{d['start']}〜{d['end']}　{d['user']}<br>本当に取り消しますか？</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("はい、取消する"):
                    if d["room"] == "全面":
                        for sub in ["前側", "奥側"]:
                            for r in st.session_state["reservations"][sub]:
                                if ((r["user"] == d["user"]) or (r["user"] == f"{d['user']}(全面)") or (d["user"] in r["user"])) \
                                    and r["start"] == d["start"] \
                                    and r["end"] == d["end"] \
                                    and str(r["date"]) == str(d["date"]) \
                                    and r["status"] == "active":
                                    r["status"] = "cancel"
                                    r["cancel"] = datetime.now().strftime("%Y-%m-%d")
                        st.success("🗑️ 全面予約を取り消しました。")
                    else:
                        cancel_reservation(**d)
                    # ← 修正：リセットを明示
                    st.session_state["pending_cancel"] = None
                    st.experimental_rerun()
            with b2:
                if st.button("戻る"):
                    st.session_state["pending_cancel"] = None

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v3.4.6 安定修正版）")
