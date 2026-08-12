import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import math

st.set_page_config(page_title="Advanced 3D RC Building Design App", layout="wide")

st.title("🏛️ Advanced 3D RC Building Analysis & Design App (ACI 318-19)")
st.caption("Complete RC Member Design, Cross-Sections, Editable Section Properties, Deformed Mode Shape, & Individual Member Results")

# ==========================================
# UNIT CONVERSION HELPERS
# ==========================================
UNIT_SYSTEMS = {
    "SI (Metric: m, kN, MPa)": {
        "len": "m", "force": "kN", "stress": "MPa", "area_load": "kN/m²", "line_load": "kN/m",
        "moment": "kN·m", "dim": "mm", "sf_len": 1.0, "sf_dim": 1000.0,
        "rebar_fmt": "mm", "default_rebar_size": 16, "bar_options": [10, 12, 16, 20, 25, 28, 32]
    },
    "Imperial (ft, kip, ksi)": {
        "len": "ft", "force": "kip", "stress": "ksi", "area_load": "ksf", "line_load": "klf",
        "moment": "kip·ft", "dim": "in", "sf_len": 3.28084, "sf_dim": 39.3701,
        "rebar_fmt": "#", "default_rebar_size": 5, "bar_options": [3, 4, 5, 6, 7, 8, 9, 10]
    },
    "Imperial (in, lb, psi)": {
        "len": "in", "force": "lb", "stress": "psi", "area_load": "psi", "line_load": "lb/in",
        "moment": "lb·in", "dim": "in", "sf_len": 39.3701, "sf_dim": 39.3701,
        "rebar_fmt": "in", "default_rebar_size": 0.625, "bar_options": [0.375, 0.5, 0.625, 0.75, 0.875, 1.0, 1.128, 1.27]
    }
}

def get_rebar_area(size, fmt):
    if fmt == "mm":
        return (math.pi / 4.0) * (size ** 2)
    elif fmt == "#":
        dia = size / 8.0 
        return (math.pi / 4.0) * (dia ** 2)
    else:
        return (math.pi / 4.0) * (size ** 2)

# ==========================================
# 1. SIDEBAR: UNITS & GEOMETRY
# ==========================================
st.sidebar.header("0. Global Unit Selection")
unit_choice = st.sidebar.selectbox("Select Primary Calculation Unit System", list(UNIT_SYSTEMS.keys()), index=0)
units = UNIT_SYSTEMS[unit_choice]
d_unit = units['dim']

st.sidebar.header("1. Grid Lines & Storey Definition")

num_stories = st.sidebar.number_input("Number of Stories", value=3, min_value=1, max_value=10)
story_height = st.sidebar.number_input(f"Typical Storey Height ({units['len']})", value=3.5 if units['len']=='m' else (11.5 if units['len']=='ft' else 138.0))

bays_x = st.sidebar.number_input("Number of Bays (X-Dir)", value=3, min_value=1)
span_x = st.sidebar.number_input(f"Bay Span X ({units['len']})", value=5.0 if units['len']=='m' else (16.5 if units['len']=='ft' else 197.0))

bays_y = st.sidebar.number_input("Number of Bays (Y-Dir)", value=2, min_value=1)
span_y = st.sidebar.number_input(f"Bay Span Y ({units['len']})", value=4.0 if units['len']=='m' else (13.0 if units['len']=='ft' else 157.0))

x_grid_labels = [chr(65 + i) for i in range(bays_x + 1)] 
y_grid_labels = [str(j + 1) for j in range(bays_y + 1)]   

st.sidebar.subheader("Storey Names")
default_storey_names = ["Base", "GF", "1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F"]
storey_names = []
for k in range(num_stories + 1):
    name = st.sidebar.text_input(f"Level {k} Name", value=default_storey_names[k] if k <= 11 else f"L{k}", key=f"storey_name_{k}")
    storey_names.append(name)

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
fc = st.sidebar.number_input(f"Concrete Strength f'c ({units['stress']})", value=28.0 if units['stress']=='MPa' else (4.0 if units['stress']=='ksi' else 4000.0))
fy = st.sidebar.number_input(f"Main Steel Rebar Strength fy ({units['stress']})", value=420.0 if units['stress']=='MPa' else (60.0 if units['stress']=='ksi' else 60000.0))
fys = st.sidebar.number_input(f"Stirrup/Tie Rebar Strength fys ({units['stress']})", value=280.0 if units['stress']=='MPa' else (40.0 if units['stress']=='ksi' else 40000.0))

# ==========================================
# 3. EDITABLE SECTION PROPERTIES
# ==========================================
st.subheader("📋 Pre-Defined Member Section Properties (Editable Table)")

