// Appends each PostToolUse event (stdin JSON) as one line to run-log.jsonl.
// Cross-platform replacement for the POSIX one-liner `(cat; echo) >> run-log.jsonl`,
// which fails under cmd.exe on Windows.
const fs = require("fs");

const LOG = "run-log.jsonl";

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  let line;
  try {
    line = JSON.stringify(JSON.parse(input));
  } catch (err) {
    line = JSON.stringify({ raw: input });
  }
  fs.appendFileSync(LOG, line + "\n");
});
