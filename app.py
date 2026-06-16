# app.py
# Public-facing PubMed search for Streamlit Community Cloud
# Includes evidence snapshot + persistent results + chatbot.

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import quote_plus
import re
import time
import pandas as pd
import streamlit as st
from Bio import Entrez
from openai import OpenAI

from dictionaries import (
    COMMON_CONDITIONS,
    INTERVENTION_CATEGORIES,
)

st.set_page_config(page_title="PubMed Search Tool", layout="wide")
st.title("Evidence Explorer -- explore treatments for neurological conditions that go beyound pharma.")
st.caption("powered by PubMed (Entrez)")
st.caption(
    "This search is being conducted on journal articles indexed in the National Library of Medicine, "
    "PubMed. PubMed® comprises more than 39 million citations for biomedical literature from MEDLINE, "
    "life science journals, and online books."
)
st.caption(
    "This search prioritizes human clinical studies, clinical trials, reviews, and evidence syntheses "
    "published in English within the selected date range."
)
st.caption("Developed by Mandy Wintink, Ph.D., Research Director at Branch Out Neurological Foundation")


# -----------------------------
# Secrets / credentials
# -----------------------------
NCBI_EMAIL = st.secrets.get("NCBI_EMAIL", "")
NCBI_API_KEY = st.secrets.get("NCBI_API_KEY", None)
NCBI_TOOL = st.secrets.get("NCBI_TOOL", "BONF_PublicPubMedSearch")
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

Entrez.email = NCBI_EMAIL
Entrez.api_key = NCBI_API_KEY

if not Entrez.email:
    st.error("Missing NCBI_EMAIL in Streamlit secrets.")
    st.stop()

if not OPENAI_API_KEY:
    st.warning(
        "OPENAI_API_KEY is missing. PubMed search will work, but evidence snapshot and chatbot will not."
    )

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# -----------------------------
# Session state
# -----------------------------
if "last_search_times" not in st.session_state:
    st.session_state.last_search_times = []

if "pubmed_chat_messages" not in st.session_state:
    st.session_state.pubmed_chat_messages = []

if "pubmed_results_df" not in st.session_state:
    st.session_state.pubmed_results_df = pd.DataFrame()

if "evidence_snapshot" not in st.session_state:
    st.session_state.evidence_snapshot = ""

if "last_query" not in st.session_state:
    st.session_state.last_query = ""


# -----------------------------
# Utilities
# -----------------------------
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


def normalize_query(q: str) -> str:
    q = (q or "").strip()
    q = re.sub(r"\s+", " ", q)
    return q[:1000]


