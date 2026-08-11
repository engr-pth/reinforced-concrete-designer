import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Advanced 3D RC Building Design App", layout="wide")

st.title("🏛️ Advanced 3D RC Building Analysis & Load Combinations (ACI 318-19)")
st.caption("Custom Grid Names, Storey Titles, Material Properties, Load Categorization, Wall/Factored Loads & Analysis Engine")

# ==========================================
# UNIT CONVERSION HELPERS
# ==========================================
# Base internal values will be stored and calculated based on selected primary unit system.
UNIT_SYSTEMS = {
    "SI (Metric: m, kN, MPa)": {
        "len": "m", "force": "kN", "stress": "MPa", "area_load": "kN/m²", "line_load": "kN/m",
        "moment": "kN·m", "dim": "mm", "sf_len": 1.0, "sf_dim": 1000.0
    },
    "Imperial (ft, kip, ksi)": {
        "len": "ft", "force": "kip", "stress": "ksi", "area_load": "ksf", "line_load": "klf",
        "moment": "kip·ft", "dim": "in", "sf_len": 3.28084, "sf_dim": 39.3701
    },
    "Imperial (in, lb, psi)": {
        "len": "in", "force": "lb", "stress": "psi", "area_load": "psi", "line_load": "lb/in",
        "moment": "lb·in", "dim": "in", "sf_len": 39.3701, "sf_dim": 39.3701
    }
}

# ==========================================
# 1. SIDEBAR: UNITS & GEOMETRY
# ==========================================
st.sidebar.header("0. Global Unit Selection")
unit_choice = st.sidebar.selectbox("Select Primary Calculation Unit System", list(UNIT_SYSTEMS.keys()), index=0)
units = UNIT_SYSTEMS[unit_choice]

st.sidebar.header("1. Grid Lines & Storey Definition")

num_stories = st.sidebar.number_input("Number of Stories", value=3, min_value=1, max_value=10)
story_height = st.sidebar.number_input(f"Typical Storey Height ({units['len']})", value=3.5 if units['len']=='m' else 11.5)

bays_x = st.sidebar.number_input("Number of Bays (X-Dir)", value=3, min_value=1)
span_x = st.sidebar.number_input(f"Bay Span X ({units['len']})", value=5.0 if units['len']=='m' else 16.5)

bays_y = st.sidebar.number_input("Number of Bays (Y-Dir)", value=2, min_value=1)
span_y = st.sidebar.number_input(f"Bay Span Y ({units['len']})", value=4.0 if units['len']=='m' else 13.0)

# Custom Grid Line Names
x_grid_labels = [chr(65 + i) for i in range(bays_x + 1)]  # A, B, C, D...
y_grid_labels = [str(j + 1) for j in range(bays_y + 1)]   # 1, 2, 3, 4...

# Custom Storey Names Input
st.sidebar.subheader("Storey Names")
default_storey_names = ["GF", "1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F"]
storey_names = []
for k in range(num_stories + 1):
    name = st.sidebar.text_input(f"Level {k} Name", value=default_storey_names[k] if k <= 10 else f"L{k}")
    storey_names.append(name)

# Building Overall Dimensions
L_total = bays_x * span_x
B_total = bays_y * span_y
H_total = num_stories * story_height

st.sidebar.markdown(f"**Total Length (L):** {L_total:.2f} {units['len']}")
st.sidebar.markdown(f"**Total Width (B):** {B_total:.2f} {units['len']}")
st.sidebar.markdown(f"**Total Height (H):** {H_total:.2f} {units['len']}")

# ==========================================
# 2. SIDEBAR: MATERIALS & REBAR STRENGTHS
# ==========================================
st.sidebar.header("2. Material Strengths")
fc = st.sidebar.number_input(f"Concrete Strength f'c ({units['stress']})", value=28.0 if units['stress']=='MPa' else 4.0)
fy = st.sidebar.number_input(f"Main Steel Rebar Strength fy ({units['stress']})", value=420.0 if units['stress']=='MPa' else 60.0)
fys = st.sidebar.number_input(f"Stirrup/Tie Rebar Strength fys ({units['stress']})", value=280.0 if units['stress']=='MPa' else 40.0)