def_col_w = 300.0 if d_unit == 'mm' else 12.0
def_beam_w = 230.0 if d_unit == 'mm' else 10.0
def_beam_h = 450.0 if d_unit == 'mm' else 18.0
def_slab_t = 150.0 if d_unit == 'mm' else 6.0

def_cover_col = 40.0 if d_unit == 'mm' else 1.5
def_cover_beam = 30.0 if d_unit == 'mm' else 1.5
def_cover_slab = 20.0 if d_unit == 'mm' else 0.75

bar_fmt = units['rebar_fmt']
def_bar = units['default_rebar_size']

if 'col_df' not in st.session_state or st.session_state.get('unit_choice_prev') != unit_choice:
    st.session_state.unit_choice_prev = unit_choice
    st.session_state.col_df = pd.DataFrame([
        {"Section Name": f"C_{int(def_col_w)}x{int(def_col_w)}", f"b ({d_unit})": float(def_col_w), f"h ({d_unit})": float(def_col_w), f"Cover ({d_unit})": float(def_cover_col), "Rebar Count": 8, f"Rebar Size ({bar_fmt})": def_bar},
        {"Section Name": f"C_{int(def_col_w+100)}x{int(def_col_w+100)}", f"b ({d_unit})": float(def_col_w + (100 if d_unit=='mm' else 4)), f"h ({d_unit})": float(def_col_w + (100 if d_unit=='mm' else 4)), f"Cover ({d_unit})": float(def_cover_col), "Rebar Count": 10, f"Rebar Size ({bar_fmt})": def_bar}
    ])

if 'beam_df' not in st.session_state or st.session_state.get('unit_choice_prev_b') != unit_choice:
    st.session_state.unit_choice_prev_b = unit_choice
    st.session_state.beam_df = pd.DataFrame([
        {"Section Name": f"B_{int(def_beam_w)}x{int(def_beam_h)}", f"b ({d_unit})": float(def_beam_w), f"h ({d_unit})": float(def_beam_h), f"Cover ({d_unit})": float(def_cover_beam), "Top Rebar Count": 3, f"Top Size ({bar_fmt})": def_bar, "Bot Rebar Count": 3, f"Bot Size ({bar_fmt})": def_bar},
        {"Section Name": f"B_{int(def_beam_w+70)}x{int(def_beam_h+50)}", f"b ({d_unit})": float(def_beam_w + (70 if d_unit=='mm' else 2)), f"h ({d_unit})": float(def_beam_h + (50 if d_unit=='mm' else 2)), f"Cover ({d_unit})": float(def_cover_beam), "Top Rebar Count": 4, f"Top Size ({bar_fmt})": def_bar, "Bot Rebar Count": 4, f"Bot Size ({bar_fmt})": def_bar}
    ])

if 'slab_df' not in st.session_state or st.session_state.get('unit_choice_prev_s') != unit_choice:
    st.session_state.unit_choice_prev_s = unit_choice
    st.session_state.slab_df = pd.DataFrame([
        {"Slab Name": f"S_{int(def_slab_t)}", f"Thickness t ({d_unit})": float(def_slab_t), f"Cover ({d_unit})": float(def_cover_slab), "Top Rebar Count/m": 5, f"Top Size ({bar_fmt})": def_bar, "Bot Rebar Count/m": 5, f"Bot Size ({bar_fmt})": def_bar},
        {"Slab Name": f"S_{int(def_slab_t+50)}", f"Thickness t ({d_unit})": float(def_slab_t + (50 if d_unit=='mm' else 2)), f"Cover ({d_unit})": float(def_cover_slab), "Top Rebar Count/m": 6, f"Top Size ({bar_fmt})": def_bar, "Bot Rebar Count/m": 6, f"Bot Size ({bar_fmt})": def_bar}
    ])

tab1, tab2, tab3 = st.tabs(["Columns Section Manager", "Beams Section Manager", "Slabs Section Manager"])

with tab1:
    edited_col = st.data_editor(st.session_state.col_df, num_rows="dynamic", use_container_width=True, key="col_editor")
    st.session_state.col_df = edited_col

with tab2:
    edited_beam = st.data_editor(st.session_state.beam_df, num_rows="dynamic", use_container_width=True, key="beam_editor")
    st.session_state.beam_df = edited_beam

with tab3:
    edited_slab = st.data_editor(st.session_state.slab_df, num_rows="dynamic", use_container_width=True, key="slab_editor")
    st.session_state.slab_df = edited_slab

col_sections = {}
for idx, row in edited_col.iterrows():
    name = str(row["Section Name"])
    b = float(row[f"b ({d_unit})"])
    h = float(row[f"h ({d_unit})"])
    cov = float(row[f"Cover ({d_unit})"])
    n_bar = int(row["Rebar Count"])
    s_bar = float(row[f"Rebar Size ({bar_fmt})"])
    col_sections[name] = {"b": b, "h": h, "cover": cov, "n_bar": n_bar, "s_bar": s_bar, "A": b * h, "Ixx": (b * h**3) / 12.0}

