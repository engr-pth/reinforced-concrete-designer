import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Advanced 3D RC Building Design App", layout="wide")

st.title("🏛️ Advanced 3D RC Building Analysis & Load Combinations (ACI 318-19)")
st.caption("Custom Grid Names, Storey Titles, Material Properties, Load Categorization & ACI Load Combinations Engine")

# ==========================================
# 1. SIDEBAR: BUILDING GEOMETRY & GRID NAMES
# ==========================================
st.sidebar.header("1. Grid Lines & Storey Definition")

num_stories = st.sidebar.number_input("Number of Stories", value=3, min_value=1, max_value=10)
story_height = st.sidebar.number_input("Typical Storey Height (m)", value=3.5)

bays_x = st.sidebar.number_input("Number of Bays (X-Dir)", value=3, min_value=1)
span_x = st.sidebar.number_input("Bay Span X (m)", value=5.0)

bays_y = st.sidebar.number_input("Number of Bays (Y-Dir)", value=2, min_value=1)
span_y = st.sidebar.number_input("Bay Span Y (m)", value=4.0)

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

st.sidebar.markdown(f"**Total Length (L):** {L_total:.2f} m")
st.sidebar.markdown(f"**Total Width (B):** {B_total:.2f} m")
st.sidebar.markdown(f"**Total Height (H):** {H_total:.2f} m")

# ==========================================
# 2. SIDEBAR: MATERIALS & REBAR STRENGTHS
# ==========================================
st.sidebar.header("2. Material Strengths")
fc = st.sidebar.number_input("Concrete Strength f'c (MPa)", value=28.0)
fy = st.sidebar.number_input("Main Steel Rebar Strength fy (MPa)", value=420.0)
fys = st.sidebar.number_input("Stirrup/Tie Rebar Strength fys (MPa)", value=280.0)

# ==========================================
# 3. SECTION DEFINITIONS & AUTO PROPERTIES
# ==========================================
st.sidebar.header("3. Section Definitions & Concrete Cover")

# Column Sections
col_sections = {
    "C300x300": {"b": 300, "h": 300, "cover": 40},
    "C400x400": {"b": 400, "h": 400, "cover": 40},
    "C500x500": {"b": 500, "h": 500, "cover": 40}
}

# Beam Sections
beam_sections = {
    "B230x450": {"b": 230, "h": 450, "cover": 30},
    "B300x500": {"b": 300, "h": 500, "cover": 30},
    "B300x600": {"b": 300, "h": 600, "cover": 30}
}

# Slab Sections
slab_sections = {
    "S125": {"t": 125, "cover": 20},
    "S150": {"t": 150, "cover": 20},
    "S200": {"t": 200, "cover": 20}
}

def calc_rect_properties(b, h):
    A = b * h                        # Area (mm2)
    Ixx = (b * h**3) / 12.0          # Inertia X (mm4)
    Iyy = (h * b**3) / 12.0          # Inertia Y (mm4)
    Zxx = (b * h**2) / 6.0           # Section Modulus Zx (mm3)
    Zyy = (h * b**2) / 6.0           # Section Modulus Zy (mm3)
    return A, Ixx, Iyy, Zxx, Zyy

def calc_slab_properties(t):
    b = 1000.0
    A = b * t
    I = (b * t**3) / 12.0
    Z = (b * t**2) / 6.0
    return A, I, Z

# ==========================================
# 4. LOAD DEFINITION & CATEGORIZATION
# ==========================================
st.sidebar.header("4. Load Definition & Categorization")

# Slab Self Weight (Auto-calculated based on selected slab)
slab_thick_mm = slab_sections["S150"]["t"]
self_weight_slab = (slab_thick_mm / 1000.0) * 24.0  # kN/m²

st.sidebar.caption(f"Calculated Slab Self Weight (24 kN/m³): {self_weight_slab:.2f} kN/m²")

# Specific Loads Input
finishing_val = st.sidebar.number_input("Floor Finishing Load (kN/m²)", value=1.2)
finishing_cat = st.sidebar.selectbox("Finishing Load Type", ["Superimposed Dead Load (D)", "Live Load (L)"], index=0)

