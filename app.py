import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker, PackingMode
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Glass Optimizer", layout="wide")

st.title("🪟 Glass Sheet Optimizer (72x84)")
st.markdown("Enter your cut list on the left to minimize scrap.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Add Cuts")

# Session state to hold the list of cuts
if 'cut_list' not in st.session_state:
    st.session_state.cut_list = []

# Input forms
with st.sidebar.form(key='cut_form'):
    c_width = st.number_input("Width (inches)", min_value=1.0, max_value=84.0, value=24.0)
    c_height = st.number_input("Height (inches)", min_value=1.0, max_value=84.0, value=24.0)
    c_qty = st.number_input("Quantity", min_value=1, value=1)
    submit_button = st.form_submit_button(label='Add to List')

if submit_button:
    # Add the cut to the list QTY times
    for _ in range(c_qty):
        st.session_state.cut_list.append((c_width, c_height))
    st.sidebar.success(f"Added {c_qty} pieces of {c_width}x{c_height}")

# Show current list in sidebar
if st.session_state.cut_list:
    st.sidebar.write("### Current List:")
    st.sidebar.write(st.session_state.cut_list)
    if st.sidebar.button("Clear List"):
        st.session_state.cut_list = []
        st.rerun()

# --- OPTIMIZATION LOGIC ---
def solve_packing(cuts):
    SHEET_W, SHEET_H = 72, 84
    packer = newPacker(mode=PackingMode.Offline, 
                       bin_algo=PackingMode.GuillotineBottomLeftFit, 
                       rotation=True)
    
    # Add enough bins (sheets) to cover likely demand
    for _ in range(20):
        packer.add_bin(SHEET_W, SHEET_H)
    
    for i, (w, h) in enumerate(cuts):
        packer.add_rect(w, h, rid=i)
        
    packer.pack()
    return packer

# --- VISUALIZATION LOGIC ---
def draw_results(packer):
    SHEET_W, SHEET_H = 72, 84
    charts = []
    
    for bin_index, abin in enumerate(packer):
        if len(abin) == 0: continue # Skip empty bins

        fig, ax = plt.subplots(1)
        fig.set_size_inches(6, 6 * (SHEET_H/SHEET_W))
        
        ax.set_xlim([0, SHEET_W])
        ax.set_ylim([0, SHEET_H])
        
        # Draw Sheet Background
        ax.add_patch(patches.Rectangle((0, 0), SHEET_W, SHEET_H, 
                                       linewidth=2, edgecolor='black', facecolor='#f0f0f0'))

        used_area = 0
        for rect in abin:
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            used_area += w * h
            rect_patch = patches.Rectangle((x, y), w, h, 
                                           linewidth=1, edgecolor='white', facecolor='#3b82f6')
            ax.add_patch(rect_patch)
            ax.text(x + w/2, y + h/2, f"{w:g}x{h:g}", 
                    ha='center', va='center', fontsize=8, color='white', fontweight='bold')

        total_area = SHEET_W * SHEET_H
        waste = 100 - (used_area / total_area * 100)
        
        plt.title(f"Sheet #{bin_index+1} (Waste: {waste:.1f}%)")
        plt.axis('off')
        charts.append(fig)
        
    return charts

# --- MAIN DISPLAY ---
if len(st.session_state.cut_list) > 0:
    if st.button("Calculate Optimization"):
        with st.spinner("Calculating best fit..."):
            packer = solve_packing(st.session_state.cut_list)
            figures = draw_results(packer)
            
            # Display results in a grid
            st.success(f"Used {len(figures)} sheets of glass.")
            cols = st.columns(2)
            for i, fig in enumerate(figures):
                with cols[i % 2]:
                    st.pyplot(fig)
else:
    st.info("Add items using the sidebar to start."
