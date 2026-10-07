# VELIN MCP server (images + music)

Zero-dependency [MCP](https://modelcontextprotocol.io) server for Claude Desktop, Cursor, Cline and other MCP clients.
Tools: `generate_image` (Nano Banana Pro/2, GPT Image 2/2.5, ~$0.037/image at 1K-4K), `generate_music` (Suno 5.5/5, ~$0.12 for 2 tracks), `get_balance`.

```json
{"mcpServers": {"velin": {"command": "node", "args": ["/abs/path/velin-mcp.mjs"],
  "env": {"VELIN_API_KEY": "your_key", "VELIN_OUT_DIR": "/abs/path/outputs"}}}}
```

Needs Node 18+ and a VELIN API key (https://72agi.com, top up from $5 by card or USDT). Each tool call that generates costs credits; failed jobs are not charged.
VELIN is an independent service, not affiliated with Google, OpenAI or Suno.
