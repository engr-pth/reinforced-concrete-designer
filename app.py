import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as patches

st.set_page_config(page_title="Advanced 3D RC Building Design App", layout="wide")

st.title("🏛️ Advanced 3D RC Building Analysis, Code Check & Section Modeler")
st.caption("Custom Grid Names, Storey Titles, Material Properties, Editable Sections, Load Takedown & ACI 318 Check Engine")

# ==========================================
# UNIT CONVERSION HELPERS
# ==========================================
UNIT_SYSTEMS = {
    "SI (Metric: m, kN, MPa)": {
        "len": "m", "force": "kN", "stress": "MPa", "area_load": "kN/m²", "line_load": "kN/m",
        "moment": "kN·m", "dim": "mm", "sf_len": 1.0, "sf_dim": 1000.0, "sf_force": 1.0
    },
    "Imperial (ft, kip, ksi)": {
        "len": "ft", "force": "kip", "stress": "ksi", "area_load": "ksf", "line_load": "klf",
        "moment": "kip·ft", "dim": "in", "sf_len": 3.28084, "sf_dim": 39.3701, "sf_force": 0.224809 # kN to kip
    }
}

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if 'col_sections' not in st.session_state:
    st.session_state['col_sections'] = {
        "C300x300": {"b": 300, "h": 300, "cover": 40},
        "C400x400": {"b": 400, "h": 400, "cover": 40}
    }
if 'beam_sections' not in st.session_state:
    st.session_state['beam_sections'] = {
        "B230x450": {"b": 230, "h": 450, "cover": 30},
        "B300x600": {"b": 300, "h": 600, "cover": 30}
    }
if 'slab_sections' not in st.session_state:
    st.session_state['slab_sections'] = {
        "S150": {"t": 150, "cover": 20},
        "S125": {"t": 125, "cover": 20}
    }

# Helper functions for property calculation
def calc_rect_properties(b, h):
    A = b * h
    Ixx = (b * h**3) / 12.0
    return A, Ixx

# ==========================================
# 1. SIDEBAR: UNITS & GEOMETRY
# ==========================================
st.sidebar.header("0. Global Unit Selection")
unit_choice = st.sidebar.selectbox("Select Primary Unit System", list(UNIT_SYSTEMS.keys()), index=0)
units = UNIT_SYSTEMS[unit_choice]

st.sidebar.header("1. Geometry & Storey")
bays_x = st.sidebar.number_input("Number of Bays X", value=2, min_value=1)
bays_y = st.sidebar.number_input("Number of Bays Y", value=2, min_value=1)
num_stories = st.sidebar.number_input("Number of Stories", value=3, min_value=1)
story_height = st.sidebar.number_input(f"Story Height ({units['len']})", value=3.5 if units['len']=='m' else 11.5)
span_x = st.sidebar.number_input(f"Bay Span X ({units['len']})", value=6.0 if units['len']=='m' else 20.0)
span_y = st.sidebar.number_input(f"Bay Span Y ({units['len']})", value=5.0 if units['len']=='m' else 16.5)

L_total = bays_x * span_x
B_total = bays_y * span_y
H_total = num_stories * story_height

st.sidebar.markdown(f"**Overall:** {L_total:.2f}x{B_total:.2f}x{H_total:.2f} {units['len']}")

# Custom Storey Names
st.sidebar.subheader("Storey Names")
storey_names = []
for k in range(num_stories + 1):
    storey_names.append(st.sidebar.text_input(f"L{k} Name", value=f"L{k}" if k > 0 else "GF"))

# ==========================================
# 2. SIDEBAR: MATERIALS
# ==========================================
st.sidebar.header("2. Materials (ACI 318)")
fc = st.sidebar.number_input(f"Concrete f'c ({units['stress']})", value=28.0 if units['stress']=='MPa' else 4.0)
fy = st.sidebar.number_input(f"Steel fy ({units['stress']})", value=420.0 if units['stress']=='MPa' else 60.0)

# ==========================================
# 3. SIDEBAR: LOADING
# ==========================================
st.sidebar.header("3. Area Loading (kN/m²)")
dead_area_load = st.sidebar.number_input("SDL & Slab Self Weight (kN/m²)", value=4.5)
live_area_load = st.sidebar.number_input("Live Load (kN/m²)", value=2.0)

