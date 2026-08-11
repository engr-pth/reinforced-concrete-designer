import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="3-Storey RC Building Auto-Design App", layout="wide")

st.title("🏗️ 3-Storey RC Building Auto-Design Tool (ACI 318-19)")
st.caption("Building Geometry, Load Takedown, Structural Analysis & Member Design Engine")

# ==========================================
# 1. SIDEBAR: GEOMETRY & MATERIAL INPUTS
# ==========================================
st.sidebar.header("1. Geometry & Material Inputs")

# Building Geometry
num_stories = 3
story_height = st.sidebar.number_input("Story Height (m)", value=3.5, step=0.5)
span_x = st.sidebar.number_input("Bay Width - Span X (m)", value=6.0, step=0.5)
bay_y = st.sidebar.number_input("Tributary Length - Y Direction (m)", value=5.0, step=0.5)

# Material Properties
st.sidebar.subheader("Material Properties")
fc = st.sidebar.number_input("Concrete Strength f'c (MPa)", value=28.0)
fy = st.sidebar.number_input("Steel Yield Strength fy (MPa)", value=420.0)
E_conc = 4700 * np.sqrt(fc) * 1e3  # kPa (ACI 318-19 Eq.)

# Section Sizing (Initial)
st.sidebar.subheader("Member Cross-Sections")
b_beam = st.sidebar.number_input("Beam Width b (mm)", value=300)
h_beam = st.sidebar.number_input("Beam Depth h (mm)", value=500)
cc_beam = st.sidebar.number_input("Concrete Cover (mm)", value=40)

# ==========================================
# 2. SIDEBAR: LOAD TAKEDOWN INPUTS
# ==========================================
st.sidebar.header("2. Loading Conditions")

slab_thickness = st.sidebar.number_input("Slab Thickness (mm)", value=150) / 1000.0  # m
sdl = st.sidebar.number_input("Superimposed Dead Load - SDL (kN/m²)", value=1.5)
live_load = st.sidebar.number_input("Live Load - LL (kN/m²)", value=2.0)
wind_load_per_floor = st.sidebar.number_input("Lateral Wind/Earthquake Force per Floor (kN)", value=25.0)

# Load Takedown Calculations
conc_unit_weight = 24.0  # kN/m³
slab_self_weight = slab_thickness * conc_unit_weight  # kN/m²

total_dead_load_area = slab_self_weight + sdl  # kN/m²
dead_load_beam = total_dead_load_area * bay_y  # Distributed load on beam (kN/m)
live_load_beam = live_load * bay_y              # Distributed load on beam (kN/m)

# ACI 318 Load Combinations for Beam Analysis
# Comb 1: 1.4D
# Comb 2: 1.2D + 1.6L
w_u_comb1 = 1.4 * dead_load_beam
w_u_comb2 = 1.2 * dead_load_beam + 1.6 * live_load_beam
w_u_design = max(w_u_comb1, w_u_comb2)  # Governing Gravity UDL (kN/m)

# ==========================================
# MAIN PAGE: DISPLAY SUMMARY & STRUCTURE
# ==========================================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Load Takedown Summary")
    st.write(f"- **Slab Self-Weight:** {slab_self_weight:.2f} kN/m²")
    st.write(f"- **Total Dead Load (Area):** {total_dead_load_area:.2f} kN/m²")
    st.write(f"- **Tributary Width (Y-Dir):** {bay_y:.2f} m")
    st.write(f"- **Beam Dead Load (UDL):** {dead_load_beam:.2f} kN/m")
    st.write(f"- **Beam Live Load (UDL):** {live_load_beam:.2f} kN/m")
    st.info(f"**Governing Ultimate Load (1.2D + 1.6L): {w_u_design:.2f} kN/m**")

with col2:
    st.subheader("🖼️ Structural Grid & Elevation")
    fig_grid, ax_grid = plt.subplots(figsize=(5, 4))
    
    # Plot frame grid
    X = [0, span_x]
    for s in range(num_stories + 1):
        Y = s * story_height
        ax_grid.plot(X, [Y, Y], 'k-', lw=2)  # Beams
    
    for x_pos in X:
        ax_grid.plot([x_pos, x_pos], [0, num_stories * story_height], 'b-', lw=3)  # Columns
        ax_grid.plot(x_pos, 0, '^r', ms=10)  # Supports
    
    ax_grid.set_ylabel("Height (m)")
    ax_grid.set_xlabel("Span X (m)")
    ax_grid.set_title("3-Storey 2D Structural Frame")
    ax_grid.grid(True, linestyle="--", alpha=0.5)
    st.pyplot(fig_grid)

st.markdown("---")