wall_val = st.sidebar.number_input("Wall / Partition Load (kN/m²)", value=1.5)
wall_cat = st.sidebar.selectbox("Wall Load Type", ["Superimposed Dead Load (D)", "Live Load (L)"], index=0)

water_val = st.sidebar.number_input("Water Tank / Fluid Load (kN/m²)", value=2.0)
water_cat = st.sidebar.selectbox("Water Load Type", ["Superimposed Dead Load (D)", "Live Load (L)", "Fluid Load (F)"], index=2)

live_val = st.sidebar.number_input("Occupancy Live Load (kN/m²)", value=2.0)
live_cat = st.sidebar.selectbox("Live Load Type", ["Live Load (L)", "Superimposed Dead Load (D)"], index=0)

# Calculate Total Dead (D), Total Live (L), Total Fluid (F)
total_D = self_weight_slab
total_L = 0.0
total_F = 0.0

loads_list = [
    (finishing_val, finishing_cat),
    (wall_val, wall_cat),
    (water_val, water_cat),
    (live_val, live_cat)
]

for val, cat in loads_list:
    if "Dead" in cat:
        total_D += val
    elif "Live" in cat:
        total_L += val
    elif "Fluid" in cat:
        total_F += val

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
            "Section Name": name, "b (mm)": p['b'], "h (mm)": p['h'], "Cover (mm)": p['cover'],
            "Area A (mm²)": f"{A:,.0f}", "Ixx (mm⁴)": f"{Ixx:,.2e}", "Zxx (mm³)": f"{Zxx:,.2e}"
        })
    st.dataframe(col_data, use_container_width=True)

with tab2:
    beam_data = []
    for name, p in beam_sections.items():
        A, Ixx, Iyy, Zxx, Zyy = calc_rect_properties(p['b'], p['h'])
        beam_data.append({
            "Section Name": name, "b (mm)": p['b'], "h (mm)": p['h'], "Cover (mm)": p['cover'],
            "Area A (mm²)": f"{A:,.0f}", "Ixx (mm⁴)": f"{Ixx:,.2e}", "Zxx (mm³)": f"{Zxx:,.2e}"
        })
    st.dataframe(beam_data, use_container_width=True)

with tab3:
    slab_data = []
    for name, p in slab_sections.items():
        A, I, Z = calc_slab_properties(p['t'])
        slab_data.append({
            "Slab Name": name, "Thickness t (mm)": p['t'], "Cover (mm)": p['cover'],
            "Area per m (mm²/m)": f"{A:,.0f}", "Inertia I (mm⁴/m)": f"{I:,.2e}", "Section Modulus Z (mm³/m)": f"{Z:,.2e}"
        })
    st.dataframe(slab_data, use_container_width=True)

# ==========================================
# 5. ACI 318-19 LOAD COMBINATIONS
# ==========================================
st.markdown("---")
st.subheader("⚖️ ACI 318-19 Ultimate Load Combinations Analysis")

col_l1, col_l2 = st.columns([1, 1.2])

with col_l1:
    st.info("### Unfactored Load Totals")
    st.write(f"- **Total Dead Load (D):** {total_D:.2f} kN/m² *(Slab Self Weight + SDL)*")
    st.write(f"- **Total Live Load (L):** {total_L:.2f} kN/m²")
    st.write(f"- **Total Fluid Load (F):** {total_F:.2f} kN/m²")

# ACI 318-19 Load Combination Equations (Chapter 5)
U1 = 1.4 * total_D + 1.4 * total_F
U2 = 1.2 * total_D + 1.6 * total_L + 1.2 * total_F
U3 = 1.2 * total_D + 1.0 * total_L + 1.2 * total_F  # Simplified gravity check

governing_U = max(U1, U2, U3)

with col_l2:
    st.success("### ACI 318-19 Factored Load Combinations (wu)")
    st.write(f"1. **U1 = 1.4D + 1.4F:** {U1:.2f} kN/m²")
    st.write(f"2. **U2 = 1.2D + 1.6L + 1.2F:** {U2:.2f} kN/m²")
    st.write(f"3. **U3 = 1.2D + 1.0L + 1.2F:** {U3:.2f} kN/m²")
    st.markdown(f"👉 **Governing Design Load (wu):** <h3 style='color:red;'>{governing_U:.2f} kN/m²</h3>", unsafe_allow_allowed_html=True)