beam_sections = {}
for idx, row in edited_beam.iterrows():
    name = str(row["Section Name"])
    b = float(row[f"b ({d_unit})"])
    h = float(row[f"h ({d_unit})"])
    cov = float(row[f"Cover ({d_unit})"])
    n_top = int(row["Top Rebar Count"])
    s_top = float(row[f"Top Size ({bar_fmt})"])
    n_bot = int(row["Bot Rebar Count"])
    s_bot = float(row[f"Bot Size ({bar_fmt})"])
    beam_sections[name] = {"b": b, "h": h, "cover": cov, "n_top": n_top, "s_top": s_top, "n_bot": n_bot, "s_bot": s_bot, "A": b * h, "Ixx": (b * h**3) / 12.0}

slab_sections = {}
for idx, row in edited_slab.iterrows():
    name = str(row["Slab Name"])
    t = float(row[f"Thickness t ({d_unit})"])
    cov = float(row[f"Cover ({d_unit})"])
    n_top = int(row["Top Rebar Count/m"])
    s_top = float(row[f"Top Size ({bar_fmt})"])
    n_bot = int(row["Bot Rebar Count/m"])
    s_bot = float(row[f"Bot Size ({bar_fmt})"])
    b_strip = 1000.0 if d_unit == 'mm' else 12.0
    slab_sections[name] = {"t": t, "cover": cov, "n_top": n_top, "s_top": s_top, "n_bot": n_bot, "s_bot": s_bot, "A": b_strip * t, "Ixx": (b_strip * t**3) / 12.0}

# ==========================================
# NEW FEATURE 1: ELEMENT DELETION & INACTIVITY MATRIX / MULTI-SELECT
# ==========================================
st.markdown("---")
st.subheader("🗑️ Element Deletion & Inactivity Matrix (Bay / Grid Filtering)")

col_del1, col_del2 = st.columns(2)
with col_del1:
    st.markdown("**Inactive / Removed Beam Bays (X-Dir & Y-Dir):**")
    all_beam_ids = []
    for k_idx in range(1, num_stories + 1):
        for bx in range(bays_x):
            all_beam_ids.append(f"Level {storey_names[k_idx]} - Beam X_{bx+1}-{bx+2}")
        for by in range(bays_y):
            all_beam_ids.append(f"Level {storey_names[k_idx]} - Beam Y_{by+1}-{by+2}")
    
    inactive_beams = st.multiselect("Select Beams to Deactivate/Remove from Analysis", options=all_beam_ids, default=[], key="inactive_beams_select")

with col_del2:
    st.markdown("**Inactive / Removed Slab Panels (Panel by Panel):**")
    all_slab_panels = []
    for k_idx in range(1, num_stories + 1):
        for bx in range(bays_x):
            for by in range(bays_y):
                all_slab_panels.append(f"Level {storey_names[k_idx]} - Panel ({x_grid_labels[bx]}-{x_grid_labels[bx+1]}, {y_grid_labels[by]}-{y_grid_labels[by+1]})")
                
    inactive_slabs = st.multiselect("Select Slab Panels to Deactivate (e.g., Openings / Voids)", options=all_slab_panels, default=[], key="inactive_slabs_select")

# ==========================================
# NEW FEATURE 2: INDIVIDUAL BEAM WALL LOAD MATRIX (st.data_editor)
# ==========================================
st.markdown("---")
st.subheader("🧱 Individual Beam Wall Load Manager (Member-Level Customization)")
st.caption("Customize specific wall load values for individual beams across storeys or use the default global value.")

default_wall_line_val = 5.0 if units['line_load']=='kN/m' else (0.35 if units['line_load']=='klf' else 29.0)

if 'beam_wall_load_df' not in st.session_state or st.session_state.get('unit_choice_prev_wall') != unit_choice:
    st.session_state.unit_choice_prev_wall = unit_choice
    beam_wall_rows = []
    for k_idx in range(1, num_stories + 1):
        for bx in range(bays_x):
            beam_wall_rows.append({
                "Storey": storey_names[k_idx],
                "Beam Element": f"Beam X_{x_grid_labels[bx]}-{x_grid_labels[bx+1]}",
                f"Wall Load ({units['line_load']})": float(default_wall_line_val),
                "Load Category": "Superimposed Dead Load (D)"
            })
        for by in range(bays_y):
            beam_wall_rows.append({
                "Storey": storey_names[k_idx],
                "Beam Element": f"Beam Y_{y_grid_labels[by]}-{y_grid_labels[by+1]}",
                f"Wall Load ({units['line_load']})": float(default_wall_line_val),
                "Load Category": "Superimposed Dead Load (D)"
            })
    st.session_state.beam_wall_load_df = pd.DataFrame(beam_wall_rows)

