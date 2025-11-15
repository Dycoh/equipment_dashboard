import streamlit as st 
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings

# ==========================================
# STEP 0: Global Warning Handling
# ==========================================
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")
warnings.filterwarnings("ignore", category=FutureWarning)

# ==========================================
# STEP 1: Load Excel files (with caching)
# ==========================================
availability_file = "EQUIPMENT AVAILABILITY AS AT 0700HRS 21TH OCT 2025.xlsx"
performance_file = "CTE Equipment Performance Analysis 09 - 2025 - SEPTEMBER.xlsx"

st.title("🚢 Equipment Overview Dashboard")

@st.cache_data
def load_excel_data(availability_file, performance_file):
    """Efficiently load all Excel sheets using Streamlit caching (pickle-safe)."""
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

# --- Load Excel files safely ---
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
# STEP 2: Raw Data Preview Toggle
# ==========================================
if st.checkbox("🔍 Show Raw Data Previews"):
    st.write("### RELIABILITY SNAP SHOT")
    st.dataframe(reliability_df.head())

    st.write("### AVAILABILITY DASHBOARD")
    st.dataframe(availability_df.head())

    st.write("### PERFORMANCE SUMMARY")
    st.dataframe(performance_summary_df.head())

    st.write("### INDIVIDUAL EQUIPMENT")
    st.dataframe(individual_equipment_df.head())

    st.write("### DAILY PERFORMANCE DATA")
    st.dataframe(daily_performance_df.head())

# ==========================================
# STEP 3: Fix Unnamed Columns + Cleaners
# ==========================================
def clean_dataframe(df):
    """Drop unnamed columns, trim spaces, and convert mixed types safely."""
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed", case=False, na=False)]
    df = df.dropna(axis=1, how="all")
    df.columns = df.columns.map(lambda x: str(x).strip())
    df = df.replace(["-", "_", " ", "N/A", "n/a", "TOTAL", "AVE.", "NaN", ""], np.nan)

    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except Exception:
            pass
    return df

# Apply cleaning
reliability_df = clean_dataframe(reliability_df)
availability_df = clean_dataframe(availability_df)
performance_summary_df = clean_dataframe(performance_summary_df)
individual_equipment_df = clean_dataframe(individual_equipment_df)
daily_performance_df = clean_dataframe(daily_performance_df)

# ==========================================
# STEP 4: Clean Availability Sheet
# ==========================================
availability_df = pd.read_excel(
    availability_file,
    sheet_name="AVAILABILITY DASHBOARD",
    skiprows=4
)
availability_df = availability_df.dropna(axis=0, how="all").dropna(axis=1, how="all")
availability_df.columns = [str(c).strip() for c in availability_df.columns]

availability_df = availability_df.rename(columns={
    availability_df.columns[0]: "Equipment_Type",
    availability_df.columns[3]: "Holding",
    availability_df.columns[4]: "Available"
})

availability_df["Holding"] = pd.to_numeric(availability_df["Holding"], errors="coerce")
availability_df["Available"] = pd.to_numeric(availability_df["Available"], errors="coerce")
availability_df = availability_df.dropna(subset=["Equipment_Type", "Holding", "Available"], how="any")

availability_df["Availability %"] = np.where(
    availability_df["Holding"] > 0,
    (availability_df["Available"] / availability_df["Holding"]) * 100,
    np.nan
)
availability_df = availability_df[availability_df["Availability %"].between(0, 100)]

st.write("✅ Cleaned Availability Data:")
st.dataframe(availability_df[["Equipment_Type", "Holding", "Available", "Availability %"]])

# ==========================================
# STEP 5: Performance Summary Cleaning
# ==========================================
performance_summary_df = performance_summary_df.replace(["-", "_", "TOTAL", "AVE."], np.nan)

for col in performance_summary_df.columns:
    try:
        performance_summary_df[col] = pd.to_numeric(performance_summary_df[col])
    except Exception:
        pass

if "% AVAIL" in individual_equipment_df.columns:
    individual_equipment_df["% AVAIL"] = pd.to_numeric(individual_equipment_df["% AVAIL"], errors="coerce")
if "EQUIP" in individual_equipment_df.columns:
    individual_equipment_df["EQUIP"] = individual_equipment_df["EQUIP"].ffill()

# ==========================================
# STEP 6: Navigation
# ==========================================
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["Overview", "Availability Dashboard", "Performance Summary", "Fault Analysis"]
)

# ==========================================
# OVERVIEW PAGE
# ==========================================
if page == "Overview":
    st.subheader("Welcome to the Overview  Dashboard")
    st.write("""
    This dashboard provides insights into equipment performance, availability, 
    and fault trends based on daily operational data.
    """)

# ==========================================
# AVAILABILITY DASHBOARD
# ==========================================
elif page == "Availability Dashboard":
    st.subheader("⚙️ Equipment Availability Overview")
    st.dataframe(availability_df[["Equipment_Type", "Holding", "Available", "Availability %"]])

    avg_avail = availability_df["Availability %"].mean(skipna=True)
    total_types = availability_df["Equipment_Type"].nunique()

    st.metric("Average Availability (%)", round(avg_avail, 2))
    st.metric("Total Equipment Types", total_types)

    st.write("### 📊 Availability by Equipment Type")
    st.bar_chart(availability_df.set_index("Equipment_Type")["Availability %"])

    st.write("### ⚙️ Overall Availability Ratio")
    total_available = availability_df["Available"].sum()
    total_holding = availability_df["Holding"].sum()
    unavailable = total_holding - total_available

    st.write(f"**Total Units:** {int(total_holding)}")
    st.write(f"**Available Units:** {int(total_available)}")
    st.write(f"**Unavailable Units:** {int(unavailable)}")

    fig, ax = plt.subplots()
    ax.pie(
        [total_available, unavailable],
        labels=["Available", "Unavailable"],
        autopct="%1.1f%%",
        startangle=90,
    )
    ax.axis("equal")
    st.pyplot(fig)

