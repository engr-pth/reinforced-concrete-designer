import streamlit as st
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as patches

st.set_page_config(page_title="Advanced 3D RC Building Design App", layout="wide")

st.title("🏛️ Advanced 3D RC Building Analysis, Code Check & Section Modeler")
st.caption("Custom Grid Names, Storey Titles, Material Properties, Editable Sections, Load Takedown & ACI 318 Check Engine")

# ==========================================
# UNIT CONVERSION DICTIONARIES & HELPERS
# ==========================================
UNIT_SYSTEMS = {
    "SI (Metric: m, kN, MPa)": {
        "len": "m", "force": "kN", "stress": "MPa", "area_load": "kN/m²", "line_load": "kN/m",
        "moment": "kN·m", "dim": "mm", "sf_len": 1.0, "sf_dim": 1000.0, "sf_force": 1.0
    },
    "Imperial (ft, kip, ksi)": {
        "len": "ft", "force": "kip", "stress": "ksi", "area_load": "ksf", "line_load": "klf",
        "moment": "kip·ft", "dim": "in", "sf_len": 3.28084, "sf_dim": 39.3701, "sf_force": 0.224809
    }
}

# Standard Rebar Sizes Database
REBAR_DB_SI = {
    "D10": {"dia": 10.0, "area": 78.54},
    "D12": {"dia": 12.0, "area": 113.10},
    "D16": {"dia": 16.0, "area": 201.06},
    "D20": {"dia": 20.0, "area": 314.16},
    "D25": {"dia": 25.0, "area": 490.87},
    "D32": {"dia": 32.0, "area": 804.25}
}

REBAR_DB_IMP = {
    "#3": {"dia": 0.375, "area": 0.11},
    "#4": {"dia": 0.500, "area": 0.20},
    "#5": {"dia": 0.625, "area": 0.31},
    "#6": {"dia": 0.750, "area": 0.44},
    "#7": {"dia": 0.875, "area": 0.60},
    "#8": {"dia": 1.000, "area": 0.79},
    "#9": {"dia": 1.128, "area": 1.00},
    "#10": {"dia": 1.270, "area": 1.27}
}

# ==========================================
# 0. GLOBAL UNITS & SESSION STATE SAFEGUARD
# ==========================================
st.sidebar.header("0. Global Unit Selection")
unit_choice = st.sidebar.selectbox("Select Primary Calculation Unit System", list(UNIT_SYSTEMS.keys()), index=0)
units = UNIT_SYSTEMS[unit_choice]
is_imperial = "Imperial" in unit_choice

rebar_db = REBAR_DB_IMP if is_imperial else REBAR_DB_SI
default_rebar_key = "#8" if is_imperial else "D20"
default_stirrup_key = "#3" if is_imperial else "D10"

# Fix KeyError: Reset or Update Session State when Unit System Changes
if 'current_unit' not in st.session_state or st.session_state['current_unit'] != unit_choice:
    st.session_state['current_unit'] = unit_choice
    
    st.session_state['col_sections'] = {
        "C1": {"b": 16.0 if is_imperial else 400.0, "h": 16.0 if is_imperial else 400.0, "cover": 1.5 if is_imperial else 40.0, "n_bars": 8, "bar_size": default_rebar_key},
        "C2": {"b": 20.0 if is_imperial else 500.0, "h": 20.0 if is_imperial else 500.0, "cover": 1.5 if is_imperial else 40.0, "n_bars": 12, "bar_size": default_rebar_key}
    }
    st.session_state['beam_sections'] = {
        "B1": {"b": 10.0 if is_imperial else 250.0, "h": 18.0 if is_imperial else 450.0, "cover": 1.5 if is_imperial else 30.0, "n_top": 3, "n_bot": 3, "bar_size": default_rebar_key},
        "B2": {"b": 12.0 if is_imperial else 300.0, "h": 24.0 if is_imperial else 600.0, "cover": 1.5 if is_imperial else 30.0, "n_top": 4, "n_bot": 4, "bar_size": default_rebar_key}
    }
    st.session_state['slab_sections'] = {
        "S1": {"t": 6.0 if is_imperial else 150.0, "cover": 0.75 if is_imperial else 20.0, "bar_size": default_stirrup_key, "spacing": 6.0 if is_imperial else 150.0},
        "S2": {"t": 8.0 if is_imperial else 200.0, "cover": 0.75 if is_imperial else 20.0, "bar_size": default_stirrup_key, "spacing": 6.0 if is_imperial else 150.0}
    }