# Load Takedown to Column (Tributary Area)
trib_area = span_x * span_y
w_unfactored = dead_area_load + live_area_load # kN/m²
w_u_area = max(1.4*dead_area_load, 1.2*dead_area_load + 1.6*live_area_load) # kN/m²
governing_U = w_u_area

# Cumulative Load on Ground Floor Column (Interior)
P_u_accum = w_u_area * trib_area * num_stories # kN

# Load on Beam (Typical Span)
w_u_beam = w_u_area * (span_y / 2.0) # Tributary from Slab, kN/m

# ==========================================
# MAIN INTERFACE: PRE-DEFINED MEMBER SECTIONS
# ==========================================
st.subheader("📋 Pre-Defined Member Section Properties (Editable Names)")

tab1, tab2, tab3 = st.tabs(["Columns", "Beams", "Slabs"])

# --- Columns ---
with tab1:
    cols_to_render = []
    current_col_names = list(st.session_state['col_sections'].keys())
    for name in current_col_names:
        p = st.session_state['col_sections'][name]
        c1, c2 = st.columns([1, 2])
        new_name = c1.text_input(f"Edit Name for {name}", value=name, key=f"col_edit_{name}")
        if new_name != name:
            st.session_state['col_sections'][new_name] = st.session_state['col_sections'].pop(name)
            current_name = new_name
            p = st.session_state['col_sections'][new_name]
        else:
            current_name = name

        A, Ixx = calc_rect_properties(p['b'], p['h'])
        cols_to_render.append({
            "Name": current_name, f"b ({units['dim']})": p['b'], f"h ({units['dim']})": p['h'], 
            f"Cover ({units['dim']})": p['cover'], f"Area ({units['dim']}²)": f"{A:,.0f}"
        })
    st.dataframe(cols_to_render, use_container_width=True)

# --- Beams ---
with tab2:
    current_beam_names = list(st.session_state['beam_sections'].keys())
    beams_to_render = []
    for name in current_beam_names:
        p = st.session_state['beam_sections'][name]
        c1, c2 = st.columns([1, 2])
        new_name = c1.text_input(f"Edit Name for {name}", value=name, key=f"beam_edit_{name}")
        if new_name != name:
            st.session_state['beam_sections'][new_name] = st.session_state['beam_sections'].pop(name)
            p = st.session_state['beam_sections'][new_name]
            current_name = new_name
        else:
            current_name = name

        A, Ixx = calc_rect_properties(p['b'], p['h'])
        beams_to_render.append({
            "Name": current_name, f"b ({units['dim']})": p['b'], f"h ({units['dim']})": p['h'], 
            f"Cover ({units['dim']})": p['cover'], f"Area ({units['dim']}²)": f"{A:,.0f}"
        })
    st.dataframe(beams_to_render, use_container_width=True)

# --- Slabs per meter width ---
with tab3:
    current_slab_names = list(st.session_state['slab_sections'].keys())
    slabs_to_render = []
    for name in current_slab_names:
        p = st.session_state['slab_sections'][name]
        c1, c2 = st.columns([1, 2])
        new_name = c1.text_input(f"Edit Name for {name}", value=name, key=f"slab_edit_{name}")
        if new_name != name:
            st.session_state['slab_sections'][new_name] = st.session_state['slab_sections'].pop(name)
            p = st.session_state['slab_sections'][new_name]
            current_name = new_name
        else:
            current_name = name

        A = 1000.0 * p['t']
        Ixx = (1000.0 * p['t']**3) / 12.0
        slabs_to_render.append({
            "Name": current_name, f"t ({units['dim']})": p['t'], f"Cover ({units['dim']})": p['cover'],
            f"Area ({units['dim']}²)": f"{A:,.0f}", f"Inertia ({units['dim']}⁴)": f"{Ixx:,.2e}"
        })
    st.dataframe(slabs_to_render, use_container_width=True)

# Member Assignment
st.sidebar.markdown("---")
st.sidebar.subheader("Member Assignment")
assigned_col_name = st.sidebar.selectbox("Critical Column Section", list(st.session_state['col_sections'].keys()))
assigned_beam_name = st.sidebar.selectbox("Critical Beam Section", list(st.session_state['beam_sections'].keys()))
assigned_slab_name = st.sidebar.selectbox("Typical Slab Section", list(st.session_state['slab_sections'].keys()))

