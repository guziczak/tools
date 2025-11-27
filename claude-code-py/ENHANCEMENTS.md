# Claude Code Python - Enhancements

This document describes the major enhancements added to Claude Code Python, based on the original TypeScript implementation.

## 🎯 New Features

### 1. **Command Registry System** 🔥

A powerful command registration system similar to the original TypeScript implementation.

**Location:** `src/commands/`

**Features:**
- Type-safe command definitions with arguments
- Automatic argument parsing and validation
- Support for positional and flag arguments
- Command aliases
- Category-based organization
- Auto-generated help text

**Usage:**
```python
from commands import command_registry, CommandDef, CommandArg, ArgType

# Define a command
command = CommandDef(
    name="mycommand",
    description="Does something cool",
    handler=async_handler_function,
    args=[
        CommandArg(
            name="file",
            description="File to process",
            type=ArgType.STRING,
            position=0,
            required=True
        ),
        CommandArg(
            name="verbose",
            description="Verbose output",
            type=ArgType.BOOLEAN,
            short_flag="v"
        )
    ],
    category="Tools",
    examples=["mycommand file.txt", "mycommand file.txt --verbose"]
)

# Register it
command_registry.register(command)
```

---

### 2. **Prompt Templates System** 🔥

Reusable prompt templates for common coding tasks.

**Location:** `src/prompts/`

**Features:**
- Pre-defined templates for common tasks
- Template variables with defaults
- System prompts for different scenarios
- Language detection from file paths

**Available Templates:**
- `explain_code` - Explain code functionality
- `refactor_code` - Refactor code for improvement
- `debug_code` - Debug code issues
- `review_code` - Code review
- `generate_code` - Generate new code
- `document_code` - Add documentation
- `test_code` - Write tests
- `fix_code` - Fix issues

**Usage:**
```python
from prompts import use_template

# Use a template
prompt, system = use_template(
    "explain_code",
    code=file_content,
    language="python"
)

# Send to Claude
response = api_client.chat(prompt, system=system)
```

**System Prompts:**
```python
from prompts import (
    CODE_ASSISTANT_SYSTEM_PROMPT,
    CODE_GENERATION_SYSTEM_PROMPT,
    CODE_REVIEW_SYSTEM_PROMPT,
    CODE_EXPLANATION_SYSTEM_PROMPT
)
```

---

### 3. **FileOperationsManager with Security** 🔥

Secure file operations with path validation and error handling.

**Location:** `src/fileops/`

**Security Features:**
- Path traversal prevention
- Workspace boundary enforcement
- File size limits
- Permission checking

**Usage:**
```python
from fileops import FileOperationsManager

# Initialize
file_ops = FileOperationsManager(workspace_path="/path/to/workspace")
file_ops.initialize()

# Read file (security checks automatic)
result = file_ops.read_file("../../../etc/passwd")  # ❌ Blocked!
result = file_ops.read_file("app.py")              # ✅ OK

# Check result
if result.success:
    print(result.content)
else:
    print(f"Error: {result.error}")

# Write file
result = file_ops.write_file("output.txt", "content", create_dirs=True)

# Other operations
exists = file_ops.file_exists("file.txt")
result = file_ops.list_directory("src")
diff = file_ops.generate_diff(original, modified)
```

**Features:**
- `read_file()` - Read with size limits
- `write_file()` - Write with directory creation
- `delete_file()` - Delete with validation
- `create_directory()` - Create directories
- `list_directory()` - List contents
- `generate_diff()` - Line-by-line diff
- `get_absolute_path()` - Path resolution with security
- `get_relative_path()` - Get relative path

---

### 4. **Better Error Handling** 🔥

Structured error handling with categories and user-friendly messages.

**Location:** `src/errors/`

**Features:**
- Error categories (authentication, file system, API, etc.)
- User-friendly error messages
- Resolution suggestions
- Cause tracking

**Usage:**
```python
from errors import create_user_error, ErrorCategory, format_error_for_display

# Create user error
error = create_user_error(
    "File not found: config.json",
    category=ErrorCategory.FILE_SYSTEM,
    resolution="Check that the file exists and the path is correct.",
    cause=original_exception
)

# Format for display
print(format_error_for_display(error))
# Output:
# ❌ File not found: config.json
# 📂 Category: file_system
# 💡 Check that the file exists and the path is correct.
```