# ==========================================
# PERFORMANCE SUMMARY PAGE
# ==========================================
elif page == "Performance Summary":
    st.subheader("📈 Performance Summary")
    st.dataframe(performance_summary_df.head())

    numeric_cols = performance_summary_df.select_dtypes(include="number").columns
    if not numeric_cols.empty:
        avg_values = performance_summary_df[numeric_cols].mean().round(2)
        st.write("### 🧮 Average Key Metrics")
        st.dataframe(avg_values.to_frame("Average Value"))

    if len(numeric_cols) >= 2:
        st.write("### 📊 Sample Comparison of First 2 Numeric Metrics")
        st.line_chart(performance_summary_df[numeric_cols[:2]])

# ==========================================
# FIXED — SIMPLE FAULT ANALYSIS (NO DATE REQUIRED)
# ==========================================
elif page == "Fault Analysis":
    st.subheader("🔧 Fault Category Analysis (Based on Individual Equipment Sheet)")

    st.write("""
    Since the dataset does not contain DATE values for faults, analysis is based on:
    - Equipment  
    - Fault Categories  
    - Downtime  
    - Calls  
    - MTTR  
    """)

    fault_df = individual_equipment_df.copy()

    # --- Detect fault column ---
    fault_col = None
    for c in fault_df.columns:
        if "FAULT" in c.upper():
            fault_col = c
    if fault_col:
        fault_df = fault_df.rename(columns={fault_col: "FAULT CATEGORY"})
    else:
        st.error("❌ No FAULT column found.")
        st.stop()

    # --- Equipment column ---
    equip_col = None
    for c in fault_df.columns:
        if c.upper() in ["EQUIP", "EQUIPMENT", "EQUIPT"]:
            equip_col = c
    if equip_col is None:
        equip_col = fault_df.columns[0]

    fault_df = fault_df.rename(columns={equip_col: "EQUIP"})

    # --- Downtime Hours ---
    downtime_col = None
    for c in fault_df.columns:
        if "HRS" in c.upper():
            downtime_col = c
    if downtime_col:
        fault_df["DOWNTIME_HRS"] = pd.to_numeric(fault_df[downtime_col], errors="coerce")
    else:
        fault_df["DOWNTIME_HRS"] = 0

    # --- Calls ---
    calls_col = None
    for c in fault_df.columns:
        if "CALL" in c.upper():
            calls_col = c
    if calls_col:
        fault_df["CALLS"] = pd.to_numeric(fault_df[calls_col], errors="coerce")
    else:
        fault_df["CALLS"] = 0

    # --- MTTR ---
    mttr_col = None
    for c in fault_df.columns:
        if "MTTR" in c.upper():
            mttr_col = c
    if mttr_col:
        fault_df["MTTR"] = pd.to_numeric(fault_df[mttr_col], errors="coerce")
    else:
        fault_df["MTTR"] = 0

    # === RAW PREVIEW ===
    st.write("### 📋 Raw Fault Data Preview")
    st.dataframe(fault_df.head(20))

    # === KPIs ===
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fault Records", len(fault_df))
    col2.metric("Total Downtime (hrs)", round(fault_df["DOWNTIME_HRS"].sum(), 2))
    col3.metric("Total Calls", int(fault_df["CALLS"].sum()))

    # === Top Fault Categories ===
    st.write("### 🧠 Top Fault Categories")
    fault_counts = fault_df["FAULT CATEGORY"].fillna("Unknown").value_counts()

    fig, ax = plt.subplots()
    fault_counts.head(10).plot(kind="barh", ax=ax)
    ax.set_xlabel("Count")
    ax.set_ylabel("Fault Category")
    st.pyplot(fig)

    # === Downtime by Equipment ===
    st.write("### ⏱️ Downtime by Equipment (Top 20)")
    downtime_rank = (
        fault_df.groupby("EQUIP")["DOWNTIME_HRS"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    st.bar_chart(downtime_rank)

    # === Calls by Equipment ===
    st.write("### 📞 Calls by Equipment (Top 20)")
    calls_rank = (
        fault_df.groupby("EQUIP")["CALLS"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    st.bar_chart(calls_rank)

# ==========================================
# STEP 7: Streamlit Arrow Compatibility Fix
# ==========================================
def make_arrow_safe(df):
    """Convert problematic types so Streamlit Arrow serializer won't break."""
    for col in df.columns:
        if df[col].dtype == "object" or "datetime" in str(df[col].dtype):
            df[col] = df[col].astype(str)
        elif pd.api.types.is_timedelta64_dtype(df[col]):
            df[col] = df[col].dt.total_seconds() / 3600  # convert to hours
    return df

availability_df = make_arrow_safe(availability_df)
performance_summary_df = make_arrow_safe(performance_summary_df)
individual_equipment_df = make_arrow_safe(individual_equipment_df)
daily_performance_df = make_arrow_safe(daily_performance_df)

st.success("✅ Dashboard optimized and loaded successfully.")

