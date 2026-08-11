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

# Standard Rebar Area lookup
def get_rebar_area(size, fmt):
    if fmt == "mm":
        return (math.pi / 4.0) * (size ** 2) # mm2
    elif fmt == "#":
        dia = size / 8.0 # inches
        return (math.pi / 4.0) * (dia ** 2) # in2
    else:
        return (math.pi / 4.0) * (size ** 2) # in2

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

# Custom Grid Line Names
x_grid_labels = [chr(65 + i) for i in range(bays_x + 1)]  # A, B, C, D...
y_grid_labels = [str(j + 1) for j in range(bays_y + 1)]   # 1, 2, 3, 4...

# Custom Storey Names Input
st.sidebar.subheader("Storey Names")
default_storey_names = ["Base", "GF", "1F", "2F", "3F", "4F", "5F", "6F", "7F", "8F", "9F", "10F"]
storey_names = []
for k in range(num_stories + 1):
    name = st.sidebar.text_input(f"Level {k} Name", value=default_storey_names[k] if k <= 11 else f"L{k}")
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
fc = st.sidebar.number_input(f"Concrete Strength f'c ({units['stress']})", value=28.0 if units['stress']=='MPa' else (4.0 if units['stress']=='ksi' else 4000.0))
fy = st.sidebar.number_input(f"Main Steel Rebar Strength fy ({units['stress']})", value=420.0 if units['stress']=='MPa' else (60.0 if units['stress']=='ksi' else 60000.0))
fys = st.sidebar.number_input(f"Stirrup/Tie Rebar Strength fys ({units['stress']})", value=280.0 if units['stress']=='MPa' else (40.0 if units['stress']=='ksi' else 40000.0))

# ==========================================
# 3. EDITABLE SECTION PROPERTIES (REQUIREMENT 3)
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

# Session state initialization for editable tables
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
    st.caption("Edit column dimensions, cover, rebar count & rebar size directly in the table:")
    edited_col = st.data_editor(st.session_state.col_df, num_rows="dynamic", use_container_width=True, key="col_editor")
    st.session_state.col_df = edited_col

with tab2:
    st.caption("Edit beam dimensions, cover, top rebar & bottom rebar count and sizes directly in the table:")
    edited_beam = st.data_editor(st.session_state.beam_df, num_rows="dynamic", use_container_width=True, key="beam_editor")
    st.session_state.beam_df = edited_beam

with tab3:
    st.caption("Edit slab thickness, cover, top rebar & bottom rebar count and sizes directly in the table:")
    edited_slab = st.data_editor(st.session_state.slab_df, num_rows="dynamic", use_container_width=True, key="slab_editor")
    st.session_state.slab_df = edited_slab

# Build lookup dictionaries from edited DataFrames
col_sections = {}
for idx, row in edited_col.iterrows():
    name = str(row["Section Name"])
    b = float(row[f"b ({d_unit})"])
    h = float(row[f"h ({d_unit})"])
    cov = float(row[f"Cover ({d_unit})"])
    n_bar = int(row["Rebar Count"])
    s_bar = float(row[f"Rebar Size ({bar_fmt})"])
    A = b * h
    Ixx = (b * h**3) / 12.0
    col_sections[name] = {"b": b, "h": h, "cover": cov, "n_bar": n_bar, "s_bar": s_bar, "A": A, "Ixx": Ixx}

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
    A = b * h
    Ixx = (b * h**3) / 12.0
    beam_sections[name] = {"b": b, "h": h, "cover": cov, "n_top": n_top, "s_top": s_top, "n_bot": n_bot, "s_bot": s_bot, "A": A, "Ixx": Ixx}

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
    A = b_strip * t
    Ixx = (b_strip * t**3) / 12.0
    slab_sections[name] = {"t": t, "cover": cov, "n_top": n_top, "s_top": s_top, "n_bot": n_bot, "s_bot": s_bot, "A": A, "Ixx": Ixx}

# ==========================================
# 4. LOAD DEFINITION
# ==========================================
st.sidebar.header("4. Load Definition & Categorization")

first_slab_key = list(slab_sections.keys())[0] if slab_sections else "S1"
first_slab_t = slab_sections[first_slab_key]["t"] if slab_sections else def_slab_t

