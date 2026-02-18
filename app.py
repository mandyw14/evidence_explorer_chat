import os
import time
import hashlib
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
from Bio import Entrez

# -----------------------------
# Server-side NCBI config
# -----------------------------
#Entrez.email = os.getenv("NCBI_EMAIL", "")
#Entrez.api_key = os.getenv("NCBI_API_KEY", None)
#TOOL_NAME = os.getenv("NCBI_TOOL", "BONF_PublicPubMedSearch")  # optional label

ncbi_email = st.secrets.get("NCBI_EMAIL", "")
ncbi_key = st.secrets.get("NCBI_API_KEY", None)
tool_name = st.secrets.get("NCBI_TOOL", "BONF_PublicPubMedSearch")

st.set_page_config(page_title="PubMed Search", layout="wide")
st.title("PubMed Search")
st.caption("Public search interface powered by NCBI PubMed (Entrez)")

if not Entrez.email:
    st.error("Server misconfigured: NCBI_EMAIL is not set.")
    st.stop()

# -----------------------------
# Simple rate limiting (per session)
# -----------------------------
if "last_search_times" not in st.session_state:
    st.session_state.last_search_times = []

def allow_search(max_per_minute=6):
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
# Helpers
# -----------------------------
def normalize_query(q: str) -> str:
    q = (q or "").strip()
    q = " ".join(q.split())  # collapse whitespace
    return q[:500]           # hard cap length

@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)  # cache 6 hours
def esearch_pmids(query: str, retmax: int):
    with Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=retmax,
        usehistory="n",
        tool=TOOL_NAME
    ) as handle:
        res = Entrez.read(handle)
    return res.get("IdList", []), int(res.get("Count", 0))

@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def efetch_details(pmids):
    if not pmids:
        return pd.DataFrame(columns=["PMID", "Year", "Title", "Journal", "Authors"])

    with Entrez.efetch(
        db="pubmed",
        id=",".join(pmids),
        retmode="xml",
        tool=TOOL_NAME
    ) as handle:
        records = Entrez.read(handle)

    rows = []
    for rec in records.get("PubmedArticle", []):
        medline = rec.get("MedlineCitation", {})
        article = medline.get("Article", {})
        pmid = str(medline.get("PMID", ""))

        title = str(article.get("ArticleTitle", "")).strip()
        journal = article.get("Journal", {}).get("Title", "")

        pubdate = (
            article.get("Journal", {})
            .get("JournalIssue", {})
            .get("PubDate", {})
        )
        year = pubdate.get("Year") or str(pubdate.get("MedlineDate", ""))[:4]

        authors_list = []
        for a in article.get("AuthorList", []):
            if "CollectiveName" in a:
                authors_list.append(str(a["CollectiveName"]))
            elif "LastName" in a:
                authors_list.append(f"{a['LastName']} {a.get('Initials','')}".strip())
        authors = ", ".join(authors_list[:15]) + ("…" if len(authors_list) > 15 else "")

        rows.append({"PMID": pmid, "Year": year, "Title": title, "Journal": journal, "Authors": authors})

    df = pd.DataFrame(rows).drop_duplicates(subset=["PMID"])
    return df

# -----------------------------
# UI
# -----------------------------
default_query = '"multiple sclerosis"[Title/Abstract] AND ("exercise"[Title/Abstract] OR "physical activity"[Title/Abstract])'
query = st.text_input("Search PubMed", value=default_query, help="Use PubMed syntax; e.g., MeSH Terms, Title/Abstract, AND/OR.")

retmax = st.slider("Max results to display", 10, 200, 50)

col1, col2 = st.columns([1, 3])
with col1:
    search = st.button("Search", type="primary")
with col2:
    st.caption("Tip: Keep searches specific. Results are cached for performance.")

# -----------------------------
# Execute
# -----------------------------
if search:
    if not allow_search(max_per_minute=6):
        st.warning("Too many searches too quickly. Please wait a minute and try again.")
        st.stop()

    q = normalize_query(query)
    if len(q) < 5:
        st.warning("Please enter a longer query.")
        st.stop()

    with st.spinner("Searching PubMed…"):
        pmids, total_count = esearch_pmids(q, int(retmax))

    st.success(f"Found {total_count} total matches in PubMed. Displaying up to {len(pmids)}.")

    # Small “polite” delay to avoid burst patterns (optional but helpful)
    time.sleep(0.2)

    with st.spinner("Fetching article details…"):
        df = efetch_details(pmids)

    st.dataframe(df, use_container_width=True, height=520)

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="pubmed_results.csv",
        mime="text/csv",
    )

st.caption("Data source: NCBI PubMed via Entrez. Please cite original articles as appropriate.")

