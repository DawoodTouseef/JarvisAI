# System Diagram Reference

## Complete System Architecture

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                              FRONTEND LAYER                              ║
║                                                                           ║
║  ┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────┐    ║
║  │  Speech Recognition │  │    React App     │  │   WebSocket      │    ║
║  │                     │  │                  │  │   Connections    │    ║
║  │ • Capture audio     │  │ • State mgmt     │  │                  │    ║
║  │ • Transcribe        │  │ • UI Components  │  │ • /agents        │    ║
║  │ • VAD detection     │  │ • Task polling   │  │ • /agent-continue│    ║
║  └────────┬────────────┘  └────────┬─────────┘  └────────┬─────────┘    ║
║           │                        │                     │               ║
║           └────────────────────────┼─────────────────────┘               ║
║                                    │                                     ║
║         User Speech ←────────────┤├────────────→ Server Events           ║
║         Transcription            │  Clarification, Status, Results       ║
║                                                                           ║
╚════════════════════════════════════╤════════════════════════════════════╝
                                     │
                                     │ WebSocket
                                     │
╔════════════════════════════════════▼════════════════════════════════════╗
║                         FASTAPI BACKEND LAYER                           ║
║                                                                          ║
║  ┌──────────────────────────────────────────────────────────────────┐  ║
║  │              AgentWebSocketIntegration                           │  ║
║  │              (server/agent_integration.py)                       │  ║
║  │                                                                  │  ║
║  │  Responsibilities:                                              │  ║
║  │  • Route incoming WebSocket messages                            │  ║
║  │  • Maintain task_id → websocket mapping                         │  ║
║  │  • Setup clarification callbacks                                │  ║
║  │  • Handle 5 message types: submit, transcribe, cancel,          │  ║
║  │    status, clarification_response                               │  ║
║  └────────────────────┬─────────────────────────────────────────┬──┘  ║
║                       │                                         │      ║
║        ┌──────────────▼──────────────────┐                     │      ║
║        │                                 │                     │      ║
║        │   TaskManager                   │  ← Clarification ──┘      ║
║        │  (server/agents/task_manager.py)│     Callback Setup         ║
║        │                                 │                            ║
║        │  Responsibilities:              │                            ║
║        │  • Create tasks (async)         │                            ║
║        │  • Track status (PENDING,       │                            ║
║        │    RUNNING, COMPLETED,          │                            ║
║        │    FAILED, CANCELLED)           │                            ║
║        │  • Persist to database          │                            ║
║        │  • Manage concurrency (max 10)  │                            ║
║        │  • Trigger callbacks            │                            ║
║        └──────────────┬──────────────────┘                            ║
║                       │                                              ║
║        ┌──────────────▼────────────────────────┐                    ║
║        │                                       │                    ║
║        │   CentralOrchestrator                 │                    ║
║        │  (server/agents/orchestrator.py)      │                    ║
║        │                                       │                    ║
║        │  Workflow:                            │                    ║
║        │  1. Decompose task                    │                    ║
║        │  2. Route to agents                   │                    ║
║        │  3. Execute agents                    │                    ║
║        │  4. Synthesize results                │                    ║
║        │  5. Finalize response                 │                    ║
║        │                                       │                    ║
║        │  Clarification Support:               │                    ║
║        │  • Call resolve_clarification()       │                    ║
║        │  • Set websocket callback             │                    ║
║        └────────────────┬──────────────────────┘                    ║
║                         │                                           ║
║        ┌────────────────▼────────────────────────┐                 ║
║        │                                        │                 ║
║        │   Agent Pool                           │                 ║
║        │   (server/agents/)                     │                 ║
║        │                                        │                 ║
║        │  ┌──────────────────────────────────┐ │                 ║
║        │  │ DeepSearchAgent                  │ │                 ║
║        │  │ - Investigative research         │ │                 ║
║        │  │ - Can clarify: scope, depth      │ │                 ║
║        │  └──────────────────────────────────┘ │                 ║
║        │                                        │                 ║
║        │  ┌──────────────────────────────────┐ │                 ║
║        │  │ WebSearchAgent                   │ │                 ║
║        │  │ - Web browsing & search          │ │                 ║
║        │  │ - Can clarify: query, sites      │ │                 ║
║        │  └──────────────────────────────────┘ │                 ║
║        │                                        │                 ║
║        │  ┌──────────────────────────────────┐ │                 ║
║        │  │ CodeInterpreterAgent             │ │                 ║
║        │  │ - Code execution & analysis      │ │                 ║
║        │  │ - Can clarify: language, format  │ │                 ║
║        │  └──────────────────────────────────┘ │                 ║
║        │                                        │                 ║
║        │  ┌──────────────────────────────────┐ │                 ║
║        │  │ SystemAgent                      │ │                 ║
║        │  │ - System operations              │ │                 ║
║        │  │ - Can clarify: scope, safety     │ │                 ║
║        │  └──────────────────────────────────┘ │                 ║
║        │                                        │                 ║
║        │  ┌──────────────────────────────────┐ │                 ║
║        │  │ ResponseGenerationAgent          │ │                 ║
║        │  │ - Synthesize results             │ │                 ║
║        │  │ - Can clarify: format, style     │ │                 ║
║        │  └──────────────────────────────────┘ │                 ║
║        │                                        │                 ║
║        └────────────────┬─────────────────────┘                  ║
║                         │                                         ║
║  ┌──────────────────────▼──────────────────────────────────────┐ ║
║  │                                                             │ ║
║  │          AgentClarificationTool                            │ ║
║  │         (server/agents/tools/agent_clarification.py)       │ ║
║  │                                                             │ ║
║  │  Responsibilities:                                         │ ║
║  │  • Store pending clarifications (task_id → Future)         │ ║
║  │  • Async wait for user response (non-blocking)             │ ║
║  │  • Support timeouts (5 minutes default)                    │ ║
║  │  • Send questions to frontend via WebSocket callback       │ ║
║  │  • Resolve futures when responses arrive                   │ ║
║  │                                                             │ ║
║  │  Key Methods:                                              │ ║
║  │  • request_clarification(question, task_id, timeout)       │ ║
║  │  • resolve_clarification(task_id, response)                │ ║
║  │  • get_pending_tasks()                                     │ ║
║  │                                                             │ ║
║  └────────────────────┬─────────────────────────────────────┬─┘ ║
║                       │                                     │    ║
║                       │ Mongita                             │    ║
║                       │ Database                            │    ║
║                       │                                     │    ║
║        ┌──────────────▼──────────────────────────────────┐  │    ║
║        │                                                │  │    ║
║        │   Mongita Local Database                       │  │    ║
║        │   (./db/tasks_db/)                             │  │    ║
║        │                                                │  │    ║
║        │  • Store tasks with full lifecycle             │  │    ║
║        │  • Persist status & results                    │  │    ║
║        │  • Auto-cleanup old tasks                      │  │    ║
║        │  • Support queries by status                   │  │    ║
║        │                                                │  │    ║
║        └────────────────────────────────────────────────┘  │    ║
║                                                             │    ║
║                                    Callback ───────────────┘    ║
║                                    (send clarification              ║
║                                     to frontend)                   ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════╝
```

## Message Flow Sequences

### Sequence 1: Task Submission
```
Frontend                      Backend
   │                            │
   ├─ /agents connect ────────→ │
   │                            │
   ├─ agent_task_submit ──────→ AgentWebSocketIntegration
   │                            │
   │                            ├─→ TaskManager.create_task()
   │                            │
   │                            ├─→ asyncio.create_task(
   │                            │      orchestrator.submit_task()
   │                            │   )
   │                            │
   │←─────── task_id response ─┤
   │
   └─ Store taskId