edited_beam_wall_df = st.data_editor(st.session_state.beam_wall_load_df, num_rows="fixed", use_container_width=True, key="beam_wall_editor")
st.session_state.beam_wall_load_df = edited_beam_wall_df

# ==========================================
# NEW FEATURE 3: SLAB PANEL BY PANEL LOAD EDITOR (st.data_editor)
# ==========================================
st.markdown("---")
st.subheader("🏢 Slab Panel by Panel Load Manager (Dead & Live Load Customization)")
st.caption("Assign independent Dead Load (D) and Live Load (L) values for each individual Slab Panel.")

default_finishing_val = 1.2 if units['area_load']=='kN/m²' else (0.025 if units['area_load']=='ksf' else 0.17)
default_live_val = 2.0 if units['area_load']=='kN/m²' else (0.04 if units['area_load']=='ksf' else 0.28)

first_slab_key = list(slab_sections.keys())[0] if slab_sections else "S1"
first_slab_t = slab_sections[first_slab_key]["t"] if slab_sections else def_slab_t
concrete_density = 24.0 if units['len'] == 'm' else (150.0 / 1000.0 if units['len']=='ft' else 0.0868)
self_weight_slab_default = (first_slab_t / (1000.0 if d_unit=='mm' else 12.0)) * concrete_density

if 'slab_panel_load_df' not in st.session_state or st.session_state.get('unit_choice_prev_slab_load') != unit_choice:
    st.session_state.unit_choice_prev_slab_load = unit_choice
    slab_panel_rows = []
    for k_idx in range(1, num_stories + 1):
        for bx in range(bays_x):
            for by in range(bays_y):
                slab_panel_rows.append({
                    "Storey": storey_names[k_idx],
                    "Panel ID": f"Panel ({x_grid_labels[bx]}-{x_grid_labels[bx+1]}, {y_grid_labels[by]}-{y_grid_labels[by+1]})",
                    f"Self-Weight ({units['area_load']})": float(round(self_weight_slab_default, 2)),
                    f"Finishing Load D ({units['area_load']})": float(default_finishing_val),
                    f"Occupancy Live Load L ({units['area_load']})": float(default_live_val),
                    "Custom Factored wu Override (Optional)": 0.0
                })
    st.session_state.slab_panel_load_df = pd.DataFrame(slab_panel_rows)

edited_slab_panel_df = st.data_editor(st.session_state.slab_panel_load_df, num_rows="fixed", use_container_width=True, key="slab_panel_editor")
st.session_state.slab_panel_load_df = edited_slab_panel_df

# ==========================================
# 4. ACI 318-19 LOAD COMBINATIONS & MEMBER ASSIGNMENT
# ==========================================
st.markdown("---")
st.subheader("⚖️ Member & Panel Level Load Combinations & Assignment")

col_assign, beam_assign, slab_assign = {}, {}, {}
c_a1, c_a2, c_a3 = st.columns(3)

col_options = list(col_sections.keys())
beam_options = list(beam_sections.keys())
slab_options = list(slab_sections.keys())

with c_a1:
    st.write("**Assign Columns:**")
    for k in range(1, num_stories + 1):
        col_assign[k] = st.selectbox(f"Column ({storey_names[k-1]} to {storey_names[k]})", col_options, index=0, key=f"col_assign_{k}")

with c_a2:
    st.write("**Assign Beams:**")
    for k in range(1, num_stories + 1):
        beam_assign[k] = st.selectbox(f"Beam Level {storey_names[k]}", beam_options, index=0, key=f"beam_assign_{k}")

with c_a3:
    st.write("**Assign Slabs:**")
    for k in range(1, num_stories + 1):
        slab_assign[k] = st.selectbox(f"Slab Level {storey_names[k]}", slab_options, index=0, key=f"slab_assign_{k}")

# ==========================================
# 5. RUN ANALYSIS & FULL RC DESIGN
# ==========================================
st.markdown("---")
st.subheader("📊 Structural Analysis Engine & RC Capacity Design")

run_analysis = st.button("🚀 Run Analysis & Design Verification", type="primary")