# ==========================================
# 1. GEOMETRY & MATERIALS
# ==========================================
st.sidebar.header("1. Geometry & Storey")
bays_x = st.sidebar.number_input("Number of Bays X", value=2, min_value=1)
bays_y = st.sidebar.number_input("Number of Bays Y", value=2, min_value=1)
num_stories = st.sidebar.number_input("Number of Stories", value=3, min_value=1)
story_height = st.sidebar.number_input(f"Story Height ({units['len']})", value=12.0 if is_imperial else 3.5)
span_x = st.sidebar.number_input(f"Bay Span X ({units['len']})", value=20.0 if is_imperial else 6.0)
span_y = st.sidebar.number_input(f"Bay Span Y ({units['len']})", value=18.0 if is_imperial else 5.5)

L_total = bays_x * span_x
B_total = bays_y * span_y
H_total = num_stories * story_height
st.sidebar.markdown(f"**Overall:** {L_total:.1f} x {B_total:.1f} x {H_total:.1f} {units['len']}")

st.sidebar.header("2. Materials (ACI 318)")
fc = st.sidebar.number_input(f"Concrete f'c ({units['stress']})", value=4.0 if is_imperial else 28.0)
fy = st.sidebar.number_input(f"Steel fy ({units['stress']})", value=60.0 if is_imperial else 420.0)

st.sidebar.header(f"3. Area Loading ({units['area_load']})")
dead_area_load = st.sidebar.number_input(f"SDL & Slab SW ({units['area_load']})", value=0.100 if is_imperial else 4.8)
live_area_load = st.sidebar.number_input(f"Live Load ({units['area_load']})", value=0.050 if is_imperial else 2.4)

# Ultimate Load Calculation
w_u_area = max(1.4 * dead_area_load, 1.2 * dead_area_load + 1.6 * live_area_load)
trib_area = span_x * span_y
P_u_max_col = w_u_area * trib_area * num_stories
w_u_beam = w_u_area * (span_y / 2.0)

# ==========================================
# MAIN INTERFACE: SECTION MODELER
# ==========================================
st.subheader("📋 Member Section & Rebar Properties (Interactive Setup)")

tab1, tab2, tab3 = st.tabs(["Columns", "Beams", "Slabs"])

unit_tag = "imp" if is_imperial else "si"

with tab1:
    cols_render = []
    for name, p in list(st.session_state['col_sections'].items()):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        p['b'] = c1.number_input(f"{name} Width b ({units['dim']})", value=float(p['b']), key=f"cb_{name}_{unit_tag}")
        p['h'] = c2.number_input(f"{name} Depth h ({units['dim']})", value=float(p['h']), key=f"ch_{name}_{unit_tag}")
        p['n_bars'] = c3.number_input(f"{name} Total Rebars", value=int(p['n_bars']), min_value=4, step=2, key=f"cn_{name}_{unit_tag}")
        
        # Safely handle bar size index
        bar_keys = list(rebar_db.keys())
        idx = bar_keys.index(p['bar_size']) if p['bar_size'] in bar_keys else 0
        p['bar_size'] = c4.selectbox(f"{name} Bar Size", bar_keys, index=idx, key=f"cs_{name}_{unit_tag}")
        
        As_prov = p['n_bars'] * rebar_db[p['bar_size']]['area']
        cols_render.append({
            "Section": name, f"b ({units['dim']})": p['b'], f"h ({units['dim']})": p['h'], 
            "Rebars": f"{p['n_bars']} - {p['bar_size']}", f"As Provided ({units['dim']}²)": f"{As_prov:.2f}"
        })
    st.dataframe(cols_render, use_container_width=True)