```

### Sequence 2: Task with Clarification
```
Frontend                      Backend
   │                            │
   ├─ user_transcription ──────→ AgentWebSocketIntegration
   │                            │
   │                            ├─→ TaskManager
   │                            │   ├─→ Orchestrator
   │                            │      ├─→ Agents (executing)
   │                            │         │
   │                            │         ├─→ Agent needs clarification
   │                            │            │
   │                            │            └─→ tool.request_clarification(
   │                            │                   "What format?",
   │                            │                   task_id
   │                            │                )
   │                            │         │
   │                            ├─────────┤ Future created
   │                            │ (blocked│ pending response)
   │                            │         │
   │←─── agent_clarification ──┤         │
   │     request event         │         │
   │                            │         │
   ├─ Display question         │         │
   ├─ Enable microphone        │         │
   │                            │         │
   ├─ user_transcription ──────→ AgentWebSocketIntegration
   │    (response)              │
   │                            ├─→ handle_user_transcription()
   │                            │
   │                            ├─→ agent_clarification_tool
   │                            │   .resolve_clarification()
   │                            │
   │                            ├─ Future resolved
   │                            │ with response
   │                            │
   │                            ├─ Agent continues execution
   │                            │   (returns from request_
   │                            │    clarification() call)
   │                            │
   │                            ├─→ Task completes
   │                            │
   ├─ Poll /agent-continue ───→ │
   │                            │
   │←─ Task status: COMPLETED ─┤
   │   with result             │
   │
   └─ Display result
