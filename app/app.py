# import sys
# from pathlib import Path

# PROJECT_ROOT = Path(__file__).resolve().parents[1]
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))

# import json
# import time
# import streamlit as st

# from rag.retriever import retrieve_top_k
# from rag.citations import build_context_with_citations, citations_to_ui_lines

# from app.prompts import SYSTEM_BASE, explain_prompt, extract_prompt, qa_prompt
# from app.generate import generate_text
# from app.context import ChatTurn, trim_history, history_to_messages
# from app.guards import (
#     validate_report_input,
#     validate_question_input,
#     validate_retrieval_results,
#     enforce_disclaimer,
# )

# st.set_page_config(page_title="DocDecode - Radiology Report Copilot", layout="wide")

# SAMPLE_REPORT = """CHEST X-RAY (PA AND LATERAL)
# CLINICAL HISTORY: Shortness of breath.

# FINDINGS: Mild patchy opacity in the right lower lung. No pleural effusion. No pneumothorax.
# Cardiomediastinal silhouette is within normal limits.

# IMPRESSION: Mild right lower lobe opacity may represent atelectasis versus early infection. Correlate clinically.
# """


# def parse_json_response(answer: str):
#     """
#     Safely extract JSON from the model response.

#     Handles:
#     1. Pure JSON
#     2. JSON inside ```json ... ``` markdown
#     3. JSON surrounded by extra text
#     """
#     answer = answer.strip()

#     # Case 1: model returned pure JSON
#     try:
#         return json.loads(answer)
#     except json.JSONDecodeError:
#         pass

#     # Case 2: JSON inside a Markdown code block
#     if "```" in answer:
#         cleaned = answer.replace("```json", "").replace("```JSON", "")
#         cleaned = cleaned.replace("```", "").strip()

#         try:
#             return json.loads(cleaned)
#         except json.JSONDecodeError:
#             pass

#     # Case 3: find the JSON object inside extra text
#     start = answer.find("{")
#     end = answer.rfind("}")

#     if start != -1 and end != -1 and start < end:
#         json_text = answer[start:end + 1]

#         try:
#             return json.loads(json_text)
#         except json.JSONDecodeError:
#             pass

#     return None


# def show_citations(citation_lines, citations):
#     with st.expander("Show citations / sources"):
#         for line in citation_lines:
#             st.write(line)
#         st.markdown("---")
#         for c in citations:
#             st.markdown(f"**[{c.cid}] {c.source} - page {c.page}** (score: {c.score:.3f})")
#             st.caption(c.snippet)


# def ensure_session_state():
#     if "chat_history" not in st.session_state:
#         st.session_state.chat_history = []
#     if "report_text" not in st.session_state:
#         st.session_state.report_text = ""
#     if "pending_question" not in st.session_state:
#         st.session_state.pending_question = None


# def main():
#     ensure_session_state()

#     # Header 
#     c1, c2 = st.columns([0.07, 0.93], vertical_alignment="center")

#     with c1:
#         st.image(str(PROJECT_ROOT / "docs" / "logo.png"), width=60)

#     with c2:
#         st.markdown(
#             """
#             <div style="display:flex; align-items:center;">
#                 <span style="font-size:40px; font-weight:900; color:#2E86C1;">
#                     DocDecode
#                 </span>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )

#     st.markdown(
#         "<i><b>Confused by radiology jargon? DocDecode is here to explain!</b></i>",
#         unsafe_allow_html=True,
#     )
#     st.caption("Only explanations with citations. Not medical advice.")

#     col_left, col_right = st.columns([1, 2], gap="large")

#     # LEFT: input panel
#     with col_left:
#         st.subheader("Input Radiology Report")

#         st.session_state.report_text = st.text_area(
#             "Paste a radiology report here:",
#             value=st.session_state.report_text,
#             height=260,
#         )

#         c1, c2 = st.columns(2)
#         with c1:
#             if st.button("Load Sample Report"):
#                 st.session_state.report_text = SAMPLE_REPORT
#                 st.rerun()
#         with c2:
#             if st.button("Reset"):
#                 st.session_state.report_text = ""
#                 st.session_state.chat_history = []
#                 st.rerun()