with tab2:
    beams_render = []
    for name, p in list(st.session_state['beam_sections'].items()):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
        p['b'] = c1.number_input(f"{name} Width b ({units['dim']})", value=float(p['b']), key=f"bb_{name}_{unit_tag}")
        p['h'] = c2.number_input(f"{name} Depth h ({units['dim']})", value=float(p['h']), key=f"bh_{name}_{unit_tag}")
        p['n_top'] = c3.number_input(f"{name} Top Bars", value=int(p['n_top']), min_value=2, key=f"bnt_{name}_{unit_tag}")
        p['n_bot'] = c4.number_input(f"{name} Bottom Bars", value=int(p['n_bot']), min_value=2, key=f"bnb_{name}_{unit_tag}")
        
        bar_keys = list(rebar_db.keys())
        idx = bar_keys.index(p['bar_size']) if p['bar_size'] in bar_keys else 0
        p['bar_size'] = c5.selectbox(f"{name} Bar Size", bar_keys, index=idx, key=f"bs_{name}_{unit_tag}")

        As_top = p['n_top'] * rebar_db[p['bar_size']]['area']
        As_bot = p['n_bot'] * rebar_db[p['bar_size']]['area']
        beams_render.append({
            "Section": name, f"b ({units['dim']})": p['b'], f"h ({units['dim']})": p['h'],
            "Top Rebar": f"{p['n_top']}-{p['bar_size']} ({As_top:.2f} {units['dim']}²)",
            "Bottom Rebar": f"{p['n_bot']}-{p['bar_size']} ({As_bot:.2f} {units['dim']}²)"
        })
    st.dataframe(beams_render, use_container_width=True)

with tab3:
    slabs_render = []
    for name, p in list(st.session_state['slab_sections'].items()):
        c1, c2, c3 = st.columns([2, 2, 2])
        p['t'] = c1.number_input(f"{name} Thickness t ({units['dim']})", value=float(p['t']), key=f"st_{name}_{unit_tag}")
        p['spacing'] = c2.number_input(f"{name} Bar Spacing ({units['dim']})", value=float(p['spacing']), key=f"ss_{name}_{unit_tag}")
        
        bar_keys = list(rebar_db.keys())
        idx = bar_keys.index(p['bar_size']) if p['bar_size'] in bar_keys else 0
        p['bar_size'] = c3.selectbox(f"{name} Mesh Bar Size", bar_keys, index=idx, key=f"sbs_{name}_{unit_tag}")

        unit_strip = 12.0 if is_imperial else 1000.0
        n_bars_per_strip = unit_strip / p['spacing'] if p['spacing'] > 0 else 0
        As_per_strip = n_bars_per_strip * rebar_db[p['bar_size']]['area']
        slabs_render.append({
            "Section": name, f"t ({units['dim']})": p['t'],
            "Top & Bottom Mesh": f"{p['bar_size']} @ {p['spacing']} {units['dim']} c/c",
            f"As Prov / Unit Strip ({units['dim']}²/unit)": f"{As_per_strip:.2f}"
        })
    st.dataframe(slabs_render, use_container_width=True)

# Assignment
st.sidebar.markdown("---")
st.sidebar.subheader("Member Assignment")
assigned_col_name = st.sidebar.selectbox("Critical Column Section", list(st.session_state['col_sections'].keys()))
assigned_beam_name = st.sidebar.selectbox("Critical Beam Section", list(st.session_state['beam_sections'].keys()))
assigned_slab_name = st.sidebar.selectbox("Typical Slab Section", list(st.session_state['slab_sections'].keys()))

assigned_col = st.session_state['col_sections'][assigned_col_name]
assigned_beam = st.session_state['beam_sections'][assigned_beam_name]
assigned_slab = st.session_state['slab_sections'][assigned_slab_name]

# ==========================================
# CROSS-SECTIONAL VISUALIZATION
# ==========================================
st.markdown("---")
st.subheader("🖼️ Critical Member Cross-Sections (With Top & Bottom Rebars)")