# ==========================================
# 3. SECTION DEFINITIONS
# ==========================================
st.sidebar.header("3. Section Definitions & Cover")

# Adaptive defaults based on unit
d_unit = units['dim']
col_w = 300 if d_unit == 'mm' else 12
beam_w = 230 if d_unit == 'mm' else 10
beam_h = 450 if d_unit == 'mm' else 18
slab_t = 150 if d_unit == 'mm' else 6

col_sections = {
    f"C_{col_w}x{col_w}": {"b": col_w, "h": col_w, "cover": 40 if d_unit=='mm' else 1.5},
    f"C_{col_w+100}x{col_w+100}": {"b": col_w+(100 if d_unit=='mm' else 4), "h": col_w+(100 if d_unit=='mm' else 4), "cover": 40 if d_unit=='mm' else 1.5}
}

beam_sections = {
    f"B_{beam_w}x{beam_h}": {"b": beam_w, "h": beam_h, "cover": 30 if d_unit=='mm' else 1.5},
    f"B_{beam_w+70}x{beam_h+50}": {"b": beam_w+(70 if d_unit=='mm' else 2), "h": beam_h+(50 if d_unit=='mm' else 2), "cover": 30 if d_unit=='mm' else 1.5}
}

slab_sections = {
    f"S_{slab_t}": {"t": slab_t, "cover": 20 if d_unit=='mm' else 0.75},
    f"S_{slab_t+50}": {"t": slab_t+(50 if d_unit=='mm' else 2), "cover": 20 if d_unit=='mm' else 0.75}
}

def calc_rect_properties(b, h):
    A = b * h
    Ixx = (b * h**3) / 12.0
    Iyy = (h * b**3) / 12.0
    Zxx = (b * h**2) / 6.0
    Zyy = (h * b**2) / 6.0
    return A, Ixx, Iyy, Zxx, Zyy

def calc_slab_properties(t):
    b = 1000.0 if d_unit == 'mm' else 12.0
    A = b * t
    I = (b * t**3) / 12.0
    Z = (b * t**2) / 6.0
    return A, I, Z

# ==========================================
# 4. LOAD DEFINITION (NO FLUID LOAD + WALL & FACTORED LOAD)
# ==========================================
st.sidebar.header("4. Load Definition & Categorization")

# Slab Self Weight Calculation
concrete_density = 24.0 if units['len'] == 'm' else (150.0 / 1000.0 if units['len']=='ft' else 0.0868)
self_weight_slab = (slab_t / (1000.0 if d_unit=='mm' else 12.0)) * concrete_density

st.sidebar.caption(f"Calculated Slab Self Weight: {self_weight_slab:.2f} {units['area_load']}")

# Unfactored Area Loads
finishing_val = st.sidebar.number_input(f"Floor Finishing Load ({units['area_load']})", value=1.2 if units['area_load']=='kN/m²' else 0.025)
finishing_cat = st.sidebar.selectbox("Finishing Load Type", ["Superimposed Dead Load (D)", "Live Load (L)"], index=0)

live_val = st.sidebar.number_input(f"Occupancy Live Load ({units['area_load']})", value=2.0 if units['area_load']=='kN/m²' else 0.04)
live_cat = st.sidebar.selectbox("Live Load Type", ["Live Load (L)", "Superimposed Dead Load (D)"], index=0)

# Feature 2: Direct Factored Load Input for Slab & Wall Load for Beam
st.sidebar.markdown("---")
st.sidebar.subheader("Additional Loads (Wall & Direct Factored)")

enable_custom_factored_slab = st.sidebar.checkbox("Override with Custom Factored Slab Load (wu)")
custom_factored_slab_val = st.sidebar.number_input(f"Direct Factored Slab Load wu ({units['area_load']})", value=10.0 if units['area_load']=='kN/m²' else 0.2, disabled=not enable_custom_factored_slab)

include_wall_load_on_beam = st.sidebar.checkbox("Add Wall Load on Beams", value=True)
wall_line_load = st.sidebar.number_input(f"Beam Wall Load ({units['line_load']})", value=5.0 if units['line_load']=='kN/m' else 0.35, disabled=not include_wall_load_on_beam)
wall_load_cat = st.sidebar.selectbox("Wall Load Type", ["Superimposed Dead Load (D)", "Live Load (L)"], index=0)

