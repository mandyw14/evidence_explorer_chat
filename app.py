# app.py
# Public-facing PubMed search (MS + exercise) for Streamlit Community Cloud
# Uses Streamlit Secrets for NCBI credentials, adds caching + simple rate limiting.

from __future__ import annotations

from datetime import datetime, timedelta
import re
import time
import pandas as pd
import streamlit as st
from Bio import Entrez


# -----------------------------
# Streamlit page config
# -----------------------------
st.set_page_config(page_title="PubMed Search: MS + Exercise", layout="wide")
st.title("PubMed Search Tool DEMO: Multiple Sclerosis")
st.caption("Public search interface powered by NCBI PubMed (Entrez)")
st.caption("Developed by Branch Out Neurological Foundation")


# -----------------------------
# Secrets / credentials (server-side)
# -----------------------------
NCBI_EMAIL = st.secrets.get("NCBI_EMAIL", "")
NCBI_API_KEY = st.secrets.get("NCBI_API_KEY", None)
NCBI_TOOL = st.secrets.get("NCBI_TOOL", "BONF_PublicPubMedSearch")

Entrez.email = NCBI_EMAIL
Entrez.api_key = NCBI_API_KEY

if not Entrez.email:
    st.error(
        "Server is missing NCBI_EMAIL. In Streamlit Community Cloud, set it under "
        "App → Settings → Secrets (NCBI_EMAIL)."
    )
    st.stop()


# -----------------------------
# Basic rate limiting (per session)
# -----------------------------
if "last_search_times" not in st.session_state:
    st.session_state.last_search_times = []

def allow_search(max_per_minute: int = 6) -> bool:
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=1)
    st.session_state.last_search_times = [
        t for t in st.session_state.last_search_times if t > window_start
    ]
    if len(st.session_state.last_search_times) >= max_per_minute:
        return False
    st.session_state.last_search_times.append(now)
    return True


# -----------------------------
# Query utilities
# -----------------------------
def normalize_query(q: str) -> str:
    """Trim, collapse whitespace, and cap length to keep public input sane."""
    q = (q or "").strip()
    q = re.sub(r"\s+", " ", q)
    return q[:500]


# -----------------------------
# Entrez calls (cached)
# -----------------------------
@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def esearch_pmids(query: str, retmax: int) -> tuple[list[str], int]:
    """
    Returns (pmids, total_count).
    total_count is the number of matches in PubMed overall.
    pmids length <= retmax.
    """
    with Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=retmax,
        usehistory="n",
        tool=NCBI_TOOL,
    ) as handle:
        res = Entrez.read(handle)

    pmids = res.get("IdList", [])
    total_count = int(res.get("Count", 0))
    return pmids, total_count


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def efetch_details(pmids: list[str]) -> pd.DataFrame:
    """Fetches basic citation details for a PMID list."""
    if not pmids:
        return pd.DataFrame(columns=["PMID", "Year", "Title", "Journal", "Authors", "DOI"])

    with Entrez.efetch(
        db="pubmed",
        id=",".join(pmids),
        retmode="xml",
        tool=NCBI_TOOL,
    ) as handle:
        records = Entrez.read(handle)

    rows = []
    for rec in records.get("PubmedArticle", []):
        medline = rec.get("MedlineCitation", {})
        article = medline.get("Article", {})

        pmid = str(medline.get("PMID", "")).strip()
        title = str(article.get("ArticleTitle", "")).strip()
        journal = article.get("Journal", {}).get("Title", "")

        # Year can be in multiple fields
        pubdate = (
            article.get("Journal", {})
            .get("JournalIssue", {})
            .get("PubDate", {})
        )
        year = pubdate.get("Year") or str(pubdate.get("MedlineDate", ""))[:4]

        # Authors (truncate for readability)
        authors_list = []
        for a in article.get("AuthorList", []):
            if "CollectiveName" in a:
                authors_list.append(str(a["CollectiveName"]))
            elif "LastName" in a:
                authors_list.append(f"{a['LastName']} {a.get('Initials', '')}".strip())
        authors = ", ".join(authors_list[:15]) + ("…" if len(authors_list) > 15 else "")

        # DOI (if present)
        doi = ""
        for eid in article.get("ELocationID", []):
            try:
                if eid.attributes.get("EIdType") == "doi":
                    doi = str(eid)
                    break
            except Exception:
                pass

        rows.append(
            {
                "Title": title,
                "PMID": pmid,
                "Year": year,
                "Journal": journal,
                "Authors": authors,
                "DOI": doi,
            }
        )

    df = pd.DataFrame(rows).drop_duplicates(subset=["PMID"])
    # Helpful sort (newest first when possible)
    df["Year_num"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.sort_values(["Year_num", "PMID"], ascending=[False, False]).drop(columns=["Year_num"])
    return df


# -----------------------------
# UI
# -----------------------------
st.sidebar.header("Search settings")

default_query = (
    '("multiple sclerosis"[Title/Abstract] OR "multiple sclerosis"[MeSH Terms]) '
    'AND ("exercise"[Title/Abstract] OR "exercise"[MeSH Terms] OR "physical activity"[Title/Abstract])'
)

query = st.text_input(
    "Search PubMed",
    value=default_query,
    help='Uses PubMed syntax (AND/OR, MeSH Terms, Title/Abstract, etc.).',
)

retmax = st.sidebar.slider(
    "Max results to display",
    min_value=10,
    max_value=200,
    value=50,
    step=10,
)

max_per_minute = st.sidebar.slider(
    "Max searches per minute (per session)",
    min_value=2,
    max_value=20,
    value=6,
    step=1,
)

search = st.button("Search", type="primary")


# -----------------------------
# Run search
# -----------------------------
if search:
    if not allow_search(max_per_minute=int(max_per_minute)):
        st.warning("Too many searches too quickly. Please wait about a minute and try again.")
        st.stop()

    q = normalize_query(query)
    if len(q) < 5:
        st.warning("Please enter a longer query.")
        st.stop()

    with st.spinner("Searching PubMed…"):
        try:
            pmids, total_count = esearch_pmids(q, int(retmax))
        except Exception as e:
            st.error(
                "PubMed search failed. This can happen if NCBI is temporarily busy, "
                "or if the query is malformed."
            )
            st.exception(e)
            st.stop()

    st.success(f"Found {total_count} total matches in PubMed. Displaying up to {len(pmids)}.")

    # Optional tiny delay to reduce burstiness
    time.sleep(0.2)

    with st.spinner("Fetching article details…"):
        try:
            df = efetch_details(pmids)
        except Exception as e:
            st.error(
                "Fetching article details failed. This can happen if NCBI is temporarily busy."
            )
            st.exception(e)
            st.stop()

    st.dataframe(df, use_container_width=True, height=560)

    # Download
    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="pubmed_results_ms_exercise.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Data source: NCBI PubMed via Entrez. This tool provides literature search results only and does not provide medical advice."
)
