# ChatGPT Task Scheduler Prototype

## System Requirements

Build a job scheduler with an MCP (Model Context Protocol) interface:
- Users schedule tasks for future execution via MCP tool calls
- A background watcher scans for due jobs and pushes them to a queue
- Workers pull jobs from the queue and execute them
- Support task creation, listing, status checking, and cancellation
- Tool naming follows namespace + action verb pattern (e.g., `task.create`)

### Architecture

```
User → MCP Tool Call → Job Scheduler API → DB
                                            ↓
                              Watcher (scans DB) → Queue → Worker (executes)
```

## Design Questions

Answer these before you start coding:

1. **Watcher vs Cron:** Why separate the watcher from the worker? What problems does a single cron job that both scans and executes have?
  
    Ans: If a single cron job scans the database and then executes the tasks itself, it becomes a bottleneck. Here are the issues:
    - Scalability : If the cron job and worker are bundled together, scaling is limited to vertical scaling, which quickly hits reousrce bottlenecks. By decoupling the worker from the cron job, we can achieve horizontal scaling allowing us to increase resources by simply adding more worker instances.
    - Fate sharing: if one task failed, it causes the following tasks failed.
    - Execution Latency: If Task A takes 10 minutes to run, Task B (scheduled for 1 minute later) is blocked until Task A finishes.



2. **Queue Layer:** Why put a queue between the watcher and worker instead of having the watcher call the worker directly? What are the benefits?
    
    Ans: Here are the several advantages to put a queue between the watehr and worker:
    1. Buffering: If 10,000 tasks are due at exactly 9:00 AM, a drect call might crash your workers. A queue allow workers to process them at a steady, sustainable rate.
    2. Retry & Reliability: If a worker dies mid-task, a queue can automatically return the message to the queue for another worker to try.
    3. Decoupling: The watcher doesn't need to know how many workers exist or where they are located; it only needs to know how to "push".

3. **Time Bucket Partitioning:** Instead of `SELECT * WHERE scheduled_at <= now()`, why partition jobs by time bucket (e.g., hour)? What happens to query performance at 1M+ jobs without partitioning?

    Ans: Partitioning by time buckets allows the watcher to query a much smaller, dedicated table. This significantly improves query performance and enables dropping old table directly rather than excuting slow delete query.
    Querying 1M+ jobs without partitioning can lead to index bload and lock contention.

4. **Tool Naming:** Why `task.create` instead of `createTask`? How does naming convention affect LLM tool selection accuracy?

    Ans: Naming conventions significantly impact how an LLM (Model) navigates your API:
    - Hierarchical Clustering: namespace.action allows the LLM to mentally group related capabilities. When the model sees task., it immediately narrows its search space to task management.

    - Disambiguation: In complex systems, create might apply to tasks, users, or reports. task.create removes ambiguity, preventing the LLM from accidentally calling user.create when the context is task-related.

    - Scalability: As you add more domains (e.g., file.upload, mail.send), the dot-notation keeps the tool list organized and predictable for the model's internal attention mechanism.

5. **Registry vs If-Else:** Why use a dictionary registry to route tool calls instead of if-else chains? What happens when you need to add the 20th tool?

  Using a dictionary registry to route calls is a standard best practice for extensible systems.

  - Maintenance: An if-else chain with 20+ branches is a "Big O(n)" lookup that is hard to read, prone to merge conflicts, and difficult to test in isolation.

  - Dynamic Loading: A registry allows you to register tools dynamically at runtime. You can add a new tool by simply adding a key-value pair to a dictionary: registry["task.create"] = create_task_handler.

  - Clean Code: It separates the routing logic (how do I find the code?) from the business logic (what does the code do?), making the system modular and "Open-Closed" (Open for extension, closed for modification).

## Verification

Your prototype is a real MCP server. Test it with the MCP inspector — no Claude needed.

### 1. Start the server (sanity check)

```bash
python -m app.mcp_server
```

The process should hang waiting on stdin (it's a stdio MCP server — that's correct). Ctrl+C to stop. If you see an `ImportError` or other crash, fix that first.

### 2. Run the MCP inspector

Requires Node.js (uses `npx`).

```bash
npx @modelcontextprotocol/inspector python -m app.mcp_server
```

This opens a browser GUI (usually `http://localhost:5173`).

Steps in the GUI:

1. Click **Connect** -> should show 4 tools: `task.create`, `task.list`, `task.status`, `task.cancel`
2. **task.create** -> fill `description="Summarize tech news"`, `scheduled_at="2025-01-01T00:00:00"` (past time so watcher picks it up immediately) -> **Run Tool** -> response should include `{"job_id": 1, "status": "pending", ...}`
3. Wait ~10 seconds, then **task.status** -> `job_id: 1` -> status should now be `"completed"`
4. **task.create** with future time `"2099-12-31T00:00:00"` -> get `job_id: 2`
5. **task.cancel** -> `job_id: 2` -> status `"cancelled"`
6. **task.list** -> see all your jobs

### 3. (Optional) Connect to Claude Desktop / Claude Code

Once the inspector tests pass, the server is ready. To talk to it through Claude:

**Claude Desktop**: edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) and add (use absolute paths):

```json
{
  "mcpServers": {
    "task-scheduler": {
      "command": "/absolute/path/to/scaffold/.venv/bin/python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/scaffold"
    }
  }
}
```

Restart Claude Desktop fully. The 🔨 icon in the chat input should show 4 tools.

**Claude Code**: edit `~/.claude.json` (top-level `mcpServers` for user scope) with the same block, or run `claude mcp add` from inside `scaffold/`.

Then chat:
> "Schedule a task to review PR #123 tomorrow at 9am."
> -> Claude calls `task.create` -> returns job_id
> "What's the status of that task?"
> -> Claude calls `task.status`

## Suggested Tech Stack

Python + the official `mcp` SDK is recommended (already in `requirements.txt` for the Guided Track). Challenge Track may use any language with an MCP SDK.
