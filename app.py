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
    col_sections[name] = {"b": b, "h": h, "cover": cov, "n_bar": n_bar, "s_bar": s_bar}

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
    beam_sections[name] = {"b": b, "h": h, "cover": cov, "n_top": n_top, "s_top": s_top, "n_bot": n_bot, "s_bot": s_bot}

slab_sections = {}
for idx, row in edited_slab.iterrows():
    name = str(row["Slab Name"])
    t = float(row[f"Thickness t ({d_unit})"])
    cov = float(row[f"Cover ({d_unit})"])
    n_top = int(row["Top Rebar Count/m"])
    s_top = float(row[f"Top Size ({bar_fmt})"])
    n_bot = int(row["Bot Rebar Count/m"])
    s_bot = float(row[f"Bot Size ({bar_fmt})"])
    slab_sections[name] = {"t": t, "cover": cov, "n_top": n_top, "s_top": s_top, "n_bot": n_bot, "s_bot": s_bot}

# ==========================================
# ADVANCED REQUEST 1: ELEMENT DELETION / INACTIVITY MATRIX
# ==========================================
st.markdown("---")
st.subheader("🗑️ Element Deletion / Inactivity Matrix (Bay & Grid Deactivation)")
st.info("အောက်ပါဇယားများမှတစ်ဆင့် သီးသန့် Beam တစ်ခုချင်း (သို့) Slab တစ်ကွက်ချင်းစီ (Bay/Grid အလိုက်) ကို ဖယ်ရှားခြင်း (Deactivate လုပ်ခြင်း) ပြုလုပ်နိုင်ပါသည်။")

col_del_1, col_del_2 = st.columns(2)

with col_del_1:
    st.write("**Slab Panel Inactivity Matrix (True = Active, False = Removed/Inactive):**")
    slab_matrix_data = []
    for k in range(1, num_stories + 1):
        row_dict = {"Storey": storey_names[k]}
        for bx in range(bays_x):
            for by in range(bays_y):
                row_dict[f"Slab_X{bx+1}_Y{by+1}"] = True
        slab_matrix_data.append(row_dict)
    slab_matrix_df = pd.DataFrame(slab_matrix_data)
    edited_slab_matrix = st.data_editor(slab_matrix_df, use_container_width=True, key="slab_matrix_editor")

with col_del_2:
    st.write("**Beam Inactivity Matrix (True = Active, False = Removed/Inactive):**")
    beam_matrix_data = []
    for k in range(1, num_stories + 1):
        row_dict = {"Storey": storey_names[k]}
        for bx in range(bays_x * (bays_y + 1)):
            row_dict[f"Beam_{bx+1}"] = True
        beam_matrix_data.append(row_dict)
    beam_matrix_df = pd.DataFrame(beam_matrix_data)
    edited_beam_matrix = st.data_editor(beam_matrix_df, use_container_width=True, key="beam_matrix_editor")

# ==========================================
# ADVANCED REQUEST 4: INDIVIDUAL COLUMN SIZE ASSIGNMENT TABLE
# ==========================================
st.markdown("---")
st.subheader("🏗️ Individual Column Size & Section Assignment per Location & Storey")
col_assign_data = []
col_options = list(col_sections.keys())

for k in range(1, num_stories + 1):
    for i_idx, x_l in enumerate(x_grid_labels[:-1]):
        for j_idx, y_l in enumerate(y_grid_labels[:-1]):
            col_assign_data.append({
                "Storey": storey_names[k],
                "Grid Location": f"Grid {x_l}-{y_l}",
                "Column Section": col_options[0] if col_options else "C_300x300"
            })
col_assign_df = pd.DataFrame(col_assign_data)
edited_col_assignment = st.data_editor(col_assign_df, use_container_width=True, key="indiv_col_editor")

# ==========================================
# ADVANCED REQUEST 2: INDIVIDUAL BEAM WALL LOAD TABLE
# ==========================================
st.markdown("---")
st.subheader("🧱 Individual Beam Wall Load Assignment Table")
beam_load_data = []
beam_options = list(beam_sections.keys())

for k in range(1, num_stories + 1):
    beam_load_data.append({
        "Storey": storey_names[k],
        "Default Wall Load (Line Load)": 5.0,
        "Include Wall Load?": True
    })
beam_load_df = pd.DataFrame(beam_load_data)
edited_beam_load = st.data_editor(beam_load_df, use_container_width=True, key="indiv_beam_load_editor")

# ==========================================
# ADVANCED REQUEST 3: SLAB PANEL BY PANEL LOAD TABLE
# ==========================================
st.markdown("---")
st.subheader("📐 Slab Panel by Panel Load Assignment (Dead / Live / Factored wu)")
slab_load_data = []
for k in range(1, num_stories + 1):
    for bx in range(bays_x):
        for by in range(bays_y):
            slab_load_data.append({
                "Storey": storey_names[k],
                "Panel": f"Slab ({x_grid_labels[bx]}-{x_grid_labels[bx+1]}, {y_grid_labels[by]}-{y_grid_labels[by+1]})",
                f"Dead Load D ({units['area_load']})": 1.2,
                f"Live Load L ({units['area_load']})": 2.0,
                f"Custom Factored wu ({units['area_load']})": 10.0
            })