#         ok, err = validate_report_input(st.session_state.report_text)
#         if not ok:
#             st.warning(err)

#         st.markdown("---")

#         with st.expander("Advanced: Retrieval Settings (ChromaDB)", expanded=False):
#             st.caption(
#                 "These settings control how many reference chunks are retrieved and how strict the filtering is. "
#                 "Higher min score = stricter evidence quality."
#             )
#             top_k = st.slider("Top-K retrieved chunks", 6, 20, 12, 1)
#             min_score = st.slider("Min similarity score", 0.30, 0.80, 0.50, 0.01)
#             final_top_k = st.slider("Final chunks used in prompt", 2, 10, 6, 1)

#     # RIGHT: tabs
#     with col_right:
#         tabs = st.tabs(["Explain", "Extract", "Evidence Q&A"])

#         # TAB 1: Explain 
#         with tabs[0]:
#             st.subheader("Explain the report")
#             level = st.selectbox("Explanation level", ["simple", "normal", "clinician"], index=1)

#             if st.button("Generate Explanation"):
#                 ok, err = validate_report_input(st.session_state.report_text)
#                 if not ok:
#                     st.error(err)
#                 else:
#                     with st.spinner("Retrieving evidence and generating explanation..."):
#                         t0 = time.time()
#                         retrieved = retrieve_top_k(
#                             query=f"Explain terms and phrases in this report: {st.session_state.report_text[:300]}",
#                             top_k=top_k,
#                             min_score=min_score,
#                             final_top_k=final_top_k,
#                         )

#                         top_score = max([r.get("score", 0) for r in retrieved], default=0)
#                         chunks_used = len(retrieved)

#                         context_block, citations = build_context_with_citations(retrieved)
#                         user_prompt = explain_prompt(level, st.session_state.report_text, context_block)
#                         answer = generate_text(SYSTEM_BASE, user_prompt)
#                         answer = enforce_disclaimer(answer)
#                         t1 = time.time()

#                     lat = t1 - t0
#                     st.success(f"Done in {lat:.2f}s")
#                     st.caption(f"Run stats: **{chunks_used} chunks used** | **top score {top_score:.3f}**")

#                     with st.container(border=True):
#                         st.markdown("### Explanation in Plain English")
#                         st.write(answer)

#                     citation_lines = citations_to_ui_lines(citations)
#                     show_citations(citation_lines, citations)

#         # TAB 2: Extract 
#         with tabs[1]:
#             st.subheader("Extract structured information (JSON)")
#             if st.button("Extract Fields"):
#                 ok, err = validate_report_input(st.session_state.report_text)
#                 if not ok:
#                     st.error(err)
#                 else:
#                     with st.spinner("Extracting..."):
#                         t0 = time.time()
#                         user_prompt = extract_prompt(st.session_state.report_text)
#                         answer = generate_text(SYSTEM_BASE, user_prompt)
#                         t1 = time.time()

#                     st.success(f"Done in {t1 - t0:.2f}s")

#                     # -----------------------------------------
#                     # Parse and display JSON
#                     # -----------------------------------------
#                     parsed = parse_json_response(answer)

#                     if parsed is None:
#                         st.warning(
#                             "Model did not return valid JSON. Showing raw output:"
#                         )
#                         st.code(answer, language="text")

#                     else:
#                         # Show complete JSON
#                         st.json(parsed)

#                         # -----------------------------------------
#                         # Findings
#                         # -----------------------------------------
#                         findings = parsed.get("findings", [])

#                         if findings:
#                             with st.container(border=True):
#                                 st.markdown("### Findings")

#                                 if isinstance(findings, list):
#                                     st.table({"findings": findings})
#                                 else:
#                                     st.write(findings)

#                         # -----------------------------------------
#                         # Impression
#                         # -----------------------------------------
#                         impression = parsed.get("impression", [])

#                         if impression:
#                             with st.container(border=True):
#                                 st.markdown("### Impression")

#                                 if isinstance(impression, list):
#                                     st.table({"impression": impression})
#                                 else:
#                                     st.write(impression)