```

### Sequence 3: Status Polling
```
Frontend                      Backend
   │                            │
   ├─ /agent-continue connect ─→ │
   │                            │
   ├─ agent_task_status ──────→ AgentWebSocketIntegration
   │   (poll every 1-2s)        │
   │                            ├─→ TaskManager.get_task()
   │                            │
   │←─── status_response ──────┤
   │     status: "pending"      │
   │                            │
   ├─ [wait 1-2 seconds]       │
   │                            │ [Task executing...]
   │                            │
   ├─ agent_task_status ──────→ │
   │                            ├─→ TaskManager.get_task()
   │                            │
   │←─── status_response ──────┤
   │     status: "running"      │
   │                            │
   ├─ [wait 1-2 seconds]       │
   │                            │ [Task completing...]
   │                            │
   ├─ agent_task_status ──────→ │
   │                            ├─→ TaskManager.get_task()
   │                            │
   │←─── status_response ──────┤
   │     status: "completed"    │
   │     result: "..."          │
   │
   └─ Stop polling
      Display result
```

## Data Structure Examples

### Task Object
```
{
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "completed",
    "created_at": "2026-01-22T10:00:00",
    "started_at": "2026-01-22T10:00:05",
    "completed_at": "2026-01-22T10:00:45",
    "result": {
        "answer": "Python is a high-level programming language...",
        "sources": [...]
    },
    "error": null,
    "metadata": {
        "query": "What is Python?",
        "auth_token": "optional",
        "base_url": "optional",
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    },
    "priority": 1,
    "cancellable": true
}
```

### Clarification Future Object
```
{
    "task_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "future": <asyncio.Future>,
    "question": "Which format do you prefer: JSON or CSV?",
    "pending_since": "2026-01-22T10:00:15",
    "timeout": 300,
    "status": "pending"  // "pending" | "resolved" | "timeout" | "cancelled"
}
```

## State Transitions

### Task Lifecycle
```
              create_task()
                   │
                   ▼
              ┌────────────┐
              │  PENDING   │
              └─────┬──────┘
                    │ start execution
                    ▼
              ┌────────────┐
              │  RUNNING   │───→ agent needs clarification
              └─────┬──────┘      (pause, wait for response)
                    │
          ┌─────────┴─────────┐
          │                   │
      SUCCESS             FAILURE
          │                   │
          ▼                   ▼
      ┌────────────┐    ┌────────────┐
      │ COMPLETED  │    │   FAILED   │
      └────────────┘    └────────────┘
          ▲                   ▲
          │                   │
      User cancelled   Exception thrown
          │                   │
          └─────────┬─────────┘
                    │
               ┌────────────┐
               │ CANCELLED  │
               └────────────┘
```

### Clarification Lifecycle
```
         request_clarification()
              │
              ▼
         ┌────────────┐
         │  PENDING   │  asyncio.Future created
         │            │  Waiting for response
         └─────┬──────┘
              │
    ┌─────────┴──────────┐
    │                    │
User responds      Timeout
    │                    │
    ▼                    ▼
┌────────────┐      ┌────────────┐
│ RESOLVED   │      │  TIMEOUT   │
│ w/ response│      │ (None)     │
└────────────┘      └────────────┘
    ▲
    │
resolve_clarification() called
```

## Integration Points

```
┌─────────────────────────────────────────────────────────┐
│  Your Frontend                                          │
│  (React Component)                                      │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Needs to:                                         │ │
│  │ • Connect to /agents WebSocket                   │ │
│  │ • Connect to /agent-continue WebSocket           │ │
│  │ • Implement speech recognition                   │ │
│  │ • Implement speech synthesis (TTS)               │ │
│  │ • Handle agent_clarification_request events      │ │
│  │ • Poll agent_task_status regularly               │ │
│  │ • Display results when complete                  │ │
│  └──────────────────────┬────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
                          │
                  [WebSocket Bridge]
                          │
┌─────────────────────────────────────────────────────────┐
│  Backend (Ready Now!)                                   │
│  ┌───────────────────────────────────────────────────┐ │
│  │ Provides:                                         │ │
│  │ • /agents WebSocket endpoint                     │ │
│  │ • /agent-continue WebSocket endpoint             │ │
│  │ • Task creation & management                     │ │
│  │ • Agent clarification requests                   │ │
│  │ • Task status tracking                           │ │
│  │ • Result delivery                                │ │
│  │ • Error handling                                 │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## References

- **Architecture Details:** See AGENT_SYSTEM_ARCHITECTURE.md
- **API Reference:** See QUICK_REFERENCE.md
- **Implementation Guide:** See AGENT_CLARIFICATION_GUIDE.md
- **Frontend Setup:** See BACKEND_STATUS.md
