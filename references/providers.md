# Provider Reference — PaperBanana

## Supported Providers

| Component | Provider | Model | Cost | Env Var |
|-----------|----------|-------|------|---------|
| VLM (planning, critique) | Google Gemini | gemini-2.0-flash | Free | `GOOGLE_API_KEY` |
| Image Generation | Google Gemini | gemini-2.0-flash-preview-image-generation | Free | `GOOGLE_API_KEY` |
| VLM (planning, critique) | OpenRouter | Any model (e.g. gpt-5.2) | Paid | `OPENROUTER_API_KEY` |
| Image Generation | OpenRouter | Any model | Paid | `OPENROUTER_API_KEY` |

> **Note:** Direct OpenAI provider is not available. To use OpenAI models (GPT-5.2, etc.),
> route through OpenRouter with `OPENROUTER_API_KEY`.

## Auto-Detection Priority

The scripts check environment variables in this order:
1. `GOOGLE_API_KEY` → uses Gemini (free tier, recommended)
2. `OPENROUTER_API_KEY` → uses OpenRouter (flexible, paid)
3. Neither → error with setup instructions

## Provider Comparison

| Aspect | Gemini (Free) | OpenRouter |
|--------|---------------|------------|
| **Quality** | Good (gemini-2.0-flash) | Varies by model |
| **Cost** | Free | Pay-per-use |
| **Speed** | Moderate (~45s per iteration) | Model-dependent |
| **Rate Limits** | 15 RPM (free tier) | Tier-dependent |
| **Best For** | Drafts, iteration, default | Specific model needs |

## Configuration Examples

### Gemini Only (Free — Recommended)
```json5
// ~/.openclaw/openclaw.json
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          GOOGLE_API_KEY: "AIzaSy..."
        }
      }
    }
  }
}
```

### OpenRouter (Access to Any Model)
```json5
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          OPENROUTER_API_KEY: "sk-or-..."
        }
      }
    }
  }
}
```

### Both (Gemini Primary, OpenRouter Fallback)
```json5
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          GOOGLE_API_KEY: "AIzaSy...",
          OPENROUTER_API_KEY: "sk-or-..."
        }
      }
    }
  }
}
```

### Model Override via Environment
```bash
# Override default Gemini models
GEMINI_VLM_MODEL=gemini-2.5-pro
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview

# Override default OpenRouter models
OPENROUTER_VLM_MODEL=openai/gpt-5.2
OPENROUTER_IMAGE_MODEL=openai/gpt-image-1.5
```

## Getting a Gemini API Key (Free)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key (starts with `AIzaSy...`)
4. Add to your OpenClaw config as shown above

## Aspect Ratios

| Ratio | Best For |
|-------|---------|
| `4:3` | Paper figures (default) |
| `16:9` | Slides, presentations |
| `1:1` | Square figures |
| `3:2` | Wide paper figures |
| `2:3` | Tall/portrait figures |
| `3:4` | Portrait paper figures |
| `9:16` | Vertical posters |
| `21:9` | Ultra-wide banners |
