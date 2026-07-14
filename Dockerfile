# For MCP registry build verification (e.g. Glama's reproducible-build gate).
# Ditto's MCP server is normally run locally as `python ditto.py mcp` so it can
# read your own mined profile under ~/.ditto. In a bare container it starts and
# lists its tool but has no local profile to serve unless ~/.ditto is mounted.
FROM python:3.12-slim
WORKDIR /app
COPY ditto.py MINING_PROMPT.md ./
ENTRYPOINT ["python", "ditto.py", "mcp"]