**Error Categories:**
- `AUTHENTICATION` - Auth errors
- `FILE_SYSTEM` - File/directory errors
- `API` - API errors
- `AI_SERVICE` - Claude API errors
- `VALIDATION` - Validation errors
- `COMMAND` - Command errors
- `NETWORK` - Network errors
- `TIMEOUT` - Timeout errors
- `RATE_LIMIT` - Rate limit errors
- `SERVER` - Server errors

**Helper Functions:**
```python
from errors.formatter import (
    handle_file_error,
    handle_api_error,
    handle_network_error,
    handle_timeout_error
)

try:
    # File operation
    file_ops.read_file("missing.txt")
except Exception as e:
    user_error = handle_file_error(e, "missing.txt", "reading")
    print(format_error_for_display(user_error))
```

---

### 5. **CLI Mode** 🔥

Execute one-off commands from the command line, similar to the original TypeScript implementation.

**Location:** `src/cli_mode.py`

**Usage:**
```bash
# Ask a question
python claude.py ask "How do I implement a binary search tree?"

# Explain code
python claude.py explain app.py

# Refactor code
python claude.py refactor app.js --focus performance

# Fix code
python claude.py fix bug.py --issue "IndexError on line 42"

# Review code
python claude.py review main.ts

# Generate code
python claude.py generate "REST API with auth" --language python

# Help
python claude.py help

# Version
python claude.py version
```

**Interactive REPL Mode:**
```bash
# Start REPL (no arguments)
python claude.py
```

---

## 🎨 Architecture Improvements

### Before:
```python
# main.py - 7,520 lines, everything in one place
def handle_command(self, command: str):
    if cmd == "/clear":
        # ...
    elif cmd == "/reset":
        # ...
    # ... hundreds of lines
```

### After:
```python
# Modular architecture
src/
├── commands/       # Command registry system
├── prompts/        # Prompt templates
├── fileops/        # Secure file operations
├── errors/         # Error handling
└── cli_mode.py     # CLI mode

# Clean registration
from commands import command_registry, CommandDef

register_all_commands(ui, api_client, tool_registry, agent_registry)

# Automatic help generation
help_text = generate_command_help(command)
```

---

## 🚀 Benefits

### 1. **Better Code Organization**
- Separation of concerns
- Modular architecture
- Reusable components

### 2. **Improved Security**
- Path traversal prevention
- File size limits
- Workspace boundaries

### 3. **Enhanced UX**
- CLI mode for quick tasks
- Better error messages
- Consistent prompt templates

### 4. **Easier Maintenance**
- Type-safe command definitions
- Auto-generated help text
- Centralized error handling

### 5. **Best of Both Worlds**
- **CLI Mode** for quick one-off tasks
- **REPL Mode** for interactive sessions
- **Tool Calling** for agentic behavior
- **Agents** for specialized tasks

---

## 📚 Migration Guide

### Old Code:
```python
# Direct file read
with open("file.txt") as f:
    content = f.read()

# Manual error handling
try:
    # ...
except Exception as e:
    print(f"Error: {e}")

# Inline prompts
prompt = f"Please explain this code:\n\n{code}"
```

### New Code:
```python
# Secure file operations
result = file_ops.read_file("file.txt")
if result.success:
    content = result.content
else:
    print(format_error_for_display(result.error))

# Structured error handling
try:
    # ...
except Exception as e:
    error = create_user_error(
        "Operation failed",
        category=ErrorCategory.API,
        resolution="Try again later",
        cause=e
    )
    print(format_error_for_display(error))

# Template-based prompts
prompt, system = use_template("explain_code", code=code, language="python")
response = api_client.chat(prompt, system=system)
```

---

## 🎯 Next Steps

These enhancements bring Claude Code Python closer to the original TypeScript implementation while maintaining the unique advantages of the Python version:

✅ Command Registry System
✅ Prompt Templates
✅ FileOperationsManager
✅ Better Error Handling
✅ CLI Mode

**Future Enhancements:**
- Plugin system (load .md-based commands/agents)
- MCP server support
- More prompt templates
- Extended file operations (search, replace, etc.)
- Configuration system

---

## 📖 Documentation

For more information:
- See `src/commands/registry.py` for command system docs
- See `src/prompts/templates.py` for template system docs
- See `src/fileops/manager.py` for file operations docs
- See `src/errors/types.py` for error handling docs
- See `src/cli_mode.py` for CLI mode docs

---

**Happy Coding! 🚀**