if run_analysis or 'analysis_results' in st.session_state:
    st.session_state.analysis_results = True
    st.success("✅ Structural Analysis & Design Verification Completed Successfully (Member & Panel Level)!")

    member_results = []

    if d_unit == "mm":
        to_mm = 1.0
    else:
        to_mm = 25.4

    def check_beam_design(b, h, cov, n_top, s_top, n_bot, s_bot, M_u, V_u):
        d = h - cov - 10
        d_mm = d * to_mm
        b_mm = b * to_mm
        fc_MPa = fc if units['stress']=='MPa' else (fc * 6.89476 if units['stress']=='ksi' else fc * 0.00689476)
        fy_MPa = fy if units['stress']=='MPa' else (fy * 6.89476 if units['stress']=='ksi' else fy * 0.00689476)

        A_s = n_bot * get_rebar_area(s_bot, bar_fmt)
        A_s_mm2 = A_s * (to_mm**2)

        a = (A_s_mm2 * fy_MPa) / (0.85 * fc_MPa * b_mm)
        Mn_Nmm = A_s_mm2 * fy_MPa * (d_mm - a / 2.0)
        phi_Mn_Nmm = 0.90 * Mn_Nmm

        if units['moment'] == "kN·m":
            phi_Mn = phi_Mn_Nmm / 1e6
        elif units['moment'] == "kip·ft":
            phi_Mn = phi_Mn_Nmm / 112984.8
        else:
            phi_Mn = phi_Mn_Nmm / 112.985

        Vc_N = 0.17 * math.sqrt(fc_MPa) * b_mm * d_mm
        phi_Vc_N = 0.75 * Vc_N

        if units['force'] == "kN":
            phi_Vc = phi_Vc_N / 1000.0
        elif units['force'] == "kip":
            phi_Vc = phi_Vc_N / 4448.22
        else:
            phi_Vc = phi_Vc_N / 4.44822

        status = "OK"
        recs = []
        if M_u > phi_Mn:
            status = "Not OK"
            recs.append(f"Increase section size (h > {h} {d_unit}) or increase bottom rebar.")
        if V_u > phi_Vc:
            recs.append(f"Add shear stirrups or increase beam width (b > {b} {d_unit}).")
            if status != "Not OK":
                status = "Not OK (Shear Stirrups Required)"
        if not recs:
            recs.append("Section capacity adequate.")

        return phi_Mn, phi_Vc, status, " ".join(recs)

    def check_col_design(b, h, cov, n_bar, s_bar, P_u):
        A_g = b * h
        A_s = n_bar * get_rebar_area(s_bar, bar_fmt)
        A_g_mm2 = A_g * (to_mm**2)
        A_s_mm2 = A_s * (to_mm**2)

        fc_MPa = fc if units['stress']=='MPa' else (fc * 6.89476 if units['stress']=='ksi' else fc * 0.00689476)
        fy_MPa = fy if units['stress']=='MPa' else (fy * 6.89476 if units['stress']=='ksi' else fy * 0.00689476)

        Pn_max_N = 0.80 * (0.85 * fc_MPa * (A_g_mm2 - A_s_mm2) + fy_MPa * A_s_mm2)
        phi_Pn_N = 0.65 * Pn_max_N

        if units['force'] == "kN":
            phi_Pn = phi_Pn_N / 1000.0
        elif units['force'] == "kip":
            phi_Pn = phi_Pn_N / 4448.22
        else:
            phi_Pn = phi_Pn_N / 4.44822

        status = "OK" if P_u <= phi_Pn else "Not OK"
        recs = ["Column section capacity adequate."] if status == "OK" else [f"Increase column dimensions b x h or rebar."]
        return phi_Pn, status, " ".join(recs)

    def check_slab_design(t, cov, n_top, s_top, n_bot, s_bot, M_u):
        b_strip = 1000.0 if d_unit == 'mm' else 12.0
        d = t - cov - 5
        d_mm = d * to_mm
        b_mm = b_strip * to_mm

        fc_MPa = fc if units['stress']=='MPa' else (fc * 6.89476 if units['stress']=='ksi' else fc * 0.00689476)
        fy_MPa = fy if units['stress']=='MPa' else (fy * 6.89476 if units['stress']=='ksi' else fy * 0.00689476)

        A_s_bot = n_bot * get_rebar_area(s_bot, bar_fmt) * (to_mm**2)
        a = (A_s_bot * fy_MPa) / (0.85 * fc_MPa * b_mm)
        Mn_Nmm = A_s_bot * fy_MPa * (d_mm - a / 2.0)
        phi_Mn_Nmm = 0.90 * Mn_Nmm

        if units['moment'] == "kN·m":
            phi_Mn = phi_Mn_Nmm / 1e6
        elif units['moment'] == "kip·ft":
            phi_Mn = phi_Mn_Nmm / 112984.8
        else:
            phi_Mn = phi_Mn_Nmm / 112.985

        status = "OK" if M_u <= phi_Mn else "Not OK"
        recs = ["Slab design adequate."] if status == "OK" else [f"Increase slab thickness t > {t} {d_unit}."]
        return phi_Mn, status, " ".join(recs)

    # Process Member Results with Panel & Beam specific editors
    for k in range(num_stories, 0, -1):
        s_name_k = storey_names[k]
        c_sec_name = col_assign[k]
        c_sec = col_sections[c_sec_name]
        b_sec_name = beam_assign[k]
        b_sec = beam_sections[b_sec_name]
        s_sec_name = slab_assign[k]
        s_sec = slab_sections[s_sec_name]

        # Evaluate Beam Level with custom wall loads
        for bx in range(bays_x):
            beam_id_str = f"Beam X_{x_grid_labels[bx]}-{x_grid_labels[bx+1]}"
            if f"Level {s_name_k} - {beam_id_str}" in inactive_beams:
                continue # Skip inactive elements
            
            # Fetch custom wall load from editor
            matched_beam_row = edited_beam_wall_df[(edited_beam_wall_df["Storey"] == s_name_k) & (edited_beam_wall_df["Beam Element"] == beam_id_str)]
            if not matched_beam_row.empty:
                w_line_val = matched_beam_row.iloc[0][f"Wall Load ({units['line_load']})"]
                w_cat = matched_beam_row.iloc[0]["Load Category"]
            else:
                w_line_val = default_wall_line_val
                w_cat = "Superimposed Dead Load (D)"

            factored_beam_wall = (1.4 * w_line_val) if "Dead" in w_cat else (1.6 * w_line_val)
            trib_width = span_y / 2.0
            
            # Average slab load for this beam
            panel_subset = edited_slab_panel_df[edited_slab_panel_df["Storey"] == s_name_k]
            if not panel_subset.empty:
                avg_slab_wu = 0.0
                for _, prow in panel_subset.iterrows():
                    custom_wu = prow["Custom Factored wu Override (Optional)"]
                    if custom_wu > 0:
                        avg_slab_wu += custom_wu
                    else:
                        sw = prow[f"Self-Weight ({units['area_load']})"]
                        fin = prow[f"Finishing Load D ({units['area_load']})"]
                        liv = prow[f"Occupancy Live Load L ({units['area_load']})"]
                        avg_slab_wu += max(1.4 * (sw + fin), 1.2 * (sw + fin) + 1.6 * liv)
                avg_slab_wu /= len(panel_subset)
            else:
                avg_slab_wu = 10.0

            w_beam_total = avg_slab_wu * trib_width + factored_beam_wall
            L_b = span_x
            M_u_beam = (w_beam_total * (L_b**2)) / 11.0
            V_u_beam = 1.15 * (w_beam_total * L_b) / 2.0

            phi_Mn_b, phi_Vc_b, status_b, rec_b = check_beam_design(
                b_sec['b'], b_sec['h'], b_sec['cover'],
                b_sec['n_top'], b_sec['s_top'], b_sec['n_bot'], b_sec['s_bot'],
                M_u_beam, V_u_beam
            )

            member_results.append({
                "Member Type": "Beam (X-Dir)",
                "Location / Level": f"Level {s_name_k} ({beam_id_str})",
                "Section Assigned": b_sec_name,
                "Rebar Details": f"Top: {b_sec['n_top']}-{b_sec['s_top']}{bar_fmt} | Bot: {b_sec['n_bot']}-{b_sec['s_bot']}{bar_fmt}",
                "Design Demand": f"Mu = {M_u_beam:.2f} {units['moment']} | Vu = {V_u_beam:.2f} {units['force']}",
                "Factored Capacity": f"ϕMn = {phi_Mn_b:.2f} {units['moment']} | ϕVc = {phi_Vc_b:.2f} {units['force']}",
                "Status": status_b,
                "Recommendation": rec_b
            })

        # Evaluate Slab Panels individually from editor
        for _, panel_row in edited_slab_panel_df[edited_slab_panel_df["Storey"] == s_name_k].iterrows():
            p_id = panel_row["Panel ID"]
            if f"Level {s_name_k} - {p_id}" in inactive_slabs:
                continue

            sw = panel_row[f"Self-Weight ({units['area_load']})"]
            fin = panel_row[f"Finishing Load D ({units['area_load']})"]
            liv = panel_row[f"Occupancy Live Load L ({units['area_load']})"]
            custom_wu = panel_row["Custom Factored wu Override (Optional)"]

            governing_panel_wu = custom_wu if custom_wu > 0 else max(1.4 * (sw + fin), 1.2 * (sw + fin) + 1.6 * liv)
            L_s = min(span_x, span_y)
            M_u_slab = (governing_panel_wu * (L_s**2)) / 16.0

            phi_Mn_s, status_s, rec_s = check_slab_design(
                s_sec['t'], s_sec['cover'],
                s_sec['n_top'], s_sec['s_top'], s_sec['n_bot'], s_sec['s_bot'],
                M_u_slab
            )

            member_results.append({
                "Member Type": "Slab Panel",
                "Location / Level": f"Level {s_name_k} ({p_id})",
                "Section Assigned": s_sec_name,
                "Rebar Details": f"Top: {s_sec['n_top']}-{s_sec['s_top']}{bar_fmt}/m | Bot: {s_sec['n_bot']}-{s_sec['s_bot']}{bar_fmt}/m",
                "Design Demand": f"wu = {governing_panel_wu:.2f} | Mu = {M_u_slab:.2f} {units['moment']}",
                "Factored Capacity": f"ϕMn = {phi_Mn_s:.2f} {units['moment']}",
                "Status": status_s,
                "Recommendation": rec_s
            })

        # Column Design evaluation
        trib_area = span_x * span_y
        col_P_demand = 1.4 * 50.0 * (num_stories - k + 1) # Simplified cumulative column load
        phi_Pn_c, status_c, rec_c = check_col_design(
            c_sec['b'], c_sec['h'], c_sec['cover'], c_sec['n_bar'], c_sec['s_bar'], col_P_demand
        )
        member_results.append({
            "Member Type": "Column",
            "Location / Level": f"{storey_names[k-1]} to {storey_names[k]}",
            "Section Assigned": c_sec_name,
            "Rebar Details": f"{c_sec['n_bar']} - {c_sec['s_bar']} {bar_fmt}",
            "Design Demand": f"Pu = {col_P_demand:.2f} {units['force']}",
            "Factored Capacity": f"ϕPn = {phi_Pn_c:.2f} {units['force']}",
            "Status": status_c,
            "Recommendation": rec_c
        })

    res_df = pd.DataFrame(member_results)
    st.subheader("📋 Member & Panel-Level Detailed Analysis Results")
    
    def highlight_status(val):
        return 'background-color: #d4edda; color: #155724;' if 'OK' in val and 'Not' not in val else 'background-color: #f8d7da; color: #721c24;'

    style_func = getattr(res_df.style, 'map', getattr(res_df.style, 'applymap', None))
    st.dataframe(style_func(highlight_status, subset=['Status']), use_container_width=True)

