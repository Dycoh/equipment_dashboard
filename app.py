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

# st.write("📘 Sheets in Availability File:", availability_sheets.sheet_names)
# st.write("📗 Sheets in Performance File:", performance_sheets.sheet_names)

# ==========================================
# STEP 2: Quick data previews (optional toggle)
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
# FIX 1: Clean unnamed and mixed-type columns globally
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
# STEP 3: Data Cleaning (Availability)
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
# STEP 4: Data Cleaning (Performance)
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
# FIX 2: Convert Excel serial dates in Daily Performance data
# ==========================================
if "DATE" in daily_performance_df.columns:
    if np.issubdtype(daily_performance_df["DATE"].dtype, np.number):
        daily_performance_df["DATE"] = pd.to_datetime(
            daily_performance_df["DATE"], origin="1899-12-30", unit="D", errors="coerce"
        )
    else:
        daily_performance_df["DATE"] = pd.to_datetime(daily_performance_df["DATE"], errors="coerce")

# ==========================================
# STEP 5: Dashboard Navigation
# ==========================================
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["Overview", "Availability Dashboard", "Performance Summary", "Fault Analysis"]
)

# --- OVERVIEW PAGE ---
if page == "Overview":
    st.subheader("Welcome to the Equipment Dashboard")
    st.write("""
    This dashboard provides insights into equipment performance, availability, 
    and fault trends based on daily operational data.
    """)

# --- AVAILABILITY PAGE ---
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

# --- PERFORMANCE SUMMARY PAGE ---
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




# --- FAULT ANALYSIS PAGE ---
elif page == "Fault Analysis":
    st.subheader("🔧 Fault Category Analysis & Trends")

    # --- Normalize column names ---
    daily_performance_df.columns = daily_performance_df.columns.str.strip().str.upper()

    # --- Identify key columns dynamically ---
    date_col = next((c for c in daily_performance_df.columns if "DATE" in c), None)
    fault_col = next((c for c in daily_performance_df.columns if "FAULT" in c), None)
    equip_col = next((c for c in daily_performance_df.columns if "EQUIP" in c), None)

    if not date_col or not fault_col:
        st.error("❌ Could not find 'DATE' or 'FAULT CATEGORY' column in the Excel file.")
    else:
        # --- Preview the first few DATE values ---
        st.write("📅 Sample of DATE column:", daily_performance_df[date_col].head(10).tolist())

        # --- Preview the first few DATE values (raw) ---


        st.write("🔍 Data type before conversion:", daily_performance_df[date_col].dtype)
        st.write("Unique sample values:", daily_performance_df[date_col].dropna().unique()[:15])


        # --- Convert DATE column to datetime robustly ---
        daily_performance_df[date_col] = pd.to_datetime( 
            daily_performance_df[date_col], errors="coerce", dayfirst=True
        )

        # If too many are NaT, try Excel serial number conversion
        if daily_performance_df[date_col].isna().mean() > 0.9:
            try:
                daily_performance_df[date_col] = pd.to_datetime(
                    pd.to_numeric(daily_performance_df[date_col], errors="coerce"),
                    origin="1899-12-30",
                    unit="D",
                )
            except Exception as e:
                st.warning(f"⚠️ Alternate date conversion failed: {e}")

        # --- Sidebar filters ---
        st.sidebar.subheader("🔍 Filter Fault Data")

        valid_dates = daily_performance_df[date_col].dropna()
        if not valid_dates.empty:
            min_date, max_date = valid_dates.min(), valid_dates.max()
        else:
            min_date, max_date = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")

        date_range = st.sidebar.date_input("Select Date Range", [min_date, max_date])

        equipment_options = (
            sorted(daily_performance_df[equip_col].dropna().unique())
            if equip_col
            else []
        )
        selected_equipment = st.sidebar.multiselect("Filter by Equipment", equipment_options)

        fault_options = (
            sorted(daily_performance_df[fault_col].dropna().unique())
            if fault_col
            else []
        )
        selected_faults = st.sidebar.multiselect("Filter by Fault Category", fault_options)

        # --- Filtering ---
        filtered_df = daily_performance_df.copy()

        # Convert date_range properly
        if isinstance(date_range, (list, tuple)):
            if len(date_range) == 2:
                start_date, end_date = map(pd.Timestamp, date_range)
            else:
                start_date = end_date = pd.Timestamp(date_range[0])
        else:
            start_date = end_date = pd.Timestamp(date_range)

        # Apply date filter only if column is valid datetime
        if pd.api.types.is_datetime64_any_dtype(filtered_df[date_col]):
            filtered_df = filtered_df[
                (filtered_df[date_col] >= start_date)
                & (filtered_df[date_col] <= end_date)
            ]
        else:
            st.warning("⚠️ DATE column not recognized as datetime — skipping date filter.")

        if selected_equipment and equip_col:
            filtered_df = filtered_df[filtered_df[equip_col].isin(selected_equipment)]
        if selected_faults and fault_col:
            filtered_df = filtered_df[filtered_df[fault_col].isin(selected_faults)]

        st.info(
            f"🔎 Filtered from **{len(daily_performance_df)}** rows → **{len(filtered_df)}** rows "
            f"for dates between {start_date.date()} and {end_date.date()}"
        )

        # --- Metrics ---
        st.metric("Total Fault Records", len(filtered_df))
        if not filtered_df.empty:
            top_fault = filtered_df[fault_col].mode().iloc[0]
            st.metric("Most Frequent Fault", top_fault)

            # --- Charts ---
            st.write("### 📆 Fault Trend Over Time")
            fault_trend = (
                filtered_df.groupby([date_col, fault_col]).size().unstack(fill_value=0)
            )
            st.line_chart(fault_trend)

            st.write("### 🧠 Top 10 Fault Categories")
            fault_counts = filtered_df[fault_col].value_counts().head(10).sort_values(ascending=True)
            fig, ax = plt.subplots()
            fault_counts.plot(kind="barh", ax=ax)
            st.pyplot(fig)
        else:
            st.warning("⚠️ No fault data available for the selected filters.")

        st.write("### 📋 Filtered Fault Data (Preview)")
        st.dataframe(filtered_df.head(20))


# ==========================================
# STEP 6: FINAL FIX — Streamlit Display Compatibility
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

