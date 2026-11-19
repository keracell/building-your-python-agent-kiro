// PreToolUse guard: block file writes under tests/. Exit 2 blocks the tool call.
let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  let path = "";
  try {
    const toolInput = JSON.parse(input).tool_input || {};
    path = String(toolInput.path || toolInput.targetFile || "");
  } catch (err) {
    process.exit(0);
  }
  if (/(^|[\\/])tests[\\/]/.test(path)) {
    console.error("Blocked: writes under tests/ are not allowed.");
    process.exit(2);
  }
});
