import json
import os
from collections import Counter
from urllib.parse import quote

import streamlit as st

from main import history_path, run_pipeline
from models import OutreachRequest


st.set_page_config(
    page_title="AI Sales Outreach Platform",
    page_icon="Email",
    layout="wide",
)


def load_history():
    path = history_path()
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def gmail_compose_url(to_email: str, email_text: str) -> str:
    lines = email_text.strip().splitlines()
    subject = ""
    body = email_text

    if lines and lines[0].lower().startswith("subject:"):
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).strip()

    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        f"&to={quote(to_email or '')}"
        f"&su={quote(subject)}"
        f"&body={quote(body)}"
    )


def render_company_news(research: dict):
    st.subheader("Company News")
    news = research.get("company_news") or []

    if not news:
        st.caption("No verified company news returned.")
        return

    for item in news:
        st.write(f"- {item}")

    sources = research.get("sources") or []
    if sources:
        with st.expander("Sources"):
            for source in sources:
                st.write(source)


def render_opportunities(opportunities: list[dict]):
    st.subheader("Sales Opportunities")

    if not opportunities:
        st.caption("No sales opportunities returned.")
        return

    for opportunity in opportunities:
        theme = opportunity.get("theme", "Untitled")
        confidence = opportunity.get("confidence", "")
        st.markdown(f"**{theme}**")
        st.caption(f"Confidence: {confidence}")

        facts = opportunity.get("supporting_facts") or []
        if facts:
            st.markdown("Supporting facts")
            for fact in facts:
                st.write(f"- {fact}")

        relevance = opportunity.get("product_relevance") or ""
        if relevance:
            st.markdown("Why it matters")
            st.write(relevance)

        st.divider()


def render_analytics(history: list[dict]):
    st.subheader("Dashboard Analytics")

    generated = [item for item in history if item.get("status") == "ok"]
    industries = Counter(
        (item.get("research") or {}).get("industry")
        for item in generated
        if (item.get("research") or {}).get("industry")
    )
    themes = Counter(
        theme
        for item in generated
        for theme in item.get("themes_used", [])
        if theme
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total emails generated", len(generated))
    col2.metric("Top industries", len(industries))
    col3.metric("Common themes", len(themes))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top industries**")
        if industries:
            for industry, count in industries.most_common(5):
                st.write(f"{industry}: {count}")
        else:
            st.caption("No industry data yet.")

    with col2:
        st.markdown("**Most common themes**")
        if themes:
            for theme, count in themes.most_common(5):
                st.write(f"{theme}: {count}")
        else:
            st.caption("No theme data yet.")

    st.markdown("**Email history**")
    if not history:
        st.caption("No emails generated yet.")
        return

    for item in reversed(history[-10:]):
        label = f"{item.get('date', '')} - {item.get('prospect', '')} at {item.get('company', '')}"
        with st.expander(label):
            st.write(f"Score: {(item.get('review') or {}).get('score', 0)}/10")
            st.write("Themes used: " + ", ".join(item.get("themes_used", []) or ["None"]))
            st.text_area(
                "Email",
                value=item.get("email", ""),
                height=220,
                key=f"history-{item.get('date', '')}-{item.get('prospect', '')}",
            )


st.title("AI Sales Outreach Platform")
st.caption("Generate reviewed, research-backed sales emails using CrewAI and live web research.")

with st.sidebar:
    st.header("Analytics")
    render_analytics(load_history())

with st.form("outreach-form"):
    st.header("Sender Information")
    col1, col2 = st.columns(2)

    with col1:
        sender_name = st.text_input("Your Name")
        sender_company = st.text_input("Your Company")
        sender_designation = st.text_input("Your Designation")

    with col2:
        sender_email = st.text_input("Your Email")

    st.divider()

    st.header("Prospect Information")
    col1, col2 = st.columns(2)

    with col1:
        receiver_name = st.text_input("Prospect Name")
        receiver_company = st.text_input("Prospect Company")
        receiver_designation = st.text_input("Prospect Designation")

    with col2:
        receiver_email = st.text_input("Prospect Email")

    st.divider()

    st.header("Product Information")
    product_name = st.text_input("Product Name")

    service_type = st.selectbox(
        "Product Category",
        [
            "AI Automation",
            "SaaS Product",
            "Consulting",
            "Marketing",
            "Sales",
            "Custom",
        ],
    )

    target_customer = st.text_input(
        "Target Customer",
        placeholder="e.g. B2B Sales Teams",
    )

    problem_solved = st.text_area(
        "Problem Your Product Solves",
        height=80,
        placeholder="Sales teams spend hours researching prospects before writing personalized emails.",
    )

    main_benefit = st.text_area(
        "Main Benefit",
        height=80,
        placeholder="Reduce prospect research time while increasing personalization.",
    )

    product_description = st.text_area(
        "Product Description",
        height=150,
        placeholder="AI platform that researches prospects, finds company news, generates sales opportunities, and drafts personalized cold emails.",
    )

    st.divider()

    st.header("Outreach Goal")
    goal = st.radio(
        "Primary Goal",
        [
            "Book a Meeting",
            "Product Demo",
            "Partnership",
            "Follow Up",
            "Networking",
            "Hiring",
        ],
        horizontal=True,
    )

    st.divider()

    st.header("Tone")
    tone = st.select_slider(
        "Email Tone",
        options=[
            "Friendly",
            "Professional",
            "Executive",
            "Formal",
            "Persuasive",
        ],
        value="Professional",
    )

    length = st.select_slider(
        "Email Length",
        options=[
            "Short",
            "Medium",
            "Detailed",
        ],
        value="Medium",
    )

    extra_instructions = st.text_area(
        "Additional Instructions",
        placeholder="Keep it under 120 words. Avoid sounding salesy.",
        height=110,
    )

    submitted = st.form_submit_button("Generate Email", use_container_width=True)

if submitted:
    request = OutreachRequest(
        sender_name=sender_name,
        sender_company=sender_company,
        sender_designation=sender_designation,
        sender_email=sender_email,
        prospect_name=receiver_name,
        prospect_company=receiver_company,
        prospect_designation=receiver_designation,
        prospect_email=receiver_email,
        product_name=product_name,
        service_type=service_type,
        target_customer=target_customer,
        problem_solved=problem_solved,
        main_benefit=main_benefit,
        product_description=product_description,
        goal=goal,
        tone=tone,
        length=length,
        additional_instructions=extra_instructions,
    )

    with st.spinner("Researching, synthesizing, writing, and reviewing..."):
        result = run_pipeline(request)

    if result.get("status") == "skipped":
        st.warning(result.get("email", "Skipped."))
    else:
        st.success("Email generated and reviewed.")

    left, right = st.columns([1, 1])

    with left:
        render_company_news(result.get("research") or {})
        render_opportunities(result.get("sales_opportunities") or [])

    with right:
        st.subheader("Email")
        review = result.get("review") or {}
        st.metric("Reviewer score", f"{review.get('score', 0)}/10")

        if review.get("feedback"):
            st.caption(review["feedback"])

        edited_email = st.text_area(
            "Edit before sending",
            value=result.get("email", ""),
            height=350,
        )

        st.link_button(
            "Open Gmail Draft",
            gmail_compose_url(receiver_email, edited_email),
            use_container_width=True,
        )
