import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, time

# -------------------------------------------------------------
# 設定
# -------------------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")
DATA_PATH = "data/reservations.csv"
os.makedirs("data", exist_ok=True)

PASSWORD = "coop"

ROOMS = ["前方区画", "後方区画", "全体利用"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# セッション初期化
# -------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "page" not in st.session_state:
    st.session_state["page"] = "calendar"
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.now().date()
if "reservations" not in st.session_state:
    st.session_state["reservations"] = {r: [] for r in ROOMS}

# -------------------------------------------------------------
# CSV 永続化（読み書き）
# -------------------------------------------------------------
def save_reservations():
    all_res = []
    for room, items in st.session_state["reservations"].items():
        for it in items:
            # store date as ISO string for portability
            dcopy = it.copy()
            if isinstance(dcopy.get("date"), datetime):
                dcopy["date"] = dcopy["date"].date().isoformat()
            elif isinstance(dcopy.get("date"), (str,)):
                # assume already string in ISO
                pass
            all_res.append({"room": room, **dcopy})
    pd.DataFrame(all_res).to_csv(DATA_PATH, index=False)

def load_reservations():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        for _, row in df.iterrows():
            d = row.to_dict()
            room = d.pop("room")
            # normalize date to datetime.date
            if "date" in d and isinstance(d["date"], str):
                try:
                    d["date"] = datetime.strptime(d["date"], "%Y-%m-%d").date()
                except Exception:
                    # leave as-is (fallback)
                    pass
            # ensure keys exist for safety
            for k in ("start", "end", "user", "purpose", "extension"):
                if k not in d:
                    d[k] = ""
            if room in st.session_state["reservations"]:
                st.session_state["reservations"][room].append(d)

# load once at startup
load_reservations()

# -------------------------------------------------------------
# ユーティリティ
# -------------------------------------------------------------
def parse_time(tstr):
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def overlap(s1, e1, s2, e2):
    return s1 < e2 and s2 < e1

def to_date(d):
    if isinstance(d, str):
        try:
            return datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            return d
    return d

# -------------------------------------------------------------
# 整合処理（全体利用は前方/後方の重なりから算出）
# ※ ここでは保存は行わない（pure function-ish）
# -------------------------------------------------------------
def sync_full_room(date):
    front = st.session_state["reservations"]["前方区画"]
    back = st.session_state["reservations"]["後方区画"]
    full_new = []

    for f in front:
        for b in back:
            if (
                to_date(f.get("date")) == to_date(b.get("date")) == date
                and overlap(parse_time(f["start"]), parse_time(f["end"]),
                            parse_time(b["start"]), parse_time(b["end"]))
            ):
                entry = {
                    "date": date,
                    "start": min(f["start"], b["start"]),
                    "end": max(f["end"], b["end"]),
                    "user": f.get("user", ""),
                    "purpose": f.get("purpose", ""),
                    "extension": f.get("extension", "")
                }
                # avoid duplicates with same start/end/date
                if not any(r["date"] == entry["date"] and r["start"] == entry["start"] and r["end"] == entry["end"] for r in full_new):
                    full_new.append(entry)

    # replace only the target day's full entries
    st.session_state["reservations"]["全体利用"] = [
        r for r in st.session_state["reservations"]["全体利用"] if to_date(r.get("date")) != date
    ] + full_new

# -------------------------------------------------------------
# 登録処理（保存はここで一度だけ）
# -------------------------------------------------------------
def register_reservation(room, date, start, end, user, purpose, extension):
    new = {"date": date, "start": start, "end": end, "user": user, "purpose": purpose, "extension": extension}

    # 全体予約の競合チェック
    if room == "全体利用":
        for rname in ("前方区画", "後方区画"):
            for r in st.session_state["reservations"][rname]:
                if to_date(r.get("date")) == date and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
                    st.warning(f"{rname} に既に予約があります。全体利用はできません。")
                    return False
        # add to all three lists: keep stored representation simple
        for rname in ROOMS:
            st.session_state["reservations"][rname].append(new.copy())
        save_reservations()
        # no rerun here; form submission will naturally re-render
        return True

    # 半面予約：全体にぶつかってないか確認
    for r in st.session_state["reservations"]["全体利用"]:
        if to_date(r.get("date")) == date and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning("この時間帯は全体利用で予約済みです。")
            return False

    st.session_state["reservations"][room].append(new)
    # recompute full view for this date (no save inside)
    sync_full_room(date)
    save_reservations()  # save once after sync
    # do not call st.experimental_rerun() — avoid double re-eval
    st.success("登録完了。")
    return True

# -------------------------------------------------------------
# 取消処理（同様に保存はここで一回）
# -------------------------------------------------------------
def cancel_reservation(room, user, start, end, date):
    for rname in ROOMS:
        st.session_state["reservations"][rname] = [
            r for r in st.session_state["reservations"][rname]
            if not (to_date(r.get("date")) == date and r.get("start") == start and r.get("end") == end and r.get("user") == user and (room == "全体利用" or rname == room))
        ]
    sync_full_room(date)
    save_reservations()
    st.success("予約を取り消しました。")
    # avoid rerun; UI will refresh on next interaction
    return

# -------------------------------------------------------------
# UI：カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    selected = st.date_input("日付を選択", st.session_state["selected_date"])
    st.session_state["selected_date"] = selected
    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()  # page switch, keep rerun

# -------------------------------------------------------------
# UI：日別表示（登録・取消）
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    date = st.session_state["selected_date"]
    # ensure full view reflects current data for the date
    sync_full_room(date)

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
                if to_date(r.get("date")) == date and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0):
                    color = "#ffcccc"
                    break
            cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;font-size:10px;padding:2px;'>{slot}</div>")
        st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;overflow-x:auto'>{''.join(cells)}</div>", unsafe_allow_html=True)

    # 登録フォーム
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
            ext = st.text_input("内線", placeholder="例：1234")
        sub = st.form_submit_button("登録")

        if sub:
            s, e = parse_time(start_sel), parse_time(end_sel)
            if e <= s:
                st.error("終了時刻は開始より後にしてください。")
            elif not user.strip():
                st.warning("氏名を入力してください。")
            else:
                ok = register_reservation(room_sel, date, start_sel, end_sel, user, purpose, ext)
                # no explicit rerun; form submit causes a rerender and success message shows

    # 削除フォーム
    st.divider()
    st.subheader("🗑️ 予約を取り消す")
    all_res = []
    for rname, items in st.session_state["reservations"].items():
        for it in items:
            if to_date(it.get("date")) == date:
                all_res.append({"room": rname, **it})

    if all_res:
        df = pd.DataFrame(all_res)
        sel = st.selectbox("削除する予約を選択",
                           df.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1))
        if st.button("選択した予約を取り消す"):
            room, user, se = sel.split(" | "); start, end = se.split("〜")
            cancel_reservation(room, user, start, end, date)
            # no rerun; UI will refresh on next interaction
    else:
        st.caption("当日の予約はありません。")

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム　ver.2025.08e（反応速度最適化版）")
