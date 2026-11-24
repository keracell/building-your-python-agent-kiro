// SessionStart hook: tell the agent which operating system it runs on.
// os.type() returns the same value as `uname -s` (Linux, Darwin) and also works on Windows.
const os = require("os");
console.log(`Operating system: ${os.type()} ${os.release()} (${os.platform()}, ${os.arch()})`);
