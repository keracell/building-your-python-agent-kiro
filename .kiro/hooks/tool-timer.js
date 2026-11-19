// Records how long each tool call takes.
// Usage: node tool-timer.js start   (PreToolUse)  -> appends a start record to tool-timer-state.jsonl
//        node tool-timer.js stop    (PostToolUse) -> appends a duration record to tool-timings.jsonl
const fs = require("fs");

const mode = process.argv[2];
const STATE = "tool-timer-state.jsonl";
const TIMINGS = "tool-timings.jsonl";

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  let event = {};
  try {
    event = JSON.parse(input);
  } catch (err) {
    process.exit(0);
  }
  const tool = event.tool_name || event.toolName || "unknown";
  const id = event.tool_use_id || event.toolUseId || event.tool_call_id || null;
  const session = event.session_id || event.sessionId || null;
  const now = Date.now();

  if (mode === "start") {
    fs.appendFileSync(STATE, JSON.stringify({ tool, id, session, start: now }) + "\n");
    return;
  }

  if (mode === "stop") {
    let starts = [];
    try {
      starts = fs.readFileSync(STATE, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
    } catch (err) {
      return;
    }
    // Match by call id when available, otherwise the latest unmatched start for the same tool.
    let index = -1;
    for (let i = starts.length - 1; i >= 0; i--) {
      const s = starts[i];
      if (id ? s.id === id : s.tool === tool && s.session === session) {
        index = i;
        break;
      }
    }
    if (index === -1) return;
    const [match] = starts.splice(index, 1);
    fs.writeFileSync(STATE, starts.map((s) => JSON.stringify(s)).join("\n") + (starts.length ? "\n" : ""));
    fs.appendFileSync(
      TIMINGS,
      JSON.stringify({ tool, session, duration_ms: now - match.start, ended_at: new Date(now).toISOString() }) + "\n"
    );
  }
});
