import streamlit as st
from auth_simple import require_user
from data_io import load_cases, save_cases, find_first_unverified_index
from annotation_logic import save_annotation_for_user
from date_utils import normalize_date_to_ymd
from report_ui import render_reports
import json
import os
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
h1 { font-size: 1.8rem; margin-bottom: 0.2rem; }
h2, h3 { margin-top: 0.6rem; }

.notice-box {
    background-color: #f8fafc;
    border-left: 4px solid #2563eb;
    padding: 0.6rem 0.8rem;
    border-radius: 6px;
    font-size: 0.9rem;
}

.success-box {
    background-color: #ecfdf5;
    border-left: 4px solid #16a34a;
    padding: 0.6rem 0.8rem;
    border-radius: 6px;
    font-size: 0.9rem;
}

.warning-box {
    background-color: #fff7ed;
    border-left: 4px solid #f97316;
    padding: 0.6rem 0.8rem;
    border-radius: 6px;
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# Login
# =====================================================
current_user = require_user()
st.sidebar.success(f"👤 {current_user}")

working_file = get_working_file(current_user)

st.markdown("""
<div class="notice-box">
🔐 <b>資料隱私說明</b><br>
本系統不會公開、分享或外流使用者上傳之資料，所有資料僅供本人操作與下載。
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
    st.error("資料讀取失敗，請重新上傳檔案")
    st.stop()

if "case_ids" not in st.session_state:
    st.session_state.case_ids = list(cases.keys())

if "idx" not in st.session_state:
    st.session_state.idx = find_first_unverified_index(
        cases, st.session_state.case_ids
    )

case_id = st.session_state.case_ids[st.session_state.idx]
case = cases[case_id]

st.title(
    f"Case {st.session_state.idx + 1} / {len(st.session_state.case_ids)} — {case_id}"
)

# =====================================================
# Layout
# =====================================================
col_l, col_r = st.columns([1, 2])

# =====================================================
# Left: Annotation
# =====================================================
# ===== Left: Annotation =====
with col_l:
    st.subheader("Annotation")

    gpt = case["gpt_oss"]["instruction_med"]
    user_anno = case.get("annotation", {}).get("by_user", {}).get(current_user)
    default_data = user_anno["data"] if user_anno else gpt

    if user_anno:
        st.markdown(
            "<div class='success-box'>✏️ 顯示您上次的標註內容</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div class='notice-box'>🤖 顯示模型建議標註</div>",
            unsafe_allow_html=True
        )

    final = {}

    # =====================================================
    # 欄位順序（與 gpt_oss.instruction_med 完全對齊）
    # =====================================================
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

    for field in FIELD_ORDER:

        # ==========================================
        # First_meta → First_meta_DATE
        # ==========================================
        if field == "First_meta_DATE":
            if final.get("First_meta", default_data.get("First_meta", 0)) != 1:
                final[field] = ""
                continue

        # ==========================================
        # Bone → bone_meta_gt3
        # ==========================================
        if field == "bone_meta_gt3":
            if final.get("Bone", default_data.get("Bone", 0)) != 1:
                final[field] = 0
                continue

        # ==========================================
        # Non_axial_involved → Non_axial_list
        # ==========================================
        if field == "Non_axial_list":
            if final.get(
                "Non_axial_involved",
                default_data.get("Non_axial_involved", 0)
            ) != 1:
                final[field] = ""
                continue

        v = default_data.get(field)

        # ==========================================
        # Binary 欄位（0 / 1）→ 左右兩欄
        # ==========================================
        if isinstance(v, int):
            col_label, col_input = st.columns([1, 2])

            with col_label:
                st.markdown(f"**{field}**")

            with col_input:
                final[field] = st.radio(
                    "",
                    [0, 1],
                    index=v,
                    horizontal=True,
                    key=f"{case_id}_{field}",
                    help=(
                        "是否為首次轉移" if field == "First_meta"
                        else "是否有骨轉移" if field == "Bone"
                        else "是否超過三個骨轉移病灶" if field == "bone_meta_gt3"
                        else "是否有非軸向骨轉移" if field == "Non_axial_involved"
                        else "是否有其他轉移部位" if field == "Other"
                        else None
                    )
                )

        # ==========================================
        # Text 欄位（DATE / LIST）
        # ==========================================
        else:
            label = (
                "First metastasis date (YYYY-MM-DD)"
                if field == "First_meta_DATE"
                else "Non-axial involved sites"
                if field == "Non_axial_list"
                else field
            )

            final[field] = st.text_input(
                label,
                value=v or "",
                placeholder=(
                    "YYYY-MM-DD" if field == "First_meta_DATE" else ""
                ),
                key=f"{case_id}_{field}"
            )

    # =====================================================
    # 儲存前最終防呆（臨床等級）
    # =====================================================
    if final.get("First_meta") != 1:
        final["First_meta_DATE"] = ""

    if final.get("Bone") != 1:
        final["bone_meta_gt3"] = 0

    if final.get("Non_axial_involved") != 1:
        final["Non_axial_list"] = ""

    # =====================================================
    # Buttons
    # =====================================================
    btn1, btn2 = st.columns(2)

    with btn1:
        if st.button("💾 儲存標註", use_container_width=True):
            changed = save_annotation_for_user(case, current_user, final)
            save_cases(working_file, cases)
            st.success("已儲存" if changed else "內容未變")

    with btn2:
        if st.button("✅ 沒問題，下一筆", use_container_width=True):
            save_annotation_for_user(case, current_user, final)
            save_cases(working_file, cases)
            st.session_state.idx += 1
            st.rerun()
# Right: Reports
# =====================================================
with col_r:
    raw = final.get("First_meta_DATE")
    first_meta_date, _ = normalize_date_to_ymd(raw)
    render_reports(case, first_meta_date)

# =====================================================
# Navigation & Status
# =====================================================
def is_annotated_by_user(case, user_email):
    return user_email in case.get("annotation", {}).get("by_user", {})

if is_annotated_by_user(case, current_user):
    st.caption("🟢 已由您標註")
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

done = sum(
    1 for c in cases.values()
    if c.get("annotation", {}).get("by_user")
)
total = len(cases)
st.caption(f"📊 標註進度：{done} / {total}")

# =====================================================
# Download & Completion
# =====================================================
st.markdown("<hr>", unsafe_allow_html=True)

with open(working_file, "r", encoding="utf-8") as f:
    st.download_button(
        "⬇️ 下載目前標註結果（JSON）",
        f,
        file_name="annotation_result.json",
        mime="application/json",
        use_container_width=True
    )

def all_verified(cases):
    return all(
        case.get("annotation", {}).get("by_user")
        for case in cases.values()
    )

if all_verified(cases):
    st.markdown(
        "<div class='success-box'>🎉 所有病例已完成標註</div>",
        unsafe_allow_html=True
    )

st.markdown("""
<div class="warning-box">
⚠️ <b>重要提醒</b><br>
本平台不保證資料長期保存，請於標註過程中隨時下載備份。
</div>
""", unsafe_allow_html=True)