# ==========================================
# 6. CROSS SECTION VISUALIZATION
# ==========================================
st.markdown("---")
st.subheader("📐 Member Cross-Section Drawings & Rebar Layout")

sec_tab1, sec_tab2, sec_tab3 = st.tabs(["Column Cross-Section", "Beam Cross-Section", "Slab Cross-Section"])

with sec_tab1:
    sel_col_sec = st.selectbox("Select Column Section to View", list(col_sections.keys()), key="cs_col")
    col_p = col_sections[sel_col_sec]
    b, h, cov = col_p['b'], col_p['h'], col_p['cover']
    n_bar, s_bar = col_p['n_bar'], col_p['s_bar']

    fig_c = go.Figure()
    fig_c.add_shape(type="rect", x0=-b/2, y0=-h/2, x1=b/2, y1=h/2, line=dict(color="gray", width=3), fillcolor="rgba(200,200,200,0.3)")
    cx0, cx1 = -b/2 + cov, b/2 - cov
    cy0, cy1 = -h/2 + cov, h/2 - cov
    
    fig_c.add_trace(go.Scatter(x=[cx0, cx1, cx1, cx0, cx0], y=[cy0, cy0, cy1, cy1, cy0], mode='lines', line=dict(color="red", width=3), name="Tie / Stirrup"))
    
    rebar_x, rebar_y = [cx0, cx0, cx1, cx1], [cy0, cy1, cy0, cy1]
    fig_c.add_trace(go.Scatter(x=rebar_x, y=rebar_y, mode='markers', marker=dict(color='black', size=14), name=f'Main Rebar ({n_bar}-{s_bar}{bar_fmt})'))
    
    fig_c.update_layout(title=f"Column: {sel_col_sec}", width=500, height=400)
    st.plotly_chart(fig_c, use_container_width=True)

