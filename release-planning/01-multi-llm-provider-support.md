# 01 - Multi-LLM Provider Support

## Overview

TravelBot v1.x is tightly coupled to Azure OpenAI. The LLM call is made via a direct HTTP POST in `daemon.py:get_comprehensive_response_from_llm()` (lines 599-684), with Azure-specific headers (`api-key`), endpoint format, and request structure hardcoded into the function. To support varied LLM providers, v2.0 must introduce a configurable provider abstraction layer.

## Current State

| Aspect | Current Implementation |
|--------|----------------------|
| **Provider** | Azure OpenAI only |
| **Model** | `gpt-4o-e2` (Azure deployment name) |
| **Auth** | `api-key` header |
| **Endpoint** | Azure-format URL with `api-version` query parameter |
| **Request format** | OpenAI chat completions JSON (`messages`, `temperature`, `max_tokens`) |
| **Response parsing** | Expects OpenAI-style `choices[0].message.content` |
| **Config** | Single `openai:` block in `config.yaml` |
| **Retry** | 3 attempts, exponential backoff (2s, 4s, 8s) |
| **Timeouts** | 10s connect, 120s read |

## Target Providers

The following providers must be investigated for direct API integration:

### 1. Anthropic (Claude)

- **API style**: Messages API (`/v1/messages`)
- **Auth**: `x-api-key` header + `anthropic-version` header
- **Request format**: `model`, `max_tokens`, `messages` array with `role`/`content`
- **Response format**: `content[0].text`
- **Key differences**: No `temperature: 0` equivalent (use `temperature: 0.0`); uses `max_tokens` as required param; supports system prompt as separate top-level field
- **MCP support**: Native — Claude supports MCP tool use, which is directly relevant to objective #5

### 2. OpenAI (Direct, non-Azure)

- **API style**: Chat completions (`/v1/chat/completions`)
- **Auth**: `Authorization: Bearer <key>` header
- **Request format**: Same as Azure minus the deployment/api-version URL params
- **Response format**: Same as current Azure parsing
- **Key differences**: Minimal changes from current code; endpoint and auth header differ

### 3. Amazon Bedrock

- **API style**: `InvokeModel` or `Converse` API via AWS SDK (`boto3`)
- **Auth**: AWS IAM credentials (access key, secret key, session token, or IAM role)
- **Request format**: Provider-specific model ID (e.g., `anthropic.claude-3-5-sonnet-20241022-v2:0`), body varies by underlying model
- **Response format**: Provider-specific; needs model-aware parsing
- **Key differences**: Requires AWS SDK rather than HTTP POST; auth is SigV4, not API key; region-specific endpoints; cost model differs (per-token, on-demand vs. provisioned throughput)
- **MCP support**: Bedrock supports MCP via its agent framework

### 4. Google Gemini

- **API style**: `generateContent` (`/v1beta/models/{model}:generateContent`)
- **Auth**: API key as query parameter or OAuth2
- **Request format**: `contents` array with `parts`, different structure from OpenAI
- **Response format**: `candidates[0].content.parts[0].text`
- **Key differences**: Completely different request/response schema from OpenAI; supports `safetySettings` for content filtering; supports multimodal input natively

### 5. Cerebras

- **API style**: OpenAI-compatible chat completions endpoint
- **Auth**: `Authorization: Bearer <key>` header
- **Request format**: Compatible with OpenAI SDK
- **Response format**: Compatible with OpenAI response format
- **Key differences**: Optimized for speed (inference on custom wafer-scale hardware); limited model selection; OpenAI SDK compatibility simplifies integration

### 6. Grok (xAI)

- **API style**: OpenAI-compatible chat completions endpoint
- **Auth**: `Authorization: Bearer <key>` header
- **Request format**: OpenAI-compatible
- **Response format**: OpenAI-compatible
- **Key differences**: OpenAI SDK compatible; different model naming conventions; real-time information access capabilities

## Proposed Architecture

### Provider Interface

A base provider class defining the contract all providers must satisfy:

```
LLMProvider (abstract)
├── configure(config: dict) → None
├── send_prompt(prompt: str) → str
├── validate_config() → bool
├── get_provider_name() → str
└── supports_mcp() → bool
```

