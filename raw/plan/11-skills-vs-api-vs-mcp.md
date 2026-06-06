# Skills vs API vs MCP — How They Differ in Our Context

---

## TL;DR

| Concept | What it is | Analogy | In LUCIA |
|---------|-----------|---------|----------|
| **NIM API** | HTTP endpoint to call a model | A phone call to a specialist | "Hey Nemotron, answer this question" |
| **Skill** | Packaged knowledge that teaches an agent HOW to use a tool | A training manual for an employee | "Here's how to solve routing problems with cuOpt" |
| **MCP** | Standard protocol for agents/tools to discover and talk to each other | A universal translator between departments | "Agent A, ask Tool B for weather data using this standard format" |

---

## Detailed Breakdown

### 1. NIM API (Model Inference Endpoint)

**What**: A REST/gRPC endpoint that takes input → runs a model → returns output.

**Level**: Low-level. Model-to-application interface.

**Example in LUCIA**:
```python
# Direct NIM API call — you're just calling a model
import openai

client = openai.OpenAI(base_url="http://localhost:8001/v1")
response = client.chat.completions.create(
    model="nvidia/nemotron-3-nano",
    messages=[{"role": "user", "content": "Summarize this traffic data..."}]
)
```

**Characteristics**:
- OpenAI-compatible REST API format
- Stateless (send request, get response)
- No tool discovery, no orchestration logic
- You manage which model to call and when
- Runs locally on DGX Spark OR via build.nvidia.com hosted endpoints

**Available NIMs we'd call**:
| NIM Endpoint | Input | Output |
|-------------|-------|--------|
| `/v1/chat/completions` (Nemotron) | Text prompt | Text response |
| `/v1/embeddings` (NV-Embed) | Text | Vector [4096] |
| `/v1/rerank` (Reranker) | Query + docs | Ranked scores |
| `/v1/audio/transcriptions` (ASR) | Audio file | Text |
| `/v1/audio/speech` (TTS) | Text | Audio file |

---

### 2. Skills (Agent Capability Packages)

**What**: Pre-packaged instructions + code that teach an agent HOW to accomplish a task using NVIDIA tools. Think of them as "recipes" or "playbooks" for the agent.

**Level**: Mid-level. Sits between raw API and orchestration.

**Example in LUCIA**:
```yaml
# A skill tells the agent: "Here's how to solve routing problems"
# It includes: prompts, code templates, API patterns, constraints

skill: cuopt-routing-api-python
description: "Solve vehicle routing, scheduling, and traffic optimization"
instructions: |
  When the user asks about optimal routes, traffic rerouting, or 
  scheduling, use the cuOpt Python API:
  1. Model the road network as a graph
  2. Define constraints (road closures, capacity)
  3. Call cuopt.routing.Solver()
  4. Return optimized routes with ETA
code_template: |
  from cuopt import routing
  solver = routing.Solver()
  solver.set_network(graph)
  result = solver.solve()
```

**Characteristics**:
- Contains INSTRUCTIONS (not just an endpoint)
- Tells the agent WHEN and HOW to use a capability
- May wrap multiple API calls into a coherent workflow
- Installable via CLI: `npx skills add nvidia/skills --skill cuopt`
- Agent reads the skill to learn what it can do

**Key difference from API**:
> An **API** is a door. A **Skill** is the knowledge of when to open the door, what to say when you walk through, and what to do with what you find on the other side.

---

### 3. MCP — Model Context Protocol (Interoperability Standard)

**What**: A universal protocol that standardizes how agents discover tools, invoke them, and share context — regardless of vendor or framework.

**Level**: High-level. Agent-to-agent and agent-to-tool communication standard.

**Example in LUCIA**:
```python
# MCP Server: LUCIA exposes its tools for any MCP client to discover
# Any MCP-compatible agent can find and call LUCIA's tools

# server config (YAML in NeMo Agent Toolkit)
mcp_server:
  transport: streamable-http
  port: 8080
  tools:
    - name: traffic_query
      description: "Query London traffic data"
      parameters:
        road: string
        time_range: string
    - name: weather_forecast
      description: "Get AI weather prediction for London location"
      parameters:
        lat: float
        lon: float
        hours_ahead: int
```

```python
# MCP Client: LUCIA discovers and calls external MCP tools
from nemo_agent_toolkit.mcp import MCPClient

weather_service = MCPClient("http://weather-agent:8080")

# Auto-discover available tools
tools = await weather_service.list_tools()
# → [{"name": "forecast", "description": "...", "parameters": {...}}]

# Invoke tool with context passing
result = await weather_service.call_tool("forecast", {
    "lat": 51.5074, "lon": -0.0878, "hours_ahead": 24
})
```

