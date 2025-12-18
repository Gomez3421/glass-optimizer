import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker, PackingMode, MaxRectsBssf
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
sheet_w = st.sidebar.number_input("Sheet Width (in)", min_value=1.0, value=72.0)
sheet_h = st.sidebar.number_input("Sheet Height (in)", min_value=1.0, value=84.0)

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
# PACKING SOLVER
# --------------------------------------------------
def solve_packing(cuts, SHEET_W, SHEET_H):
    # Sort pieces by area (largest first)
    sorted_cuts = sorted(
        enumerate(cuts),
        key=lambda x: x[1][0] * x[1][1],
        reverse=True
    )

    packer = newPacker(
        mode=PackingMode.Offline,
        rotation=True,
        pack_algo=MaxRectsBssf
    )

    # Add rectangles
    for rid, (w, h) in sorted_cuts:
        packer.add_rect(w, h, rid=rid)

    # Start with one bin
    packer.add_bin(SHEET_W, SHEET_H)
    packer.pack()

    # Add new bins dynamically for leftovers
    leftovers = [r for abin in packer for r in abin if not abin]
    while leftovers:
        packer.add_bin(SHEET_W, SHEET_H)
        packer.pack()
        leftovers = [r for abin in packer for r in abin if not abin]

    return packer

# --------------------------------------------------
# VISUALIZATION
# --------------------------------------------------
def draw_results(packer, SHEET_W, SHEET_H, original_cuts):
    figures = []
    summary = []

    for idx, abin in enumerate(packer):
        if not abin:
            continue

        fig, ax = plt.subplots()
        fig.set_size_inches(8, 8 * (SHEET_H / SHEET_W))

        ax.set_xlim(0, SHEET_W)
        ax.set_ylim(0, SHEET_H)

        # Sheet outline
        ax.add_patch(
            patches.Rectangle(
                (0, 0),
                SHEET_W,
                SHEET_H,
                linewidth=2,
                edgecolor="black",
                facecolor="#f0f0f0"
            )
        )

        used_area = 0
        count = 0

        for rect in abin:
            x, y = rect.x, rect.y
            w, h = rect.width, rect.height
            orig_w, orig_h = original_cuts[rect.rid]

            used_area += w * h
            count += 1

            ax.add_patch(
                patches.Rectangle(
                    (x, y),
                    w,
                    h,
                    linewidth=1,
                    edgecolor="white",
                    facecolor="#3b82f6"
                )
            )

            if w > 5 and h > 5:
                rotated = (w != orig_w or h != orig_h)
                label = f"{orig_w:g}x{orig_h:g}" + (" ↺" if rotated else "")
                ax.text(
                    x + w / 2,
                    y + h / 2,
                    label,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold"
                )

        total_area = SHEET_W * SHEET_H
        waste = 100 * (1 - used_area / total_area)

        summary.append({
            "Sheet #": idx + 1,
            "Items Packed": count,
            "Used Area (in²)": used_area,
            "Total Area (in²)": total_area,
            "Utilization": f"{100 - waste:.1f}%",
            "Waste": f"{waste:.1f}%"
        })

        ax.set_title(
            f"Sheet #{idx + 1} ({SHEET_W}x{SHEET_H} | Waste: {waste:.1f}%)"
        )
        ax.axis("off")
        figures.append(fig)

    return figures, summary

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if st.session_state.cut_list:
    if st.button("Calculate Optimization"):
        with st.spinner("Calculating optimal layout..."):
            packer = solve_packing(st.session_state.cut_list, sheet_w, sheet_h)
            figs, summary = draw_results(packer, sheet_w, sheet_h, st.session_state.cut_list)
            packed = sum(len(b) for b in packer)

            st.success(
                f"Optimization complete: {packed} of {len(st.session_state.cut_list)} "
                f"pieces packed using {len(figs)} sheet(s)."
            )

            if packed < len(st.session_state.cut_list):
                st.error(
                    f"{len(st.session_state.cut_list) - packed} "
                    "piece(s) could not be packed."
                )

            if summary:
                st.header("✨ Optimization Summary")
                df = pd.DataFrame(summary)
                total_used = df["Used Area (in²)"].sum()
                total_stock = df["Total Area (in²)"].sum()
                util = 100 * total_used / total_stock

                st.metric(
                    f"Overall Utilization ({len(figs)} Sheets)",
                    f"{util:.2f}%",
                    f"Waste: {100 - util:.2f}%"
                )

                st.dataframe(df.set_index("Sheet #"), use_container_width=True)

            st.header("🖼️ Cutting Plan Visualizations")
            cols = st.columns(2)
            for i, fig in enumerate(figs):
                with cols[i % 2]:
                    st.pyplot(fig)

else:
    st.info(
        "Set sheet dimensions, then upload a file or add pieces "
        "to start optimization."
    )
