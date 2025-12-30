import streamlit as st
import json
import os

from auth_simple import require_user
from data_io import load_cases, save_cases, find_first_unverified_index
from annotation_logic import save_annotation_for_user
from date_utils import normalize_date_to_ymd
from report_ui import render_reports
from user_workspace import get_working_file

# =====================================================
# Page config
# =====================================================
st.set_page_config(
    page_title="Prostate Cancer Imaging Annotation",
    layout="wide"
)

# =====================================================
# Global CSS
# =====================================================
st.markdown("""
<style>
.notice-box {
    background-color: #f8fafc;
    border-left: 4px solid #2563eb;
    padding: 0.6rem 0.8rem;
    border-radius: 6px;
}
.caption {
    font-size: 0.85rem;
    color: #555;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# Login
# =====================================================
current_user = require_user()
st.sidebar.success(f":bust_in_silhouette: {current_user}")

working_file = get_working_file(current_user)

st.markdown("""
<div class="notice-box">
<b>資料隱私說明</b><br>
本系統不會公開、分享或外流使用者上傳之資料，資料僅供本人操作與下載。
</div>
""", unsafe_allow_html=True)

# =====================================================
# Upload (first time only)
# =====================================================
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

# =====================================================
# Load data
# =====================================================
cases = load_cases(working_file)
if cases is None:
    st.error("資料讀取失敗")
    st.stop()

if "case_ids" not in st.session_state:
    st.session_state.case_ids = list(cases.keys())

# =====================================================
# ⭐ 重啟時：跳到第一筆尚未標註 ⭐
# =====================================================
if "prev_case_id" not in st.session_state:
    st.session_state.idx = find_first_unverified_index(
        cases, st.session_state.case_ids
    )

# =====================================================
# Current case
# =====================================================
case_id = st.session_state.case_ids[st.session_state.idx]
case = cases[case_id]

# =====================================================
# Helper
# =====================================================
def is_user_annotation(case, user):
    return user in case.get("annotation", {}).get("by_user", {})

def ensure_case_initialized(case_id, source):
    for f in BINARY_FIELDS:
        key = f"{case_id}_{f}"
        if key not in st.session_state:
            st.session_state[key] = int(source.get(f, 0) or 0)

    for f in TEXT_FIELDS:
        key = f"{case_id}_{f}"
        if key not in st.session_state:
            st.session_state[key] = "" if source.get(f) is None else str(source.get(f))

    prev_key = f"{case_id}_First_meta_prev"
    if prev_key not in st.session_state:
        st.session_state[prev_key] = source.get("First_meta", 0)

# =====================================================
# Progress bar
# =====================================================
total = len(st.session_state.case_ids)
done = sum(
    1 for cid in st.session_state.case_ids
    if is_user_annotation(cases[cid], current_user)
)

st.progress(done / total, text=f"進度：{done} / {total}")

# =====================================================
# Field definitions
# =====================================================
BINARY_FIELDS = [
    "First_meta",
    "Bone",
    "bone_meta_gt3",
    "Lymph_node",
    "Lung",
    "Liver",
    "Brain",
    "Adrenal_gland",
    "Non_axial_involved",
]

TEXT_FIELDS = [
    "First_meta_DATE",
    "Non_axial_list",
    "Other",
]

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
    "Non_axial_involved",
    "Non_axial_list",
    "Other",
]

# =====================================================
# Init / restore
# =====================================================
restore_gpt = st.session_state.pop("restore_gpt", False)

source = (
    case.get("annotation", {})
    .get("by_user", {})
    .get(current_user, {})
    .get("data")
    or case["gpt_oss"]["instruction_med"]
)

if restore_gpt:
    source = case["gpt_oss"]["instruction_med"]

# ✅ 關鍵修正：保證所有欄位已初始化
ensure_case_initialized(case_id, source)

if restore_gpt:
    source = case["gpt_oss"]["instruction_med"]

prev_case = st.session_state.get("prev_case_id")
if prev_case != case_id or restore_gpt:
    for f in BINARY_FIELDS:
        st.session_state[f"{case_id}_{f}"] = int(source.get(f, 0) or 0)
    for f in TEXT_FIELDS:
        st.session_state[f"{case_id}_{f}"] = "" if source.get(f) is None else str(source.get(f))
    st.session_state[f"{case_id}_First_meta_prev"] = source.get("First_meta", 0)

st.session_state["prev_case_id"] = case_id

# =====================================================
# Title & layout
# =====================================================
st.title(f"Case {st.session_state.idx + 1} / {total} — {case_id}")

status = (
    "✏️ 已標註"
    if is_user_annotation(case, current_user)
    else "🤖 電腦建議標註"
)

col_l, col_r = st.columns([1, 2])

# =====================================================
# Left: Annotation
# =====================================================
with col_l:
    st.subheader(f"Annotation - {status}")

    st.radio("First_meta", [0, 1], horizontal=True, key=f"{case_id}_First_meta")

    prev = st.session_state[f"{case_id}_First_meta_prev"]
    now = st.session_state[f"{case_id}_First_meta"]

    if prev == 1 and now == 0:
        for f in BINARY_FIELDS:
            if f != "First_meta":
                st.session_state[f"{case_id}_{f}"] = 0
        for f in TEXT_FIELDS:
            st.session_state[f"{case_id}_{f}"] = ""

    st.session_state[f"{case_id}_First_meta_prev"] = now

    for field in FIELD_ORDER:
        if field == "First_meta":
            continue
        if field == "First_meta_DATE" and now != 1:
            continue
        if field == "bone_meta_gt3" and st.session_state[f"{case_id}_Bone"] != 1:
            continue
        if field == "Non_axial_list" and st.session_state[f"{case_id}_Non_axial_involved"] != 1:
            continue

        if field in BINARY_FIELDS:
            st.radio(field, [0, 1], horizontal=True, key=f"{case_id}_{field}")
        else:
            st.text_input(field, key=f"{case_id}_{field}")

    final = {f: int(st.session_state[f"{case_id}_{f}"]) for f in BINARY_FIELDS}
    final.update({f: st.session_state[f"{case_id}_{f}"] for f in TEXT_FIELDS})

    if final["First_meta"] != 1:
        for f in BINARY_FIELDS:
            if f != "First_meta":
                final[f] = 0
        for f in TEXT_FIELDS:
            final[f] = ""

    st.caption("請使用下方按鈕進行操作")

    col_prev, col_save, col_next = st.columns([1, 1.5, 2])

    with col_prev:
        if st.button("上一筆", use_container_width=True):
            if st.session_state.idx > 0:
                st.session_state.idx -= 1
                st.rerun()

    with col_save:
        if st.button("儲存", use_container_width=True):
            save_annotation_for_user(case, current_user, final)
            save_cases(working_file, cases)
            st.success("已儲存")

    with col_next:
        if st.button("儲存並下一筆 ▶", use_container_width=True):
            save_annotation_for_user(case, current_user, final)
            save_cases(working_file, cases)
            if st.session_state.idx < total - 1:
                st.session_state.idx += 1
            st.rerun()

    if st.button("還原電腦標註", use_container_width=True):
        st.session_state["restore_gpt"] = True
        st.rerun()

# =====================================================
# Right: Reports
# =====================================================
with col_r:
    first_meta_date, _ = normalize_date_to_ymd(final.get("First_meta_DATE"))
    render_reports(case, first_meta_date)

# =====================================================
# Download
# =====================================================
st.divider()
with open(working_file, "r", encoding="utf-8") as f:
    st.download_button(
        "下載目前標註結果（JSON）",
        f,
        file_name="annotation_result.json",
        mime="application/json",
        use_container_width=True
    )

st.caption(":warning: 本平台不保證資料長期保存，請隨時下載備份")