with sec_tab2:
    sel_beam_sec = st.selectbox("Select Beam Section to View", list(beam_sections.keys()), key="cs_beam")
    beam_p = beam_sections[sel_beam_sec]
    b, h, cov = beam_p['b'], beam_p['h'], beam_p['cover']
    n_top, s_top = beam_p['n_top'], beam_p['s_top']
    n_bot, s_bot = beam_p['n_bot'], beam_p['s_bot']

    fig_b = go.Figure()
    fig_b.add_shape(type="rect", x0=-b/2, y0=-h/2, x1=b/2, y1=h/2, line=dict(color="gray", width=3), fillcolor="rgba(200,200,200,0.3)")
    bx0, bx1 = -b/2 + cov, b/2 - cov
    by0, by1 = -h/2 + cov, h/2 - cov
    
    fig_b.add_trace(go.Scatter(x=[bx0, bx1, bx1, bx0, bx0], y=[by0, by0, by1, by1, by0], mode='lines', line=dict(color="green", width=3), name="Stirrup"))
    top_x = np.linspace(bx0, bx1, n_top)
    top_y = [by1] * n_top
    bot_x = np.linspace(bx0, bx1, n_bot)
    bot_y = [by0] * n_bot
    
    fig_b.add_trace(go.Scatter(x=top_x, y=top_y, mode='markers', marker=dict(color='blue', size=12), name='Top Rebar'))
    fig_b.add_trace(go.Scatter(x=bot_x, y=bot_y, mode='markers', marker=dict(color='red', size=12), name='Bottom Rebar'))
    fig_b.update_layout(title=f"Beam: {sel_beam_sec}", width=500, height=400)
    st.plotly_chart(fig_b, use_container_width=True)

