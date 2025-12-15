import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker, PackingMode
import io
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Glass Optimizer", layout="wide")

st.title("🪟 Sheet Stock Optimizer")
st.markdown("Enter cuts manually or upload a list. **Sheet dimensions are now customizable!**")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Sheet Dimensions")
# Allow user to define the sheet size, defaulting to the original 72x84
sheet_w = st.sidebar.number_input("Sheet Width (in)", min_value=1.0, value=72.0)
sheet_h = st.sidebar.number_input("Sheet Height (in)", min_value=1.0, value=84.0)
st.sidebar.markdown("---")

st.sidebar.header("2. Upload File (Optional)")
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
st.sidebar.header("3. Manual Add")

# Manual Input Form
with st.sidebar.form(key='cut_form'):
    # Max values are set to the current sheet max for convenience
    c_width = st.number_input("Width", min_value=1.0, max_value=sheet_h, value=24.0)
    c_height = st.number_input("Height", min_value=1.0, max_value=sheet_h, value=24.0)
    c_qty = st.number_input("Quantity", min_value=1, value=1)
    submit_button = st.form_submit_button(label='Add Manual Piece')

if submit_button:
    for _ in range(c_qty):
        st.session_state.cut_list.append((c_width, c_height))
    st.sidebar.success(f"Added {c_qty} pieces")

# Show current list
if st.session_state.cut_list:
    st.sidebar.write("### Current List:")
    # Calculate total area of all required pieces
    total_cut_area = sum(w * h for w, h in st.session_state.cut_list)
    st.sidebar.write(f"Total Items: **{len(st.session_state.cut_list)}**")
    st.sidebar.write(f"Total Required Area: **{total_cut_area:,.2f} in²**")

    if st.sidebar.button("Clear All"):
        st.session_state.cut_list = []
        st.rerun()

# --- OPTIMIZATION LOGIC ---
def solve_packing(cuts, SHEET_W, SHEET_H):
    # Use Best Short Side Fit heuristic for high utilization
    packer = newPacker(mode=PackingMode.Offline, rotation=True)
    
    # Add a generous number of bins (sheets)
    for _ in range(100):
        packer.add_bin(SHEET_W, SHEET_H)
    
    # Add all rectangles to be packed
    for i, (w, h) in enumerate(cuts):
        packer.add_rect(w, h, rid=i)
        
    packer.pack()
    return packer

# --- VISUALIZATION LOGIC ---
def draw_results(packer, SHEET_W, SHEET_H):
    charts = []
    summary_data = [] # For the summary table
    
    for bin_index, abin in enumerate(packer):
        if len(abin) == 0: continue 

        fig, ax = plt.subplots(1)
        # Calculate aspect ratio for correct display
        fig.set_size_inches(8, 8 * (SHEET_H/SHEET_W)) 
        
        ax.set_xlim([0, SHEET_W])
        ax.set_ylim([0, SHEET_H])
        
        # Draw Sheet (Bin)
        ax.add_patch(patches.Rectangle((0, 0), SHEET_W, SHEET_H, 
                                        linewidth=2, edgecolor='black', facecolor='#f0f0f0'))

        used_area = 0
        item_count = 0
        for rect in abin:
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            used_area += w * h
            item_count += 1
            
            # Use a distinctive color for the cuts
            rect_patch = patches.Rectangle((x, y), w, h, 
                                            linewidth=1, edgecolor='white', facecolor='#3b82f6')
            ax.add_patch(rect_patch)
            
            # Smart Labeling (check if piece is large enough for text)
            if w > 5 and h > 5:
                ax.text(x + w/2, y + h/2, f"{w:g}x{h:g}", 
                        ha='center', va='center', fontsize=8, color='white', fontweight='bold')

        total_area = SHEET_W * SHEET_H
        utilization = (used_area / total_area)
        waste_percent = 100 - (utilization * 100)
        
        summary_data.append({
            "Sheet #": bin_index + 1,
            "Items Packed": item_count,
            "Used Area (in²)": used_area,
            "Total Area (in²)": total_area,
            "Utilization": f"{utilization * 100:.1f}%",
            "Waste": f"{waste_percent:.1f}%"
        })

        plt.title(f"Sheet #{bin_index+1} ({SHEET_W}x{SHEET_H} | Waste: {waste_percent:.1f}%)")
        plt.axis('off')
        charts.append(fig)
        
    return charts, summary_data

# --- MAIN DISPLAY ---
if len(st.session_state.cut_list) > 0:
    if st.button("Calculate Optimization"):
        with st.spinner(f"Calculating best fit for a {sheet_w}x{sheet_h} sheet..."):
            
            # Pass user-defined sheet dimensions to the solver
            packer = solve_packing(st.session_state.cut_list, sheet_w, sheet_h)
            figures, summary_data = draw_results(packer, sheet_w, sheet_h)
            
            # --- Results Summary ---
            packed_items = 0
            for abin in packer:
                packed_items += len(abin)
            
            # Display overall results
            st.success(f"Optimization Complete: {packed_items} of {len(st.session_state.cut_list)} pieces packed using {len(figures)} sheet(s) of {sheet_w}x{sheet_h}.")

            # Handle unpacked items
            if packed_items < len(st.session_state.cut_list):
                 st.error(f"Error: {len(st.session_state.cut_list) - packed_items} item(s) could not be packed (either too large or no space found).")
            
            # Display Summary Table
            if summary_data:
                st.header("✨ Optimization Summary")
                df_summary = pd.DataFrame(summary_data)
                
                # Calculate grand totals
                total_used_area = df_summary["Used Area (in²)"].sum()
                total_stock_area = df_summary["Total Area (in²)"].sum()
                overall_utilization = (total_used_area / total_stock_area) * 100
                
                st.metric(
                    label=f"Overall Utilization Across {len(figures)} Sheet(s)", 
                    value=f"{overall_utilization:.2f}%",
                    delta=f"Waste: {(100 - overall_utilization):.2f}%"
                )
                
                # Display detailed table
                st.dataframe(df_summary.set_index("Sheet #"), use_container_width=True)
            
            # --- Visualization ---
            st.header("🖼️ Cutting Plan Visualizations")
            cols = st.columns(2)
            for i, fig in enumerate(figures):
                with cols[i % 2]:
                    st.pyplot(fig)
else:
    st.info("Set your Sheet Dimensions (Step 1), then upload a file or add items manually (Steps 2 & 3) to start the optimization.")
