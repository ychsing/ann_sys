import re
import streamlit as st
from collections import defaultdict

def compact_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)      # 移除空白行
    text = re.sub(r"\n{2,}", "\n\n", text)      # 多行 → 1 空行
    return text.strip()

import re

def Deidentify_Report_Content(report: str, source: str):
    if not report:
        return None

    report = report.strip()

    # ===== CT / MRI =====
    if source in ("CT", "MRI"):
        report = re.sub(r'^.*?＜檢查目的及病程摘要＞','＜檢查目的及病程摘要＞', report, flags=re.S)

        if "＜報告內容＞" in report and "主治醫師：" in report:
            content = re.findall(r'＜報告內容＞.*?收件號：\s?\d*(.*?)主治醫師：', report, re.S)
            if content:
                content = content[0]
                content = re.sub(r'＜摘要＞[\s\S]*$', '', content)
                content = re.sub(r'.*(報告.*醫師|住院醫師).*', '', content)
                content = re.sub(r'^.*?＜檢查目的及病程摘要＞','＜檢查目的及病程摘要＞', content, flags=re.S)
                content = re.sub(r'＜摘要＞[\s\S]*$', '', content)

                return content.strip()

        return report.strip()

    # ===== Bone Scan / NM =====

    m = re.search(r'\bReport\s*:\s*(.*)', report, re.S | re.I)
    content = m.group(1) if m else report
    content = re.split(r'(判讀醫師|報告醫師|主治醫師|Reading\s+Physician|Interpreting\s+Physician)', content, maxsplit=1)[0]
    content = re.sub(r'\bMemo\s*:\s*.*?(?=\n\s*\n|$)', '', content, flags=re.S | re.I)
    content = re.sub(r'.*(Injection\s+by|Draft\s+by|Prepared\s+by|Verified\s+by).*', '', content, flags=re.I)
    content = re.sub(r'.*(姓名|病歷號|醫師|Physician).*', '', content)
    content = re.sub(r'^.*?＜檢查目的及病程摘要＞','＜檢查目的及病程摘要＞', content, flags=re.S)
    content = re.sub(r'.*(報告.*醫師|住院醫師).*', '', content)
    content = re.sub(r'＜摘要＞[\s\S]*$', '', content)


    return content.strip()


def render_reports(case, first_meta_date):
    grouped = defaultdict(list)
    for r in case["report"]:
        grouped[r["modality"]].append(r)

    tab_ct, tab_mri, tab_bs = st.tabs(["CT", "MRI", "Bone Scan"])

    for modality, tab in zip(["CT", "MRI", "Bone Scan"], [tab_ct, tab_mri, tab_bs]):
        with tab:
            reports = grouped.get(modality, [])

            # ===== 完全沒有該 modality =====
            if not reports:
                st.info(f"無 {modality} 報告")
                continue

            has_any_content = False

            for r in reports:
                date = str(r["date"]).strip()
                is_first = first_meta_date and date == first_meta_date

                content = Deidentify_Report_Content(r["finding"], r["modality"])
                content = compact_text(content)

                if content:
                    has_any_content = True

                if is_first:
                    st.markdown(
                        "<b style='color:#b00020'>★ First Meta</b>",
                        unsafe_allow_html=True
                    )

                with st.expander(date):
                    st.text(content if content else "（此報告去識別後無可顯示內容）")

            # ===== 全部報告都被清空 =====
            if not has_any_content:
                st.info(f"無 {modality} 報告")
