# Provider Configuration Reference

Provider configuration lives in `configs/providers.example.yaml`; model
selection lives in `configs/models.example.yaml`.

Each provider should define:

```yaml
provider-name:
  base_url: https://api.example.com/v1
  api_key_env: EXAMPLE_API_KEY
  protocol: chat_completions
```

Supported protocols are `chat_completions`, `responses`, and `anthropic`.
Provider names are labels only; the model ID must be verified against the
upstream API rather than inferred from a console display name.

For an OpenAI-compatible relay:

1. Set the base URL exactly as documented by the relay.
2. Put the key in the named environment variable.
3. Validate the repository locally.
4. Make one harmless request with the selected model.
5. Record the endpoint, model ID, protocol, parameters, response status, and
   timestamp without recording the key.

Never place `api_key`, `Authorization`, cookies, or full `.env` contents in
YAML, JSON, Markdown, result files, or commits.