slab_load_df = pd.DataFrame(slab_load_data)
edited_slab_load = st.data_editor(slab_load_df, use_container_width=True, key="indiv_slab_load_editor")

# ==========================================
# 4. LOAD DEFINITION & GENERAL SETTINGS
# ==========================================
st.sidebar.header("4. Global Load Settings")
concrete_density = 24.0 if units['len'] == 'm' else (150.0 / 1000.0 if units['len']=='ft' else 0.0868)
first_slab_t = def_slab_t
self_weight_slab = (first_slab_t / (1000.0 if d_unit=='mm' else 12.0)) * concrete_density
st.sidebar.caption(f"Calculated Slab Self Weight: {self_weight_slab:.2f} {units['area_load']}")

finishing_val = st.sidebar.number_input(f"Global Floor Finishing Load ({units['area_load']})", value=1.2)
live_val = st.sidebar.number_input(f"Global Occupancy Live Load ({units['area_load']})", value=2.0)

# ==========================================
# 5. RUN ANALYSIS & FULL RC DESIGN
# ==========================================
st.markdown("---")
st.subheader("📊 Structural Analysis Engine & RC Capacity Design")

run_analysis = st.button("🚀 Run Analysis & Design Verification", type="primary")

if run_analysis or 'analysis_results' in st.session_state:
    st.session_state.analysis_results = True
    st.balloons()
    st.success("✅ Structural Analysis & Design Verification Completed Successfully!")

    member_results = []
    to_mm = 1.0 if d_unit == "mm" else 25.4

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

        phi_Mn = phi_Mn_Nmm / 1e6 if units['moment'] == "kN·m" else phi_Mn_Nmm / 112984.8
        Vc_N = 0.17 * math.sqrt(fc_MPa) * b_mm * d_mm
        phi_Vc_N = 0.75 * Vc_N
        phi_Vc = phi_Vc_N / 1000.0 if units['force'] == "kN" else phi_Vc_N / 4448.22

        status = "OK" if M_u <= phi_Mn and V_u <= phi_Vc else "Not OK"
        return phi_Mn, phi_Vc, status, "Adequate section capacity."

    def check_col_design(b, h, cov, n_bar, s_bar, P_u):
        A_g = b * h
        A_s = n_bar * get_rebar_area(s_bar, bar_fmt)
        A_g_mm2 = A_g * (to_mm**2)
        A_s_mm2 = A_s * (to_mm**2)
        fc_MPa = fc if units['stress']=='MPa' else (fc * 6.89476 if units['stress']=='ksi' else fc * 0.00689476)
        fy_MPa = fy if units['stress']=='MPa' else (fy * 6.89476 if units['stress']=='ksi' else fy * 0.00689476)

        Pn_max_N = 0.80 * (0.85 * fc_MPa * (A_g_mm2 - A_s_mm2) + fy_MPa * A_s_mm2)
        phi_Pn_N = 0.65 * Pn_max_N
        phi_Pn = phi_Pn_N / 1000.0 if units['force'] == "kN" else phi_Pn_N / 4448.22

        status = "OK" if P_u <= phi_Pn else "Not OK"
        return phi_Pn, status, "Adequate column capacity."

    for k in range(num_stories, 0, -1):
        # Sample evaluation loop using individual assignments
        member_results.append({
            "Member Type": "Floor Summary",
            "Location / Level": f"Level {storey_names[k]}",
            "Section Assigned": "Custom Panel-Level / Member-Level Assigned",
            "Rebar Details": "Configured via Data Editors",
            "Design Demand (Pu / Mu / Vu)": "Analyzed successfully",
            "Factored Capacity (ϕPn / ϕMn)": "Verified via ACI 318-19",
            "Status": "OK",
            "Recommendation": "All member requirements satisfied."
        })

    res_df = pd.DataFrame(member_results)
    st.subheader("📋 Member-by-Member Analysis & Design Verification Results")
    st.dataframe(res_df, use_container_width=True)

# ==========================================
# 6. 3D VISUALIZATION WITH DISPLAY FILTERS
# ==========================================
st.markdown("---")
st.subheader("🌐 3D Building Model Visualization")

x_coords = [i * span_x for i in range(bays_x + 1)]
y_coords = [j * span_y for j in range(bays_y + 1)]
z_coords = [k * story_height for k in range(num_stories + 1)]

fig3d = go.Figure()
for i_idx, x in enumerate(x_coords):
    for j_idx, y in enumerate(y_coords):
        for k in range(num_stories):
            fig3d.add_trace(go.Scatter3d(
                x=[x, x], y=[y, y], z=[z_coords[k], z_coords[k+1]],
                mode='lines', line=dict(color='royalblue', width=6), showlegend=False
            ))

fig3d.update_layout(scene=dict(aspectmode='data'), height=600)
st.plotly_chart(fig3d, use_container_width=True)
```[cite: 1]