# Calculate Unfactored Totals
total_D = self_weight_slab
total_L = 0.0

loads_list = [(finishing_val, finishing_cat), (live_val, live_cat)]
for val, cat in loads_list:
    if "Dead" in cat: total_D += val
    elif "Live" in cat: total_L += val

beam_wall_D = wall_line_load if (include_wall_load_on_beam and "Dead" in wall_load_cat) else 0.0
beam_wall_L = wall_line_load if (include_wall_load_on_beam and "Live" in wall_load_cat) else 0.0

# ==========================================
# MAIN INTERFACE: SECTION TABLES & LOAD SUMMARY
# ==========================================
st.subheader("📋 Pre-Defined Member Section Properties")

tab1, tab2, tab3 = st.tabs(["Columns", "Beams", "Slabs"])

with tab1:
    col_data = []
    for name, p in col_sections.items():
        A, Ixx, Iyy, Zxx, Zyy = calc_rect_properties(p['b'], p['h'])
        col_data.append({
            "Section Name": name, f"b ({d_unit})": p['b'], f"h ({d_unit})": p['h'], f"Cover ({d_unit})": p['cover'],
            f"Area A ({d_unit}²)": f"{A:,.0f}", f"Ixx ({d_unit}⁴)": f"{Ixx:,.2e}", f"Zxx ({d_unit}³)": f"{Zxx:,.2e}"
        })
    st.dataframe(col_data, use_container_width=True)

with tab2:
    beam_data = []
    for name, p in beam_sections.items():
        A, Ixx, Iyy, Zxx, Zyy = calc_rect_properties(p['b'], p['h'])
        beam_data.append({
            "Section Name": name, f"b ({d_unit})": p['b'], f"h ({d_unit})": p['h'], f"Cover ({d_unit})": p['cover'],
            f"Area A ({d_unit}²)": f"{A:,.0f}", f"Ixx ({d_unit}⁴)": f"{Ixx:,.2e}", f"Zxx ({d_unit}³)": f"{Zxx:,.2e}"
        })
    st.dataframe(beam_data, use_container_width=True)

with tab3:
    slab_data = []
    for name, p in slab_sections.items():
        A, I, Z = calc_slab_properties(p['t'])
        slab_data.append({
            "Slab Name": name, f"Thickness t ({d_unit})": p['t'], f"Cover ({d_unit})": p['cover'],
            f"Area/unit ({d_unit}²)": f"{A:,.0f}", f"Inertia I ({d_unit}⁴)": f"{I:,.2e}"
        })
    st.dataframe(slab_data, use_container_width=True)

# ==========================================
# 5. ACI 318-19 LOAD COMBINATIONS (NO FLUID LOAD)
# ==========================================
st.markdown("---")
st.subheader("⚖️ ACI 318-19 Ultimate Load Combinations Analysis")

col_l1, col_l2 = st.columns([1, 1.2])

with col_l1:
    st.info("### Unfactored Load Totals")
    st.write(f"- **Total Slab Dead Load (D):** {total_D:.2f} {units['area_load']}")
    st.write(f"- **Total Slab Live Load (L):** {total_L:.2f} {units['area_load']}")
    if include_wall_load_on_beam:
        st.write(f"- **Beam Wall Load:** {wall_line_load:.2f} {units['line_load']} ({wall_load_cat})")

# ACI 318-19 Equations (Without Fluid Load F)
U1_calc = 1.4 * total_D
U2_calc = 1.2 * total_D + 1.6 * total_L

if enable_custom_factored_slab:
    governing_U = custom_factored_slab_val
else:
    governing_U = max(U1_calc, U2_calc)

with col_l2:
    st.success("### ACI 318-19 Factored Load Combinations (wu)")
    st.write(f"1. **U1 = 1.4D:** {U1_calc:.2f} {units['area_load']}")
    st.write(f"2. **U2 = 1.2D + 1.6L:** {U2_calc:.2f} {units['area_load']}")
    if enable_custom_factored_slab:
        st.warning(f"⚠️ Overridden with Direct Factored Load: {governing_U:.2f} {units['area_load']}")
    else:
        st.markdown(f"👉 **Governing Design Load (wu):** :red[{governing_U:.2f} {units['area_load']}]")

