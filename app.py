import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

# ==========================================
# STEP 0: Global Warning Handling & CSS
# ==========================================
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
warnings.filterwarnings("ignore", category=FutureWarning)

# Inject a navy → light-blue gradient background and ensure dataframes readable
st.markdown(
    """
    <style>
    /* Page background gradient */
    .stApp {
        background: linear-gradient(180deg,#001f3f 0%, #1e90ff 100%);
        color: #ffffff;
    }
    /* Make dataframes readable on dark bg by giving them a white-ish background */
    .stDataFrame table { color: #000 !important; background: rgba(255,255,255,0.95) !important; }
    /* Align header elements better */
    .logo-title-row { display:flex; align-items:center; gap:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# STEP 1: Files & Title (logo placeholder)
# ==========================================
availability_file = "EQUIPMENT AVAILABILITY AS AT 0700HRS 21TH OCT 2025.xlsx"
performance_file = "CTE Equipment Performance Analysis 09 - 2025 - SEPTEMBER.xlsx"

# Align logo and title horizontally
col_logo, col_title = st.columns([1, 10])
with col_logo:
    try:
        st.image("KPA_logo.jpeg", width=180)
    except Exception:
        st.write("")
with col_title:
    st.markdown("<h1 style='margin:0; padding-top:6px; color: white;'>Equipment Overview Dashboard</h1>", unsafe_allow_html=True)

# ==========================================
# Helper functions (display-only formatting)
# ==========================================
def display_copy_with_format(df: pd.DataFrame, decimals: int = 2, drop_empty_cols=True, drop_empty_rows=True):
    """
    Return a *display* copy of df:
     - optional drop fully empty columns
     - optional drop fully empty rows
     - round numeric columns for display only
    """
    display_df = df.copy(deep=True)
    if drop_empty_cols:
        # drop columns that are entirely NA or blank strings
        empty_cols = [c for c in display_df.columns if display_df[c].dropna().shape[0] == 0]
        display_df = display_df.drop(columns=empty_cols, errors="ignore")
    if drop_empty_rows:
        display_df = display_df.dropna(axis=0, how="all")

    # Round numeric columns for display only
    for col in display_df.select_dtypes(include=[np.number]).columns:
        display_df[col] = display_df[col].round(decimals)

    # Replace NaN with empty string for cleaner display
    display_df = display_df.fillna("")
    return display_df

def display_availability_with_one_decimal(df: pd.DataFrame):
    """
    Return a display copy of availability df with Availability % to 1 decimal,
    other numeric columns to 2 decimals.
    """
    disp = df.copy(deep=True)
    disp = disp.dropna(axis=1, how="all")
    disp = disp.dropna(axis=0, how="all")
    for col in disp.select_dtypes(include=[np.number]).columns:
        if col == "Availability %":
            disp[col] = disp[col].round(1)
        else:
            disp[col] = disp[col].round(2)
    disp = disp.fillna("")
    return disp

# ==========================================
# STEP 2: Load Excel files (with caching)
# ==========================================
@st.cache_data
def load_excel_data(availability_file, performance_file):
    reliability_df = pd.read_excel(availability_file, sheet_name="RELIABILITY SNAP SHOT")
    availability_df = pd.read_excel(availability_file, sheet_name="AVAILABILITY DASHBOARD")
    executive_summary_df = pd.read_excel(availability_file, sheet_name="EXECUTIVE SUMMARY")

    performance_summary_df = pd.read_excel(performance_file, sheet_name="1. Performance summary")
    individual_equipment_df = pd.read_excel(performance_file, sheet_name="5. Individual Equipment")
    daily_performance_df = pd.read_excel(performance_file, sheet_name="6. Daily Performance data")

    return (
        reliability_df,
        availability_df,
        executive_summary_df,
        performance_summary_df,
        individual_equipment_df,
        daily_performance_df,
    )

# Load sheets
availability_sheets = pd.ExcelFile(availability_file)
performance_sheets = pd.ExcelFile(performance_file)
(
    reliability_df,
    availability_df,
    executive_summary_df,
    performance_summary_df,
    individual_equipment_df,
    daily_performance_df,
) = load_excel_data(availability_file, performance_file)

# ==========================================
# STEP 3: Minimal cleaning (preserve data, only fix headers/unwanted empty cols)
# ==========================================
def clean_dataframe_minimal(df):
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed", case=False, na=False)]
    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.replace(["-", "_", " ", "N/A", "n/a", "TOTAL", "AVE.", "NaN", ""], np.nan)
    return df

# Apply minimal cleaning
reliability_df = clean_dataframe_minimal(reliability_df)
availability_df = clean_dataframe_minimal(availability_df)
performance_summary_df = clean_dataframe_minimal(performance_summary_df)
individual_equipment_df = clean_dataframe_minimal(individual_equipment_df)
daily_performance_df = clean_dataframe_minimal(daily_performance_df)
executive_summary_df = clean_dataframe_minimal(executive_summary_df)

# ==========================================
# STEP 4: Compute cleaned availability (original logic preserved)
# ==========================================
availability_proc = pd.read_excel(availability_file, sheet_name="AVAILABILITY DASHBOARD", skiprows=4)
availability_proc = availability_proc.dropna(axis=0, how="all").dropna(axis=1, how="all")
availability_proc.columns = [str(c).strip() for c in availability_proc.columns]

# try rename as original code did
try:
    availability_proc = availability_proc.rename(columns={
        availability_proc.columns[0]: "Equipment_Type",
        availability_proc.columns[3]: "Holding",
        availability_proc.columns[4]: "Available"
    })
except Exception:
    # keep as-is if not matching the expected layout
    pass

if "Holding" in availability_proc.columns:
    availability_proc["Holding"] = pd.to_numeric(availability_proc["Holding"], errors="coerce")
if "Available" in availability_proc.columns:
    availability_proc["Available"] = pd.to_numeric(availability_proc["Available"], errors="coerce")

if all(c in availability_proc.columns for c in ["Equipment_Type", "Holding", "Available"]):
    availability_proc = availability_proc.dropna(subset=["Equipment_Type", "Holding", "Available"], how="any")
    availability_proc["Availability %"] = np.where(
        availability_proc["Holding"] > 0,
        (availability_proc["Available"] / availability_proc["Holding"]) * 100,
        np.nan
    )
    availability_proc = availability_proc[availability_proc["Availability %"].between(0, 100)]
# else: leave availability_proc as-is

# ==========================================
# STEP 5: Performance summary numeric casts (display-only)
# ==========================================
performance_summary_df = performance_summary_df.replace(["-", "_", "TOTAL", "AVE."], np.nan)
for col in performance_summary_df.columns:
    try:
        performance_summary_df[col] = pd.to_numeric(performance_summary_df[col])
    except Exception:
        pass

# Fill % AVAIL in individual equipment as earlier
if "% AVAIL" in individual_equipment_df.columns:
    individual_equipment_df["% AVAIL"] = pd.to_numeric(individual_equipment_df["% AVAIL"], errors="coerce")
if "EQUIP" in individual_equipment_df.columns:
    individual_equipment_df["EQUIP"] = individual_equipment_df["EQUIP"].ffill()

# ==========================================
# STEP 6: Navigation (label left as "navigation bar")
# ==========================================
st.sidebar.markdown("### navigation bar")
page = st.sidebar.radio(
    "Go to:",
    ["Overview", "Availability Dashboard", "Performance Summary", "Fault Analysis"]
)

# ==========================================
# OVERVIEW PAGE
# ==========================================
if page == "Overview":
    st.subheader("Overview")
    st.write(
        "Welcome to the Overview dashboard — this provides insights into equipment performance, availability, "
        "and fault trends based on operational data."
    )

    # Checkbox to show raw data previews (FULL sheets, formatted display)
    if st.checkbox("🔍 Show Raw Data Previews"):
        # RELIABILITY: try to show full cleaned sheet; fallback to raw sheet head() only if cleaned display is empty
        try:
            rel_display = display_copy_with_format(reliability_df, decimals=2, drop_empty_cols=True)
            if rel_display.shape[0] == 0 or rel_display.shape[1] == 0:
                # Fallback: read raw sheet without our minimal cleaning (attempt to show the original file contents)
                try:
                    raw_reliability = pd.read_excel(availability_file, sheet_name="RELIABILITY SNAP SHOT", header=None)
                    # If the raw read has rows, show top rows (headerless) to avoid empty display
                    if raw_reliability.shape[0] > 0:
                        st.write("### RELIABILITY SNAP SHOT")
                        # Show first 20 rows of raw sheet so layout is visible (headerless)
                        st.dataframe(raw_reliability.head(20).fillna("").reset_index(drop=True))
                    else:
                        st.write("### RELIABILITY SNAP SHOT")
                        st.dataframe(reliability_df.head())
                except Exception:
                    # final fallback to cleaned head
                    st.write("### RELIABILITY SNAP SHOT")
                    st.dataframe(reliability_df.head())
            else:
                st.write("### RELIABILITY SNAP SHOT")
                st.dataframe(rel_display)
        except Exception:
            st.write("### RELIABILITY SNAP SHOT")
            st.dataframe(reliability_df.head())

        # Full sheet — empty columns removed
        st.write("### AVAILABILITY DASHBOARD")
        st.dataframe(display_copy_with_format(availability_df, decimals=2, drop_empty_cols=True))

        st.write("### PERFORMANCE SUMMARY")
        st.dataframe(display_copy_with_format(performance_summary_df, decimals=2, drop_empty_cols=True))

        st.write("### INDIVIDUAL EQUIPMENT")
        st.dataframe(display_copy_with_format(individual_equipment_df, decimals=2, drop_empty_cols=True))

        # (Full sheet, DATE column shown as-is)
        st.write("### DAILY PERFORMANCE DATA")
        st.dataframe(display_copy_with_format(daily_performance_df, decimals=2, drop_empty_cols=True))

    # On overview, show a checkbox that displays the cleaned availability snapshot (1 decimal)
    if st.checkbox("Show cleaned availability snapshot (Overview)"):
        if "Equipment_Type" in availability_proc.columns:
            st.write("### Cleaned Availability Snapshot")
            st.dataframe(display_availability_with_one_decimal(availability_proc[["Equipment_Type", "Holding", "Available", "Availability %"]]))
        else:
            st.warning("Cleaned availability data not available — check sheet format.")

# ==========================================
# AVAILABILITY DASHBOARD PAGE
# ==========================================
elif page == "Availability Dashboard":
    st.subheader("⚙️ Equipment Availability Overview")

    if "Equipment_Type" in availability_proc.columns:
        st.write("### Cleaned Availability Data")
        st.dataframe(display_availability_with_one_decimal(availability_proc[["Equipment_Type", "Holding", "Available", "Availability %"]]))
    else:
        st.warning("Cleaned availability data could not be prepared — check availability sheet structure.")

    # Compute metrics using availability_proc
    try:
        avg_avail = availability_proc["Availability %"].mean(skipna=True)
        total_types = availability_proc["Equipment_Type"].nunique()
    except Exception:
        avg_avail = np.nan
        total_types = 0

    st.metric("Average Availability (%)", round(avg_avail, 1) if not pd.isna(avg_avail) else "N/A")
    st.metric("Total Equipment Types", total_types)

    st.write("### 📊 Availability by Equipment Type")
    if "Equipment_Type" in availability_proc.columns and "Availability %" in availability_proc.columns:
        chart_series = availability_proc.set_index("Equipment_Type")["Availability %"].round(1)
        st.bar_chart(chart_series)
    else:
        st.info("No availability chart available due to missing columns.")

    st.write("### ⚙️ Overall Availability Ratio")
    try:
        total_available = availability_proc["Available"].sum()
        total_holding = availability_proc["Holding"].sum()
        unavailable = total_holding - total_available
        st.write(f"**Total Units:** {int(total_holding)}")
        st.write(f"**Available Units:** {int(total_available)}")
        st.write(f"**Unavailable Units:** {int(unavailable)}")
    except Exception:
        st.write("Insufficient data to compute totals.")

    # Pie chart
    try:
        fig, ax = plt.subplots()
        ax.pie([total_available, unavailable], labels=["Available", "Unavailable"], autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
    except Exception:
        pass

# ==========================================
# PERFORMANCE SUMMARY PAGE
# ==========================================
elif page == "Performance Summary":
    st.subheader("📈 Performance Summary")

    st.write("### Full Performance Summary")
    st.dataframe(display_copy_with_format(performance_summary_df, decimals=2, drop_empty_cols=True))

    numeric_cols = performance_summary_df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        avg_values = performance_summary_df[numeric_cols].mean().round(2)
        st.write("### 🧮 Average Key Metrics")
        st.dataframe(avg_values.to_frame("Average Value").round(2))

    # --- Scatter comparison for months/metrics (Option A: equipment auto-detect, dots only) ---
    st.write("### 📊 Comparison: choose one or more months to compare")
    # Auto-detect equipment column: first textual (object) column having >0 non-null string values
    equipment_col = None
    for c in performance_summary_df.columns:
        if performance_summary_df[c].dtype == object or performance_summary_df[c].dtype == "string":
            non_null = performance_summary_df[c].dropna().astype(str).str.strip()
            if non_null.shape[0] > 0 and non_null.str.len().gt(0).sum() > 0:
                equipment_col = c
                break
    if equipment_col is None:
        equipment_col = performance_summary_df.columns[0]

    st.write(f"Detected equipment column: **{equipment_col}**")

    month_options = [c for c in performance_summary_df.columns if c != equipment_col and pd.api.types.is_numeric_dtype(performance_summary_df[c])]
    selected_months = st.multiselect("Select months/metrics to plot", month_options, default=month_options[:2] if len(month_options) >= 2 else month_options)

    if selected_months:
        # Prepare plotting dataframe: drop rows with empty equipment names
        plot_df = performance_summary_df[[equipment_col] + selected_months].copy()
        plot_df = plot_df.dropna(subset=[equipment_col])
        plot_df[equipment_col] = plot_df[equipment_col].astype(str).str.strip()
        plot_df = plot_df[plot_df[equipment_col] != ""]
        plot_df = plot_df.reset_index(drop=True)

        if plot_df.empty:
            st.warning("No data available to plot after filtering empty equipment names.")
        else:
            equipment_names = plot_df[equipment_col].astype(str).tolist()
            x_positions = np.arange(len(equipment_names))

            fig, ax = plt.subplots(figsize=(10, 4 + max(0, len(equipment_names)//10)))
            marker_style = "o"
            for col in selected_months:
                y = pd.to_numeric(plot_df[col], errors="coerce")
                ax.scatter(x_positions, y, label=str(col), marker=marker_style, s=60, alpha=0.8)

            ax.set_xticks(x_positions)
            ax.set_xticklabels(equipment_names, rotation=45, ha="right")
            ax.set_xlabel("Equipment")
            ax.set_ylabel(", ".join([str(m) for m in selected_months]))
            ax.set_title("Equipment comparison (scatter)")
            ax.legend(title="Metric")
            plt.tight_layout()
            st.pyplot(fig)
    else:
        st.info("Select one or more months/metrics to plot a scatter comparison.")

# ==========================================
# FAULT ANALYSIS PAGE
# ==========================================
elif page == "Fault Analysis":
    st.subheader("🔧 Fault Analysis Based on Individual Equipment Sheet")

    st.write(
        "Since the dataset does not contain DATE values for faults, analysis is based on the full Individual Equipment sheet."
    )

    # Work on a copy for processing (do not mutate the cached original)
    fault_df = individual_equipment_df.copy()

    # --- Detect fault column (preserve original mapping logic)
    fault_col = None
    for c in fault_df.columns:
        if "FAULT" in str(c).upper():
            fault_col = c
            break
    if fault_col:
        fault_df = fault_df.rename(columns={fault_col: "FAULT CATEGORY"})
    else:
        st.error("❌ No FAULT column found in the Individual Equipment sheet.")
        st.stop()

    # --- Equipment column mapping (preserve original behavior)
    equip_col = None
    for c in fault_df.columns:
        if str(c).upper() in ["EQUIP", "EQUIPMENT", "EQUIPT"]:
            equip_col = c
            break
    if equip_col is None:
        equip_col = fault_df.columns[0]
    fault_df = fault_df.rename(columns={equip_col: "EQUIP"})

    # --- Downtime, Calls, MTTR extraction (preserve your original logic)
    downtime_col = None
    for c in fault_df.columns:
        if "HRS" in str(c).upper():
            downtime_col = c
            break
    if downtime_col:
        fault_df["DOWNTIME_HRS"] = pd.to_numeric(fault_df[downtime_col], errors="coerce")
    else:
        fault_df["DOWNTIME_HRS"] = 0

    calls_col = None
    for c in fault_df.columns:
        if "CALL" in str(c).upper():
            calls_col = c
            break
    if calls_col:
        fault_df["CALLS"] = pd.to_numeric(fault_df[calls_col], errors="coerce")
    else:
        fault_df["CALLS"] = 0

    mttr_col = None
    for c in fault_df.columns:
        if "MTTR" in str(c).upper():
            mttr_col = c
            break
    if mttr_col:
        fault_df["MTTR"] = pd.to_numeric(fault_df[mttr_col], errors="coerce")
    else:
        fault_df["MTTR"] = 0

    # === Show the full Individual Equipment sheet (formatted for display only) ===
    st.write("### 📋 Full Individual Equipment")
    st.dataframe(display_copy_with_format(fault_df, decimals=2, drop_empty_cols=True))

    # === KPIs ===
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fault Records", len(fault_df))
    col2.metric("Total Downtime (hrs)", round(fault_df["DOWNTIME_HRS"].sum(), 2))
    col3.metric("Total Calls", int(fault_df["CALLS"].sum() if pd.notna(fault_df["CALLS"].sum()) else 0))

    # === Top Fault Categories ===
    st.write("### 🧠 Top Fault Categories")
    fault_counts = fault_df["FAULT CATEGORY"].fillna("Unknown").value_counts()
    fig, ax = plt.subplots()
    fault_counts.head(10).plot(kind="barh", ax=ax)
    ax.set_xlabel("Count")
    ax.set_ylabel("Fault Category")
    st.pyplot(fig)

    # === September 2025 daily faults — show full "6. Daily Performance data" sheet (ignore DATE column) ===
    st.write("### 📆 September 2025 Daily Faults")
    daily_display = daily_performance_df.copy()
    if "DATE" in daily_display.columns:
        daily_display = daily_display.drop(columns=["DATE"])
    # Search box to filter across all columns for equipment/text
    search_text = st.text_input("Search Daily Faults (search across all columns)")
    if search_text:
        mask = daily_display.astype(str).apply(lambda row: row.str.contains(search_text, case=False, na=False)).any(axis=1)
        daily_search_results = daily_display[mask]
        st.write(f"Filtered {len(daily_search_results)} rows matching '{search_text}'")
        st.dataframe(display_copy_with_format(daily_search_results, decimals=2, drop_empty_cols=True))
    else:
        st.dataframe(display_copy_with_format(daily_display, decimals=2, drop_empty_cols=True))

    # === Downtime by Equipment (Top 20) — USES the "5. Individual Equipment" sheet aggregation (keeps original logic) ===
    st.write("### ⏱️ Downtime by Equipment (Top 20)")
    downtime_rank = (
        fault_df.groupby("EQUIP")["DOWNTIME_HRS"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    st.bar_chart(downtime_rank)

    # === Calls by Equipment (Top 20) — USES the "5. Individual Equipment" sheet aggregation (keeps original logic) ===
    st.write("### 📞 Calls by Equipment (Top 20)")
    calls_rank = (
        fault_df.groupby("EQUIP")["CALLS"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    st.bar_chart(calls_rank)

# ==========================================
# FINAL: Success message
# ==========================================
st.success("✅ Dashboard loaded. (Display formatting applied only to visible tables.)")
