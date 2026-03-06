# app.py
# Public-facing PubMed search for Streamlit Community Cloud
# Users can choose a neurological condition and intervention category,
# and the app builds the PubMed query automatically.
# Includes Simple vs Advanced mode, clickable PMID/DOI links,
# Open in PubMed button, and abstract preview expanders.

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import quote_plus
import re
import time
import pandas as pd
import streamlit as st
from Bio import Entrez


# -----------------------------
# Streamlit page config
# -----------------------------
st.set_page_config(page_title="PubMed Search Tool", layout="wide")
st.title("PubMed Search Tool")
st.caption("Public search interface powered by NCBI PubMed (Entrez)")
st.caption("Developed by Branch Out Neurological Foundation")
st.caption(
    "This search is being conducted on journal articles indexed in the National Library of Medicine, "
    "PubMed. PubMed® comprises more than 39 million citations for biomedical literature from MEDLINE, "
    "life science journals, and online books. Citations may include links to full text content from "
    "PubMed Central and publisher web sites."
)
st.caption(
    "This search prioritizes human clinical studies, clinical trials, reviews, and evidence syntheses "
    "published in English within the past 10 years."
)


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
    q = (q or "").strip()
    q = re.sub(r"\s+", " ", q)
    return q[:1000]


def clean_filename(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "neurological_condition"


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
    """
    Extract abstract text from PubMed article structure.
    Handles both plain strings and labeled abstract sections.
    """
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


# -----------------------------
# Entrez calls (cached)
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
                "Title", "Year", "Journal", "Authors",
                "PMID", "PMID_URL", "DOI", "DOI_URL", "Abstract"
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
                authors_list.append(f"{a['LastName']} {a.get('Initials', '')}".strip())
        authors = ", ".join(authors_list[:15]) + ("…" if len(authors_list) > 15 else "")

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
    df = df.sort_values(["Year_num", "PMID"], ascending=[False, False]).drop(columns=["Year_num"])
    return df


# -----------------------------
# UI
# -----------------------------
st.sidebar.header("Search settings")

mode = st.radio(
    "Search mode",
    ["Simple", "Advanced"],
    horizontal=True,
    help="Simple mode uses friendly menus only. Advanced mode lets you edit the full PubMed query."
)

common_conditions = [
    "multiple sclerosis",
    "Parkinson disease",
    "Alzheimer disease",
    "dementia",
    "epilepsy",
    "migraine",
    "stroke",
    "traumatic brain injury",
    "concussion",
    "autism spectrum disorder",
    "ADHD",
    "depression",
    "anxiety",
    "chronic pain",
    "neuropathy",
    "amyotrophic lateral sclerosis",
    "Huntington disease",
    "cerebral palsy",
    "spinal cord injury",
    "Other / type your own",
]

selected_condition = st.selectbox(
    "Choose a neurological condition",
    options=common_conditions,
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

intervention_categories = {
    "Mind-body": [
        "exercise",
        "physical activity",
        "mindfulness",
        "meditation",
        "yoga",
        "tai chi",
        "qigong",
        "pilates",
        "cognitive behavioral therapy",
        "CBT",
        "psychotherapy",
        "behavior therapy",
        "stress management",
        "relaxation therapy",
        "acceptance and commitment therapy",
        "sleep intervention",
        "sleep hygiene",
        "fatigue management",
        "acupuncture",
        "massage",
        "music therapy",
        "art therapy",
        "occupational therapy",
        "physiotherapy",
        "rehabilitation",
    ],
    "Nutraceuticals / diet": [
        "diet",
        "nutrition",
        "ketogenic diet",
        "Mediterranean diet",
        "probiotics",
        "prebiotics",
        "omega-3",
        "vitamin D",
        "magnesium",
        "creatine",
        "curcumin",
        "supplements",
        "fecal transplants",
        "psilocybin",
        "mushrooms",
        "ibogaine",
    ],
    "Neurotechnology": [
        "transcranial magnetic stimulation",
        "transcranial direct current stimulation",
        "focused ultrasound",
        "neurofeedback",
        "biofeedback",
        "vagus nerve stimulation",
        "functional electrical stimulation",
        "virtual reality therapy",
        "augmented reality therapy",
    ],
}

category_names = list(intervention_categories.keys())

selected_category = st.selectbox(
    "Choose an intervention category",
    options=category_names,
    index=0,
)

default_interventions = intervention_categories[selected_category][:2]

interventions = st.multiselect(
    "Choose intervention term(s) from the drop-down menu",
    options=intervention_categories[selected_category],
    default=default_interventions,
    help="Choose one or more intervention terms to include in the search.",
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

years_back = st.sidebar.slider(
    "Years back",
    min_value=1,
    max_value=20,
    value=10,
    step=1,
)

auto_query = build_pubmed_query(condition, interventions, years_back=years_back) if condition.strip() else ""

if mode == "Advanced":
    st.subheader("Advanced query editor")
    query = st.text_area(
        "PubMed query",
        value=auto_query,
        height=180,
        help="Edit the automatically generated PubMed query before searching.",
    )
    st.caption("You can directly customize PubMed syntax here.")
else:
    query = auto_query
    st.subheader("Search summary")
    st.write(f"**Condition:** {condition if condition else 'Not selected'}")
    st.write(f"**Intervention category:** {selected_category}")
    st.write(f"**Intervention term(s):** {', '.join(interventions) if interventions else 'None selected'}")
    st.write(f"**Date filter:** Past {years_back} years")
    with st.expander("Preview generated PubMed query"):
        st.code(query, language="text")

search = st.button("Search", type="primary")


# -----------------------------
# Run search
# -----------------------------
if search:
    if not condition.strip():
        st.warning("Please choose or enter a neurological condition.")
        st.stop()

    if not interventions:
        st.warning("Please select at least one intervention term.")
        st.stop()

    if not allow_search(max_per_minute=int(max_per_minute)):
        st.warning("Too many searches too quickly. Please wait about a minute and try again.")
        st.stop()

    q = normalize_query(query)
    if len(q) < 5:
        st.warning("Please enter a longer query.")
        st.stop()

    pubmed_search_url = build_pubmed_search_url(q)

    with st.spinner("Searching PubMed…"):
        try:
            pmids, total_count = esearch_pmids(q, int(retmax))
        except Exception as e:
            st.error(
                "PubMed search failed. This can happen if NCBI is temporarily busy, or if the query is malformed."
            )
            st.exception(e)
            st.stop()

    st.success(
        f'Found {total_count} total matches in PubMed for "{condition}" and the selected intervention(s). '
        f"Displaying up to {len(pmids)}."
    )

    st.link_button("Open in PubMed Search", pubmed_search_url)

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

    display_df = df.copy()

    st.dataframe(
        display_df,
        use_container_width=True,
        height=560,
        column_config={
            "PMID_URL": st.column_config.LinkColumn(
                "PMID",
                help="Open PubMed record",
                display_text=r"https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/",
            ),
            "DOI_URL": st.column_config.LinkColumn(
                "DOI",
                help="Open article DOI link",
                display_text=r"https://doi\.org/(.*)",
            ),
        },
        column_order=["Title", "Year", "Journal", "Authors", "PMID_URL", "DOI_URL"],
        hide_index=True,
    )

    st.subheader("Abstract previews")

    if df.empty:
        st.info("No records found.")
    else:
        for _, row in df.iterrows():
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

    filename_condition = clean_filename(condition)
    filename_category = clean_filename(selected_category)
    st.download_button(
        "Download CSV",
        data=df.drop(columns=["PMID_URL", "DOI_URL"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name=f"pubmed_results_{filename_condition}_{filename_category}.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Data source: NCBI PubMed via Entrez. This tool provides literature search results only and does not provide medical advice."
)