def plot_section_matplotlib(sec_type, p, fc_val, fy_val, is_imp):
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    dim_unit = "in" if is_imp else "mm"
    
    b = float(p['b']) if sec_type != 'Slab' else (12.0 if is_imp else 1000.0)
    h = float(p['h']) if sec_type != 'Slab' else float(p['t'])
    cover = float(p['cover'])

    # Concrete Boundary
    concrete = patches.Rectangle((0, 0), b, h, linewidth=1.5, edgecolor='black', facecolor='#e0e0e0')
    ax.add_patch(concrete)

    # Stirrup line for Column & Beam
    if sec_type in ['Column', 'Beam']:
        stirrup = patches.Rectangle((cover, cover), b - 2*cover, h - 2*cover, linewidth=1, edgecolor='red', facecolor='none', linestyle='--')
        ax.add_patch(stirrup)

    rebar_color = 'darkblue'

    if sec_type == 'Column':
        n = p['n_bars']
        xs = [cover, b - cover]
        ys = [cover, h - cover]
        for x in xs:
            for y in ys:
                ax.add_patch(patches.Circle((x, y), radius=b*0.04, facecolor=rebar_color))
        if n > 4:
            rem = n - 4
            for i in range(1, rem // 2 + 1):
                y_mid = cover + i * (h - 2*cover) / (rem // 2 + 1)
                ax.add_patch(patches.Circle((cover, y_mid), radius=b*0.04, facecolor=rebar_color))
                ax.add_patch(patches.Circle((b - cover, y_mid), radius=b*0.04, facecolor=rebar_color))

    elif sec_type == 'Beam':
        for i in range(p['n_top']):
            x = cover + i * (b - 2*cover) / max(1, (p['n_top'] - 1))
            ax.add_patch(patches.Circle((x, h - cover), radius=b*0.04, facecolor=rebar_color))
        for i in range(p['n_bot']):
            x = cover + i * (b - 2*cover) / max(1, (p['n_bot'] - 1))
            ax.add_patch(patches.Circle((x, cover), radius=b*0.04, facecolor=rebar_color))

    elif sec_type == 'Slab':
        spacing = float(p['spacing'])
        num_bars = int(b / spacing) + 1 if spacing > 0 else 1
        for i in range(num_bars):
            x = cover + i * spacing
            if x <= b - cover:
                # Both Top Mesh & Bottom Mesh Included
                ax.add_patch(patches.Circle((x, h - cover), radius=h*0.05, facecolor='darkred'))
                ax.add_patch(patches.Circle((x, cover), radius=h*0.05, facecolor=rebar_color))

    ax.set_xlim(-b*0.15, b*1.15)
    ax.set_ylim(-h*0.15, h*1.15)
    ax.set_title(f"{sec_type}: {b:.0f}x{h:.0f} {dim_unit}", fontsize=10, fontweight='bold')
    ax.set_aspect('equal')
    plt.axis('off')
    return fig

sc1, sc2, sc3 = st.columns(3)
with sc1:
    st.pyplot(plot_section_matplotlib('Column', assigned_col, fc, fy, is_imperial))
with sc2:
    st.pyplot(plot_section_matplotlib('Beam', assigned_beam, fc, fy, is_imperial))
with sc3:
    st.pyplot(plot_section_matplotlib('Slab', assigned_slab, fc, fy, is_imperial))

# ==========================================
# 3D MODEL WITH DISPLAY UNIT SELECTOR & HOVER RESULTS
# ==========================================
st.markdown("---")
st.subheader("🌐 3D Structural Visualizer & Load Analysis Engine")

col_3d_ctrl1, col_3d_ctrl2, col_3d_ctrl3 = st.columns([2, 2, 3])

display_unit = col_3d_ctrl1.selectbox("3D Graphics Display Unit", ["m", "ft", "mm", "in"], index=0)
view_mode = col_3d_ctrl2.radio("Shape Mode", ["Undeformed", "Deformed Shape"], index=0)
def_scale = col_3d_ctrl3.slider("Deformation Scale Factor", 100, 5000, 1000)

len_to_m = 0.3048 if is_imperial else 1.0
disp_scale_dict = {"m": 1.0, "ft": 3.28084, "mm": 1000.0, "in": 39.3701}
sf_disp = len_to_m * disp_scale_dict[display_unit]

fig = go.Figure()

x_coords = [i * span_x for i in range(bays_x + 1)]
y_coords = [j * span_y for j in range(bays_y + 1)]
z_coords = [k * story_height for k in range(num_stories + 1)]

element_results = []

def col_capacity(b, h, n_bars, bar_key, fc_val, fy_val, is_imp):
    Ag = b * h
    Ast = n_bars * rebar_db[bar_key]['area']
    if is_imp:
        Pn = 0.80 * 0.65 * (0.85 * fc_val * (Ag - Ast) + fy_val * Ast)
    else:
        Pn = (0.80 * 0.65 * (0.85 * fc_val * (Ag - Ast) + fy_val * Ast)) / 1000.0
    return Pn

phi_Pn_col = col_capacity(assigned_col['b'], assigned_col['h'], assigned_col['n_bars'], assigned_col['bar_size'], fc, fy, is_imperial)

# Draw Columns & Accumulate Hover Info
for ix, x in enumerate(x_coords):
    for iy, y in enumerate(y_coords):
        trib_mult = 1.0 if (ix in [0, bays_x] and iy in [0, bays_y]) else (2.0 if (ix in [0, bays_x] or iy in [0, bays_y]) else 4.0)
        trib_factor = trib_mult / 4.0
        
        for k in range(num_stories):
            z1, z2 = z_coords[k], z_coords[k+1]
            stories_above = num_stories - k
            Pu_col = w_u_area * (span_x * span_y * trib_factor) * stories_above
            dc_ratio = Pu_col / phi_Pn_col if phi_Pn_col > 0 else 0
            
            status = "PASS" if dc_ratio <= 1.0 else "FAIL"
            color = 'blue' if status == "PASS" else 'red'

            hover_text = (
                f"<b>Column C[{ix},{iy}] Story {k+1}</b><br>"
                f"Section: {assigned_col_name}<br>"
                f"Axial Load Pu: {Pu_col:.1f} {units['force']}<br>"
                f"Capacity φPn: {phi_Pn_col:.1f} {units['force']}<br>"
                f"D/C Ratio: {dc_ratio:.2f} ({status})"
            )

            gx = [x * sf_disp, x * sf_disp]
            gy = [y * sf_disp, y * sf_disp]
            gz = [z1 * sf_disp, z2 * sf_disp]

            if view_mode == "Deformed Shape":
                dx = (Pu_col / 10000.0) * def_scale * 0.01 * sf_disp
                gx = [gx[0] + dx, gx[1] + dx]

            fig.add_trace(go.Scatter3d(
                x=gx, y=gy, z=gz, mode='lines',
                line=dict(color=color, width=6),
                hoverinfo='text', text=hover_text, showlegend=False
            ))

            element_results.append({
                "Member": f"Col X{ix}-Y{iy}-L{k+1}", "Type": "Column",
                f"Applied Load ({units['force']})": f"{Pu_col:.1f}",
                f"Capacity ({units['force']})": f"{phi_Pn_col:.1f}",
                "D/C Ratio": f"{dc_ratio:.2f}", "Status": status
            })

# Draw Beams
M_u_beam = (w_u_beam * span_x**2) / 10.0
for k in range(1, num_stories + 1):
    z = z_coords[k]
    for y in y_coords:
        for i in range(bays_x):
            hover_txt = f"<b>Beam Span X-{i+1} L{k}</b><br>Mu: {M_u_beam:.1f} {units['moment']}"
            fig.add_trace(go.Scatter3d(
                x=[x_coords[i]*sf_disp, x_coords[i+1]*sf_disp],
                y=[y*sf_disp, y*sf_disp],
                z=[z*sf_disp, z*sf_disp],
                mode='lines', line=dict(color='green', width=4),
                hoverinfo='text', text=hover_txt, showlegend=False
            ))

fig.update_layout(
    scene=dict(
        xaxis_title=f"X ({display_unit})",
        yaxis_title=f"Y ({display_unit})",
        zaxis_title=f"Z ({display_unit})",
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=20),
    height=550
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("### 📊 Detailed Member Element Load Results")
st.dataframe(element_results, use_container_width=True)
