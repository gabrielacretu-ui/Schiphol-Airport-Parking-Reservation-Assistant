# Schiphol Airport Parking Reservation Assistant

A Python-based intelligent assistant for managing parking reservations at Schiphol Airport. The system is built around a multi-agent pipeline: a **chatbot** converses with users, an **admin agent** reviews and approves reservation actions, and a **FastMCP server** executes the approved operations and logs every event to a secured FastAPI endpoint.

---

## Features

- **Chatbot agent** — converses with users, validates input, and prepares reservation actions using LangChain tool-calling (gpt-4o-mini)
- **Admin agent** — independently reviews every reservation request and approves or rejects it based on configurable policies
- **LangGraph pipeline** — the full chatbot → admin → MCP workflow is modelled as a compiled state graph (`build_graph()`)
- **Dual database**
  - **SQLite** for structured reservation and parking-space data
  - **Weaviate** (local, Docker) for semantic RAG retrieval of static parking information
- **MCP server** — FastMCP subprocess that executes make / cancel / modify operations and forwards events to the REST API
- **FastAPI logging server** — receives approved reservation events, writes them to a flat log file, and exposes an authenticated `/reservations` endpoint for auditing
- **Input guardrails** — Presidio-based PII masking (credit cards, IBAN, email, phone, Dutch BSN, Dutch passport); Dutch licence plate validation via the live RDW API; fuzzy matching for location and name fields
- **RAG evaluation** — Stage 1 includes a `rag_evaluator.py` for measuring retrieval quality

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| Docker + Docker Compose | any recent version |

You will also need API keys for:

- **OpenAI** (used for all LLM calls)
- **FastAPI logging server** (a secret you choose yourself — see below)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/gabrielacretu-ui/Schiphol-Airport-Parking-Reservation-Assistant.git
cd Schiphol-Airport-Parking-Reservation-Assistant
```

### 2. Install the package and its dependencies

```bash
pip install -e .
```

The project ships a `pyproject.toml`; installing in editable mode makes the `parking` package importable from every Stage script.

---

## Environment Configuration

Create a `.env` file in the **project root** with the following variables:

```env
OPENAI_API_KEY=<your_openai_key>

# Secret used by the FastAPI server to authorise incoming events
FASTAPI_KEY=<any_secret_string>

# Leave as default if running locally with Docker
MCP_SERVER_URL=http://127.0.0.1:8000
WEAVIATE_URL=http://localhost:8180

# Optional overrides
DB_PATH=dynamic_parking.db
LLM_MODEL=gpt-4o-mini
```

---

## Reset to a Clean State

Run this before a fresh setup to tear down all containers, volumes, and generated data files.

```powershell
# Kill anything running on port 8000 (FastAPI logging server)
$proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess
if ($proc) { Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue }

# Stop and remove containers, volumes, and orphaned services
docker-compose down -v --remove-orphans
docker volume prune -f

# Delete local data
Remove-Item -Recurse -Force .\collections -ErrorAction SilentlyContinue
Remove-Item -Force .\parking_static_data.joblib -ErrorAction SilentlyContinue
Remove-Item -Force .\logs -ErrorAction SilentlyContinue
Remove-Item -Force .\dynamic_parking.db -ErrorAction SilentlyContinue
```

After this, follow the Setup & Initialisation steps below from scratch.

---

## Setup & Initialisation

Follow these steps **in order** before running any stage.

### 1. Start Weaviate

```bash
docker-compose up -d
```

This starts three containers:

| Container | Purpose | Port  |
|---|---|-------|
| `weaviate` | Vector database API | 50051 |
| `t2v-transformers` | `all-MiniLM-L6-v2` embeddings | 8081  |
| `t2v-reranker` | `baai-bge-reranker-v2-m3` reranker | 8082  |

Weaviate data is persisted in `./collections/`.

### 2. Initialise the databases

```bash
python -m scripts.database_seeding      # creates SQLite tables and seeds sample data
python -m scripts.weaviate_seeding # seeds Weaviate with static parking information
```

### 3. Start the FastAPI logging server

```bash
python -m uvicorn parking.mcp.api:app --port 8000
```

The server exposes:

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check |
| `/reservation-events-approved` | POST | Receives approved events (requires `x-api-key` header) |
| `/reservations` | GET | Returns all logged events (requires `x-api-key` header) |

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Running the Stages

Each stage is a self-contained script. The stages are incremental — each one builds on the previous.

### Stage 1 — Chatbot

A standalone chatbot agent with conversation memory. Queries the SQLite database and Weaviate for information; validates and prepares reservation requests but does not write to the database.

```bash
python -m Stage_1.main
```

Run the automated test suite:

```bash
python -m unittest Stage_1.tests
```

Run the RAG evaluator:

```bash
python -m Stage_1.rag_evaluator
```

### Stage 2 — Chatbot + Admin Approval

Introduces the admin agent. After the chatbot validates a reservation action, the admin agent runs its own tool checks (reservation history, advance-booking limit, duration limits) and issues an APPROVE or REJECT decision.

```bash
python -m Stage_2.main
```

```bash
python -m unittest Stage_2.tests
```

### Stage 3 — MCP Logging Integration

Adds the MCP server layer. Approved operations are routed through the FastMCP subprocess via the stdio protocol, written to the database, and forwarded to the FastAPI logging server.

> Requires the FastAPI server to be running (Step 3 above).

```bash
python -m Stage_3.main
```

### Stage 4 — LangGraph Pipeline

The complete system modelled as a compiled LangGraph state graph. All components from the previous stages are wired together into a single callable pipeline built by `build_graph()`.

```bash
python -m Stage_4.main
```

---

## System Architecture

### Agent workflow (Stage 4)

```
User input
    └─► agent_chatbot_calling
            │
            ├─ (read-only query / validation failed) ──► END
            │
            └─ (reservation action validated as 'success')
                    └─► admin_chatbot_calling
                                │
                                ├─ (REJECT) ──► END
                                │
                                └─ (APPROVE)
                                        └─► mcp_logging
                                                │
                                                └─► END