**Characteristics**:
- **Discovery**: Tools self-describe (agents find what's available at runtime)
- **Standardized**: Any MCP client talks to any MCP server (vendor-neutral)
- **Context passing**: Rich context flows between agents (not just request/response)
- **Session state**: Can maintain conversation/workflow state across calls
- **Streaming**: Supports real-time streaming responses
- **Auth**: Built-in JWT/API key authentication

**Key difference from API and Skills**:
> An **API** is a specific phone number. A **Skill** teaches you who to call. **MCP** is the phone network itself — it lets anyone discover, connect to, and communicate with anyone else using a shared standard.

---

## How All Three Work Together in LUCIA

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│   User: "What happens to traffic on London Bridge when it rains?"    │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌───────────────────────────────────────────────────────────┐      │
│   │  AGENT (NemoClaw + NeMo Agent Toolkit)                     │      │
│   │                                                            │      │
│   │  1. READS SKILLS to understand what tools are available    │      │
│   │     └─ "I have: rag_search, sql_query, weather_forecast,  │      │
│   │         traffic_optimizer (cuOpt), earth2studio..."        │      │
│   │                                                            │      │
│   │  2. PLANS using LLM (calls NIM API for reasoning)         │      │
│   │     └─ NIM API call: POST /v1/chat/completions            │      │
│   │        → "I need weather data + traffic data + correlation"│      │
│   │                                                            │      │
│   │  3. EXECUTES tools:                                        │      │
│   │     a) Via MCP → calls weather tool (earth2studio)        │      │
│   │        └─ MCP protocol: discover → invoke → get result    │      │
│   │     b) Via NIM API → calls embedding model                │      │
│   │        └─ POST /v1/embeddings → vector search             │      │
│   │     c) Via Skill code → runs cuOpt routing analysis       │      │
│   │        └─ Skill taught agent the cuOpt Python pattern     │      │
│   │                                                            │      │
│   │  4. SYNTHESIZES (calls NIM API for final answer)          │      │
│   │     └─ NIM API call: POST /v1/chat/completions            │      │
│   │        → "When it rains on Friday, London Bridge traffic   │      │
│   │           increases 34%, with cascading delays on A3..."   │      │
│   │                                                            │      │
│   └───────────────────────────────────────────────────────────┘      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Comparison Matrix

| Dimension | NIM API | Skill | MCP |
|-----------|---------|-------|-----|
| **Purpose** | Call a model/service | Teach agent a capability | Connect agents & tools |
| **Who uses it** | Developer (code) | Agent (runtime learning) | Agent ↔ Agent/Tool |
| **Format** | REST/gRPC endpoint | YAML + code templates | Protocol spec (HTTP/SSE) |
| **Discovery** | Manual (you hardcode URL) | Agent reads skill manifest | Auto-discovery at runtime |
| **Statefulness** | Stateless | Stateless (instructions) | Stateful (sessions) |
| **Vendor lock-in** | NVIDIA NIM specific | NVIDIA skills catalog | Vendor-neutral standard |
| **When needed** | Always (model inference) | Setup time (configure agent) | Multi-tool/multi-agent systems |
| **Analogy** | The engine | The driving manual | The road network |

---

## In Our Hackathon: What We Actually Use

### NIM APIs (Direct model calls)
```
✅ Nemotron 3 Nano/Super  → /v1/chat/completions (reasoning)
✅ NV-Embed-v2            → /v1/embeddings (vector generation)  
✅ NeMo Reranker          → /v1/rerank (result ordering)
✅ Nemotron ASR           → /v1/audio/transcriptions (voice in)
✅ Magpie TTS             → /v1/audio/speech (voice out)
✅ Content Safety         → /v1/safety/check (guardrails)
```

### Skills (Agent capabilities)
```
✅ rag-blueprint          → Teaches agent how to do RAG
✅ cuopt-routing           → Teaches agent traffic optimization
✅ earth2studio            → Teaches agent weather forecasting
✅ nemoclaw-agent-skills   → Teaches agent sandbox patterns
🎯 cudf                    → Teaches agent GPU data processing
🎯 deepstream             → Teaches agent video analytics
```

### MCP (Tool orchestration protocol)
```
✅ NeMo Agent Toolkit MCP Server → Expose LUCIA tools externally
✅ MCP Client in agent           → Discover & call tools dynamically
✅ Tool registration             → Tools self-describe their capabilities
✅ Context passing               → State flows between tool calls
```

---

## Why MCP Matters for Scoring

Using MCP shows **systems engineering maturity** (judges look for this):

1. **Modularity** — Tools are independently deployable MCP servers
2. **Extensibility** — Add new tools without changing agent code
3. **Standard compliance** — Industry-standard protocol (not custom glue)
4. **Multi-agent ready** — Could have specialist sub-agents communicate
5. **NVIDIA ecosystem** — NeMo Agent Toolkit has native MCP support

### Demo talking point:
> "Our tools are exposed as MCP servers. If the City of London wanted to add a new data source tomorrow — say, Thames flood sensors — they'd just deploy an MCP server. LUCIA would auto-discover it and start using it. No code changes needed."

---

## Architecture Decision

For the hackathon, our stack uses all three layers:

```
┌────────────────────────────────────────────┐
│  MCP Layer (NeMo Agent Toolkit)            │  ← Tool discovery & orchestration
│  ┌──────────────────────────────────────┐  │
│  │  Skills (installed in agent)          │  │  ← Agent knowledge/capabilities  
│  │  ┌────────────────────────────────┐  │  │
│  │  │  NIM APIs (model endpoints)     │  │  │  ← Raw model inference
│  │  └────────────────────────────────┘  │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

Each layer builds on the one below it.
