# Prompts Configuration

This directory contains all the prompt templates and configurations used in the project.

## Directory Structure

```
prompts/
├── base_chat.yaml       # Base chat model configurations
├── device_control.yaml  # Device control specific prompts
├── test_template.yaml   # Test templates
└── templates/          # Template directory for dynamic prompts
```

## Configuration Files

### base_chat.yaml
Base configuration for chat model interactions, including:
- System prompts
- Basic interaction templates
- Response formats

### device_control.yaml
Device control specific prompts, including:
- Device command templates
- Status query templates
- Error handling responses

### test_template.yaml
Templates used in testing, including:
- Mock response templates
- Test scenario prompts
- Validation patterns

## Usage
1. All yaml files should follow the standard format
2. Each prompt should have a clear description
3. Variables should be clearly marked with {variable_name}
4. Include examples where appropriate 