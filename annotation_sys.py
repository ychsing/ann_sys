import streamlit as st
from auth_simple import require_user
from data_io import load_cases, save_cases, find_first_unverified_index
from annotation_logic import save_annotation_for_user
from date_utils import normalize_date_to_ymd
from report_ui import render_reports
import json
import os
from user_workspace import get_working_file

# DATA_PATH = "data/experiment_70case_0shot.json"

st.set_page_config(layout="wide")

# ===== Login =====
current_user = require_user()
st.sidebar.success(f"Logged in as {current_user}")

working_file = get_working_file(current_user)


if not os.path.exists(working_file):
    st.info("請先上傳標註檔案（JSON）")

    uploaded = st.file_uploader("上傳資料檔", type=["json"])

    if not uploaded:
        st.stop()

    cases = json.load(uploaded)

    with open(working_file, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    st.success("檔案已上傳，開始標註")
    st.rerun()


# ===== Load data =====

cases = load_cases(working_file)

if "case_ids" not in st.session_state:
    st.session_state.case_ids = list(cases.keys())

if "idx" not in st.session_state:
    st.session_state.idx = find_first_unverified_index(
        cases, st.session_state.case_ids
    )

case_id = st.session_state.case_ids[st.session_state.idx]
case = cases[case_id]

st.title(f"Case {st.session_state.idx+1} / {len(st.session_state.case_ids)} — {case_id}")

col_l, col_r = st.columns([1, 2])

# ===== Left: Annotation =====
with col_l:
    st.subheader("Annotation")

    gpt = case["gpt_oss"]["instruction_med"]
    user_anno = case.get("annotation", {}).get("by_user", {}).get(current_user)
    default_data = user_anno["data"] if user_anno else gpt

    if user_anno:
        st.caption("✏️ 您上次的標註內容")
    else:
        st.caption("🤖 模型建議標註")

    final = {}

    FIELD_ORDER = [
        "First_meta",
        "First_meta_DATE",
        "Bone",
        "bone_meta_gt3",
        "Lymph_node",
        "Lung",
        "Liver",
        "Brain",
        "Adrenal_gland",
    ]

    for field in FIELD_ORDER:
        v = default_data.get(field)

        if field == "bone_meta_gt3":
            if final.get("Bone", default_data.get("Bone", 0)) != 1:
                final[field] = 0
                continue

        if isinstance(v, int):
            final[field] = st.radio(field, [0, 1], index=v)
        else:
            final[field] = st.text_input(field, value=v or "")

    if st.button("💾 儲存（取代我的標註）"):
        changed = save_annotation_for_user(case, current_user, final)
        save_cases(working_file, cases)
        st.success("已儲存" if changed else "內容未變")

    if st.button("✅ 沒問題，下一筆"):
        save_annotation_for_user(case, current_user, final)
        save_cases(working_file, cases)
        st.session_state.idx += 1
        st.rerun()

# ===== Right: Reports =====
with col_r:
    raw = final.get("First_meta_DATE")
    first_meta_date, ok = normalize_date_to_ymd(raw)
    render_reports(case, first_meta_date)

def is_annotated_by_user(case, user_email):
    return user_email in case.get("annotation", {}).get("by_user", {})

if is_annotated_by_user(case, current_user):
    st.caption("🟢 已由你標註")
else:
    st.caption("🟡 尚未標註")

col_prev, col_next = st.columns(2)

with col_prev:
    if st.button("⬅ 上一筆") and st.session_state.idx > 0:
        st.session_state.idx -= 1
        st.rerun()

with col_next:
    if st.button("下一筆 ➡") and st.session_state.idx < len(st.session_state.case_ids) - 1:
        st.session_state.idx += 1
        st.rerun()


def all_verified(cases):
    return all(
        case.get("annotation", {}).get("by_user")
        for case in cases.values()
    )


st.divider()

with open(working_file, "r", encoding="utf-8") as f:
    st.download_button(
        "⬇️ 下載目前標註內容",
        f,
        file_name="annotation_result.json",
        mime="application/json"
    )
if all_verified(cases):
    st.success("所有病例已標註完成")

st.warning("⚠️ 本平台不保證資料長期保存，請隨時下載備份")