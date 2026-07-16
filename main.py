#!/usr/bin/env python3
"""
main.py
--------

CLI entry point and orchestration for the Cold Outreach pipeline.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any

from crewai import Crew, Process

from agents import (
    build_researcher_agent,
    build_scoring_agent,
    build_synthesizer_agent,
    build_writer_agent,
)
from config import Config, logger
from models import OutreachRequest
from tasks import (
    build_research_task,
    build_review_task,
    build_synthesis_task,
    build_writing_task,
)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Autonomous cold outreach pipeline."
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Prospect name",
    )

    parser.add_argument(
        "--company",
        required=True,
        help="Company",
    )

    return parser.parse_args()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def safe_filename(name: str) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9\s-]",
        "",
        name,
    ).strip().lower()

    return re.sub(r"\s+", "_", cleaned) or "unknown"


def is_skip_signal(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().upper().startswith("SKIPPED")


def clean_email_output(text: str) -> str:
    """
    Removes leaked reasoning if the model accidentally outputs it.
    """

    markers = [
        "Let's think",
        "I will output",
        "Your final answer",
        "Reasoning:",
        "Thought:",
        "Self-Correction",
        "Analysis:",
        "Checks out",
        "Final Answer:",
        "*Critique:*",
        "*Word Count",
        "Output Constraint",
    ]

    for marker in markers:
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]

    return text.strip()


def extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def looks_like_valid_output(text: str) -> bool:
    text = text.strip()

    if is_skip_signal(text):
        return True

    if not text.lower().startswith("subject:"):
        return False

    if len(text) < 40:
        return False

    return True


def format_opportunities(opportunities: list[dict[str, Any]]) -> str:
    formatted = []

    for index, item in enumerate(opportunities, start=1):
        facts = item.get("supporting_facts") or []
        facts_text = "\n".join(f"- {fact}" for fact in facts if fact)

        formatted.append(
            f"Opportunity {index}\n"
            f"Theme: {item.get('theme', '')}\n"
            f"Confidence: {item.get('confidence', '')}\n"
            f"Supporting Facts:\n{facts_text}\n"
            f"Product Relevance: {item.get('product_relevance', '')}"
        )

    return "\n\n".join(formatted).strip()


def has_insufficient_research(opportunities: list[dict[str, Any]]) -> bool:
    return any(
        str(item.get("theme", "")).upper() == "INSUFFICIENT_RESEARCH"
        for item in opportunities
    )


def history_path() -> str:
    return os.path.join("output", "history.json")


def append_history(result: dict[str, Any]) -> None:
    os.makedirs("output", exist_ok=True)
    path = history_path()

    history = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Existing history file could not be read; starting fresh.")
            history = []

    history.append(result)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


# ------------------------------------------------------------------
# Research + Synthesis
# ------------------------------------------------------------------

def run_research_and_synthesis(
    request: OutreachRequest,
) -> dict[str, Any]:
    researcher = build_researcher_agent()
    synthesizer = build_synthesizer_agent()

    research_task = build_research_task(
        researcher,
        request,
    )

    synthesis_task = build_synthesis_task(
        synthesizer,
        request,
        research_task,
    )

    crew = Crew(
        agents=[
            researcher,
            synthesizer,
        ],
        tasks=[
            research_task,
            synthesis_task,
        ],
        process=Process.sequential,
        verbose=True,
        max_rpm=Config.MAX_RPM,
    )

    crew.kickoff()

    raw_research = ""
    if research_task.output is not None and research_task.output.raw is not None:
        raw_research = research_task.output.raw.strip()

    research_json = extract_json(raw_research) or {
        "company_news": [],
        "prospect_information": {},
        "industry": "",
        "sources": [],
    }

    if synthesis_task.output is None or synthesis_task.output.raw is None:
        logger.warning("Synthesizer produced no output.")
        return {
            "status": "skipped",
            "reason": "INSUFFICIENT_RESEARCH",
            "research": research_json,
            "sales_opportunities": [],
            "formatted_opportunities": "",
        }

    raw = synthesis_task.output.raw.strip()
    print("\n========== RAW SYNTHESIS ==========")
    print(raw)
    print("==================================\n")

    logger.info("Raw synthesis output:\n%s", raw)

    parsed = extract_json(raw)
    if parsed is None:
        logger.warning("Synthesizer returned invalid JSON.")
        return {
            "status": "skipped",
            "reason": "INSUFFICIENT_RESEARCH",
            "research": research_json,
            "sales_opportunities": [],
            "formatted_opportunities": "",
        }

    opportunities = parsed.get("sales_opportunities") or []

    if not isinstance(opportunities, list) or not opportunities:
        logger.warning("No sales opportunities returned.")
        return {
            "status": "skipped",
            "reason": "INSUFFICIENT_RESEARCH",
            "research": research_json,
            "sales_opportunities": [],
            "formatted_opportunities": "",
        }

    if has_insufficient_research(opportunities):
        return {
            "status": "skipped",
            "reason": "INSUFFICIENT_RESEARCH",
            "research": research_json,
            "sales_opportunities": opportunities,
            "formatted_opportunities": format_opportunities(opportunities),
        }

    formatted_opportunities = format_opportunities(opportunities)

    return {
        "status": "ok",
        "research": research_json,
        "sales_opportunities": opportunities,
        "formatted_opportunities": formatted_opportunities,
    }


# ------------------------------------------------------------------
# Writer + Reviewer
# ------------------------------------------------------------------

def run_single_writer_attempt(
    request: OutreachRequest,
    opportunities: str,
    review_feedback: str = "",
) -> str:
    writer = build_writer_agent()

    writing_task = build_writing_task(
        writer,
        request,
    )

    writing_task.description += (
        "\n\nSales Opportunities:\n"
        f"{opportunities}"
    )

    if review_feedback:
        writing_task.description += (
            "\n\nReviewer Feedback to Address:\n"
            f"{review_feedback}"
        )

    crew = Crew(
        agents=[writer],
        tasks=[writing_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=Config.MAX_RPM,
    )

    raw_result = str(crew.kickoff())
    return clean_email_output(raw_result)


def run_reviewer(
    request: OutreachRequest,
    email: str,
    opportunities: str,
) -> dict[str, Any]:
    reviewer = build_scoring_agent()

    review_task = build_review_task(
        reviewer,
        request,
        email,
        opportunities,
    )

    crew = Crew(
        agents=[reviewer],
        tasks=[review_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=Config.MAX_RPM,
    )

    try:
        raw_result = str(crew.kickoff()).strip()
    except Exception as e:
        logger.warning("Reviewer failed: %s", e)
        return {
            "score": 0,
            "feedback": "Reviewer failed to produce a score.",
        }

    parsed = extract_json(raw_result)
    if parsed is None:
        logger.warning("Reviewer returned invalid JSON: %s", raw_result[:300])
        return {
            "score": 0,
            "feedback": "Reviewer returned invalid JSON.",
        }

    return parsed


def run_writer(
    request: OutreachRequest,
    opportunities: str,
) -> dict[str, Any]:
    """
    Runs the writer and reviewer. If the reviewer scores below 8/10,
    the writer gets one or more chances to rewrite using reviewer feedback.
    """

    last_email = "SKIPPED: writer failed to produce a valid email after retries."
    last_review: dict[str, Any] = {
        "score": 0,
        "feedback": "Writer did not produce a valid email.",
    }
    review_feedback = ""

    for attempt in range(1, Config.WRITER_MAX_ATTEMPTS + 1):
        logger.info(
            "Writer attempt %d/%d",
            attempt,
            Config.WRITER_MAX_ATTEMPTS,
        )

        try:
            email = run_single_writer_attempt(
                request,
                opportunities,
                review_feedback,
            )
        except Exception as e:
            logger.warning("Writer failed on attempt %d: %s", attempt, e)
            continue

        last_email = email

        if not looks_like_valid_output(email):
            logger.warning(
                "Invalid writer output on attempt %d:\n%s",
                attempt,
                email[:300],
            )
            review_feedback = "Output must start with Subject: and contain only the email."
            continue

        if is_skip_signal(email):
            return {
                "email": email,
                "review": {
                    "score": 0,
                    "feedback": "Writer skipped due to insufficient research.",
                },
            }

        review = run_reviewer(request, email, opportunities)
        last_review = review

        score = int(review.get("score") or 0)
        if score >= 8:
            logger.info("Writer passed review with score %d.", score)
            return {
                "email": email,
                "review": review,
            }

        logger.warning("Email scored %d/10; requesting rewrite.", score)
        review_feedback = str(review.get("feedback") or "Improve accuracy and specificity.")

    logger.warning("Writer exhausted all retries.")
    return {
        "email": last_email,
        "review": last_review,
    }


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------

def run_pipeline(
    request: OutreachRequest,
) -> dict[str, Any]:
    """
    Full pipeline.

    Research -> Synthesis -> Writer -> Reviewer -> History
    """

    synthesis = run_research_and_synthesis(request)

    if synthesis["status"] != "ok":
        logger.warning(
            "Skipping '%s' because synthesis failed.",
            request.prospect_name,
        )
        result = {
            "status": "skipped",
            "prospect": request.prospect_name,
            "company": request.prospect_company,
            "date": datetime.now().isoformat(timespec="seconds"),
            "research": synthesis.get("research", {}),
            "sales_opportunities": synthesis.get("sales_opportunities", []),
            "themes_used": [],
            "email": "SKIPPED: insufficient research data to personalize this email.",
            "review": {
                "score": 0,
                "feedback": "Insufficient research.",
            },
        }
        append_history(result)
        return result

    opportunities_text = synthesis["formatted_opportunities"]

    bad_phrases = [
        "YOUR FINAL ANSWER",
        "I WILL OUTPUT",
        "LET'S THINK",
        "SELF-CORRECTION",
        "PROCEEDS",
        "THOUGHT:",
        "ANALYSIS:",
    ]

    upper = opportunities_text.upper()
    for phrase in bad_phrases:
        if phrase in upper:
            logger.warning("Invalid synthesis output detected (%s).", phrase)
            result = {
                "status": "skipped",
                "prospect": request.prospect_name,
                "company": request.prospect_company,
                "date": datetime.now().isoformat(timespec="seconds"),
                "research": synthesis["research"],
                "sales_opportunities": synthesis["sales_opportunities"],
                "themes_used": [],
                "email": "SKIPPED: insufficient research data to personalize this email.",
                "review": {
                    "score": 0,
                    "feedback": "Invalid synthesis output.",
                },
            }
            append_history(result)
            return result

    writer_result = run_writer(request, opportunities_text)
    opportunities = synthesis["sales_opportunities"]
    themes_used = [
        item.get("theme", "")
        for item in opportunities
        if item.get("confidence", "").lower() == "high"
    ][:1]

    if not themes_used and opportunities:
        themes_used = [opportunities[0].get("theme", "")]

    result = {
        "status": "ok" if not is_skip_signal(writer_result["email"]) else "skipped",
        "prospect": request.prospect_name,
        "company": request.prospect_company,
        "date": datetime.now().isoformat(timespec="seconds"),
        "research": synthesis["research"],
        "sales_opportunities": opportunities,
        "formatted_opportunities": opportunities_text,
        "themes_used": [theme for theme in themes_used if theme],
        "email": writer_result["email"],
        "review": writer_result["review"],
    }

    append_history(result)
    return result


# ------------------------------------------------------------------
# Save Output
# ------------------------------------------------------------------

def save_output(
    prospect_name: str,
    email_text: str,
) -> str:
    os.makedirs(
        Config.OUTPUT_DIR,
        exist_ok=True,
    )

    filepath = os.path.join(
        Config.OUTPUT_DIR,
        f"{safe_filename(prospect_name)}.txt",
    )

    with open(
        filepath,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(email_text)

    return filepath


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    args = parse_args()
    Config.validate()

    logger.info(
        "Starting pipeline for prospect='%s' company='%s'",
        args.name,
        args.company,
    )

    try:
        request = OutreachRequest(
            sender_name="CLI User",
            sender_company="CLI Company",
            sender_designation="",
            sender_email="",
            prospect_name=args.name,
            prospect_company=args.company,
            prospect_designation="",
            prospect_email="",
            product_name="Test Product",
            service_type="SaaS Product",
            target_customer="Businesses",
            problem_solved="Test Problem",
            main_benefit="Test Benefit",
            product_description="Test Description",
            goal="Book a Meeting",
            tone="Professional",
            length="Medium",
            additional_instructions="",
        )

        result = run_pipeline(request)

    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)

    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)

    email = result["email"]

    if is_skip_signal(email):
        print("\n--- SKIPPED ---\n")
        print(email)
        return

    filepath = save_output(args.name, email)

    print("\n--- FINAL EMAIL ---\n")
    print(email)
    print(f"\nScore: {result.get('review', {}).get('score', 0)}/10")
    print(f"Saved to: {filepath}")


# ------------------------------------------------------------------

if __name__ == "__main__":
    main()