# ==========================================
# 6. MEMBER ASSIGNMENT
# ==========================================
st.markdown("---")
st.subheader("⚙️ Frame Member Assignment per Storey")

col_assign, beam_assign, slab_assign = {}, {}, {}
c_a1, c_a2, c_a3 = st.columns(3)

with c_a1:
    st.write("**Assign Columns:**")
    for k in range(1, num_stories + 1):
        col_assign[k] = st.selectbox(f"Column ({storey_names[k-1]} to {storey_names[k]})", list(col_sections.keys()), index=0)

with c_a2:
    st.write("**Assign Beams:**")
    for k in range(1, num_stories + 1):
        beam_assign[k] = st.selectbox(f"Beam Level {storey_names[k]}", list(beam_sections.keys()), index=0)

with c_a3:
    st.write("**Assign Slabs:**")
    for k in range(1, num_stories + 1):
        slab_assign[k] = st.selectbox(f"Slab Level {storey_names[k]}", list(slab_sections.keys()), index=0)

# ==========================================
# 7. RUN ANALYSIS & RESULT DISPLAY
# ==========================================
st.markdown("---")
st.subheader("📊 Structural Analysis Engine")

run_analysis = st.button("🚀 Run Analysis", type="primary")

if run_analysis:
    st.balloons()
    st.success("✅ Structural Analysis Completed Successfully!")
    
    # Calculate tributary load on typical critical beam
    trib_width = span_y / 2.0  # Tributary width for beam
    factored_beam_wall = (1.4 * beam_wall_D + 1.6 * beam_wall_L)
    w_beam_total = governing_U * trib_width + factored_beam_wall
    
    # Critical Beam Calculations (Simplified Frame Analysis)
    L_b = span_x
    M_pos = (w_beam_total * (L_b**2)) / 11.0  # Approx positive moment ACI
    M_neg = (w_beam_total * (L_b**2)) / 9.0   # Approx negative moment ACI
    V_max = 1.15 * (w_beam_total * L_b) / 2.0  # Approx shear force ACI
    
    # Critical Column Load (Accumulated Axial Load)
    trib_area_col = (span_x) * (span_y)
    P_u_per_floor = governing_U * trib_area_col + factored_beam_wall * (span_x + span_y)
    P_u_total = P_u_per_floor * num_stories
    
    res_col1, res_col2 = st.columns(2)
    
    with res_col1:
        st.markdown("### 🔴 Critical Beam Results (Typical Span)")
        st.metric(label=f"Total Line Load on Beam ({units['line_load']})", value=f"{w_beam_total:.2f}")
        st.metric(label=f"Max (+) Bending Moment ({units['moment']})", value=f"{M_pos:.2f}")
        st.metric(label=f"Max (-) Bending Moment ({units['moment']})", value=f"{M_neg:.2f}")
        st.metric(label=f"Max Shear Force V_u ({units['force']})", value=f"{V_max:.2f}")

    with res_col2:
        st.markdown("### 🔵 Critical Column Results (Ground Level)")
        st.metric(label=f"Axial Load per Floor ({units['force']})", value=f"{P_u_per_floor:.2f}")
        st.metric(label=f"Total Design Axial Load P_u ({units['force']})", value=f"{P_u_total:.2f}")
        st.metric(label=f"Design Governing Combo", value="1.2D + 1.6L" if governing_U == U2_calc else "1.4D")

# ==========================================
# 8. 3D VISUALIZATION WITH SEPARATE VIEW UNIT
# ==========================================
st.markdown("---")
st.subheader("🌐 3D Building Model Visualization")

# Feature 4: Independent View Unit Selection
view_unit = st.selectbox("Select 3D Display Unit (Visual Only)", ["m", "ft", "in", "mm"], index=0)

