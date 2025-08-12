import streamlit as st
import pandas as pd
import io
import plotly.graph_objects as go
import re

st.set_page_config(page_title="OHLC CSV Viewer", layout="wide")
st.title("OHLC CSV Viewer & Candlestick Chart")

def read_csv_auto_sep(uploaded_file):
    # Try comma, then tab
    for sep in [",", "\t"]:
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, sep=sep)
            if df.shape[1] < 2:
                continue
            return df
        except Exception:
            continue
    raise ValueError("Could not read file as CSV (comma or tab separated).")

uploaded = st.file_uploader("Upload CSV file (comma or tab separated)", type=["csv", "txt", "tsv"])

if uploaded is None:
    st.info("Upload a CSV to begin.")
    st.stop()

try:
    df = read_csv_auto_sep(uploaded)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

# Clean column names
df.columns = [col.strip() for col in df.columns]
st.write("Columns detected:", df.columns.tolist())  # Show columns for debugging

# Try to auto-detect and rename columns for candlestick
col_map = {}
for col in df.columns:
    col_clean = col.strip().lower()
    if 'date' in col_clean:
        col_map[col] = 'DateTime'
    elif re.match(r'open', col_clean):
        col_map[col] = 'Open'
    elif re.match(r'high', col_clean):
        col_map[col] = 'High'
    elif re.match(r'low', col_clean):
        col_map[col] = 'Low'
    elif re.match(r'close', col_clean):
        col_map[col] = 'Close'

df = df.rename(columns=col_map)

st.success(f"Loaded {uploaded.name} — {df.shape[0]:,} rows × {df.shape[1]:,} columns")
st.dataframe(df, use_container_width=True)

# Candlestick chart
ohlc_cols = ['DateTime', 'Open', 'High', 'Low', 'Close']
if all(col in df.columns for col in ohlc_cols):
    df['DateTime'] = pd.to_datetime(df['DateTime'], errors='coerce')
    fig = go.Figure(data=[go.Candlestick(
        x=df['DateTime'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        increasing_line_color='green',
        decreasing_line_color='red'
    )])
    fig.update_layout(
        title="Monthly OHLC Candlestick Chart",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"Candlestick chart not shown: Data must have columns {ohlc_cols}. Your columns: {df.columns.tolist()}")

# Summary
with st.expander("Summary"):
    st.write("Dtypes")
    st.write(df.dtypes.astype(str))
    st.write("Describe (numeric)")
    st.write(df.describe())
    st.write("Describe (all columns)")
    st.write(df.describe(include="all").T)

# Downloads
with st.expander("Downloads"):
    pq_buf = io.BytesIO()
    try:
        df.to_parquet(pq_buf, index=False)
        st.download_button(
            "Download as Parquet (.parquet)",
            data=pq_buf.getvalue(),
            file_name="data.parquet",
            mime="application/octet-stream",
        )
    except Exception:
        st.info("Install 'pyarrow' in requirements.txt to enable Parquet export.")

    st.download_button(
        "Download as CSV (.csv)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="data_clean.csv",
        mime="text/csv",
    )
