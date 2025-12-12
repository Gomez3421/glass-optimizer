import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker, PackingMode
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Glass Optimizer", layout="wide")

st.title("🪟 Glass Sheet Optimizer (72x84)")
st.markdown("Enter cuts manually or upload a list.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Upload File (Optional)")
uploaded_file = st.sidebar.file_uploader("Upload .txt or .csv", type=['txt', 'csv'])

st.sidebar.info("Format: Width, Height, Qty\nExample:\n24, 36, 1\n30, 40, 2")

# Initialize session state
if 'cut_list' not in st.session_state:
    st.session_state.cut_list = []

# Process the file if uploaded and button clicked
if uploaded_file is not None:
    if st.sidebar.button("Process Uploaded File"):
        # Clear current list so we don't double up
        st.session_state.cut_list = []
        
        # Read the file
        string_data = uploaded_file.getvalue().decode("utf-8")
        
        lines = string_data.splitlines()
        success_count = 0
        
        for line in lines:
            # Skip empty lines
            if not line.strip(): continue
            
            try:
                # Split by comma
                parts = [p.strip() for p in line.split(',')]
                
                # Parse Width and Height
                w = float(parts[0])
                h = float(parts[1])
                
                # Parse Quantity (default to 1 if missing)
                qty = int(parts[2]) if len(parts) > 2 else 1
                
                # Add to list
                for _ in range(qty):
                    st.session_state.cut_list.append((w, h))
                success_count += qty
            except ValueError:
                # Skip lines that aren't numbers (like headers)
                continue
                
        st.sidebar.success(f"Imported {success_count} pieces!")

st.sidebar.markdown("---")
st.sidebar.header("2. Manual Add")

# Manual Input Form
with st.sidebar.form(key='cut_form'):
    c_width = st.number_input("Width", min_value=1.0, max_value=84.0, value=24.0)
    c_height = st.number_input("Height", min_value=1.0, max_value=84.0, value=24.0)
    c_qty = st.number_input("Quantity", min_value=1, value=1)
    submit_button = st.form_submit_button(label='Add Manual Piece')

if submit_button:
    for _ in range(c_qty):
        st.session_state.cut_list.append((c_width, c_height))
    st.sidebar.success(f"Added {c_qty} pieces")

# Show current list
if st.session_state.cut_list:
    st.sidebar.write("### Current List:")
    st.sidebar.write(f"Total Items: {len(st.session_state.cut_list)}")
    if st.sidebar.button("Clear All"):
        st.session_state.cut_list = []
        st.rerun()

# --- OPTIMIZATION LOGIC ---
def solve_packing(cuts):
    SHEET_W, SHEET_H = 72, 84
    
    # FIXED: Removed the crashing bin_algo setting
    packer = newPacker(mode=PackingMode.Offline, rotation=True)
    
    # Add enough bins (sheets) to cover likely demand
    for _ in range(100):
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
        if len(abin) == 0: continue 

        fig, ax = plt.subplots(1)
        fig.set_size_inches(6, 6 * (SHEET_H/SHEET_W))
        
        ax.set_xlim([0, SHEET_W])
        ax.set_ylim([0, SHEET_H])
        
        # Draw Sheet
        ax.add_patch(patches.Rectangle((0, 0), SHEET_W, SHEET_H, 
                                       linewidth=2, edgecolor='black', facecolor='#f0f0f0'))

        used_area = 0
        for rect in abin:
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            used_area += w * h
            rect_patch = patches.Rectangle((x, y), w, h, 
                                           linewidth=1, edgecolor='white', facecolor='#3b82f6')
            ax.add_patch(rect_patch)
            
            # Smart Labeling (don't label if too small)
            if w > 5 and h > 5:
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
            
            # Check for unpacked items
            packed_items = 0
            for abin in packer:
                packed_items += len(abin)
            
            if packed_items < len(st.session_state.cut_list):
                 st.warning(f"Warning: Only {packed_items} items fit. {len(st.session_state.cut_list) - packed_items} items were too big or didn't fit.")

            st.success(f"Used {len(figures)} sheets of glass.")
            cols = st.columns(2)
            for i, fig in enumerate(figures):
                with cols[i % 2]:
                    st.pyplot(fig)
else:
    st.info("Upload a file or add items manually to start.")
