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
* **Development & Tooling:** UV, Pre-commit hooks, Git & GitHub, Faker, Pytest

![Receipty Architecture](/assets/receipty_architecture.jpg)

## Current Status

The project currently features a deployed and functional Streamlit dashboard that provides interactive analysis of expense data. The backend infrastructure is established with a clear database schema on Supabase (PostgreSQL), and scripts are in place to generate both clean and raw simulated data for development and demonstration purposes.


## Next Steps

1.  **Implement LLM Processing:** Develop the Python logic to read 'pending' receipts, send the `extracted_text` to an LLM for structured data extraction, and populate the database accordingly.
2.  **Integrate OCR:** Add an OCR component to process actual image files and feed the `extracted_text` into the pipeline.
3.  **Add Testing:** Implement unit and integration tests using `pytest` to ensure data integrity and component reliability.
