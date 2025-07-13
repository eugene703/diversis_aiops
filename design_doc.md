# Design Document: Data Analyst Chat Agent

## **Problem Statement**

Modern e-commerce platforms generate immense amounts of clickstream data, tracking every user interaction—from product views and cart additions to purchases—across thousands of products and categories. However, extracting actionable business insights from this raw, event-level data typically requires specialized analytics skills and manual querying.

### Challenge:
Despite the data’s potential, business leaders and operational teams lack an accessible, real-time way to turn raw events into actionable insights. Analytics bottlenecks often slow down category management, campaign evaluation, and conversion optimization.

### AI Transformation Objective:
To accelerate value creation, we are deploying an AI-powered chat analyst agent. This tool enables business stakeholders—category managers, marketers, and executives—to interact directly with the company’s behavioral data using plain-English questions. The agent automatically:

- Translates business questions into targeted SQL queries

- Extracts and analyzes relevant data

- Returns clear explanations and visualizations, empowering rapid and informed decision-making

This capability aims to democratize data access, reduce analytics cycle time, and drive measurable improvements in growth, margin, and customer experience—aligning with the PE firm’s broader digital transformation and value realization strategy.

## **Data Scope**

**Dataset:**

* [E-commerce behavior data from multi-category store (Kaggle)](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store/data)
* Contains detailed clickstream data from a large multi-category online retailer, covering:

  * **Event types:** product view, add-to-cart, remove-from-cart, and purchase
  * **Event time:** timestamped at the second
  * **Product and category metadata**
  * **User and session identifiers**

**Subset Used for Prototype:**

* **Timeframe:** For this implementation, I use **November 2019** (`2019-Nov.csv`) and **October 2019** (`2019-Oct.csv`) as a representative sample

  * Balances high event volume with manageable file size for rapid prototyping and demonstration
* **Categories:** All available product categories included to maximize business question diversity

**Sample Data Columns:**

* `event_time` (timestamp)
* `event_type` (view, cart, remove\_from\_cart, purchase)
* `product_id`, `category_id`, `category_code`
* `brand`, `price`
* `user_id`, `user_session`

## **Design Choices**

### **a. System Architecture**

* **Frontend:** [Chainlit](https://github.com/Chainlit/chainlit) for conversational chat interface
* **Agent Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) for managing LLM tool usage and reasoning steps
* **Database:** PostgreSQL (via Docker Compose) for scalable, SQL-based analytics
* **Data Layer:** Pandas for result manipulation and matplotlib/plotly for charting

### **b. Reasoning/Planning**

* **LLM-driven tool-use:** Agent interprets business question, generates relevant SQL query, executes it, summarizes results, and (optionally) visualizes insights.
* **Chain-of-thought tracing:** Each reasoning step (intent recognition, SQL construction, execution, summarization) can be logged and displayed for transparency.

### **c. Modularity & Extensibility**

* **Separation of Concerns:**

  * DB setup and import scripts are independent from app logic
  * Data-access layer abstracts DB connection from the agent logic
  * Easily swap out charting or agent modules

### **d. Tradeoffs**

* Chose a relational DB (Postgres) for robust, well-known analytics workflow, at the cost of slightly more setup vs. Pandas-only
* Focused on a single month for rapid prototyping and easier resource management
* Leverages LLMs for SQL generation; this enables flexible user queries but requires careful prompt and tool design to ensure correctness


## **4. Why This Design?**

* Mimics realistic business-user workflows: ask, understand, visualize, act
* Each piece (Chainlit, LangGraph, Postgres, charting) can be swapped or scaled as needed
* The architecture supports easy demoing, debugging, and future productionization