#                         # -----------------------------------------
#                         # Key Terms
#                         # -----------------------------------------
#                         key_terms = parsed.get("key_terms", [])

#                         if key_terms:
#                             with st.container(border=True):
#                                 st.markdown("### Key Terms")

#                                 if isinstance(key_terms, list):
#                                     st.write(
#                                         " • ".join(
#                                             str(term)
#                                             for term in key_terms[:25]
#                                         )
#                                     )
#                                 else:
#                                     st.write(key_terms)

#                         # -----------------------------------------
#                         # Uncertainty / Hedging
#                         # -----------------------------------------
#                         uncertainty = parsed.get("uncertainty_phrases", [])

#                         if uncertainty:
#                             with st.container(border=True):
#                                 st.markdown("### Uncertainty / Hedging")

#                                 if isinstance(uncertainty, list):
#                                     st.table({
#                                         "uncertainty": uncertainty
#                                     })
#                                 else:
#                                     st.write(uncertainty)

#                         # -----------------------------------------
#                         # Critical Flags
#                         # -----------------------------------------
#                         critical_flags = parsed.get("critical_flags", [])

#                         if critical_flags:
#                             with st.container(border=True):
#                                 st.markdown("### Critical Flags")

#                                 if isinstance(critical_flags, list):
#                                     st.table({
#                                         "critical_flags": critical_flags
#                                     })
#                                 else:
#                                     st.write(critical_flags)

#                         # -----------------------------------------
#                         # Recommended Follow-up
#                         # -----------------------------------------
#                         followup = parsed.get(
#                             "recommended_followup_in_report",
#                             []
#                         )

#                         if followup:
#                             with st.container(border=True):
#                                 st.markdown("### Recommended Follow-up")

#                                 if isinstance(followup, list):
#                                     st.table({
#                                         "follow-up": followup
#                                     })
#                                 else:
#                                     st.write(followup)

#         # TAB 3: Evidence Q&A 
#         with tabs[2]:
#             st.subheader("Ask questions (answers must cite sources)")

#             # Display history
#             for turn in st.session_state.chat_history:
#                 with st.chat_message(turn.role):
#                     st.write(turn.content)

#             st.markdown("#### Suggested questions")
#             sq1, sq2, sq3 = st.columns(3)

#             # Suggested questions --> store in session
#             with sq1:
#                 if st.button("Explain the impression"):
#                     st.session_state.pending_question = "Explain the impression in simple terms."
#             with sq2:
#                 if st.button("Is anything urgent?"):
#                     st.session_state.pending_question = "Is there anything urgent or concerning in this report?"
#             with sq3:
#                 if st.button("Define key terms"):
#                     st.session_state.pending_question = "Define key terms mentioned in this report (e.g., opacity, atelectasis, effusion)."

#             question = st.session_state.pending_question or st.chat_input("Ask a question about the report...")

#             # If the question came from a suggested button, clear it after consuming
#             if st.session_state.pending_question is not None and question == st.session_state.pending_question:
#                 st.session_state.pending_question = None

#             if question is not None:
#                 ok_r, err_r = validate_report_input(st.session_state.report_text)
#                 ok_q, err_q = validate_question_input(question)

#                 if not ok_r:
#                     st.error(err_r)
#                     return
#                 if not ok_q:
#                     st.error(err_q)
#                     return

#                 # Add user message to chat
#                 st.session_state.chat_history.append(ChatTurn(role="user", content=question))
#                 with st.chat_message("user"):
#                     st.write(question)

#                 with st.spinner("Retrieving evidence + answering..."):
#                     t0 = time.time()
#                     retrieved = retrieve_top_k(
#                         query=question,
#                         top_k=top_k,
#                         min_score=min_score,
#                         final_top_k=final_top_k,
#                     )

#                     # -----------------------------------------
#                     # Evidence handling
#                     # -----------------------------------------
#                     # The radiology report itself is always available
#                     # and is the primary source for report-specific
#                     # questions. ChromaDB evidence is supporting context.
#                     #
#                     # If enough evidence is retrieved, use it.
#                     # If evidence is insufficient, continue with the
#                     # report text instead of stopping before the LLM.
#                     ok_ev, err_ev = validate_retrieval_results(
#                         retrieved,
#                         min_results=2
#                     )

