# Take Home Project for Diversis AIOPS

This project demonstrates an AI-powered data-insight chat analyst agent that enables business users to ask natural language questions over e-commerce clickstream data. The agent translates user questions into SQL, runs them over a large dataset (67M rows), and returns insights as plain English and charts—all in a modern chat interface.

---

## **Getting Started**

### **1. Python Environment Setup**

This project requires **Python 3.12.3**.
Create and activate a virtual environment:

```bash
python3 -m venv env
source env/bin/activate
```

---

### **2. Install Dependencies**

```bash
pip install -r requirements.txt
```

---

### **3. Environment Variables**

Create a `.env` file in the project root with the following (replace with your actual keys):

```env
ANTHROPIC_API_KEY=your_anthropic_key
LANGCHAIN_API_KEY=your_langchain_key
LANGCHAIN_TRACING_V2=true
```

---

### **4. Download and Prepare the Dataset**

This will download the e-commerce behavior dataset from Kaggle, extract the CSVs, and convert them to Parquet format for fast querying with DuckDB.

```bash
python import_data.py
```

Parquet files will be saved to the `data/` folder.

---

### **5. Run the Application**

```bash
PYTHONPATH=$(pwd) chainlit run src/chainlit_app.py
```

Then open the provided local URL to start asking business questions in the chat UI!

---

## **Project Structure**

```
.
├── data/                # Parquet data files (auto-generated)
├── src/
│   ├── agent.py         # Main Agent orchestration logic
│   ├── tools.py         # Sub Agents and functions to help the main agent
│   └── chainlit_app.py  # Chainlit chat app
├── import_data.py       # Download and convert dataset to Parquet
├── requirements.txt
├── .env.example
├── design_doc.md        # Documentation with justifications for design choices 
└── README.md
```

---

## **How it Works**

* **Ask business questions** in natural language via the chat UI
* **Agent generates SQL** queries to answer your questions
* **Queries run on DuckDB** directly over Parquet files for high performance (no database server needed)
* **Results are displayed** in plain English and optionally as charts

---

## **Notes**

* Data is downloaded from [Kaggle: E-commerce behavior data from multi-category store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store/data)
* Large files are handled efficiently with Parquet + DuckDB
* Requires API keys for Anthropic and LangChain LLM integration

---

## **Contact / Questions**

For any questions about setup or architecture, please contact \[Your Name Here] or open an issue.

---

Let me know if you want a more technical/brief/verbose version, or a separate “About the Problem” or “Design Choices” section!
