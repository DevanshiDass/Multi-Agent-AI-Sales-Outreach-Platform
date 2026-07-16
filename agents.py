"""
agents.py
---------
Defines all CrewAI agents used in the Cold Outreach pipeline.
"""

from crewai import Agent, LLM

from config import Config
from tools import SerperSearchTool


# ------------------------------------------------------------------
# Shared LLM Factory
# ------------------------------------------------------------------

def build_llm(temperature: float | None = None) -> LLM:
    """
    Shared LLM configuration.

    Lower retries because the pipeline already retries
    at the application level.
    """

    return LLM(
        model=Config.LITELLM_MODEL_STRING,
        api_key=Config.GROQ_API_KEY,
        temperature=(
            temperature
            if temperature is not None
            else Config.DEFAULT_TEMPERATURE
        ),
        request_timeout=120,
        num_retries=3,
    )


# ------------------------------------------------------------------
# Research Agent
# ------------------------------------------------------------------

def build_researcher_agent() -> Agent:
    return Agent(
        role="Senior B2B OSINT Researcher",
        goal=(
            "Collect ONLY verified public facts about the prospect "
            "and the company using web search. "
            "Never infer pain points. "
            "Never assume responsibilities. "
            "Never speculate. "
            "If something cannot be verified, leave it empty."
        ),
        backstory=(
            "You are an OSINT researcher. "
            "You only collect evidence. "
            "You never interpret evidence. "
            "You never predict business priorities. "
            "You never guess what a prospect needs. "
            "Your only job is to return verified facts."
        ),
        tools=[
            SerperSearchTool(),
        ],
        llm=build_llm(
            temperature=0.1,
        ),
        allow_delegation=False,
        verbose=True,
        max_iter=3,
    )


# ------------------------------------------------------------------
# Synthesizer Agent
# ------------------------------------------------------------------

def build_synthesizer_agent() -> Agent:
    return Agent(
        role="Sales Strategy Agent",
        goal=(
            "Cluster verified facts into sales opportunity themes, "
            "assess cautious product relevance, and assign confidence "
            "without inventing new facts."
        ),
        backstory=(
            "You transform verified research into sales opportunities. "
            "You group similar facts into themes. "
            "You explain why each theme may make the product relevant. "
            "You never introduce new facts. "
            "You never claim the company already needs the product. "
            "You never output commentary. "
            "You never explain your reasoning. "
            "Output only the requested JSON."
        ),
        tools=[],
        llm=build_llm(
            temperature=0.15,
        ),
        allow_delegation=False,
        verbose=True,
        max_iter=2,
    )


# ------------------------------------------------------------------
# Writer Agent
# ------------------------------------------------------------------

def build_writer_agent() -> Agent:
    return Agent(
        role="Enterprise Cold Email Copywriter",
        goal=(
            "Write highly personalized cold emails using only the supplied "
            "sales opportunities."
        ),
        backstory=(
            "You are a senior B2B SaaS copywriter. "
            "Your emails feel personal rather than automated. "
            "Every email follows this structure:\n"
            "1. Subject\n"
            "2. One factual observation\n"
            "3. Natural bridge to the product\n"
            "4. One clear benefit\n"
            "5. Low-pressure CTA\n\n"
            "Rules:\n"
            "- Use one high-confidence opportunity.\n"
            "- Mention only one supporting fact.\n"
            "- Never invent facts.\n"
            "- Never use placeholders.\n"
            "- Never explain your reasoning.\n"
            "- Never output markdown.\n"
            "- Never output commentary.\n"
            "- Output only the final email."
        ),
        tools=[],
        llm=build_llm(
            temperature=0.45,
        ),
        allow_delegation=False,
        verbose=True,
        max_iter=2,
    )


# ------------------------------------------------------------------
# Reviewer Agent
# ------------------------------------------------------------------

def build_scoring_agent() -> Agent:
    return Agent(
        role="Cold Email Quality Reviewer",
        goal=(
            "Review generated cold emails and score them based on "
            "personalization, factual accuracy, repetition, CTA, tone, "
            "and hallucination risk."
        ),
        backstory=(
            "You are a Sales Director reviewing outbound emails before "
            "they are sent to prospects. "
            "You reject generic emails. "
            "You reward specificity and factual personalization. "
            "You flag unsupported claims. "
            "Never rewrite unless asked."
        ),
        tools=[],
        llm=build_llm(
            temperature=0.0,
        ),
        allow_delegation=False,
        verbose=True,
        max_iter=2,
    )
