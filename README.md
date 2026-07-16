# Multi-Agent AI Sales Outreach Platform

An end-to-end AI-powered sales outreach platform that performs live prospect research, identifies sales opportunities, generates personalized cold emails, reviews email quality, and prepares Gmail-ready drafts using a multi-agent CrewAI workflow.

---

## Features

- Live web research using Serper API
- Multi-Agent workflow using CrewAI
- Prospect and company intelligence collection
- Research-backed sales opportunity detection
- Personalized cold email generation
- AI email quality reviewer
- Editable email preview
- Gmail draft integration
- Interactive Streamlit dashboard

---

## Workflow

```
User Input
      │
      ▼
Research Agent
      │
      ▼
Sales Strategy Agent
      │
      ▼
Email Writer Agent
      │
      ▼
Email Reviewer Agent
      │
      ▼
Interactive Dashboard
      │
      ▼
Open Gmail Draft
```

---

## Tech Stack

- Python
- CrewAI
- Groq LLM
- LiteLLM
- Streamlit
- Serper API
- Pydantic
- Requests

---

# Project Screenshots

## 1. Dashboard

Collect sender information, prospect information and product details.

![](assets/dashboard_1.png)

---

## 2. Product Configuration

Configure the product/service being offered, target customer, business problem and product description.

![](assets/dashboard_2.png)

---

## 3. Outreach Configuration

Customize outreach goal, tone, email length and additional instructions.

![](assets/dashboard_3.png)

---

## 4. Research & Generated Email

Displays live company research, AI reviewer score and generated personalized email.

![](assets/dashboard_4.png)

---

## 5. Sales Opportunities

Shows research-backed sales opportunities extracted from company news.

![](assets/dashboard_5.png)

---

## 6. Sales Opportunity Analysis

Displays grouped business opportunities with supporting facts and confidence scores.

![](assets/dashboard_6.png)

---

## 7. Gmail Draft

One-click generation of a Gmail draft with the generated email.

![](assets/gmail_page.png)

---

# Project Structure

```
Multi-Agent-AI-Sales-Outreach-Platform
│
├── app.py
├── main.py
├── agents.py
├── tasks.py
├── tools.py
├── config.py
├── models.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
├── assets
│   ├── dashboard_1.png
│   ├── dashboard_2.png
│   ├── dashboard_3.png
│   ├── dashboard_4.png
│   ├── dashboard_5.png
│   ├── dashboard_6.png
│   └── gmail_page.png
│
└── output
```

---

# Installation

## 1. Clone the repository

```bash
git clone https://github.com/<your-username>/Multi-Agent-AI-Sales-Outreach-Platform.git
```

## 2. Open the project

```bash
cd Multi-Agent-AI-Sales-Outreach-Platform
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Create a `.env` file

```
GROQ_API_KEY=YOUR_GROQ_API_KEY

SERPER_API_KEY=YOUR_SERPER_API_KEY

GROQ_MODEL=llama-3.3-70b-versatile

LLM_TEMPERATURE=0.3

OUTPUT_DIR=output

MAX_RPM=4

WRITER_MAX_ATTEMPTS=2
```

---

## 5. Run the application

```bash
streamlit run app.py
```

---

# Future Improvements

- Gmail API integration for one-click sending
- CRM integration
- Bulk outreach using CSV uploads
- Email history dashboard
- Analytics and outreach tracking
- RAG-powered company knowledge base
- Multi-language email generation

---

# License

This project is licensed under the MIT License.

---

