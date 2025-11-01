# Receipty

[> **Receipty dashboard live demo** <](https://receipty-paul-lch.streamlit.app/)

*You can log into the **Receipty dashboard live demo** using the following password :*
- **Guest:** `guest123`

*Please note: The demo currently runs on synthetically generated data. This approach was deliberately chosen to build and validate all dashboard functionalities first. While this may result in some data inconsistencies, this development step does not affect the final architecture, which is designed to process real-time, structured data accurately.*

---

#### **Receipty** is a personal project for automated expense tracking based on shopping receipts. The user sends a photo of a receipt, which is then processed to extract purchases, categorize expenses, generate visual statistics, and provide saving advice. The project combines OCR, NLP, API development, and a data visualization dashboard.

## Technical Stack & Architecture

* **Backend:** Python 3.13, FastAPI, Pydantic
* **Database:** Supabase (PostgreSQL)
* **AI & Data Processing:** LLMs-strucutured output (in progress), OCR Library (future)
* **Frontend & Visualization:** Streamlit, Streamlit Community Cloud
* **Development & Tooling:** UV, Pre-commit hooks, Git & GitHub, Pytest

![Receipty Architecture](/assets/receipty_architecture.jpg)

## Current Status

The project currently features a **deployed and functional Streamlit dashboard** that provides interactive analysis of expense data.

The **backend infrastructure is fully operational**:
* The database schema is established in Supabase (PostgreSQL).
* Data generation scripts (for both clean demo data and raw simulated OCR text) are complete.
* The end-to-end data processing pipeline is functional: A FastAPI endpoint (`/process-receipts`) triggers a background task that reads 'pending' receipts, sends the raw text to the **OpenAI API** (`gpt-4o-mini`), and uses **Pydantic** models with OpenAI's **Tool Calling** feature to enforce a reliable **structured JSON output**. This response is then validated and used to correctly populate the database.

## Next Steps

1.  **Automate Processing Trigger:** The current LLM pipeline is triggered manually. The immediate next step is to automate this process. This will involve:
    * Deploying the FastAPI application (which includes the `llm_processor`) to a production service like **Render**.
    * Implementing a **Supabase Database Webhook** (or Trigger) that automatically calls the deployed API endpoint whenever a new receipt is inserted with a 'pending' status.

2.  **Integrate OCR:** Replace the simulated text script with a true OCR component (e.g., OpenCV, Tesseract, or a cloud vision API) to process actual image files from a user.

3.  **Add Testing:** Implement unit and integration tests using `pytest` to ensure data integrity and the reliability of the LLM pipeline.
