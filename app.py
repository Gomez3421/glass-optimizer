import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

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
uploaded_file = st.sidebar.file_uploader("Upload .txt or .csv", type=["txt", "csv"])
st.sidebar.info(
    "Format: Width, Height, Qty\n"
    "Example:\n"
    "24, 36, 1\n"
    "30, 40, 2"
)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "cut_list" not in st.session_state:
    st.session_state.cut_list = []

# --------------------------------------------------
# FILE PROCESSING
# --------------------------------------------------
if uploaded_file is not None:
    if st.sidebar.button("Process Uploaded File"):
        st.session_state.cut_list = []
        text = uploaded_file.getvalue().decode("utf-8")
        lines = text.splitlines()
        imported = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                parts = [p.strip() for p in line.split(",")]
                w = float(parts[0])
                h = float(parts[1])
                qty = int(parts[2]) if len(parts) > 2 else 1
                for _ in range(qty):
                    st.session_state.cut_list.append((w, h))
                imported += qty
            except ValueError:
                continue
        st.sidebar.success(f"Imported {imported} pieces")

st.sidebar.markdown("---")
st.sidebar.header("3. Manual Add")
with st.sidebar.form("manual_add"):
    c_w = st.number_input("Width", min_value=1.0, value=24.0)
    c_h = st.number_input("Height", min_value=1.0, value=24.0)
    c_q = st.number_input("Quantity", min_value=1, value=1)
    add_btn = st.form_submit_button("Add Manual Piece")

if add_btn:
    for _ in range(c_q):
        st.session_state.cut_list.append((c_w, c_h))
    st.sidebar.success(f"Added {c_q} piece(s)")

# --------------------------------------------------
# CURRENT LIST SUMMARY
# --------------------------------------------------
if st.session_state.cut_list:
    total_area = sum(w * h for w, h in st.session_state.cut_list)
    st.sidebar.write("### Current List")
    st.sidebar.write(f"Total Pieces: **{len(st.session_state.cut_list)}**")
    st.sidebar.write(f"Total Required Area: **{total_area:,.2f} in²**")
    if st.sidebar.button("Clear All"):
        st.session_state.cut_list = []
        st.experimental_rerun()

# --------------------------------------------------
# MULTI-SHEET PLACEMENT
# --------------------------------------------------
def place_cuts_multi_sheet(cuts, SHEET_W, SHEET_H):
    sheets = []
    remaining_cuts = cuts.copy()
    
    while remaining_cuts:
        placements = []
        y_offset = 0
        row_height = 0
        x_offset = 0
        new_remaining = []

        for w, h in remaining_cuts:
            # Rotate if it fits better
            if w > h and w > SHEET_W and h <= SHEET_W:
                w, h = h, w

            if x_offset + w > SHEET_W:
                x_offset = 0
                y_offset += row_height
                row_height = 0

            if y_offset + h > SHEET_H:
                # Move to next sheet
                new_remaining.append((w, h))
                continue

            placements.append((x_offset, y_offset, w, h))
            x_offset += w
            row_height = max(row_height, h)

        sheets.append(placements)
        remaining_cuts = new_remaining

    return sheets

# --------------------------------------------------
# VISUALIZATION WITH AUTO-SCALING
# --------------------------------------------------
def draw_sheets_multi(sheets, SHEET_W, SHEET_H):
    figs = []
    MAX_DISPLAY_WIDTH = 12
    MAX_DISPLAY_HEIGHT = 8

    for idx, placements in enumerate(sheets):
        scale_w = MAX_DISPLAY_WIDTH / SHEET_W
        scale_h = MAX_DISPLAY_HEIGHT / SHEET_H
        scale = min(scale_w, scale_h)

        fig, ax = plt.subplots()
        fig.set_size_inches(SHEET_W * scale, SHEET_H * scale)
        ax.set_xlim(0, SHEET_W)
        ax.set_ylim(0, SHEET_H)
        ax.set_aspect('equal')

        # Sheet outline
        ax.add_patch(
            patches.Rectangle((0, 0), SHEET_W, SHEET_H, linewidth=2, edgecolor="black", facecolor="#f0f0f0")
        )

        # Draw all cuts
        for x, y, w, h in placements:
            ax.add_patch(
                patches.Rectangle((x, y), w, h, linewidth=1, edgecolor="white", facecolor="#3b82f6")
            )
            ax.text(x + w/2, y + h/2, f"{w:g}x{h:g}", ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold")

        ax.set_title(f"Sheet #{idx+1} ({SHEET_W}x{SHEET_H})")
        ax.axis("off")
        figs.append(fig)
    return figs

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if st.session_state.cut_list:
    if st.button("Calculate Optimization"):
        with st.spinner("Placing cuts across sheets..."):
            sheets = place_cuts_multi_sheet(st.session_state.cut_list, sheet_w, sheet_h)
            figs = draw_sheets_multi(sheets, sheet_w, sheet_h)

            total_packed = sum(len(sheet) for sheet in sheets)
            st.success(f"Optimization complete: {total_packed} pieces packed across {len(sheets)} sheet(s).")

            # Overall utilization summary
            total_used = sum(w*h for sheet in sheets for x,y,w,h in sheet)
            total_area = sheet_w*sheet_h*len(sheets)
            utilization = 100 * total_used / total_area
            st.metric("Overall Utilization", f"{utilization:.2f}%", f"Waste: {100 - utilization:.2f}%")

            # Display all sheets
            st.header("🖼️ Cutting Plan Visualizations")
            for i, fig in enumerate(figs):
                st.pyplot(fig)
else:
    st.info("Set sheet dimensions, then upload a file or add pieces to start optimization.")
