"""The triage prompt: a guided investigation of a symptom in the logs."""

from fastmcp import FastMCP
from pydantic import Field

PROMPT_DESCRIPTION = "A guided investigation of a symptom in the logs."
SYMPTOM_DESCRIPTION = "What the user saw, in their words"
PATH_DESCRIPTION = "The file or folder to look in; the whole log root when it is empty or not given"
SINCE_DESCRIPTION = "The start of the time to look at"
UNTIL_DESCRIPTION = "The end of the time to look at"


def register(mcp: FastMCP) -> None:
    @mcp.prompt(name="triage", description=PROMPT_DESCRIPTION)
    def triage(
        symptom: str = Field(description=SYMPTOM_DESCRIPTION),
        path: str = Field(default="", description=PATH_DESCRIPTION),
        since: str = Field(default="", description=SINCE_DESCRIPTION),
        until: str = Field(default="", description=UNTIL_DESCRIPTION),
    ) -> str:
        """Guide an agent through a structured log triage workflow."""
        text_lines = [
            f"Symptom: {symptom}",
        ]
        if path:
            text_lines.append(f"Path: {path}")
        if since:
            text_lines.append(f"Since: {since}")
        if until:
            text_lines.append(f"Until: {until}")

        workflow_guidance = (
            "\nFollow this investigative process using available tools in this order when appropriate:\n"
            "1. list_logs — start here to see what logs and services exist.\n"
            "2. summarize_logs — get high-level group counts and message signatures across files.\n"
            "3. group_lines — drill down into specific group patterns without re-scanning.\n"
            "4. timeline — examine how patterns and metrics shift over time.\n"
            "5. search_logs — search for specific needles and error markers.\n"
            "6. read_lines — inspect surrounding context around key lines.\n"
            "7. save_finding — document confirmed conclusions with concrete evidence.\n\n"
            "Rules for investigation:\n"
            "- Compare the symptom window against a quiet window before it to spot anomalies.\n"
            "- Treat groups that are steady across days as background noise.\n"
            "- Check that sources agree on time before trusting the observed sequence of events.\n"
            "- Cite a file and line for every claim made.\n"
            "- Clearly state what the logs do not show."
        )

        text_lines.append(workflow_guidance)
        return "\n".join(text_lines)