#                     if ok_ev:
#                         context_block, citations = build_context_with_citations(
#                             retrieved
#                         )
#                         evidence_status = "with retrieved evidence"
#                     else:
#                         context_block = (
#                             "No sufficient external knowledge-base evidence "
#                             "was retrieved for this question. "
#                             "Answer using the REPORT TEXT only. "
#                             "Do not invent or add unsupported facts."
#                         )
#                         citations = []
#                         evidence_status = "using report text only"

#                     user_prompt = qa_prompt(
#                         question,
#                         st.session_state.report_text,
#                         context_block
#                     )

#                     # Context management: include last N turns
#                     trimmed = trim_history(st.session_state.chat_history[:-1], max_turns=6)
#                     history_msgs = history_to_messages(trimmed)

#                     assistant_reply = generate_text(SYSTEM_BASE, user_prompt, history_messages=history_msgs)
#                     assistant_reply = enforce_disclaimer(assistant_reply)
#                     t1 = time.time()

#                 with st.chat_message("assistant"):
#                     st.write(assistant_reply)

#                 st.session_state.chat_history.append(ChatTurn(role="assistant", content=assistant_reply))
#                 st.info(
#                     f"Done in {t1 - t0:.2f}s ({evidence_status})"
#                 )

#                 citation_lines = citations_to_ui_lines(citations)

#                 with st.expander("Top evidence snippets (preview)", expanded=False):
#                     for c in citations[:3]:
#                         with st.container(border=True):
#                             st.markdown(f"**[{c.cid}] {c.source} — page {c.page}** (score: {c.score:.3f})")
#                             st.caption(c.snippet)
                        
#                 show_citations(citation_lines, citations)


# if __name__ == "__main__":
#     main()





import sys
from pathlib import Path
import json
import time
import streamlit as st
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.retriever import retrieve_top_k
from rag.citations import build_context_with_citations, citations_to_ui_lines
from app.prompts import SYSTEM_BASE, explain_prompt, extract_prompt, qa_prompt
from app.generate import generate_text
from app.context import ChatTurn, trim_history, history_to_messages
from app.guards import (
    validate_report_input,
    validate_question_input,
    validate_retrieval_results,
    enforce_disclaimer,
)

st.set_page_config(
    page_title="DocDecode - Radiology Report Copilot",
    layout="wide"
)


def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)

    pages_text = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages_text.append(text)

    return "\n\n".join(pages_text).strip()


SAMPLE_REPORT = """CHEST X-RAY (PA AND LATERAL)

CLINICAL HISTORY: Shortness of breath.

FINDINGS: Mild patchy opacity in the right lower lung. No pleural effusion. No pneumothorax.

Cardiomediastinal silhouette is within normal limits.

IMPRESSION: Mild right lower lobe opacity may represent atelectasis versus early infection. Correlate clinically.
"""


def parse_json_response(answer: str):
    answer = answer.strip()

    try:
        return json.loads(answer)
    except json.JSONDecodeError:
        pass

    if "```" in answer:
        cleaned = answer.replace("```json", "").replace("```JSON", "")
        cleaned = cleaned.replace("```", "").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    start = answer.find("{")
    end = answer.rfind("}")

    if start != -1 and end != -1 and start < end:
        json_text = answer[start:end + 1]

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    return None


def show_citations(citation_lines, citations):
    with st.expander("Show citations / sources"):
        for line in citation_lines:
            st.write(line)

        st.markdown("---")

        for c in citations:
            st.markdown(
                f"**[{c.cid}] {c.source} - page {c.page}** "
                f"(score: {c.score:.3f})"
            )
            st.caption(c.snippet)


def ensure_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "report_text" not in st.session_state:
        st.session_state.report_text = ""

    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None

    if "uploaded_pdf_signature" not in st.session_state:
        st.session_state.uploaded_pdf_signature = None