# Get Assigned Properties
assigned_col = st.session_state['col_sections'][assigned_col_name]
assigned_beam = st.session_state['beam_sections'][assigned_beam_name]
assigned_slab = st.session_state['slab_sections'][assigned_slab_name]

# ==========================================
# RUN ANALYSIS, CODE CHECK & RECOMMENDATIONS
# ==========================================
st.markdown("---")
st.subheader("⚙️ ACI 318 Code Check & Design Results")

# Simplified Analysis Engine for Moments/Shear
L = span_x
M_u_beam_pos = (w_u_beam * L**2) / 11.0 # Approximate Pos Moment (kN-m)
M_u_beam_neg = (w_u_beam * L**2) / 9.0  # Approximate Neg Moment (kN-m)
V_u_beam = (w_u_beam * L) / 2.0         # Approximate Max Shear (kN)

def calc_beam_capacity(b, h, cover, fc_val, fy_val):
    d = h - cover - 10
    phi_mn = 0.90
    As_min = max(0.25 * np.sqrt(fc_val) / fy_val, 1.4 / fy_val) * b * d
    As_estimated = As_min * 1.5 
    Mn_estimated = (As_estimated * fy_val * (d - 0.5*As_estimated*fy_val/(0.85*fc_val*b))) / 1e6 # kN-m
    phi_vn = 0.75
    Vn_estimated = (0.17 * np.sqrt(fc_val) * b * d) / 1000.0 # kN
    return phi_mn * Mn_estimated, phi_vn * Vn_estimated, As_min

def calc_column_capacity(B, H, fc_val, fy_val):
    Ag = B * H
    Ast_min = 0.01 * Ag
    phi = 0.65
    alpha = 0.80
    Pn_max = (alpha * phi * (0.85 * fc_val * (Ag - Ast_min) + fy_val * Ast_min)) / 1000.0 # kN
    return Pn_max

results_col = {}
results_beam = {}
results_slab = {}

with st.expander("Show detailed code check calculation parameters", expanded=False):
    st.write(f"Governing Area Load: {w_u_area:.2f} kN/m²")
    st.write(f"Beam Design Load (UDL): {w_u_beam:.2f} kN/m")

run_analysis = st.button("🚀 Run Analysis & Code Check", type="primary")

if run_analysis:
    st.markdown("### Analysis Results & Recommendation")
    col_r1, col_r2, col_r3 = st.columns(3)
    
    # Critical Column Check
    Pn_max = calc_column_capacity(assigned_col['b'], assigned_col['h'], fc, fy)
    Pn_max_disp = Pn_max * units['sf_force']
    P_u_accum_disp = P_u_accum * units['sf_force']

    is_col_ok = Pn_max > P_u_accum
    results_col['text'] = "OK" if is_col_ok else "NOT OK"
    results_col['color'] = "green" if is_col_ok else "red"
    results_col['rec'] = "Increase column dimension (BxH) Thicker dimensions may be needed." if not is_col_ok else "No action required."

    # Critical Beam Check
    phiMn, phiVn, As_min = calc_beam_capacity(assigned_beam['b'], assigned_beam['h'], assigned_beam['cover'], fc, fy)
    max_Mu = max(M_u_beam_pos, M_u_beam_neg)
    is_beam_ok = phiMn > max_Mu
    results_beam['text'] = "OK" if is_beam_ok else "NOT OK"
    results_beam['color'] = "green" if is_beam_ok else "red"
    results_beam['rec'] = "Increase beam depth (h) for higher Mn capacity. Or add reinforcement." if not is_beam_ok else "Verify reinforcement detailing."

    # Slab Check
    w_u_slab = w_u_area * 1.0
    L_s = span_x if span_x < span_y else span_y
    M_u_slab = (w_u_slab * L_s**2) / 10.0
    phiMn_slab, phiVn_slab, As_min_slab = calc_beam_capacity(1000.0, assigned_slab['t'], assigned_slab['cover'], fc, fy)
    is_slab_ok = phiMn_slab > M_u_slab
    results_slab['text'] = "OK" if is_slab_ok else "NOT OK"
    results_slab['color'] = "green" if is_slab_ok else "red"
    results_slab['rec'] = "Increase slab thickness (t) to meet moment requirement." if not is_slab_ok else "Provide required As_min."

    with col_r1:
        st.markdown(f"**🔵 Critical Column:** {assigned_col_name}")
        st.markdown(f"Applied Pu: **{P_u_accum_disp:.1f} {units['force']}**")
        st.markdown(f"Capacity φPn,max: **{Pn_max_disp:.1f} {units['force']}**")
        st.markdown(f"Status: <span style='color:{results_col['color']}; font-weight:bold;'>{results_col['text']}</span>", unsafe_allow_html=True)
        st.info(f"👉 **Recommendation:** {results_col['rec']}")

    with col_r2:
        st.markdown(f"**🔴 Critical Beam:** {assigned_beam_name}")
        st.markdown(f"Applied Mu: **{max_Mu:.1f} kN-m**")
        st.markdown(f"Status: <span style='color:{results_beam['color']}; font-weight:bold;'>{results_beam['text']}</span>", unsafe_allow_html=True)
        st.info(f"👉 **Recommendation:** {results_beam['rec']}")

    with col_r3:
        st.markdown(f"**⚪ Typical Slab:** {assigned_slab_name}")
        st.markdown(f"Status: <span style='color:{results_slab['color']}; font-weight:bold;'>{results_slab['text']}</span>", unsafe_allow_html=True)
        st.info(f"👉 **Recommendation:** {results_slab['rec']}")