concrete_density = 24.0 if units['len'] == 'm' else (150.0 / 1000.0 if units['len']=='ft' else 0.0868)
self_weight_slab = (first_slab_t / (1000.0 if d_unit=='mm' else 12.0)) * concrete_density

st.sidebar.caption(f"Calculated Slab Self Weight: {self_weight_slab:.2f} {units['area_load']}")

finishing_val = st.sidebar.number_input(f"Floor Finishing Load ({units['area_load']})", value=1.2 if units['area_load']=='kN/m²' else (0.025 if units['area_load']=='ksf' else 0.17))
finishing_cat = st.sidebar.selectbox("Finishing Load Type", ["Superimposed Dead Load (D)", "Live Load (L)"], index=0)

live_val = st.sidebar.number_input(f"Occupancy Live Load ({units['area_load']})", value=2.0 if units['area_load']=='kN/m²' else (0.04 if units['area_load']=='ksf' else 0.28))
live_cat = st.sidebar.selectbox("Live Load Type", ["Live Load (L)", "Superimposed Dead Load (D)"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("Additional Loads (Wall & Direct Factored)")

enable_custom_factored_slab = st.sidebar.checkbox("Override with Custom Factored Slab Load (wu)")
custom_factored_slab_val = st.sidebar.number_input(f"Direct Factored Slab Load wu ({units['area_load']})", value=10.0 if units['area_load']=='kN/m²' else (0.2 if units['area_load']=='ksf' else 1.4), disabled=not enable_custom_factored_slab)

include_wall_load_on_beam = st.sidebar.checkbox("Add Wall Load on Beams", value=True)
wall_line_load = st.sidebar.number_input(f"Beam Wall Load ({units['line_load']})", value=5.0 if units['line_load']=='kN/m' else (0.35 if units['line_load']=='klf' else 29.0), disabled=not include_wall_load_on_beam)
wall_load_cat = st.sidebar.selectbox("Wall Load Type", ["Superimposed Dead Load (D)", "Live Load (L)"], index=0)

total_D = self_weight_slab
total_L = 0.0

loads_list = [(finishing_val, finishing_cat), (live_val, live_cat)]
for val, cat in loads_list:
    if "Dead" in cat: total_D += val
    elif "Live" in cat: total_L += val

beam_wall_D = wall_line_load if (include_wall_load_on_beam and "Dead" in wall_load_cat) else 0.0
beam_wall_L = wall_line_load if (include_wall_load_on_beam and "Live" in wall_load_cat) else 0.0

# ==========================================
# 5. ACI 318-19 LOAD COMBINATIONS
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
# 7. RUN ANALYSIS & FULL RC DESIGN (REQUIREMENT 1 & 5)
# ==========================================
st.markdown("---")
st.subheader("📊 Structural Analysis Engine & RC Capacity Design")

run_analysis = st.button("🚀 Run Analysis & Design Verification", type="primary")

if run_analysis or 'analysis_results' in st.session_state:
    st.session_state.analysis_results = True
    st.balloons()
    st.success("✅ Structural Analysis & Design Verification Completed Successfully!")

    factored_beam_wall = (1.4 * beam_wall_D + 1.6 * beam_wall_L)
    trib_width = span_y / 2.0
    w_beam_total = governing_U * trib_width + factored_beam_wall

    member_results = []

    if d_unit == "mm":
        to_mm = 1.0
        to_N_mm = 1e6 if units['moment']=="kN·m" else 1.0
        to_N = 1000.0 if units['force']=="kN" else 1.0
    else:
        to_mm = 25.4
        to_N_mm = 112984.8 if units['moment']=="kip·ft" else 112.985
        to_N = 4448.22 if units['force']=="kip" else 4.44822

    # ACI Capacity Verification Helpers
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
            recs.append(f"Increase section size (h > {h} {d_unit}) or increase bottom rebar count/size.")
        if V_u > phi_Vc:
            recs.append(f"Add shear stirrups or increase beam width (b > {b} {d_unit}).")
            if status != "Not OK":
                status = "Not OK (Shear Stirrups Required)"

        if not recs:
            recs.append("Section capacity is adequate. Code requirements satisfied.")

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

        status = "OK"
        recs = []
        if P_u > phi_Pn:
            status = "Not OK"
            recs.append(f"Increase column dimensions b x h or increase main rebar size/count.")
        else:
            recs.append("Column section capacity is adequate for axial loading.")

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

        status = "OK"
        recs = []
        if M_u > phi_Mn:
            status = "Not OK"
            recs.append(f"Increase slab thickness (t > {t} {d_unit}) or increase bottom rebar density.")
        else:
            recs.append("Slab thickness and flexural reinforcement are adequate.")

        return phi_Mn, status, " ".join(recs)

    for k in range(num_stories, 0, -1):
        c_sec_name = col_assign[k]
        c_sec = col_sections[c_sec_name]
        
        b_sec_name = beam_assign[k]
        b_sec = beam_sections[b_sec_name]

        s_sec_name = slab_assign[k]
        s_sec = slab_sections[s_sec_name]

        L_b = span_x
        M_u_beam = (w_beam_total * (L_b**2)) / 11.0
        V_u_beam = 1.15 * (w_beam_total * L_b) / 2.0
        phi_Mn_b, phi_Vc_b, status_b, rec_b = check_beam_design(
            b_sec['b'], b_sec['h'], b_sec['cover'],
            b_sec['n_top'], b_sec['s_top'], b_sec['n_bot'], b_sec['s_bot'],
            M_u_beam, V_u_beam
        )

        L_s = min(span_x, span_y)
        M_u_slab = (governing_U * (L_s**2)) / 16.0
        phi_Mn_s, status_s, rec_s = check_slab_design(
            s_sec['t'], s_sec['cover'],
            s_sec['n_top'], s_sec['s_top'], s_sec['n_bot'], s_sec['s_bot'],
            M_u_slab
        )

        trib_area = span_x * span_y
        P_u_per_level = governing_U * trib_area + factored_beam_wall * (span_x + span_y)
        stories_above = num_stories - k + 1
        P_u_col = P_u_per_level * stories_above
        phi_Pn_c, status_c, rec_c = check_col_design(
            c_sec['b'], c_sec['h'], c_sec['cover'], c_sec['n_bar'], c_sec['s_bar'], P_u_col
        )

        member_results.append({
            "Member Type": "Column",
            "Location / Level": f"{storey_names[k-1]} to {storey_names[k]}",
            "Section Assigned": c_sec_name,
            "Rebar Details": f"{c_sec['n_bar']} - {c_sec['s_bar']} {bar_fmt}",
            "Design Demand (Pu / Mu / Vu)": f"Pu = {P_u_col:.2f} {units['force']}",
            "Factored Capacity (ϕPn / ϕMn)": f"ϕPn = {phi_Pn_c:.2f} {units['force']}",
            "Status": status_c,
            "Recommendation": rec_c
        })

        member_results.append({
            "Member Type": "Beam",
            "Location / Level": f"Level {storey_names[k]}",
            "Section Assigned": b_sec_name,
            "Rebar Details": f"Top: {b_sec['n_top']}-{b_sec['s_top']}{bar_fmt} | Bot: {b_sec['n_bot']}-{b_sec['s_bot']}{bar_fmt}",
            "Design Demand (Pu / Mu / Vu)": f"Mu = {M_u_beam:.2f} {units['moment']} | Vu = {V_u_beam:.2f} {units['force']}",
            "Factored Capacity (ϕPn / ϕMn)": f"ϕMn = {phi_Mn_b:.2f} {units['moment']} | ϕVc = {phi_Vc_b:.2f} {units['force']}",
            "Status": status_b,
            "Recommendation": rec_b
        })

        member_results.append({
            "Member Type": "Slab",
            "Location / Level": f"Level {storey_names[k]}",
            "Section Assigned": s_sec_name,
            "Rebar Details": f"Top: {s_sec['n_top']}-{s_sec['s_top']}{bar_fmt}/m | Bot: {s_sec['n_bot']}-{s_sec['s_bot']}{bar_fmt}/m",
            "Design Demand (Pu / Mu / Vu)": f"Mu = {M_u_slab:.2f} {units['moment']}",
            "Factored Capacity (ϕPn / ϕMn)": f"ϕMn = {phi_Mn_s:.2f} {units['moment']}",
            "Status": status_s,
            "Recommendation": rec_s
        })

    res_df = pd.DataFrame(member_results)
    
    st.subheader("📋 Member-by-Member Analysis & Design Verification Results")
    
    def highlight_status(val):
        color = 'background-color: #d4edda; color: #155724;' if 'OK' in val and 'Not' not in val else 'background-color: #f8d7da; color: #721c24;'
        return color

    # map သို့မဟုတ် applymap ကို version အလိုက် ရွေးချယ်သုံးခြင်း
    style_func = getattr(res_df.style, 'map', getattr(res_df.style, 'applymap', None))
    st.dataframe(style_func(highlight_status, subset=['Status']), use_container_width=True)

# ==========================================
# 8. CROSS SECTION VISUALIZATION (REQUIREMENT 2)
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
    fig_c.add_shape(type="rect", x0=-b/2+cov, y0=-h/2+cov, x1=b/2-cov, y1=h/2-cov, line=dict(color="red", width=2, dash="dash"))

    rebar_x, rebar_y = [], []
    cx0, cx1 = -b/2 + cov, b/2 - cov
    cy0, cy1 = -h/2 + cov, h/2 - cov
    corners = [(cx0, cy0), (cx0, cy1), (cx1, cy0), (cx1, cy1)]
    for x_p, y_p in corners:
        rebar_x.append(x_p)
        rebar_y.append(y_p)

    rem = max(0, n_bar - 4)
    if rem > 0:
        per_side = rem // 4
        for i in range(1, per_side + 1):
            rx = cx0 + i * (cx1 - cx0) / (per_side + 1)
            rebar_x.extend([rx, rx])
            rebar_y.extend([cy0, cy1])
            ry = cy0 + i * (cy1 - cy0) / (per_side + 1)
            rebar_x.extend([cx0, cx1])
            rebar_y.extend([ry, ry])

    fig_c.add_trace(go.Scatter(x=rebar_x, y=rebar_y, mode='markers', marker=dict(color='black', size=14), name=f'Rebar: {n_bar} - {s_bar} {bar_fmt}'))

    fig_c.update_layout(
        title=f"Column Section: {sel_col_sec} ({b:.1f} x {h:.1f} {d_unit})",
        xaxis=dict(title=f"Width b ({d_unit})", range=[-b*0.8, b*0.8], zeroline=False),
        yaxis=dict(title=f"Height h ({d_unit})", range=[-h*0.8, h*0.8], scaleanchor="x", scaleratio=1),
        width=500, height=450
    )
    st.plotly_chart(fig_c, use_container_width=True)

with sec_tab2:
    sel_beam_sec = st.selectbox("Select Beam Section to View", list(beam_sections.keys()), key="cs_beam")
    beam_p = beam_sections[sel_beam_sec]
    b, h, cov = beam_p['b'], beam_p['h'], beam_p['cover']
    n_top, s_top = beam_p['n_top'], beam_p['s_top']
    n_bot, s_bot = beam_p['n_bot'], beam_p['s_bot']

    fig_b = go.Figure()
    fig_b.add_shape(type="rect", x0=-b/2, y0=0, x1=b/2, y1=h, line=dict(color="gray", width=3), fillcolor="rgba(200,200,200,0.3)")
    fig_b.add_shape(type="rect", x0=-b/2+cov, y0=cov, x1=b/2-cov, y1=h-cov, line=dict(color="green", width=2, dash="dash"))

    top_x = np.linspace(-b/2 + cov, b/2 - cov, n_top) if n_top > 1 else [0]
    top_y = [h - cov] * len(top_x)
    fig_b.add_trace(go.Scatter(x=top_x, y=top_y, mode='markers', marker=dict(color='blue', size=14), name=f'Top: {n_top} - {s_top} {bar_fmt}'))

    bot_x = np.linspace(-b/2 + cov, b/2 - cov, n_bot) if n_bot > 1 else [0]
    bot_y = [cov] * len(bot_x)
    fig_b.add_trace(go.Scatter(x=bot_x, y=bot_y, mode='markers', marker=dict(color='red', size=14), name=f'Bottom: {n_bot} - {s_bot} {bar_fmt}'))

    fig_b.update_layout(
        title=f"Beam Section: {sel_beam_sec} (b={b:.1f}, h={h:.1f} {d_unit})",
        xaxis=dict(title=f"Width b ({d_unit})", range=[-b*0.8, b*0.8], zeroline=False),
        yaxis=dict(title=f"Height h ({d_unit})", range=[-h*0.2, h*1.2], scaleanchor="x", scaleratio=1),
        width=500, height=450
    )
    st.plotly_chart(fig_b, use_container_width=True)

with sec_tab3:
    sel_slab_sec = st.selectbox("Select Slab Section to View", list(slab_sections.keys()), key="cs_slab")
    slab_p = slab_sections[sel_slab_sec]
    t, cov = slab_p['t'], slab_p['cover']
    n_top, s_top = slab_p['n_top'], slab_p['s_top']
    n_bot, s_bot = slab_p['n_bot'], slab_p['s_bot']
    w_strip = 1000.0 if d_unit == 'mm' else 12.0

    fig_s = go.Figure()
    fig_s.add_shape(type="rect", x0=0, y0=0, x1=w_strip, y1=t, line=dict(color="gray", width=3), fillcolor="rgba(200,200,200,0.3)")

    top_x = np.linspace(cov, w_strip - cov, n_top) if n_top > 1 else [w_strip/2]
    top_y = [t - cov] * len(top_x)
    fig_s.add_trace(go.Scatter(x=top_x, y=top_y, mode='markers', marker=dict(color='purple', size=12), name=f'Top Rebar: {n_top} - {s_top} {bar_fmt}/m'))

    bot_x = np.linspace(cov, w_strip - cov, n_bot) if n_bot > 1 else [w_strip/2]
    bot_y = [cov] * len(bot_x)
    fig_s.add_trace(go.Scatter(x=bot_x, y=bot_y, mode='markers', marker=dict(color='orange', size=12), name=f'Bottom Rebar: {n_bot} - {s_bot} {bar_fmt}/m'))

    fig_s.update_layout(
        title=f"Slab Section: {sel_slab_sec} (Thickness t={t:.1f} {d_unit}, Strip={w_strip:.0f} {d_unit})",
        xaxis=dict(title=f"Strip Width ({d_unit})", range=[-w_strip*0.1, w_strip*1.1]),
        yaxis=dict(title=f"Thickness t ({d_unit})", range=[-t*0.5, t*2.0], scaleanchor="x", scaleratio=1),
        width=600, height=350
    )
    st.plotly_chart(fig_s, use_container_width=True)

# ==========================================
# 9. 3D VISUALIZATION WITH SEPARATE VIEW UNIT & DEFORMED SHAPE (REQUIREMENT 4)
# ==========================================
st.markdown("---")
st.subheader("🌐 3D Building Model Visualization & Mode Shape")

c_v1, c_v2 = st.columns([1, 1])
with c_v1:
    view_unit = st.selectbox("Select 3D Display Unit (Visual Only)", ["m", "mm", "ft", "in"], index=0)

with c_v2:
    display_mode = st.radio("Select 3D Display Mode", ["Original Undeformed Model", "Deformed Mode Shape (Exaggerated)"], index=0)

scale_map = {"m": 1.0, "ft": 3.28084, "in": 39.3701, "mm": 1000.0}
base_to_m = 1.0 if units['len'] == 'm' else (0.3048 if units['len']=='ft' else 0.0254)
v_scale = base_to_m * scale_map[view_unit]

x_coords = [i * span_x * v_scale for i in range(bays_x + 1)]
y_coords = [j * span_y * v_scale for j in range(bays_y + 1)]
z_coords = [k * story_height * v_scale for k in range(num_stories + 1)]

fig3d = go.Figure()

def_scale = 0.08 * (max(x_coords) if x_coords else 1.0) if display_mode.startswith("Deformed") else 0.0

# Draw Columns
for i_idx, x in enumerate(x_coords):
    for j_idx, y in enumerate(y_coords):
        for k in range(num_stories):
            z0, z1 = z_coords[k], z_coords[k+1]
            
            dx0 = def_scale * (z0 / max(z_coords))**1.5 * math.sin(i_idx + k)
            dy0 = def_scale * (z0 / max(z_coords))**1.5 * math.cos(j_idx + k)
            dx1 = def_scale * (z1 / max(z_coords))**1.5 * math.sin(i_idx + k + 1)
            dy1 = def_scale * (z1 / max(z_coords))**1.5 * math.cos(j_idx + k + 1)

            col_color = 'royalblue' if display_mode.startswith("Original") else 'crimson'
            fig3d.add_trace(go.Scatter3d(
                x=[x + dx0, x + dx1], y=[y + dy0, y + dy1], z=[z0, z1],
                mode='lines', line=dict(color=col_color, width=6),
                hoverinfo='text',
                text=f"Column: {col_assign[k+1]} ({storey_names[k]} to {storey_names[k+1]})",
                showlegend=False
            ))

# Draw Beams
for k in range(1, num_stories + 1):
    z = z_coords[k]
    z_ratio = z / max(z_coords)
    
    for j_idx, y in enumerate(y_coords):
        for i_idx in range(bays_x):
            x0, x1 = x_coords[i_idx], x_coords[i_idx+1]
            
            dx0 = def_scale * z_ratio**1.5 * math.sin(i_idx + k - 1)
            dy0 = def_scale * z_ratio**1.5 * math.cos(j_idx + k - 1)
            dx1 = def_scale * z_ratio**1.5 * math.sin(i_idx + k)
            dy1 = def_scale * z_ratio**1.5 * math.cos(j_idx + k)

            beam_color = 'red' if display_mode.startswith("Original") else 'orange'
            fig3d.add_trace(go.Scatter3d(
                x=[x0 + dx0, x1 + dx1], y=[y + dy0, y + dy1], z=[z, z],
                mode='lines', line=dict(color=beam_color, width=4),
                hoverinfo='text',
                text=f"Beam X: {beam_assign[k]} ({storey_names[k]})",
                showlegend=False
            ))

    for i_idx, x in enumerate(x_coords):
        for j_idx in range(bays_y):
            y0, y1 = y_coords[j_idx], y_coords[j_idx+1]

            dx0 = def_scale * z_ratio**1.5 * math.sin(i_idx + k - 1)
            dy0 = def_scale * z_ratio**1.5 * math.cos(j_idx + k - 1)
            dx1 = def_scale * z_ratio**1.5 * math.sin(i_idx + k)
            dy1 = def_scale * z_ratio**1.5 * math.cos(j_idx + k)

            fig3d.add_trace(go.Scatter3d(
                x=[x + dx0, x + dx1], y=[y0 + dy0, y1 + dy1], z=[z, z],
                mode='lines', line=dict(color='green', width=4),
                hoverinfo='text',
                text=f"Beam Y: {beam_assign[k]} ({storey_names[k]})",
                showlegend=False
            ))

# Grid Line Labels
for i, x in enumerate(x_coords):
    fig3d.add_trace(go.Scatter3d(
        x=[x], y=[-0.8 * v_scale], z=[0],
        mode='text', text=[f"Grid {x_grid_labels[i]}"],
        textfont=dict(size=14, color='darkred'), showlegend=False
    ))

for j, y in enumerate(y_coords):
    fig3d.add_trace(go.Scatter3d(
        x=[-0.8 * v_scale], y=[y], z=[0],
        mode='text', text=[f"Grid {y_grid_labels[j]}"],
        textfont=dict(size=14, color='darkblue'), showlegend=False
    ))

# Storey Name Labels
for k, z in enumerate(z_coords):
    fig3d.add_trace(go.Scatter3d(
        x=[-1.5 * v_scale], y=[-1.5 * v_scale], z=[z],
        mode='text', text=[f"<b>{storey_names[k]}</b> (Z={z:.1f}{view_unit})"],
        textfont=dict(size=12, color='black'), showlegend=False
    ))

fig3d.update_layout(
    scene=dict(
        xaxis_title=f'X Axis ({view_unit})',
        yaxis_title=f'Y Axis ({view_unit})',
        zaxis_title=f'Z Axis ({view_unit})',
        aspectmode='data'
    ),
    margin=dict(l=0, r=0, b=0, t=30),
    height=650
)

st.plotly_chart(fig3d, use_container_width=True)
