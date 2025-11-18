# =========================================================
# 中大生協 会議室予約システム v3.4.7 Full（Memory Extension, Fixed)
# - GCPスコープ明示（RefreshError防止）
# - Sheets保存時は《全面》を1行に統合
# - 読込時は《全面》を前側/奥側の2件に復元（内部処理互換）
# - 取消候補は重複除去（全面1行のみ表示）
# =========================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import gspread
from google.oauth2.service_account import Credentials

# -------------------------------------------------------------
# ページ設定
# -------------------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")

# -------------------------------------------------------------
# ログイン認証（必要ならPASSWORDを設定）
# -------------------------------------------------------------
PASSWORD = ""
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

# -------------------------------------------------------------
# Google Sheets 永続化設定
# -------------------------------------------------------------
SHEET_ID = "1ebbNq681Loz2r-_Wkgbd_6qABN_H1GzsG2Ja0p9JJOg"

def get_gsheet():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

@st.cache_data(ttl=30)
def load_reservations_from_gsheet():
    """Sheetsから読み込み。全面1行は内部で前側/奥側の2件に展開し、user名は(全面)を付与して互換維持"""
    try:
        sheet = get_gsheet()
        records = sheet.get_all_records()
        st.session_state["reservations"] = {"前側": [], "奥側": []}
        for row in records:
            room = row.get("区画", "")
            date = row.get("日付", "")
            start = row.get("開始", "")
            end = row.get("終了", "")
            user = row.get("担当者", "")
            purpose = row.get("目的", "")
            ext = row.get("内線", "")
            status = row.get("状態", "")
            cancel = row.get("取消日", "")

            if room == "全面":
                for sub in ["前側", "奥側"]:
                    st.session_state["reservations"][sub].append({
                        "date": date,
                        "start": start,
                        "end": end,
                        "user": f"{user}(全面)",
                        "purpose": purpose,
                        "ext": ext,
                        "status": status or "active",
                        "cancel": cancel or "",
                    })
            elif room in ["前側", "奥側"]:
                st.session_state["reservations"][room].append({
                    "date": date,
                    "start": start,
                    "end": end,
                    "user": user,
                    "purpose": purpose,
                    "ext": ext,
                    "status": status or "active",
                    "cancel": cancel or "",
                })
        st.caption("📗 Google Sheetsから既存データを読み込みました。")
    except Exception as e:
        st.warning(f"Google Sheetsの読み込みに失敗しました（初回または権限）。{e}")

def save_reservations_to_gsheet():
    """内部の前側/奥側データを、Sheets保存時に《全面》1行へ統合（同一キーで両室が揃っていれば全面）"""
    try:
        sheet = get_gsheet()

        def _norm_user(u: str) -> str:
            return (u or "").replace("(全面)", "")

        # keyでグルーピング（前側/奥側の揃いを検出）
        buf = {}  # key -> {"rooms": set(), "purpose": str, "ext": str}
        # key = (date, start, end, user_norm, status, cancel)
        for room, items in st.session_state["reservations"].items():
            for r in items:
                key = (
                    str(r.get("date")),
                    r.get("start"),
                    r.get("end"),
                    _norm_user(r.get("user", "")),
                    r.get("status", "active"),
                    r.get("cancel", ""),
                )
                if key not in buf:
                    buf[key] = {"rooms": set(), "purpose": r.get("purpose", ""), "ext": r.get("ext", "")}
                buf[key]["rooms"].add(room)
                # latest purpose/ext wins（同一キー内で差異ない前提）

        # 書き出し配列を生成
        all_data = []
        for (date, start, end, user_norm, status, cancel), meta in buf.items():
            out_room = "全面" if {"前側", "奥側"}.issubset(meta["rooms"]) else list(meta["rooms"])[0]
            all_data.append([
                out_room, date, start, end, user_norm,  # （全面）は外した素の担当者名で保存
                meta.get("purpose", ""), meta.get("ext", ""),
                status, cancel
            ])

        # ヘッダ＋本体で更新
        sheet.clear()
        sheet.update([
            ["区画", "日付", "開始", "終了", "担当者", "目的", "内線", "状態", "取消日"],
            *all_data
        ])
        st.caption("💾 Google Sheetsに保存しました。")
    except Exception as e:
        st.error(f"Google Sheetsへの保存に失敗しました: {e}")

# 起動時にデータ読込
load_reservations_from_gsheet()