# ==========================================
# MEMBER CROSS-SECTIONAL VISUALIZATION
# ==========================================
st.markdown("---")
st.subheader("🖼️ Critical Member Cross-Sections")

def plot_section_matplotlib(section_type, section_data, fc_val, fy_val, units_dim):
    fig, ax = plt.subplots(figsize=(4, 4))
    b = float(section_data['b'])
    h = float(section_data['h'])
    cover = float(section_data['cover'])
    
    concrete_rect = patches.Rectangle((0, 0), b, h, linewidth=2, edgecolor='black', facecolor='lightgrey')
    ax.add_patch(concrete_rect)
    
    rebar_radius = b * 0.03
    stirrup_rect = patches.Rectangle((cover, cover), b-2*cover, h-2*cover, linewidth=1, edgecolor='red', facecolor='none', linestyle='-')
    ax.add_patch(stirrup_rect)
    
    rebar_color = 'darkblue'
    if section_type == 'Column':
        rebar_pos = [
            (cover+rebar_radius, cover+rebar_radius), 
            (b-cover-rebar_radius, cover+rebar_radius),
            (cover+rebar_radius, h-cover-rebar_radius),
            (b-cover-rebar_radius, h-cover-rebar_radius)
        ]
        for x, y in rebar_pos:
            reb_circle = patches.Circle((x, y), radius=rebar_radius, facecolor=rebar_color, edgecolor='none')
            ax.add_patch(reb_circle)
            
    elif section_type == 'Beam':
        rebar_pos_beam = [
            (cover+rebar_radius, cover+rebar_radius), 
            (b-cover-rebar_radius, cover+rebar_radius),
            (b/2.0, h-cover-rebar_radius),
            (cover+rebar_radius, h-cover-rebar_radius),
            (b-cover-rebar_radius, h-cover-rebar_radius)
        ]
        for x, y in rebar_pos_beam:
            reb_circle = patches.Circle((x, y), radius=rebar_radius, facecolor=rebar_color, edgecolor='none')
            ax.add_patch(reb_circle)
            
    elif section_type == 'Slab':
        num_rebars_slab = 10
        spacing = b / num_rebars_slab
        for i in range(num_rebars_slab):
            x = i * spacing + spacing/2.0
            y = cover
            reb_circle = patches.Circle((x, y), radius=rebar_radius/2.0, facecolor=rebar_color, edgecolor='none')
            ax.add_patch(reb_circle)

    ax.plot([0, b], [-h*0.05, -h*0.05], 'k-', lw=1)
    ax.text(b/2.0, -h*0.1, f"b={b:.0f}{units_dim}", ha='center')
    ax.plot([-b*0.05, -b*0.05], [0, h], 'k-', lw=1)
    ax.text(-b*0.1, h/2.0, f"h={h:.0f}{units_dim}", va='center', rotation='vertical')
    ax.text(cover*1.1, h-cover*1.1, f"Cover={cover:.0f}{units_dim}", size=8, color='red')

    ax.text(b, h, f"f'c: {fc_val:.0f}{units_dim[:-1]}Pa", ha='right', va='top', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2'))
    ax.text(b, h*0.9, f"fy: {fy_val:.0f}{units_dim[:-1]}Pa", ha='right', va='top', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.2'))

    ax.set_title(f"{section_type} Section")
    ax.set_aspect('equal', adjustable='box')
    plt.axis('off')
    return fig

sec_col1, sec_col2, sec_col3 = st.columns(3)

with sec_col1:
    st.pyplot(plot_section_matplotlib('Column', assigned_col, fc, fy, units['dim']))
with sec_col2:
    st.pyplot(plot_section_matplotlib('Beam', assigned_beam, fc, fy, units['dim']))
with sec_col3:
    st.pyplot(plot_section_matplotlib('Slab', {'b': 1000.0 if units['dim']=='mm' else 12.0, 'h': assigned_slab['t'], 'cover': assigned_slab['cover']}, fc, fy, units['dim']))

# ==========================================
# 3D MODEL & DEFORMED SHAPE DISPLAY
# ==========================================
st.markdown("---")
st.subheader("🌐 Interactive 3D Structural View (Deformed Mode Shape Selection)")

c3d_1, c3d_2 = st.columns([1, 4])
view_mode = c3d_1.radio("Select View Mode", ["Undeformed (Original Shape)", "Deformed (Mode Shape Exaggerated)"], index=1)
def_factor = c3d_2.slider("Exaggeration Factor (for deformed shape only)", 100, 10000, 2000, 100)

fig = go.Figure()

x_coords = [i * span_x for i in range(bays_x + 1)]
y_coords = [j * span_y for j in range(bays_y + 1)]
z_coords = [k * story_height for k in range(num_stories + 1)]

def calc_approx_displ(x_val, y_val, z_val):
    w = governing_U
    E_matrix = fc
    dx, dy, dz = 0.0, 0.0, 0.0
    if z_val > 0:
        dy = -( (w * x_val**4 * y_val**4) / E_matrix ) * def_factor / 1e12
        dz = -( (w * (span_x*span_y)**2) / E_matrix ) * def_factor / 1e11
    return dx, dy, dz

def draw_line(x_pair, y_pair, z_pair, color, width, hover_txt, is_deformed):
    x_node = np.array(x_pair, dtype=float)
    y_node = np.array(y_pair, dtype=float)
    z_node = np.array(z_pair, dtype=float)
    
    if is_deformed:
        disp_A = calc_approx_displ(x_node[0], y_node[0], z_node[0])
        disp_B = calc_approx_displ(x_node[1], y_node[1], z_node[1])
        x_node[0] += disp_A[0]
        y_node[0] += disp_A[1]
        z_node[0] += disp_A[2]
        x_node[1] += disp_B[0]
        y_node[1] += disp_B[1]
        z_node[1] += disp_B[2]
        
    fig.add_trace(go.Scatter3d(
        x=x_node, y=y_node, z=z_node,
        mode='lines', line=dict(color=color, width=width),
        hoverinfo='text',
        text=hover_txt,
        showlegend=False
    ))

is_deformed = (view_mode == "Deformed (Mode Shape Exaggerated)")

# Columns drawing
for x in x_coords:
    for y in y_coords:
        for k in range(num_stories):
            txt = f"Column: {assigned_col_name} (Z={z_coords[k]} to {z_coords[k+1]} {units['len']})"
            draw_line([x, x], [y, y], [z_coords[k], z_coords[k+1]], 'blue', 6, txt, is_deformed)

# Beams drawing
for k in range(num_stories + 1):
    z = z_coords[k]
    for y in y_coords:
        for i in range(bays_x):
            txt = f"Beam: {assigned_beam_name} (Span X={span_x} {units['len']})"
            draw_line([x_coords[i], x_coords[i+1]], [y, y], [z, z], 'red', 4, txt, is_deformed)
    for x in x_coords:
        for j in range(bays_y):
            txt = f"Beam: {assigned_beam_name} (Span Y={span_y} {units['len']})"
            draw_line([x, x], [y_coords[j], y_coords[j+1]], [z, z], 'green', 4, txt, is_deformed)

fig.update_layout(
    scene=dict(
        xaxis_title=f'X Axis ({units["len"]})',
        yaxis_title=f'Y Axis ({units["len"]})',
        zaxis_title=f'Z Axis (Height - {units["len"]})',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=30),
    height=600
)

st.plotly_chart(fig, use_container_width=True)
