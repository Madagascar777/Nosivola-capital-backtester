import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="CSV Loader", layout="wide")
st.title("CSV Loader (CSV -> typed DataFrame, optional Parquet)")

@st.cache_data(show_spinner=False)
def read_csv_robust(content: bytes) -> pd.DataFrame:
    """
    Read CSV from bytes with delimiter + encoding sniffing.
    """
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    last_err = None
    for enc in encodings:
        try:
            text = content.decode(enc)
        except Exception as e:
            last_err = e
            continue

        s = io.StringIO(text)
        try:
            # Try automatic delimiter detection
            df = pd.read_csv(
                s,
                sep=None,
                engine="python",
                on_bad_lines="skip",
            )
            return df
        except Exception as e:
            last_err = e
            # Fallback to common delimiters
            for sep in [",", ";", "\t", "|"]:
                s.seek(0)
                try:
                    df = pd.read_csv(
                        s,
                        sep=sep,
                        engine="python",
                        on_bad_lines="skip",
                    )
                    return df
                except Exception as e2:
                    last_err = e2
                    continue

    raise RuntimeError(f"Failed to parse CSV. Last error: {last_err}")

def infer_types(df: pd.DataFrame):
    """
    Heuristically convert object columns to datetime or numeric where appropriate.
    Returns a new DataFrame and a list of conversion notes.
    """
    out = df.copy()
    conversions = []

    # Convert likely date columns first
    for col in out.select_dtypes(include=["object"]).columns:
        sample = out[col].dropna().astype(str).head(500)
        if sample.empty:
            continue
        maybe_date = sample.str.contains(
            r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4}",
            regex=True,
        ).mean() > 0.5
        if maybe_date:
            parsed = pd.to_datetime(out[col], errors="coerce", infer_datetime_format=True, utc=False)
            if parsed.notna().mean() >= 0.8:
                out[col] = parsed
                conversions.append(f"{col} -> datetime")

    # Convert remaining object columns to numeric if 80%+ convertible
    for col in out.select_dtypes(include=["object"]).columns:
        cleaned = (
            out[col]
            .astype(str)
            .str.replace(",", "", regex=False)  # remove thousands sep
            .str.replace(" ", "", regex=False)
        )
        coerced = pd.to_numeric(cleaned, errors="coerce")
        if coerced.notna().mean() >= 0.8:
            if (coerced.dropna() % 1 == 0).all():
                out[col] = coerced.astype("Int64")  # nullable integer
                conversions.append(f"{col} -> integer")
            else:
                out[col] = coerced  # float64
                conversions.append(f"{col} -> float")

    return out, conversions

uploaded = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded is None:
    st.info("Upload a CSV to begin.")
    st.stop()

# Read
with st.spinner("Reading CSV..."):
    try:
        df = read_csv_robust(uploaded.getvalue())
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        st.stop()

# Type inference
df_typed, conversions = infer_types(df)

st.success(f"Loaded {uploaded.name} — {df_typed.shape[0]:,} rows × {df_typed.shape[1]:,} columns")
if conversions:
    st.caption("Type conversions applied: " + ", ".join(conversions))

# Preview
st.dataframe(df_typed.head(1000), use_container_width=True)

# Summary
with st.expander("Summary"):
    st.write("Dtypes")
    st.write(df_typed.dtypes.astype(str))
    st.write("Describe (numeric)")
    st.write(df_typed.describe())
    st.write("Describe (all columns)")
    st.write(df_typed.describe(include="all").T)

# Downloads
with st.expander("Downloads"):
    # Parquet (higher fidelity than CSV; recommended)
    pq_buf = io.BytesIO()
    try:
        df_typed.to_parquet(pq_buf, index=False)  # requires pyarrow
        st.download_button(
            "Download as Parquet (.parquet)",
            data=pq_buf.getvalue(),
            file_name="data.parquet",
            mime="application/octet-stream",
        )
    except Exception:
        st.info("Install 'pyarrow' in requirements.txt to enable Parquet export.")

    # CSV
    st.download_button(
        "Download as CSV (.csv)",
        data=df_typed.to_csv(index=False).encode("utf-8"),
        file_name="data_clean.csv",
        mime="text/csv",
    )