# Convert coordinates to view unit
scale_map = {"m": 1.0, "ft": 3.28084, "in": 39.3701, "mm": 1000.0}
# Base length in meters for geometry rendering
base_to_m = 1.0 if units['len'] == 'm' else (0.3048 if units['len']=='ft' else 0.0254)
v_scale = base_to_m * scale_map[view_unit]

x_coords = [i * span_x * v_scale for i in range(bays_x + 1)]
y_coords = [j * span_y * v_scale for j in range(bays_y + 1)]
z_coords = [k * story_height * v_scale for k in range(num_stories + 1)]

fig = go.Figure()

# Draw Columns
for x in x_coords:
    for y in y_coords:
        for k in range(num_stories):
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[y, y], z=[z_coords[k], z_coords[k+1]],
                mode='lines', line=dict(color='blue', width=6),
                hoverinfo='text',
                text=f"Column: {col_assign[k+1]} ({storey_names[k]} to {storey_names[k+1]})",
                showlegend=False
            ))

# Draw Beams
for k in range(1, num_stories + 1):
    z = z_coords[k]
    for y in y_coords:
        for i in range(bays_x):
            fig.add_trace(go.Scatter3d(
                x=[x_coords[i], x_coords[i+1]], y=[y, y], z=[z, z],
                mode='lines', line=dict(color='red', width=4),
                hoverinfo='text',
                text=f"Beam: {beam_assign[k]} ({storey_names[k]})",
                showlegend=False
            ))
    for x in x_coords:
        for j in range(bays_y):
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[y_coords[j], y_coords[j+1]], z=[z, z],
                mode='lines', line=dict(color='green', width=4),
                hoverinfo='text',
                text=f"Beam: {beam_assign[k]} ({storey_names[k]})",
                showlegend=False
            ))

# Grid Line Labels
for i, x in enumerate(x_coords):
    fig.add_trace(go.Scatter3d(
        x=[x], y=[-0.8 * v_scale], z=[0],
        mode='text', text=[f"Grid {x_grid_labels[i]}"],
        textfont=dict(size=14, color='darkred'), showlegend=False
    ))

for j, y in enumerate(y_coords):
    fig.add_trace(go.Scatter3d(
        x=[-0.8 * v_scale], y=[y], z=[0],
        mode='text', text=[f"Grid {y_grid_labels[j]}"],
        textfont=dict(size=14, color='darkblue'), showlegend=False
    ))

# Storey Name Labels
for k, z in enumerate(z_coords):
    fig.add_trace(go.Scatter3d(
        x=[-1.5 * v_scale], y=[-1.5 * v_scale], z=[z],
        mode='text', text=[f"<b>{storey_names[k]}</b> (Z={z:.1f}{view_unit})"],
        textfont=dict(size=12, color='black'), showlegend=False
    ))

# Dimension Indicators
fig.add_trace(go.Scatter3d(
    x=[0, L_total * v_scale], y=[-2 * v_scale, -2 * v_scale], z=[0, 0],
    mode='lines+text', line=dict(color='purple', width=4, dash='dash'),
    text=["", f"Length L = {L_total * v_scale:.1f} {view_unit}"], textposition="top center",
    name="Length L"
))

fig.add_trace(go.Scatter3d(
    x=[-2 * v_scale, -2 * v_scale], y=[0, B_total * v_scale], z=[0, 0],
    mode='lines+text', line=dict(color='orange', width=4, dash='dash'),
    text=["", f"Width B = {B_total * v_scale:.1f} {view_unit}"], textposition="top center",
    name="Width B"
))

fig.add_trace(go.Scatter3d(
    x=[-2 * v_scale, -2 * v_scale], y=[-2 * v_scale, -2 * v_scale], z=[0, H_total * v_scale],
    mode='lines+text', line=dict(color='magenta', width=4, dash='dash'),
    text=["", f"Height H = {H_total * v_scale:.1f} {view_unit}"], textposition="top center",
    name="Height H"
))

fig.update_layout(
    scene=dict(
        xaxis_title=f'X Axis ({view_unit})',
        yaxis_title=f'Y Axis ({view_unit})',
        zaxis_title=f'Z Axis ({view_unit})',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=30),
    height=650
)

st.plotly_chart(fig, use_container_width=True)
