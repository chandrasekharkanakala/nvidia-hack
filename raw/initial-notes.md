Context
All submissions must align with one of the three Challenge Tracks below. Leveraging open data from the City of London, these tracks guide submissions across diverse facets of urban life and community growth.
Each track defines a theme of impact, not the scope of your idea – teams are free to build any solution using any of the open datasets linked above.
1. Economic Systems
Focus: Improving how money flows through the city across businesses, workers, and markets.
The Goal: Build agentic systems that help individuals and organizations make better economic decisions, unlock opportunities, or optimize costs.
2. Public Services
Focus: Enhancing how people access and interact with city services and resources.
The Goal: Use data to build tools that simplify navigation of public systems, making essential services more accessible, efficient, and user-friendly.
3. Urban Operations
Focus: Optimizing how London runs, from large-scale infrastructure to everyday city life.
The Goal: Develop systems that improve how the city functions behind the scenes and in real time.



Judging Criteria
Philosophy
We are judging Systems Engineering. A winning project isn't just a slide deck or a simple API wrapper; it is a functioning system that ingests raw data, processes it locally using the DGX Spark, and produces a valuable result.
The Scoring Breakdown (100 Points Total)
1. Technical Execution & Completeness (30 Points)
Did they actually build a working, complex system?
* 15 pts - Completeness: Does the system successfully complete the full data workflow without crashing?
* 15 pts - Technical Depth: Is there significant engineering "under the hood"? Did they build a complex pipeline (e.g., Simulation, RAG, Fine-Tuning, or Custom Logic) rather than just a simple static dashboard or basic API wrapper?
2. NVIDIA Ecosystem & Spark Utility (30 Points)
Did they leverage the unique hardware and software provided?
* 15 pts - The Stack: Did they use at least one major NVIDIA library/tool, NemoClaw, nemotran? (e.g., NIMs, RAPIDS, cuOpt, Modulus, NeMo Models). Note: Merely calling GPT-4 via API gets 0 points here.
* 15 pts - The "Spark Story": Can they articulate why this runs better on a DGX Spark?
    * Examples: "We used the 128GB Unified Memory to hold the video buffer and the LLM context simultaneously" or "We ran inference locally to ensure privacy/latency."
* 3. Value & Impact (20 Points)
* Is the solution actually useful?
* 10 pts - Insight Quality: Is the insight non-obvious and valuable? (e.g., "Traffic jams happen at 5 PM" is obvious. "Rain causes specific stalls on this specific ramp" is valuable).
* 10 pts - Usability: Could a real City Planner, or Factory Foreman actually use this tool to make a decision tomorrow?
* 4. Innovation & Execution (20 Points)
* Did they push the boundaries?
* 10 pts - Creativity: Did they combine data or models in a novel way? (e.g., Using vision models to "read" traffic maps).
* 10 pts - Performance: Did they optimize the system for speed or scale? (e.g., "We optimized the simulation to run at 50x real-time speed").

What we have 

Welcome to NVIDIA DGX Spark Version 7.5.0 (GNU/Linux 6.17.0-1021-nvidia aarch64)

This machine available via SSH to login from our machines.

What we need

We would want to build an working agent to end consumers where they can use Chat, API and Voice (from eleven labs integration) with choice of light and deep agent selection, history of chats etc 
Can take text, voice and images 

Usecase can be <TBC by me> - once use case finalised and based on context outcomes — need. Spec driven approach to develop using target architecture & design
use case outcome can be - insights (based on history), prediction, or 



1. Will use Nvidia family  - model nemotran (but based on use case we end up using different variations), Agent orchestration (nemoclaw could be choice) and etc
2. It’ll be front end and backend — (need to check how to run web in SSH based machine to run browser) otherwise backend runs purely on DGX but need to understand how to connect both.
3. Data ingestion 
    1. Raw data — I believe its structured (excel, csvs) but you can validate 
    2. Able to call or scrape the webpages in realtime — (for eg: weather APIs not free but so, call url and scrape) 
    3. Any other data 
4. Now, steps to make an proper agent (vector sets, RAG and memory etc)
5. Olly set up e2e, eval on data ingestion, reflection, hallusination and response and context windows, performance simutaion incl insights
6. Must be clean code, modular, secure
7. Must track every lib and SDK being used as a notes 

Lets start with high level e2e architecture covers every aspect and another version with what’s possible for this hackathon in 12 hours on top of that architecture

then next could be repo strcuture with every aspect to cover (incl docs, decision, why, copilot instructions etc )

