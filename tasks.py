"""
tasks.py
--------
Defines the sequential CrewAI tasks.

Changes:
- Research returns STRICT JSON with verified facts only.
- Synthesizer returns STRICT JSON sales opportunities.
- Writer receives validated opportunities, not raw research.
- Reviewer scores the generated email before final output.
"""

from crewai import Task

from models import OutreachRequest


# ------------------------------------------------------------------
# Research Task
# ------------------------------------------------------------------

def build_research_task(
    agent,
    request: OutreachRequest,
) -> Task:
    return Task(
        description=f"""
Research the prospect "{request.prospect_name}" at "{request.prospect_company}".
==================================================
PRODUCT CONTEXT FOR SEARCH PLANNING ONLY
==================================================

Product Name:
{request.product_name}

Category:
{request.service_type}

Target Customer:
{request.target_customer}

Problem Solved:
{request.problem_solved}

Main Benefit:
{request.main_benefit}

Description:
{request.product_description}

==================================================
TASK
==================================================

Collect ONLY verified facts.

Do NOT mention the product.

Do NOT explain why the product is useful.

Do NOT infer product relevance.

Your job is ONLY to collect factual research.

Prioritize:

1. Product launches
2. AI initiatives
3. Partnerships
4. Funding
5. Acquisitions
6. Leadership announcements
7. Earnings reports
8. Strategic initiatives
9. Hiring trends
10. Major customer wins

Search at most THREE times.

Generate your own search queries based on the company, prospect, industry,
and public facts worth verifying. You may use the product context only to
choose where to search, but never include product relevance in the output.

Do NOT return:

- Website names
- Page titles
- Navigation pages
- Marketing slogans
- Blog names

BAD:
Salesforce Newsroom

GOOD:
Salesforce introduced Agentforce 3 during its Summer '26 release.

BAD:
Salesforce Blog

GOOD:
Salesforce expanded its AI CRM capabilities with new Agentforce features.

Every company_news item MUST be a factual sentence.

Do NOT infer pain points.

Do NOT assume business priorities.

Do NOT guess the prospect's responsibilities.

Only return information that is directly supported by search results.

Never invent facts.

Never explain your reasoning.

Return ONLY valid JSON.
""",
        expected_output="""
{
    "company_news": [
        "...",
        "..."
    ],
    "prospect_information": {
        "designation": "",
        "department": "",
        "location": ""
    },
    "industry": "",
    "sources": [
        "...",
        "..."
    ]
}

Rules:

Return ONLY JSON.

Do not add product-relevance fields to the research output.

Do not explain product relevance.

Never invent facts.

No markdown.

No commentary.
""",
        agent=agent,
    )


# ------------------------------------------------------------------
# Synthesis Task
# ------------------------------------------------------------------

def build_synthesis_task(
    agent,
    request: OutreachRequest,
    research_task: Task,
) -> Task:
    return Task(
        description=f"""
Using ONLY the verified JSON produced by the Research task:

Read every research fact.

Group similar facts into themes.

Choose the THREE strongest themes.

For every theme:

1. Theme title
2. Supporting facts
3. Explain why this theme may make the product relevant.
4. Confidence: High, Medium, or Low

PRODUCT CONTEXT
Product Name: {request.product_name}
Category: {request.service_type}
Target Customer: {request.target_customer}
Problem Solved: {request.problem_solved}
Main Benefit: {request.main_benefit}
Description: {request.product_description}

Never claim the company already needs the product.

Never invent information.

Never introduce new facts.

Do NOT assume the prospect's responsibilities.

Do NOT assume what the prospect is interested in.

If no useful research exists, return:

{{
    "sales_opportunities": [
        {{
            "theme": "INSUFFICIENT_RESEARCH",
            "supporting_facts": [],
            "product_relevance": "",
            "confidence": "Low"
        }}
    ]
}}

Output JSON only.
""",
        expected_output="""
{
    "sales_opportunities": [
        {
            "theme": "Enterprise AI",
            "supporting_facts": [
                "Verified research fact 1",
                "Verified research fact 2"
            ],
            "product_relevance": "Why this theme may make the product relevant.",
            "confidence": "High"
        }
    ]
}

Rules:

- Output ONLY JSON.
- No markdown.
- No explanations.
- No commentary.
- No reasoning.
- No text before or after the JSON.
""",
        context=[research_task],
        agent=agent,
    )


# ------------------------------------------------------------------
# Writing Task
# ------------------------------------------------------------------

def build_writing_task(
    agent,
    request: OutreachRequest,
) -> Task:
    return Task(
        description=f"""
You are writing a personalized B2B cold email.

=========================
SENDER
=========================

Name:
{request.sender_name}

Company:
{request.sender_company}

Designation:
{request.sender_designation}

Email:
{request.sender_email}

=========================
PROSPECT
=========================

Name:
{request.prospect_name}

Company:
{request.prospect_company}

Designation:
{request.prospect_designation}

=========================
PRODUCT / SERVICE
=========================

PRODUCT NAME

{request.product_name}

CATEGORY

{request.service_type}

TARGET CUSTOMER

{request.target_customer}

PROBLEM SOLVED

{request.problem_solved}

MAIN BENEFIT

{request.main_benefit}

PRODUCT DESCRIPTION

{request.product_description}
=========================
EMAIL SETTINGS
=========================

Goal:
{request.goal}

Tone:
{request.tone}

Length:
{request.length}

Additional Instructions:
{request.additional_instructions}

=========================
TASK
=========================

Write a highly personalized cold email.

Use ONLY the verified sales opportunities supplied by the pipeline.

Rules:

- Choose ONE high-confidence opportunity.
- Mention ONE supporting fact.
- Bridge naturally to the product.
- Explain the benefit.
- Avoid repeating multiple facts.
- Do not list research.
- Write conversationally.
- Match the requested tone.
- Keep the requested length.
- End with ONE clear CTA.
- Sign using the sender's name.
- Never invent facts.
- Never explain your reasoning.
- Output ONLY the email.

If the sales opportunities contain

INSUFFICIENT_RESEARCH

output EXACTLY

SKIPPED: insufficient research data to personalize this email.
""",
        expected_output="""
Subject: ...

Email body only.

OR

SKIPPED: insufficient research data to personalize this email.
""",
        agent=agent,
    )


# ------------------------------------------------------------------
# Review Task
# ------------------------------------------------------------------

def build_review_task(
    agent,
    request: OutreachRequest,
    email: str,
    opportunities: str,
) -> Task:
    return Task(
        description=f"""
Review this generated B2B cold email before it is shown to the user.

Score the email from 1 to 10 on:

- Personalization
- Accuracy
- Repetition
- CTA
- Tone
- Hallucination risk

Use ONLY the sales opportunities below as factual grounding.

PROSPECT
Name: {request.prospect_name}
Company: {request.prospect_company}
Designation: {request.prospect_designation}

SALES OPPORTUNITIES
{opportunities}

EMAIL
{email}

Return JSON only.
Never rewrite the email.
Never introduce new facts.
""",
        expected_output="""
{
    "score": 8,
    "personalization": 8,
    "accuracy": 9,
    "repetition": 8,
    "cta": 8,
    "tone": 8,
    "hallucination_risk": "Low",
    "feedback": "Brief rewrite guidance if score is below 8."
}

Rules:

- Output ONLY JSON.
- No markdown.
- No commentary.
""",
        agent=agent,
    )