# ==========================================
# 6. STOREY-WISE MEMBER ASSIGNMENT
# ==========================================
st.markdown("---")
st.subheader("⚙️ Frame Member Assignment per Storey")

col_assign, beam_assign, slab_assign = {}, {}, {}

c_a1, c_a2, c_a3 = st.columns(3)

with c_a1:
    st.write("**Assign Columns:**")
    for k in range(1, num_stories + 1):
        col_assign[k] = st.selectbox(f"Column ({storey_names[k-1]} to {storey_names[k]})", list(col_sections.keys()), index=1)

with c_a2:
    st.write("**Assign Beams:**")
    for k in range(1, num_stories + 1):
        beam_assign[k] = st.selectbox(f"Beam Level {storey_names[k]}", list(beam_sections.keys()), index=1)

with c_a3:
    st.write("**Assign Slabs:**")
    for k in range(1, num_stories + 1):
        slab_assign[k] = st.selectbox(f"Slab Level {storey_names[k]}", list(slab_sections.keys()), index=1)

# ==========================================
# 7. 3D VISUALIZATION WITH LABELS & DIMENSIONS
# ==========================================
st.markdown("---")
st.subheader("🌐 3D Building Model with Dimensions, Grid & Storey Labels")

fig = go.Figure()

x_coords = [i * span_x for i in range(bays_x + 1)]
y_coords = [j * span_y for j in range(bays_y + 1)]
z_coords = [k * story_height for k in range(num_stories + 1)]

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
    # Beams along X
    for y in y_coords:
        for i in range(bays_x):
            fig.add_trace(go.Scatter3d(
                x=[x_coords[i], x_coords[i+1]], y=[y, y], z=[z, z],
                mode='lines', line=dict(color='red', width=4),
                hoverinfo='text',
                text=f"Beam: {beam_assign[k]} ({storey_names[k]})",
                showlegend=False
            ))
    # Beams along Y
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
        x=[x], y=[-0.8], z=[0],
        mode='text', text=[f"Grid {x_grid_labels[i]}"],
        textfont=dict(size=14, color='darkred'), showlegend=False
    ))

for j, y in enumerate(y_coords):
    fig.add_trace(go.Scatter3d(
        x=[-0.8], y=[y], z=[0],
        mode='text', text=[f"Grid {y_grid_labels[j]}"],
        textfont=dict(size=14, color='darkblue'), showlegend=False
    ))

# Storey Name Labels
for k, z in enumerate(z_coords):
    fig.add_trace(go.Scatter3d(
        x=[-1.5], y=[-1.5], z=[z],
        mode='text', text=[f"<b>{storey_names[k]}</b> (Z={z:.1f}m)"],
        textfont=dict(size=12, color='black'), showlegend=False
    ))

# Dimension Indicators
fig.add_trace(go.Scatter3d(
    x=[0, L_total], y=[-2, -2], z=[0, 0],
    mode='lines+text', line=dict(color='purple', width=4, dash='dash'),
    text=["", f"Length L = {L_total:.1f}m"], textposition="top center",
    name="Length L"
))

fig.add_trace(go.Scatter3d(
    x=[-2, -2], y=[0, B_total], z=[0, 0],
    mode='lines+text', line=dict(color='orange', width=4, dash='dash'),
    text=["", f"Width B = {B_total:.1f}m"], textposition="top center",
    name="Width B"
))

fig.add_trace(go.Scatter3d(
    x=[-2, -2], y=[-2, -2], z=[0, H_total],
    mode='lines+text', line=dict(color='magenta', width=4, dash='dash'),
    text=["", f"Height H = {H_total:.1f}m"], textposition="top center",
    name="Height H"
))

fig.update_layout(
    scene=dict(
        xaxis_title='X Axis (m)',
        yaxis_title='Y Axis (m)',
        zaxis_title='Z Axis (m)',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=30),
    height=650
)

st.plotly_chart(fig, use_container_width=True)