# ==========================================
# 3. 2D FRAME STRUCTURAL ANALYSIS ENGINE
# ==========================================
st.subheader("⚡ Structural Analysis (1st Floor Critical Beam)")

# Simplified Frame Moment Coefficient Approximation (ACI 318 Chapter 6 / Elastic Approx)
# Critical Mid-span Moment Mu(+) and Negative End Moment Mu(-)
L = span_x
M_u_pos = (w_u_design * L**2) / 11.0   # Mid-span positive moment (kNm)
M_u_neg = (w_u_design * L**2) / 9.0    # Support negative moment (kNm)
V_u = (w_u_design * L) / 2.0           # Ultimate Shear Force (kN)

c1, c2, c3 = st.columns(3)
c1.metric("Max Positive Moment (Mu+)", f"{M_u_pos:.2f} kNm")
c2.metric("Max Negative Moment (Mu-)", f"{M_u_neg:.2f} kNm")
c3.metric("Max Shear Force (Vu)", f"{V_u:.2f} kN")

# ==========================================
# 4. ACI 318-19 FLEXURAL & SHEAR DESIGN
# ==========================================
st.subheader("📐 ACI 318-19 Member Auto-Design (Beam Section)")

d_eff = h_beam - cc_beam - 10 - 20/2  # Effective depth assuming 10mm stirrup & 20mm rebar
phi_flexure = 0.90
phi_shear = 0.75

def design_flexure(M_u, b, d, fc, fy):
    """ACI 318 Flexural Reinforcement Calculation"""
    M_u_Nmm = M_u * 1e6
    Rn = M_u_Nmm / (phi_flexure * b * d**2)
    
    # Check Section Capacity Limit
    rho_max = 0.85 * (0.85 * fc / fy) * (3/8)  # Tension-controlled limit (epsilon_t >= 0.005)
    
    term = 1 - (2 * Rn) / (0.85 * fc)
    if term < 0:
        return None, "Section dimensions too small! Doubly reinforced section required."
    
    rho = (0.85 * fc / fy) * (1 - np.sqrt(term))
    
    # Minimum Reinforcement Check (ACI 318-19 Section 9.6.1.2)
    rho_min = max(0.25 * np.sqrt(fc) / fy, 1.4 / fy)
    rho_provided = max(rho, rho_min)
    
    As_required = rho_provided * b * d
    return As_required, rho_provided

# Flexure Design
As_pos, rho_pos = design_flexure(M_u_pos, b_beam, d_eff, fc, fy)
As_neg, rho_neg = design_flexure(M_u_neg, b_beam, d_eff, fc, fy)

# Shear Design (ACI 318-19 Section 22.5)
Vc = 0.17 * np.sqrt(fc) * b_beam * d_eff / 1000.0  # Concrete Shear Strength (kN)
phi_Vc = phi_shear * Vc

st.markdown("#### Design Results Summary")

col_des1, col_des2 = st.columns(2)

with col_des1:
    st.write("**Flexural Reinforcement (As):**")
    if As_pos:
        st.write(f"- **Mid-Span (+Mu):** As = **{As_pos:.1f} mm²** (ρ = {rho_pos*100:.2f}%)")
        rebar_pos = int(np.ceil(As_pos / (np.pi * 20**2 / 4)))
        st.info(f"👉 Provide: **{max(2, rebar_pos)} - D20 Bars** at Bottom")
        
    if As_neg:
        st.write(f"- **Support (-Mu):** As = **{As_neg:.1f} mm²** (ρ = {rho_neg*100:.2f}%)")
        rebar_neg = int(np.ceil(As_neg / (np.pi * 20**2 / 4)))
        st.info(f"👉 Provide: **{max(2, rebar_neg)} - D20 Bars** at Top")

with col_des2:
    st.write("**Shear Reinforcement (Stirrups):**")
    st.write(f"- **Concrete Shear Strength (φVc):** {phi_Vc:.2f} kN")
    st.write(f"- **Applied Ultimate Shear (Vu):** {V_u:.2f} kN")
    
    if V_u <= 0.5 * phi_Vc:
        st.success("✅ Minimum stirrups required by code.")
    elif V_u <= phi_Vc:
        st.warning("⚠️ Vu > 0.5φVc: Provide minimum stirrups (e.g., RB10 @ 200mm c/c).")
    else:
        Vs_req = (V_u - phi_Vc) / phi_shear  # kN
        Av = 2 * (np.pi * 10**2 / 4)         # 2-legged 10mm stirrup area (mm²)
        s_req = (Av * fy * d_eff) / (Vs_req * 1000.0)
        s_final = min(s_req, d_eff/2, 300.0)
        st.error(f"❌ Shear Reinforcement Required: **RB10 @ {int(s_final)} mm c/c**")
