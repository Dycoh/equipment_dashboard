import pandas as pd
import streamlit as st

# --------- UPDATE THIS LINE ---------
FILE_PATH = "CTE Equipment Performance Analysis 09 - 2025 - SEPTEMBER.xlsx"
# ------------------------------------

st.title("🔍 DATE Column Diagnostic Tool")

st.write("Loading dataset…")

try:
    df = pd.read_excel(FILE_PATH)
except Exception as e:
    st.error(f"Could not load file: {e}")
    st.stop()

st.success("File loaded successfully!")
st.write("Columns detected:", list(df.columns))

# Import the diagnostic function
def diagnose_date_column(df, col="DATE", max_samples=50):
    st.write("## 🔍 DATE column diagnostic")
    if col not in df.columns:
        st.error(f"Column '{col}' not found.")
        return

    raw = df[col]
    st.write("Data type (pandas):", raw.dtype)
    st.write("Total rows:", len(raw))
    st.write("Non-null count:", raw.notna().sum())
    st.write("Null (NaN/NaT) count:", raw.isna().sum())

    st.write(f"### Raw values (repr) — first {max_samples}")
    sample = raw.astype(object).head(max_samples).apply(lambda x: repr(x))
    st.dataframe(sample.to_frame(name=f"{col} (repr)"))

    st.write("### Value types:")
    st.write(raw.dropna().apply(type).value_counts())

    st.write("### Attempt: pandas text parsing")
    parsed_text = pd.to_datetime(raw, errors="coerce", infer_datetime_format=True)
    st.write("Parsed count:", parsed_text.notna().sum())
    st.dataframe(
        pd.DataFrame({
            "raw": raw.astype(object).head(20).apply(lambda x: repr(x)),
            "parsed_text": parsed_text.head(20).astype(str)
        })
    )

    st.write("### Attempt: numeric conversions (Excel/Unix)")
    numeric = pd.to_numeric(raw, errors="coerce")
    st.write("Numeric values detected:", numeric.notna().sum())

    if numeric.notna().any():
        try:
            excel_conv = pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
            st.write("Excel conversion valid count:", excel_conv.notna().sum())
        except Exception as e:
            st.warning(f"Excel conversion error: {e}")

        try:
            unix_ms = pd.to_datetime(numeric, unit="ms", origin="unix", errors="coerce")
            st.write("UNIX milliseconds count:", unix_ms.notna().sum())
        except:
            pass

        try:
            unix_s = pd.to_datetime(numeric, unit="s", origin="unix", errors="coerce")
            st.write("UNIX seconds count:", unix_s.notna().sum())
        except:
            pass


# Run the diagnostic
diagnose_date_column(df, "DATE")
