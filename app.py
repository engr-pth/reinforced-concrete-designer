import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="3D Structural Frame Auto-Design App", layout="wide")

st.title("🏛️ 3D RC Building Analysis & Visualization (ACI 318)")
st.caption("Interactive 3D Frame Geometry, 3D Load Takedown & Member Auto-Design Engine")

# ==========================================
# 1. SIDEBAR: 3D GEOMETRY & LOADS
# ==========================================
st.sidebar.header("1. 3D Building Geometry")

num_stories = st.sidebar.number_input("Number of Stories", value=3, min_value=1, max_value=10)
story_height = st.sidebar.number_input("Story Height (m)", value=3.5)

bays_x = st.sidebar.number_input("Number of Bays (X-Dir)", value=2, min_value=1)
span_x = st.sidebar.number_input("Bay Span X (m)", value=6.0)

bays_y = st.sidebar.number_input("Number of Bays (Y-Dir)", value=2, min_value=1)
span_y = st.sidebar.number_input("Bay Span Y (m)", value=5.0)

st.sidebar.header("2. Material & Sizing")
fc = st.sidebar.number_input("Concrete Strength f'c (MPa)", value=28.0)
fy = st.sidebar.number_input("Steel Strength fy (MPa)", value=420.0)

# Section sizes
b_beam = st.sidebar.number_input("Beam Width b (mm)", value=300)
h_beam = st.sidebar.number_input("Beam Depth h (mm)", value=500)
b_col = st.sidebar.number_input("Column Size B (mm)", value=400)
h_col = st.sidebar.number_input("Column Size H (mm)", value=400)

st.sidebar.header("3. Area Loading (kN/m²)")
dead_area = st.sidebar.number_input("Superimposed Dead Load (kN/m²)", value=1.5) + (0.15 * 24.0)  # Including 150mm slab self-weight
live_area = st.sidebar.number_input("Live Load (kN/m²)", value=2.0)

# ==========================================
# 2. 3D VISUALIZATION ENGINE (Plotly)
# ==========================================
fig = go.Figure()

# Generate 3D Grid Nodes & Draw Members
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
                showlegend=False
            ))

# Draw Beams (X-direction)
for z in z_coords[1:]:
    for y in y_coords:
        for i in range(bays_x):
            fig.add_trace(go.Scatter3d(
                x=[x_coords[i], x_coords[i+1]], y=[y, y], z=[z, z],
                mode='lines', line=dict(color='red', width=4),
                showlegend=False
            ))

# Draw Beams (Y-direction)
for z in z_coords[1:]:
    for x in x_coords:
        for j in range(bays_y):
            fig.add_trace(go.Scatter3d(
                x=[x, x], y=[y_coords[j], y_coords[j+1]], z=[z, z],
                mode='lines', line=dict(color='green', width=4),
                showlegend=False
            ))

# Add Support Points at Base
base_x, base_y, base_z = np.meshgrid(x_coords, y_coords, [0])
fig.add_trace(go.Scatter3d(
    x=base_x.flatten(), y=base_y.flatten(), z=base_z.flatten(),
    mode='markers', marker=dict(symbol='square', size=8, color='black'),
    name='Supports'
))

fig.update_layout(
    scene=dict(
        xaxis_title='X Axis (m)',
        yaxis_title='Y Axis (m)',
        zaxis_title='Z Axis (Height - m)',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=30),
    height=550
)

# Display 3D Layout
st.subheader("🌐 Interactive 3D Frame View")
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 3. 3D LOAD TAKEDOWN & CRITICAL DESIGN
# ==========================================
st.markdown("---")
st.subheader("📊 Load Takedown & Critical Column/Beam Design")

# Tributary Area Calculation for Interior Column
trib_area_col = span_x * span_y
w_u_area = 1.2 * dead_area + 1.6 * live_area  # kN/m²

# Cumulative Load on Ground Floor Interior Column
Pu_ground_col = w_u_area * trib_area_col * num_stories

# Critical Beam Design Force (Span X)
w_u_beam = w_u_area * span_y  # Distributed Load on Beam (kN/m)
Mu_beam = (w_u_beam * span_x**2) / 10.0  # Approx Bending Moment (kNm)

col1, col2 = st.columns(2)

with col1:
    st.info("### 🟢 Ground Floor Interior Column")
    st.write(f"- **Tributary Area:** {trib_area_col:.2f} m²")
    st.write(f"- **Ultimate Axial Load (Pu):** **{Pu_ground_col:.2f} kN**")
    
    # ACI Column Axial Capacity Check
    Ag = b_col * h_col  # mm²
    phi_Pn_max = 0.65 * 0.80 * (0.85 * fc * (Ag - 0.01*Ag) + fy * 0.01*Ag) / 1000.0  # kN (Assuming 1% steel)
    
    st.write(f"- **Nominal Capacity (φPn,max):** {phi_Pn_max:.2f} kN")
    if Pu_ground_col <= phi_Pn_max:
        st.success("✅ Column Size is ADEQUATE for Axial Compression.")
    else:
        st.error("❌ Column Size is TOO SMALL! Increase B x H dimensions.")

with col2:
    st.info("### 🔴 Critical Beam Section (Ground/1st Floor)")
    st.write(f"- **Beam Distributed Load (wu):** {w_u_beam:.2f} kN/m")
    st.write(f"- **Max Design Moment (Mu):** **{Mu_beam:.2f} kNm**")
    
    # Simple Flexure Steel Calculation
    d_eff = h_beam - 55  # mm
    Rn = (Mu_beam * 1e6) / (0.9 * b_beam * d_eff**2)
    rho = (0.85 * fc / fy) * (1 - np.sqrt(max(0, 1 - (2 * Rn) / (0.85 * fc))))
    As_req = max(rho, 1.4/fy) * b_beam * d_eff
    
    st.write(f"- **Required Steel Area (As):** **{As_req:.1f} mm²**")
    rebar_count = int(np.ceil(As_req / 314.0))  # Using D20 bars
    st.success(f"👉 Provide: **{max(2, rebar_count)} - D20 Bars**")
