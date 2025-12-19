import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import io
from openpyxl import load_workbook
from openpyxl.drawing.image import Image

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Glass Optimizer", layout="wide")
st.title("🪟 Sheet Stock Optimizer")
st.markdown("Enter cuts manually or upload a list. **Sheet dimensions are customizable.**")

# --------------------------------------------------
# SIDEBAR INPUTS
# --------------------------------------------------
st.sidebar.header("1. Sheet Dimensions")
sheet_w = st.sidebar.number_input("Sheet Width (in)", min_value=1.0, value=84.0)
sheet_h = st.sidebar.number_input("Sheet Height (in)", min_value=1.0, value=72.0)

st.sidebar.markdown("---")
st.sidebar.header("2. Upload File (Optional)")
uploaded_files = st.sidebar.file_uploader(
    "Upload .txt or .csv",
    type=["txt", "csv"],
    accept_multiple_files=True
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "cut_list" not in st.session_state:
    st.session_state.cut_list = []

# --------------------------------------------------
# FILE PROCESSING (BULLETPROOF TXT PARSER)
# --------------------------------------------------
if uploaded_files:
    if st.sidebar.button("Process Uploaded Files"):
        st.session_state.cut_list = []

        for uploaded_file in uploaded_files:
            text = uploaded_file.getvalue().decode("utf-8")

            for line in text.splitlines():
                line = line.strip()

                # Skip junk / headers
                if not line or line.startswith(("#", "*", "<", "COMMENTS")):
                    continue
                if line.startswith('"V"') or line.startswith('"H"'):
                    continue

                parts = [p.strip().strip('"') for p in line.split(",")]

                if len(parts) >= 6:
                    try:
                        width = float(parts[4])
                        height = float(parts[5])

                        # Reverse order (your requirement)
                        st.session_state.cut_list.append((height, width))
                    except ValueError:
                        continue

        st.sidebar.success(
            f"{len(uploaded_files)} file(s) processed — {len(st.session_state.cut_list)} total cuts"
        )


# --------------------------------------------------
# MANUAL INPUT
# --------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("3. Manual Add")
with st.sidebar.form("manual_add"):
    c_w = st.number_input("Width", min_value=1.0, value=24.0)
    c_h = st.number_input("Height", min_value=1.0, value=24.0)
    c_q = st.number_input("Quantity", min_value=1, value=1)
    if st.form_submit_button("Add"):
        for _ in range(c_q):
            st.session_state.cut_list.append((c_w, c_h))

# --------------------------------------------------
# MULTI-SHEET PLACEMENT
# --------------------------------------------------
def place_cuts_multi_sheet(cuts, W, H):
    sheets, remaining = [], cuts.copy()
    while remaining:
        sheet, new_remaining = [], []
        x = y = row_h = 0
        for w, h in remaining:
            if x + w > W:
                x = 0
                y += row_h
                row_h = 0
            if y + h > H:
                new_remaining.append((w, h))
                continue
            sheet.append((x, y, w, h))
            x += w
            row_h = max(row_h, h)
        sheets.append(sheet)
        remaining = new_remaining
    return sheets

# --------------------------------------------------
# DRAW SHEETS
# --------------------------------------------------
def draw_sheets(sheets, W, H):
    figs = []
    for i, sheet in enumerate(sheets):
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.set_aspect("equal")
        ax.add_patch(patches.Rectangle((0, 0), W, H, edgecolor="black", facecolor="#f0f0f0", linewidth=2))
        for x, y, w, h in sheet:
            ax.add_patch(patches.Rectangle((x, y), w, h, facecolor="#3b82f6", edgecolor="white"))
            ax.text(x + w/2, y + h/2, f"{w:g}×{h:g}", ha="center", va="center", color="white", fontsize=8)
        ax.set_title(f"Sheet #{i+1}")
        ax.axis("off")
        figs.append(fig)
    return figs

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if st.session_state.cut_list:
    if st.button("Calculate Optimization"):
        sheets = place_cuts_multi_sheet(st.session_state.cut_list, sheet_w, sheet_h)
        figs = draw_sheets(sheets, sheet_w, sheet_h)

        # -------------------------
        # PER-SHEET SUMMARY
        # -------------------------
        summary = []
        for i, sheet in enumerate(sheets):
            used = sum(w*h for x,y,w,h in sheet)
            total = sheet_w * sheet_h
            util = round(100 * used / total, 2)
            summary.append({
                "Sheet #": i+1,
                "Pieces Packed": len(sheet),
                "Used Area (in²)": used,
                "Total Area (in²)": total,
                "Utilization (%)": util,
                "Waste (%)": round(100-util, 2)
            })

        df_summary = pd.DataFrame(summary)
        st.header("📊 Sheet Utilization Summary")
        st.dataframe(df_summary.set_index("Sheet #"), use_container_width=True)

        # -------------------------
        # CREATE BAR CHART
        # -------------------------
        fig_bar, ax = plt.subplots(figsize=(6,4))
        ax.bar(df_summary["Sheet #"], df_summary["Utilization (%)"])
        ax.set_ylim(0,100)
        ax.set_xlabel("Sheet #")
        ax.set_ylabel("Utilization (%)")
        ax.set_title("Sheet Utilization")
        for i, v in enumerate(df_summary["Utilization (%)"]):
            ax.text(df_summary["Sheet #"][i], v + 1, f"{v}%", ha="center")
        plt.tight_layout()

        # -------------------------
        # EXPORT TO EXCEL
        # -------------------------
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_summary.to_excel(writer, sheet_name="Sheet Summary", index=False)
            fig_bar.savefig("util_chart.png")

            wb = writer.book
            ws = wb["Sheet Summary"]
            img = Image("util_chart.png")
            img.anchor = "H2"
            ws.add_image(img)

        output.seek(0)

        st.download_button(
            "📥 Download Excel Summary",
            data=output,
            file_name="sheet_summary.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # -------------------------
        # DISPLAY VISUALS
        # -------------------------
        st.header("🖼️ Cutting Layouts")
        for fig in figs:
            st.pyplot(fig)

else:
    st.info("Add cuts to begin optimization.")