### Provider Implementations

```
LLMProvider
├── AzureOpenAIProvider      (current behavior, extracted)
├── OpenAIProvider           (direct OpenAI API)
├── AnthropicProvider        (Claude Messages API)
├── BedrockProvider          (AWS SDK-based)
├── GeminiProvider           (Google AI API)
├── CerebrasProvider         (OpenAI-compatible)
└── GrokProvider             (OpenAI-compatible)
```

### Configuration Changes

The `config.yaml` structure should evolve from the current flat `openai:` block to a provider-selectable model:

```yaml
llm:
  provider: "anthropic"          # Provider selector

  # Provider-specific configurations
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: "claude-sonnet-4-20250514"
    max_tokens: 8000

  azure_openai:
    api_key: "${AZURE_OPENAI_KEY}"
    model: "gpt-4o-e2"
    endpoint: "https://..."
    api_version: "2024-02-15-preview"
    deployment: "your-deployment"

  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4o"

  bedrock:
    region: "us-east-1"
    model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
    # Uses AWS credential chain (env vars, IAM role, etc.)

  gemini:
    api_key: "${GEMINI_API_KEY}"
    model: "gemini-2.0-flash"

  cerebras:
    api_key: "${CEREBRAS_API_KEY}"
    model: "llama-4-scout-17b-16e"

  grok:
    api_key: "${XAI_API_KEY}"
    model: "grok-3"
```

### Provider Factory

A factory function to instantiate the correct provider from configuration:

```python
def create_provider(config: dict) -> LLMProvider:
    provider_name = config["llm"]["provider"]
    provider_config = config["llm"].get(provider_name, {})
    provider_class = PROVIDER_REGISTRY[provider_name]
    provider = provider_class()
    provider.configure(provider_config)
    return provider
```

## Requirements

### Functional Requirements

- [ ] Abstract provider interface with `send_prompt()`, `validate_config()`, and `supports_mcp()` methods
- [ ] Provider factory that instantiates the correct provider from `config.yaml`
- [ ] Azure OpenAI provider (extract from current `get_comprehensive_response_from_llm()`)
- [ ] Direct OpenAI provider
- [ ] Anthropic Claude provider
- [ ] Amazon Bedrock provider (requires `boto3` dependency)
- [ ] Google Gemini provider
- [ ] Cerebras provider
- [ ] Grok (xAI) provider
- [ ] Provider-specific retry and timeout configuration
- [ ] Config validation at startup (fail fast on missing/invalid provider config)

### Non-Functional Requirements

- [ ] Provider switching requires only a config change, no code modification
- [ ] Each provider encapsulates its own auth, request format, and response parsing
- [ ] Consistent error handling and logging across all providers
- [ ] Response format normalization — all providers must return the same JSON structure to the daemon
- [ ] New providers can be added by implementing the interface and registering in the factory

### Dependencies

- `boto3` for Bedrock
- `anthropic` SDK (optional, could use raw HTTP)
- `google-generativeai` SDK (optional, could use raw HTTP)
- Providers using OpenAI-compatible endpoints (Cerebras, Grok) may share a common base class

## MCP Considerations

MCP support varies by provider and is directly relevant to objective #5 (MCP Travel Service Integration). Providers that natively support MCP tool use (Anthropic, Bedrock) can enable richer agentic workflows. The `supports_mcp()` method on the provider interface should indicate whether the provider can participate in tool-use loops for travel service queries.

## Risks and Open Questions

1. **Prompt portability**: The current prompt (~700+ lines) is optimized for GPT-4o. Different models may need different prompt structures or perform inconsistently. This is addressed by objective #2 (Prompt Externalization) which enables provider-specific prompt templates.
2. **Response parsing reliability**: The current code handles multiple markdown fence styles. Different LLMs may format JSON responses differently, requiring provider-specific post-processing.
3. **Cost variance**: Token pricing differs significantly across providers. Should a cost tracking/alerting mechanism be added?
4. **Rate limits**: Each provider has different rate limits. Provider-specific rate limiting configuration may be needed.
5. **Bedrock auth complexity**: AWS credential management (IAM roles, session tokens, credential chain) is significantly more complex than API key auth and may require additional configuration documentation.
