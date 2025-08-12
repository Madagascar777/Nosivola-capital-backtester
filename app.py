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