```

### MCP execution path

When the admin approves:

1. `router.py` — an LLM selects the right MCP tool (`make_reservation`, `cancel_reservation`, or `modify_reservation`) from the validated payload
2. `server.py` — the FastMCP subprocess receives the call over stdio, writes to SQLite, and POSTs the event to the FastAPI server
3. `api.py` — the FastAPI server authenticates the request, appends the event to `logs/confirmed_reservations_events.txt`, and stores it in memory

### Input validation pipeline

Every user message passes through:

1. **Presidio anonymiser** — masks PII (credit cards, IBAN, email, phone, IP address, Dutch BSN, Dutch passport number)
2. **RDW licence plate check** — validates Dutch plates against the live RDW open data API
3. **Fuzzy DB validation** — verifies parking location and customer name against existing database values using difflib (cutoff 0.6)
4. **Dutch name standardisation** — capitalises name parts and preserves lowercase prefixes (*van*, *de*, *ter*, …)

### Admin policy checks

The admin agent runs these tools before issuing a decision:

| Tool | Rule |
|---|---|
| `check_car_reservation_history_tool` | A car may not have more than 9 active reservations |
| `check_advance_booking_tool` | Reservations cannot be made more than 30 days ahead |
| `check_reservation_length_tool` | Duration must be between 1 hour and 14 days |
| `check_available_slots_creation_tool` | At least one spot must be free at the requested location and time |
| `check_available_slots_modification_tool` | Same check applied when modifying an existing reservation |

---

## Project Structure

```
Schiphol-Airport-Parking-Reservation-Assistant/
│
├── src/
│   └── parking/
│       ├── agents/
│       │   ├── chatbot.py          LangChain chatbot agent factory
│       │   └── admin.py            LangChain admin agent factory
│       ├── database/
│       │   ├── connection.py       SQLite connection helper
│       │   ├── schema.py           Table creation + auto-seed
│       │   ├── seed.py             Sample parking spaces and reservations
│       │   ├── vector.py           Weaviate client + collection management
│       │   └── vector_seed.py      Seeds Weaviate with static PDF content
│       ├── mcp/
│       │   ├── server.py           FastMCP server (make/cancel/modify/list)
│       │   ├── api.py              FastAPI logging server
│       │   └── router.py           LLM-based MCP tool router (stdio client)
│       ├── pipeline/
│       │   └── graph.py            build_graph() — compiled LangGraph pipeline
│       ├── services/
│       │   ├── guard_rails.py      PII masking, plate validation, name standardisation
│       │   ├── queries.py          DB query helpers (availability, reservations, …)
│       │   └── reservation.py      Core make/cancel/modify business logic
│       ├── tools/
│       │   ├── read.py             Chatbot read tools (availability, info, …)
│       │   ├── write.py            Chatbot write tools (validate make/cancel/modify)
│       │   ├── admin_checks.py     Admin policy check tools
│       │   └── search.py           Weaviate RAG search tool
│       └── config.py               Centralised config from .env
│
├── Stage_1/
│   ├── main.py                  Chatbot-only interactive loop
│   ├── tests.py     Automated chatbot tests
│   └── rag_evaluator.py            RAG retrieval quality evaluation
├── Stage_2/
│   ├── main.py                  Chatbot + admin agent loop
│   └── tests.py
├── Stage_3/
│   └── main.py                  Adds MCP logging (imperative style)
├── Stage_4/
│   └── main.py                  LangGraph pipeline entry point
│
├── scripts/
│   ├── database_seeding.py         Initialise SQLite (creates tables + seeds data)
│   └── weaviate_seeding.py         Seed Weaviate with parking PDF chunks
│
├── collections/                    Weaviate persistent data (Docker volume)
├── logs/
│   └── confirmed_reservations_events.txt
├── docker-compose.yaml
├── pyproject.toml
└── README.md
```

---

## License

MIT License

---

## Author

**Gabriela Creţu** — EPAM Systems  
[gabriela_cretu@epam.com](mailto:gabriela_cretu@epam.com)