ROOMS = ["前側", "奥側", "全面"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 関数定義（UI内ロジック）
# -------------------------------------------------------------
def parse_time(tstr):
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def has_conflict(room, date, start, end):
    """全面予約時は前/奥のどちらかに衝突があれば不可"""
    date_str = str(date)
    # 既存の全面扱い（userが(全面)付き）のブロッキング
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
        # 片側にでも衝突があれば全面不可
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
        save_reservations_to_gsheet()
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
        save_reservations_to_gsheet()
        st.session_state["pending_register"] = None
        st.success("✅ 登録が完了しました。")
        st.experimental_rerun()

def cancel_reservation(room, user, start, end, date):
    for r in st.session_state["reservations"][room]:
        if (
            (r["user"] == user or r["user"] == f"{user}(全面)" or user in r["user"])
            and r["start"] == start
            and r["end"] == end
            and str(r["date"]) == str(date)
            and r.get("status") == "active"
        ):
            r["status"] = "cancel"
            r["cancel"] = datetime.now().strftime("%Y-%m-%d")
    save_reservations_to_gsheet()
    st.session_state["pending_cancel"] = None
    st.success("🗑️ 予約を取り消しました。")
    st.experimental_rerun()
def render_day_indicator(date):
    """既存の“日別インジケータ”描画ロジックを日単位で再利用（閲覧専用）"""
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    w = weekday_map[date.weekday()]

    for layer in ["前側", "奥側"]:
        row = [
            f"<div style='width:60px;text-align:center;font-weight:600;font-size:14px;border:1px solid #999;background:#f9f9f9;'>{layer}</div>"
        ]
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            active = any(
                r["status"] == "active"
                and str(r["date"]) == str(date)
                and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                for r in st.session_state["reservations"][layer]
            )
            color = "#ffcccc" if active else "#ccffcc"
            text = f"<span style='font-size:12px;font-weight:500;'>{slot}</span>"
            row.append(
                f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;padding:2px;'>{text}</div>"
            )
        st.markdown(f"<div style='display:flex;'>{''.join(row)}</div>", unsafe_allow_html=True)
    st.markdown("---")

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")

    selected = st.date_input("日付を選択", datetime.now().date())
    st.session_state["selected_date"] = selected

    # 選択した日を含む週（月曜〜日曜）を作る
    start_of_week = selected - timedelta(days=selected.weekday())
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

    # 週データを保存
    st.session_state["selected_week"] = week_dates

    if st.button("この週の予約状況を見る"):
        st.session_state["page"] = "week_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 週間表示（閲覧のみ）
# -------------------------------------------------------------
elif st.session_state["page"] == "week_view":
    st.title("📅 週間利用状況")
    # --- 🔄 データ再読み込みボタンをここに追加 ---
    if st.button("🔄 データを再読み込み"):
        with st.spinner("Google Sheets から最新データを取得中..."):
            load_reservations_from_gsheet()
        st.success("✅ 最新データを読み込みました。")
        st.experimental_rerun()
    # --- ここまで追加 ---
    week = st.session_state.get("selected_week", [])
    if not week:
        st.warning("⚠️ 週データが見つかりません。カレンダーから再選択してください。")
        st.stop()

    for d in week:
        weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
        w = weekday_map[d.weekday()]
        col_date, col_btn = st.columns([7, 3])
        with col_date:
            st.markdown(f"### 📅 {d.strftime('%Y-%m-%d')}（{w}）")
        with col_btn:
            st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)
            if st.button("🔍 この日の予約を見る", key=f"btn_{d}"):
                st.session_state["selected_date"] = d
                st.session_state["page"] = "day_view"
                st.experimental_rerun()

        # 週用の簡易インジケータ（空満）
        for idx, layer in enumerate(["前側", "奥側"]):
            label = ["前側", "奥側",][idx]
            row = [
                f"<div style='width:60px;text-align:center;font-weight:600;font-size:14px;border:1px solid #999;background:#f9f9f9;'>{label}</div>"
            ]
            for slot in TIME_SLOTS:
                s0 = parse_time(slot)
                e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
                color, text = "#ffffff", ""
                if layer in ["前側", "奥側"]:
                    active = any(
                        r["status"] == "active"
                        and str(r["date"]) == str(d)
                        and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                        for r in st.session_state["reservations"][layer]
                    )
                    color = "#ffcccc" if active else "#ccffcc"
                    text = f"<span style='font-size:14px;font-weight:500;'>{slot}</span>"
                else:
                    # ← ここは d（日付）を使う
                    front_busy = any(
                        r["status"] == "active"
                        and str(r["date"]) == str(d)
                        and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                        for r in st.session_state["reservations"]["前側"]
                    )
                    back_busy = any(
                        r["status"] == "active"
                        and str(r["date"]) == str(d)
                        and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                        for r in st.session_state["reservations"]["奥側"]
                    )
                    if front_busy and back_busy:
                        color = "#ff3333"
                        text = "<b><span style='color:white;font-size:15px;'>満</span></b>"
                row.append(
                    f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;padding:4px;'>{text}</div>"
                )
            st.markdown(f"<div style='display:flex;'>{''.join(row)}</div>", unsafe_allow_html=True)

    st.markdown("---")
   # --- 週移動ボタン ---
    col_prev, col_home, col_next = st.columns(3)

    with col_prev:
        if st.button("⬅ 前週"):
            week = st.session_state.get("selected_week", [])
            if week:
                new_start = week[0] - timedelta(days=7)
                st.session_state["selected_week"] = [new_start + timedelta(days=i) for i in range(7)]
                st.experimental_rerun()

    with col_home:
        if st.button("📅 カレンダーに戻る"):
            st.session_state["page"] = "calendar"
            st.experimental_rerun()

    with col_next:
        if st.button("次週 ➡"):
            week = st.session_state.get("selected_week", [])
            if week:
                new_start = week[0] + timedelta(days=7)
                st.session_state["selected_week"] = [new_start + timedelta(days=i) for i in range(7)]
                st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示（詳細）
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    date = st.session_state["selected_date"]
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    w = weekday_map[date.weekday()]
    st.markdown(f"## 📅 {date}（{w}）の利用状況")

    # --- インジケータ（赤：使用中／緑：空き／満：両室占有） ---
    st.markdown("### 🏢 会議室 利用状況")
    for idx, layer in enumerate(["前側", "奥側", "空満"]):
        label = ["前側", "奥側", "空満"][idx]
        row = [
            f"<div style='width:60px;text-align:center;font-weight:600;font-size:14px;border:1px solid #999;background:#f9f9f9;'>{label}</div>"
        ]
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color, text = "#ffffff", ""
            if layer in ["前側", "奥側"]:
                active = any(
                    r["status"] == "active"
                    and str(r["date"]) == str(date)
                    and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"][layer]
                )
                color = "#ffcccc" if active else "#ccffcc"
                text = f"<span style='font-size:14px;font-weight:500;'>{slot}</span>"
            else:
                front_busy = any(
                    r["status"] == "active"
                    and str(r["date"]) == str(date)
                    and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"]["前側"]
                )
                back_busy = any(
                    r["status"] == "active"
                    and str(r["date"]) == str(date)
                    and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"]["奥側"]
                )
                if front_busy and back_busy:
                    color = "#ff3333"
                    text = "<b><span style='color:white;font-size:15px;'>満</span></b>"
            row.append(
                f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;padding:4px;'>{text}</div>"
            )
        st.markdown(f"<div style='display:flex;'>{''.join(row)}</div>", unsafe_allow_html=True)

    # （この下の「一覧表／登録／取消／戻る」ロジックは現行のまま）

    # --- 一覧表（全面統合表示） ---
    st.divider()
    st.markdown("### 📋 使用状況一覧（時間順）")
    all_recs = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if str(r["date"]) == str(date):
                all_recs.append({
                    "区画": room,
                    "時間": f"{r['start']}〜{r['end']}",
                    "担当者": r["user"].replace("(全面)", ""),   # ← この1行だけ変更
                    "目的": r["purpose"],
                    "内線": r["ext"],
                    "状態": "取消" if r["status"] == "cancel" else "有効",
                    "取消日": r["cancel"]
                })

    # 前側+奥側の同一（担当者/時間/状態）を全面へ統合表示
    merged = []
    seen = set()
    for i, r1 in enumerate(all_recs):
        if i in seen:
            continue
        same = [r for r in all_recs if r["担当者"] == r1["担当者"]
                and r["時間"] == r1["時間"]
                and r["状態"] == r1["状態"]
                and r["区画"] in ["前側", "奥側"]]
        if len(same) == 2:
            merged.append({**r1, "区画": "全面"})
            seen.update([all_recs.index(x) for x in same])
        else:
            merged.append(r1)

    if merged:
        df = pd.DataFrame(merged).sort_values(by="時間")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("当日の予約はありません。")

    # --- 登録 ---
    st.divider()
    st.subheader("📝 新しい予約を登録")

    c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 2, 1])
    room = c1.selectbox("区画", ROOMS)
    start = c2.selectbox("開始", TIME_SLOTS)
    end = c3.selectbox("終了", TIME_SLOTS)
    user = c4.text_input("担当者")
    purpose = c5.text_input("目的（任意）")
    ext = c6.text_input("内線（任意）")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    btn_center = st.columns([1, 1, 1])[1]
    with btn_center:
        if st.button("登録", use_container_width=True):
            if not user:
                st.error("担当者名を入力してください。")
            elif parse_time(end) <= parse_time(start):
                st.error("終了時刻は開始より後にしてください。")
            elif has_conflict(room, date, start, end):
                st.warning("⚠️ この時間帯はすでに予約されています。")
            else:
                st.session_state["pending_register"] = {"room": room, "date": date, "start": start, "end": end,
                                                         "user": user, "purpose": purpose, "ext": ext}

    if st.session_state["pending_register"]:
        d = st.session_state["pending_register"]
        st.markdown(f"<div style='border:2px solid #666;padding:10px;background:#f0f0f0;text-align:center;'>"
                    f"<b>登録内容確認：</b><br>{d['room']}　{d['start']}〜{d['end']}　{d['user']}<br>これで登録しますか？</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("はい、登録する"):
                    register_reservation(**d)
            with b2:
                if st.button("戻る"):
                    st.session_state["pending_register"] = None

    # --- 取消 ---
    st.divider()
    st.subheader("🗑️ 予約取消")

    # まず、前側/奥側のペアを検出（キー：担当者・時間）
    pairs_set = set()
    for r in st.session_state["reservations"]["前側"]:
        for s in st.session_state["reservations"]["奥側"]:
            if (r["user"] == s["user"]
                and r["start"] == s["start"]
                and r["end"] == s["end"]
                and str(r["date"]) == str(s["date"])
                and r["status"] == "active"
                and s["status"] == "active"):
                pairs_set.add((r["user"], r["start"], r["end"], str(r["date"])))

    # 取消候補を重複なく構築。ペアがある場合は《全面》のみ出す
    cancels = []
    seen_keys = set()
    for room_name, items in st.session_state["reservations"].items():
        for r in items:
            if str(r["date"]) == str(date) and r["status"] == "active":
                key = (r["user"], r["start"], r["end"], str(r["date"]))
                if key in seen_keys:
                    continue
                if key in pairs_set:
                    cancels.append(f"全面 | {r['user'].replace('(全面)', '')} | {r['start']}〜{r['end']}")
                else:
                    cancels.append(f"{room_name} | {r['user'].replace('(全面)', '')} | {r['start']}〜{r['end']}")

                seen_keys.add(key)

    if cancels:
        sel = st.selectbox("取消対象を選択", cancels, key=f"cancel_sel_{date}")
        if st.button("取消"):
            room_sel, user_sel, t = sel.split(" | ")
            start_sel, end_sel = t.split("〜")
            st.session_state["pending_cancel"] = {
                "room": room_sel, "user": user_sel, "start": start_sel, "end": end_sel, "date": date
            }

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
                        # 両室とも該当をcancel
                        for sub in ["前側", "奥側"]:
                            for r in st.session_state["reservations"][sub]:
                                if ((r["user"] == d["user"]) or (r["user"] == f"{d['user']}(全面)") or (d["user"] in r["user"])) \
                                    and r["start"] == d["start"] \
                                    and r["end"] == d["end"] \
                                    and str(r["date"]) == str(d["date"]) \
                                    and r["status"] == "active":
                                    r["status"] = "cancel"
                                    r["cancel"] = datetime.now().strftime("%Y-%m-%d")
                        save_reservations_to_gsheet()
                        st.success("🗑️ 全面予約を取り消しました。")
                        st.session_state["pending_cancel"] = None
                        st.experimental_rerun()
                    else:
                        cancel_reservation(**d)
            with b2:
                if st.button("戻る"):
                    st.session_state["pending_cancel"] = None

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（Ver.Oct.2025）")