with sec_tab3:
    sel_slab_sec = st.selectbox("Select Slab Section to View", list(slab_sections.keys()), key="cs_slab")
    slab_p = slab_sections[sel_slab_sec]
    t, cov = slab_p['t'], slab_p['cover']
    w_strip = 1000.0 if d_unit == 'mm' else 12.0

    fig_s = go.Figure()
    fig_s.add_shape(type="rect", x0=0, y0=0, x1=w_strip, y1=t, line=dict(color="gray", width=3), fillcolor="rgba(200,200,200,0.3)")
    fig_s.update_layout(title=f"Slab Section: {sel_slab_sec} (t={t:.1f} {d_unit})", width=500, height=300)
    st.plotly_chart(fig_s, use_container_width=True)

# ==========================================
# 7. 3D VISUALIZATION WITH ACTIVE / DELETED FILTERS
# ==========================================
st.markdown("---")
st.subheader("🌐 3D Building Model Visualization")

c_v1, c_v2, c_v3 = st.columns(3)
with c_v1:
    view_unit = st.selectbox("Select 3D Display Unit", ["m", "mm", "ft", "in"], index=0)
with c_v2:
    display_mode = st.radio("Display Mode", ["Original Model", "Deformed Mode Shape"], index=0)
with c_v3:
    deform_scale_factor = st.slider("Deformation Scale Factor", 1.0, 100.0, 20.0) if display_mode == "Deformed Mode Shape" else 0.0

scale_map = {"m": 1.0, "ft": 3.28084, "in": 39.3701, "mm": 1000.0}
base_to_m = 1.0 if units['len'] == 'm' else (0.3048 if units['len']=='ft' else 0.0254)
v_scale = base_to_m * scale_map[view_unit]

x_coords = [i * span_x * v_scale for i in range(bays_x + 1)]
y_coords = [j * span_y * v_scale for j in range(bays_y + 1)]
z_coords = [k * story_height * v_scale for k in range(num_stories + 1)]

fig3d = go.Figure()

# Render Columns
for i_idx, x in enumerate(x_coords):
    for j_idx, y in enumerate(y_coords):
        for k in range(num_stories):
            z0, z1 = z_coords[k], z_coords[k+1]
            fig3d.add_trace(go.Scatter3d(
                x=[x, x], y=[y, y], z=[z0, z1],
                mode='lines', line=dict(color='royalblue', width=6),
                showlegend=False, hoverinfo='text', text=f"Column: {col_assign[k+1]}"
            ))

# Render Slabs (excluding deactivated panels)
for k in range(1, num_stories + 1):
    z = z_coords[k]
    for i_idx in range(bays_x):
        for j_idx in range(bays_y):
            p_name_check = f"Level {storey_names[k]} - Panel ({x_grid_labels[i_idx]}-{x_grid_labels[i_idx+1]}, {y_grid_labels[j_idx]}-{y_grid_labels[j_idx+1]})"
            if p_name_check in inactive_slabs:
                continue # Skip drawing deleted/inactive panels
                
            x0, x1 = x_coords[i_idx], x_coords[i_idx+1]
            y0, y1 = y_coords[j_idx], y_coords[j_idx+1]
            fig3d.add_trace(go.Mesh3d(
                x=[x0, x1, x1, x0], y=[y0, y0, y1, y1], z=[z, z, z, z],
                color='lightblue', opacity=0.35, showlegend=False, hoverinfo='text', text=p_name_check
            ))

fig3d.update_layout(scene=dict(xaxis_title=f'X ({view_unit})', yaxis_title=f'Y ({view_unit})', zaxis_title=f'Z ({view_unit})', aspectmode='data'), height=600)
st.plotly_chart(fig3d, use_container_width=True)
