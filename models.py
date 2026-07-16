from dataclasses import dataclass


@dataclass
class OutreachRequest:

    # ---------------- Sender ---------------- #

    sender_name: str

    sender_company: str

    sender_designation: str

    sender_email: str

    # ---------------- Prospect ---------------- #

    prospect_name: str

    prospect_company: str

    prospect_designation: str

    prospect_email: str

    # ---------------- Product ---------------- #

    product_name: str

    service_type: str

    target_customer: str

    problem_solved: str

    main_benefit: str

    product_description: str

    # ---------------- Email Preferences ---------------- #

    goal: str

    tone: str

    length: str

    additional_instructions: str