def clean_filename(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "pubmed_results"


def build_pubmed_query(condition: str, interventions: list[str], years_back: int = 10) -> str:
    condition = condition.strip()
    condition_block = f'("{condition}"[Title/Abstract] OR "{condition}"[MeSH Terms])'

    intervention_terms = []
    for item in interventions:
        intervention_terms.append(f'"{item}"[MeSH Terms]')
        intervention_terms.append(f'"{item}"[Title/Abstract]')

    intervention_block = "(" + " OR ".join(intervention_terms) + ")"

    filter_block = (
        f'((y_{years_back}[Filter]) AND '
        f'(clinicalstudy[Filter] OR clinicaltrial[Filter] OR meta-analysis[Filter] '
        f'OR randomizedcontrolledtrial[Filter] OR review[Filter] OR scopingreview[Filter] '
        f'OR systematicreview[Filter] OR validationstudy[Filter]) AND '
        f'(humans[Filter]) AND (english[Filter]))'
    )

    return f"{condition_block} AND {intervention_block} AND {filter_block}"


def build_pubmed_search_url(query: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/?term={quote_plus(query)}"


def get_abstract_text(article: dict) -> str:
    abstract = article.get("Abstract", {})
    abstract_text_items = abstract.get("AbstractText", [])

    if not abstract_text_items:
        return ""

    parts = []

    for item in abstract_text_items:
        try:
            label = item.attributes.get("Label", "")
        except Exception:
            label = ""

        text = str(item).strip()

        if not text:
            continue

        if label:
            parts.append(f"{label}: {text}")
        else:
            parts.append(text)

    return "\n\n".join(parts).strip()


def summarize_pubmed_results(results_df: pd.DataFrame, client: OpenAI) -> str:
    context_df = results_df.head(25).copy()

    article_context = context_df[
        [
            "Title",
            "Year",
            "Journal",
            "Authors",
            "PMID",
            "PMID_URL",
            "DOI",
            "DOI_URL",
            "Abstract",
        ]
    ].to_markdown(index=False)

    system_prompt = f"""
You are an evidence summary assistant.

Summarize ONLY the PubMed records provided below.

Strict rules:
- Do not use outside knowledge.
- Do not mention articles not included in the provided records.
- Do not make medical recommendations.
- Do not invent findings, methods, populations, authors, dates, journals, DOIs, or links.
- If there are few records or limited abstracts, say so clearly.
- Base the summary only on titles and abstracts.
- Include PMID or DOI links when useful.

Write a concise evidence snapshot with this structure:

### Evidence Snapshot
Briefly summarize what the returned articles appear to cover.

### Main themes
List 3–5 themes across the abstracts.

### What the evidence seems to suggest
Use cautious language.

### Limitations of this search
Mention limits such as number of returned records, missing abstracts, or narrow search terms.

### Example articles
List 3–5 relevant articles with links.

Returned PubMed records:
{article_context}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Create an evidence snapshot of these returned PubMed records.",
            },
        ],
    )

    return response.choices[0].message.content


# -----------------------------
# Entrez calls
# -----------------------------
@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def esearch_pmids(query: str, retmax: int) -> tuple[list[str], int]:
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
    if not pmids:
        return pd.DataFrame(
            columns=[
                "Title",
                "Year",
                "Journal",
                "Authors",
                "PMID",
                "PMID_URL",
                "DOI",
                "DOI_URL",
                "Abstract",
            ]
        )

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
                authors_list.append(
                    f"{a['LastName']} {a.get('Initials', '')}".strip()
                )

        authors = ", ".join(authors_list[:15]) + (
            "…" if len(authors_list) > 15 else ""
        )

        doi = ""

        for eid in article.get("ELocationID", []):
            try:
                if eid.attributes.get("EIdType") == "doi":
                    doi = str(eid)
                    break
            except Exception:
                pass

        abstract_text = get_abstract_text(article)

        doi_url = f"https://doi.org/{doi}" if doi else ""
        pmid_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

        rows.append(
            {
                "Title": title,
                "Year": year,
                "Journal": journal,
                "Authors": authors,
                "PMID": pmid,
                "PMID_URL": pmid_url,
                "DOI": doi,
                "DOI_URL": doi_url,
                "Abstract": abstract_text,
            }
        )

    df = pd.DataFrame(rows).drop_duplicates(subset=["PMID"])
    df["Year_num"] = pd.to_numeric(df["Year"], errors="coerce")
    df = (
        df.sort_values(["Year_num", "PMID"], ascending=[False, False])
        .drop(columns=["Year_num"])
    )

    return df


# -----------------------------
# UI controls
# -----------------------------
st.sidebar.header("Search settings")

mode = st.radio(
    "Search mode",
    ["Simple", "Advanced"],
    horizontal=True,
    help="Simple mode uses friendly menus only. Advanced mode lets you add custom terms or edit the full PubMed query.",
)

options=COMMON_CONDITIONS

selected_condition = st.selectbox(
    "Choose a neurological condition",
    options=COMMON_CONDITIONS,
    index=0,
)

if selected_condition == "Other / type your own":
    condition = st.text_input(
        "Type your neurological condition",
        value="",
        help="Enter any neurological condition you would like to search.",
    )
else:
    condition = selected_condition

category_names = list(INTERVENTION_CATEGORIES.keys())

selected_category = st.selectbox(
    "Choose an intervention category",
    options=category_names,
    index=0,
)

default_interventions = INTERVENTION_CATEGORIES[selected_category][:2]



interventions = st.multiselect(
    "Choose intervention term(s)",
    options=INTERVENTION_CATEGORIES[selected_category],
    default=default_interventions,
)

retmax = st.sidebar.slider(
    "Max results to display",
    min_value=10,
    max_value=200,
    value=50,
    step=10,
)

max_per_minute = st.sidebar.slider(
    "Max searches per minute",
    min_value=2,
    max_value=20,
    value=6,
    step=1,
)

years_back = st.sidebar.slider(
    "Years back",
    min_value=1,
    max_value=20,
    value=10,
    step=1,
)

auto_query = (
    build_pubmed_query(condition, interventions, years_back=years_back)
    if condition.strip()
    else ""
)

if mode == "Advanced":
    st.subheader("Advanced query builder")

    user_terms = st.text_input(
        "Add your own search terms",
        value="",
        help="Example: fatigue, cognition, inflammation, microbiome, sleep, quality of life",
    )

    use_auto_query = st.checkbox(
        "Include the selected condition and intervention filters",
        value=True,
    )

    extra_terms = normalize_query(user_terms)

    if use_auto_query:
        if extra_terms:
            query = f"{auto_query} AND ({extra_terms})"
        else:
            query = auto_query
    else:
        query = extra_terms

    st.caption("Final PubMed query")
    st.code(query, language="text")

    with st.expander("Edit full PubMed query manually"):
        query = st.text_area(
            "PubMed query",
            value=query,
            height=180,
        )

else:
    query = auto_query
    st.subheader("Search summary")
    st.write(f"**Condition:** {condition if condition else 'Not selected'}")
    st.write(f"**Intervention category:** {selected_category}")
    st.write(
        f"**Intervention term(s):** {', '.join(interventions) if interventions else 'None selected'}"
    )
    st.write(f"**Date filter:** Past {years_back} years")

    with st.expander("Preview generated PubMed query"):
        st.code(query, language="text")

search = st.button("Search", type="primary")


# -----------------------------
# Run search and save to session
# -----------------------------
if search:
    if not condition.strip() and mode == "Simple":
        st.warning("Please choose or enter a neurological condition.")
        st.stop()

    if not interventions and mode == "Simple":
        st.warning("Please select at least one intervention term.")
        st.stop()

    if mode == "Advanced" and not normalize_query(query):
        st.warning("Please enter search terms or include the selected filters.")
        st.stop()

    if not allow_search(max_per_minute=int(max_per_minute)):
        st.warning("Too many searches too quickly. Please wait about a minute and try again.")
        st.stop()

    q = normalize_query(query)

    if len(q) < 5:
        st.warning("Please enter a longer query.")
        st.stop()

    st.session_state.last_query = q
    pubmed_search_url = build_pubmed_search_url(q)

    with st.spinner("Searching PubMed…"):
        try:
            pmids, total_count = esearch_pmids(q, int(retmax))
        except Exception as e:
            st.error("PubMed search failed.")
            st.exception(e)
            st.stop()

    st.success(
        f"Found {total_count} total matches in PubMed. Displaying up to {len(pmids)}."
    )
    st.link_button("Open in PubMed Search", pubmed_search_url)

    time.sleep(0.2)

    with st.spinner("Fetching article details…"):
        try:
            df = efetch_details(pmids)
        except Exception as e:
            st.error("Fetching article details failed.")
            st.exception(e)
            st.stop()

    st.session_state.pubmed_results_df = df
    st.session_state.pubmed_chat_messages = []
    st.session_state.evidence_snapshot = ""

    if client is not None and not df.empty:
        with st.spinner("Creating evidence snapshot…"):
            st.session_state.evidence_snapshot = summarize_pubmed_results(df, client)


# -----------------------------
# Display saved search results
# -----------------------------
results_df = st.session_state.get("pubmed_results_df", pd.DataFrame())

if not results_df.empty:

    if st.session_state.get("evidence_snapshot"):
        st.subheader("Evidence Snapshot")
        st.markdown(st.session_state.evidence_snapshot)

    st.subheader("Abstract Previews")
    st.caption("Showing up to 10 abstracts from the returned PubMed results.")

    preview_df = results_df.head(10)

    for _, row in preview_df.iterrows():
        expander_title = f"{row['Year']} — {row['Title']}"

        with st.expander(expander_title):
            st.markdown(f"**Journal:** {row['Journal']}")
            st.markdown(f"**Authors:** {row['Authors']}")

            if row.get("PMID"):
                st.markdown(f"**PMID:** [{row['PMID']}]({row['PMID_URL']})")

            if row.get("DOI"):
                st.markdown(f"**DOI:** [{row['DOI']}]({row['DOI_URL']})")

            abstract_text = row.get("Abstract", "")

            if abstract_text:
                st.markdown("**Abstract**")
                st.write(abstract_text)
            else:
                st.caption("No abstract available in the PubMed record.")

    st.subheader("Save your Results")
    st.caption("You can download your search results into a file so you can come back and read/review them at a later time.")

    file_stub = clean_filename(st.session_state.get("last_query", "pubmed_results"))

    st.download_button(
        "Download your results",
        data=results_df.drop(columns=["PMID_URL", "DOI_URL"], errors="ignore")
        .to_csv(index=False)
        .encode("utf-8"),
        file_name=f"{file_stub}.csv",
        mime="text/csv",
    )


# -----------------------------
# Chatbot
# -----------------------------
st.subheader("Chat with these PubMed results")

if results_df.empty:
    st.info("Run a PubMed search first, then you can chat with the returned results.")
elif client is None:
    st.warning("Add OPENAI_API_KEY to Streamlit secrets to enable the chatbot.")
else:
    st.caption("The chatbot answers only from the PubMed records returned by your search.")

    for message in st.session_state.pubmed_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input("Ask about the returned PubMed results...")

    if user_question:
        st.session_state.pubmed_chat_messages.append(
            {"role": "user", "content": user_question}
        )

        with st.chat_message("user"):
            st.markdown(user_question)

        context_df = results_df.head(25).copy()

        article_context = context_df[
            [
                "Title",
                "Year",
                "Journal",
                "Authors",
                "PMID",
                "PMID_URL",
                "DOI",
                "DOI_URL",
                "Abstract",
            ]
        ].to_markdown(index=False)

        system_prompt = f"""
You are a PubMed results assistant.

You must answer ONLY using the PubMed records provided below.

Strict rules:
- Do not use outside knowledge.
- Do not mention articles that are not in the returned PubMed results.
- Do not make medical recommendations.
- Do not invent findings, methods, populations, dates, journals, authors, DOIs, or links.
- If the returned results do not contain enough information, say so.
- If only a few relevant articles are present, say so clearly.
- When summarizing articles, state: "This summary is based on the PubMed abstract."
- Only use article links that are provided in the returned results.

You may:
- Summarize abstracts.
- Compare papers in the returned results.
- Define general terms briefly, but label them as "General definition."
- Identify themes, gaps, or limitations based only on the returned abstracts.

When citing papers, include:
- Title
- Year
- Authors if available
- PMID link or DOI link if available

Evidence snapshot already shown to the user:
{st.session_state.get("evidence_snapshot", "")}

Returned PubMed results:
{article_context}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            *[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.pubmed_chat_messages
            ],
        ]

        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
            )

            response = st.write_stream(stream)

        st.session_state.pubmed_chat_messages.append(
            {"role": "assistant", "content": response}
        )


st.divider()
st.caption(
    "Data source: NCBI PubMed via Entrez. This tool provides literature search results only and does not provide medical advice."
)