def main():
    ensure_session_state()

    c1, c2 = st.columns(
        [0.07, 0.93],
        vertical_alignment="center"
    )

    with c1:
        st.image(
            str(PROJECT_ROOT / "docs" / "logo.png"),
            width=60
        )

    with c2:
        st.markdown(
            """
            <div style="display:flex; align-items:center;">
                <span style="font-size:40px; font-weight:900; color:#2E86C1;">
                    DocDecode
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<i><b>Confused by radiology jargon? DocDecode is here to explain!</b></i>",
        unsafe_allow_html=True,
    )

    st.caption("Only explanations with citations. Not medical advice.")

    col_left, col_right = st.columns(
        [1, 2],
        gap="large"
    )

    with col_left:
        st.subheader("Input Radiology Report")

        st.session_state.report_text = st.text_area(
            "Paste a radiology report here:",
            value=st.session_state.report_text,
            height=260,
        )

        st.markdown("**Or upload a radiology report PDF:**")

        uploaded_pdf = st.file_uploader(
            "Upload a radiology report PDF",
            type=["pdf"],
            help="Upload a text-based PDF radiology report. Scanned/image-only PDFs may require OCR.",
            key="report_pdf_uploader",
        )

        if uploaded_pdf is not None:
            pdf_signature = (
                uploaded_pdf.name,
                uploaded_pdf.size,
                getattr(uploaded_pdf, "file_id", None),
            )

            if pdf_signature != st.session_state.uploaded_pdf_signature:
                try:
                    with st.spinner("Reading PDF..."):
                        extracted_text = extract_pdf_text(uploaded_pdf)

                    if extracted_text:
                        st.session_state.report_text = extracted_text
                        st.session_state.uploaded_pdf_signature = pdf_signature

                        st.success(
                            f"PDF uploaded successfully: {uploaded_pdf.name}"
                        )

                        st.rerun()

                    else:
                        st.session_state.uploaded_pdf_signature = pdf_signature

                        st.warning(
                            "No selectable text could be extracted from this PDF. "
                            "It may be a scanned/image-based PDF and may require OCR."
                        )

                except Exception as exc:
                    st.session_state.uploaded_pdf_signature = pdf_signature

                    st.error(
                        f"Could not read the PDF: {exc}"
                    )

        if uploaded_pdf is not None and st.session_state.report_text.strip():
            st.caption(
                "The extracted PDF text is loaded into the report box above. "
                "You can edit it before analyzing."
            )

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Load Sample Report"):
                st.session_state.report_text = SAMPLE_REPORT
                st.rerun()

        with c2:
            if st.button("Reset"):
                st.session_state.report_text = ""
                st.session_state.chat_history = []
                st.session_state.uploaded_pdf_signature = None
                st.rerun()

        ok, err = validate_report_input(
            st.session_state.report_text
        )

        if not ok:
            st.warning(err)

        st.markdown("---")

        with st.expander(
            "Advanced: Retrieval Settings (ChromaDB)",
            expanded=False
        ):
            st.caption(
                "These settings control how many reference chunks are retrieved "
                "and how strict the filtering is. Higher min score = stricter evidence quality."
            )

            top_k = st.slider(
                "Top-K retrieved chunks",
                6,
                20,
                12,
                1
            )

            min_score = st.slider(
                "Min similarity score",
                0.30,
                0.80,
                0.50,
                0.01
            )

            final_top_k = st.slider(
                "Final chunks used in prompt",
                2,
                10,
                6,
                1
            )

    with col_right:
        tabs = st.tabs(
            [
                "Explain",
                "Extract",
                "Evidence Q&A"
            ]
        )

        with tabs[0]:
            st.subheader("Explain the report")

            level = st.selectbox(
                "Explanation level",
                [
                    "simple",
                    "normal",
                    "clinician"
                ],
                index=1
            )

            if st.button("Generate Explanation"):
                ok, err = validate_report_input(
                    st.session_state.report_text
                )

                if not ok:
                    st.error(err)

                else:
                    with st.spinner(
                        "Retrieving evidence and generating explanation..."
                    ):
                        t0 = time.time()

                        retrieved = retrieve_top_k(
                            query=(
                                "Explain terms and phrases in this report: "
                                f"{st.session_state.report_text[:300]}"
                            ),
                            top_k=top_k,
                            min_score=min_score,
                            final_top_k=final_top_k,
                        )

                        top_score = max(
                            [
                                r.get("score", 0)
                                for r in retrieved
                            ],
                            default=0
                        )

                        chunks_used = len(retrieved)

                        context_block, citations = (
                            build_context_with_citations(
                                retrieved
                            )
                        )

                        user_prompt = explain_prompt(
                            level,
                            st.session_state.report_text,
                            context_block
                        )

                        answer = generate_text(
                            SYSTEM_BASE,
                            user_prompt
                        )

                        answer = enforce_disclaimer(answer)

                        t1 = time.time()

                    lat = t1 - t0

                    st.success(
                        f"Done in {lat:.2f}s"
                    )

                    st.caption(
                        f"Run stats: **{chunks_used} chunks used** | "
                        f"**top score {top_score:.3f}**"
                    )

                    with st.container(border=True):
                        st.markdown(
                            "### Explanation in Plain English"
                        )

                        st.write(answer)

                    citation_lines = citations_to_ui_lines(
                        citations
                    )

                    show_citations(
                        citation_lines,
                        citations
                    )

        with tabs[1]:
            st.subheader(
                "Extract structured information (JSON)"
            )

            if st.button("Extract Fields"):
                ok, err = validate_report_input(
                    st.session_state.report_text
                )

                if not ok:
                    st.error(err)

                else:
                    with st.spinner("Extracting..."):
                        t0 = time.time()

                        user_prompt = extract_prompt(
                            st.session_state.report_text
                        )

                        answer = generate_text(
                            SYSTEM_BASE,
                            user_prompt
                        )

                        t1 = time.time()

                    st.success(
                        f"Done in {t1 - t0:.2f}s"
                    )

                    parsed = parse_json_response(answer)

                    if parsed is None:
                        st.warning(
                            "Model did not return valid JSON. "
                            "Showing raw output:"
                        )

                        st.code(
                            answer,
                            language="text"
                        )

                    else:
                        st.json(parsed)

                        findings = parsed.get(
                            "findings",
                            []
                        )

                        if findings:
                            with st.container(border=True):
                                st.markdown(
                                    "### Findings"
                                )

                                if isinstance(
                                    findings,
                                    list
                                ):
                                    st.table(
                                        {
                                            "findings": findings
                                        }
                                    )

                                else:
                                    st.write(findings)

                        impression = parsed.get(
                            "impression",
                            []
                        )

                        if impression:
                            with st.container(border=True):
                                st.markdown(
                                    "### Impression"
                                )

                                if isinstance(
                                    impression,
                                    list
                                ):
                                    st.table(
                                        {
                                            "impression": impression
                                        }
                                    )

                                else:
                                    st.write(impression)

                        key_terms = parsed.get(
                            "key_terms",
                            []
                        )

                        if key_terms:
                            with st.container(border=True):
                                st.markdown(
                                    "### Key Terms"
                                )

                                if isinstance(
                                    key_terms,
                                    list
                                ):
                                    st.write(
                                        " • ".join(
                                            str(term)
                                            for term in key_terms[:25]
                                        )
                                    )

                                else:
                                    st.write(key_terms)

                        uncertainty = parsed.get(
                            "uncertainty_phrases",
                            []
                        )

                        if uncertainty:
                            with st.container(border=True):
                                st.markdown(
                                    "### Uncertainty / Hedging"
                                )

                                if isinstance(
                                    uncertainty,
                                    list
                                ):
                                    st.table(
                                        {
                                            "uncertainty": uncertainty
                                        }
                                    )

                                else:
                                    st.write(uncertainty)

                        critical_flags = parsed.get(
                            "critical_flags",
                            []
                        )

                        if critical_flags:
                            with st.container(border=True):
                                st.markdown(
                                    "### Critical Flags"
                                )

                                if isinstance(
                                    critical_flags,
                                    list
                                ):
                                    st.table(
                                        {
                                            "critical_flags": critical_flags
                                        }
                                    )

                                else:
                                    st.write(critical_flags)

                        followup = parsed.get(
                            "recommended_followup_in_report",
                            []
                        )

                        if followup:
                            with st.container(border=True):
                                st.markdown(
                                    "### Recommended Follow-up"
                                )

                                if isinstance(
                                    followup,
                                    list
                                ):
                                    st.table(
                                        {
                                            "follow-up": followup
                                        }
                                    )

                                else:
                                    st.write(followup)

        with tabs[2]:
            st.subheader(
                "Ask questions (answers must cite sources)"
            )

            for turn in st.session_state.chat_history:
                with st.chat_message(turn.role):
                    st.write(turn.content)

            st.markdown(
                "#### Suggested questions"
            )

            sq1, sq2, sq3 = st.columns(3)

            with sq1:
                if st.button(
                    "Explain the impression"
                ):
                    st.session_state.pending_question = (
                        "Explain the impression in simple terms."
                    )

            with sq2:
                if st.button(
                    "Is anything urgent?"
                ):
                    st.session_state.pending_question = (
                        "Is there anything urgent or concerning in this report?"
                    )

            with sq3:
                if st.button(
                    "Define key terms"
                ):
                    st.session_state.pending_question = (
                        "Define key terms mentioned in this report "
                        "(e.g., opacity, atelectasis, effusion)."
                    )

            question = (
                st.session_state.pending_question
                or st.chat_input(
                    "Ask a question about the report..."
                )
            )

            if (
                st.session_state.pending_question is not None
                and question == st.session_state.pending_question
            ):
                st.session_state.pending_question = None

            if question is not None:
                ok_r, err_r = validate_report_input(
                    st.session_state.report_text
                )

                ok_q, err_q = validate_question_input(
                    question
                )

                if not ok_r:
                    st.error(err_r)
                    return

                if not ok_q:
                    st.error(err_q)
                    return

                st.session_state.chat_history.append(
                    ChatTurn(
                        role="user",
                        content=question
                    )
                )

                with st.chat_message("user"):
                    st.write(question)

                with st.spinner(
                    "Retrieving evidence + answering..."
                ):
                    t0 = time.time()

                    retrieved = retrieve_top_k(
                        query=question,
                        top_k=top_k,
                        min_score=min_score,
                        final_top_k=final_top_k,
                    )

                    ok_ev, err_ev = validate_retrieval_results(
                        retrieved,
                        min_results=2
                    )

                    if ok_ev:
                        context_block, citations = (
                            build_context_with_citations(
                                retrieved
                            )
                        )

                        evidence_status = (
                            "with retrieved evidence"
                        )

                    else:
                        context_block = (
                            "No sufficient external knowledge-base "
                            "evidence was retrieved for this question. "
                            "Answer using the REPORT TEXT only. "
                            "Do not invent or add unsupported facts."
                        )

                        citations = []

                        evidence_status = (
                            "using report text only"
                        )

                    user_prompt = qa_prompt(
                        question,
                        st.session_state.report_text,
                        context_block
                    )

                    trimmed = trim_history(
                        st.session_state.chat_history[:-1],
                        max_turns=6
                    )

                    history_msgs = history_to_messages(
                        trimmed
                    )

                    assistant_reply = generate_text(
                        SYSTEM_BASE,
                        user_prompt,
                        history_messages=history_msgs
                    )

                    assistant_reply = enforce_disclaimer(
                        assistant_reply
                    )

                    t1 = time.time()

                with st.chat_message("assistant"):
                    st.write(assistant_reply)

                st.session_state.chat_history.append(
                    ChatTurn(
                        role="assistant",
                        content=assistant_reply
                    )
                )

                st.info(
                    f"Done in {t1 - t0:.2f}s "
                    f"({evidence_status})"
                )

                citation_lines = citations_to_ui_lines(
                    citations
                )

                with st.expander(
                    "Top evidence snippets (preview)",
                    expanded=False
                ):
                    for c in citations[:3]:
                        with st.container(border=True):
                            st.markdown(
                                f"**[{c.cid}] {c.source} — "
                                f"page {c.page}** "
                                f"(score: {c.score:.3f})"
                            )

                            st.caption(c.snippet)

                show_citations(
                    citation_lines,
                    citations
                )


if __name__ == "__main__":
    main()
