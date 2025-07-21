# Using Kimi API with Claude Code CLI

This setup allows you to use Kimi (Moonshot AI) API instead of Claude Opus in the Claude Code CLI.

## Setup Instructions

1. **Copy the Kimi configuration file to your project:**
   ```bash
   cp .env.kimi /your/project/directory/
   ```

2. **Edit `.env.kimi` and add your Kimi API key:**
   ```env
   KIMI_API_KEY=your-kimi-api-key-here
   ```

3. **Run Claude Code normally:**
   ```bash
   python claude.py
   ```

## How it Works

- When `claude.py` starts, it checks for `.env.kimi` in the current project directory
- If found and properly configured (with API key), it switches to Kimi mode
- Environment variables are automatically set to redirect API calls to Kimi
- The console will show "Starting Kimi session" instead of "Starting Claude session"

## Configuration Details

The `.env.kimi` file contains:

- `KIMI_API_BASE_URL`: Kimi API endpoint (https://api.moonshot.cn/v1)
- `KIMI_API_KEY`: Your Kimi API key (leave empty initially, add your key)
- `KIMI_MODEL`: Model to use (moonshot-v1-128k)
- `API_TIMEOUT`: Optional timeout in seconds
- `MAX_TOKENS`: Optional max tokens for responses

## Troubleshooting

1. **"KIMI_API_KEY is empty" warning:**
   - Make sure you've added your API key to `.env.kimi`

2. **Still using Claude instead of Kimi:**
   - Ensure `.env.kimi` is in your project directory (not just in claude-code-starter)
   - Check that all required fields are present in the file

3. **API errors:**
   - Verify your API key is valid
   - Check that the API URL is correct for your region