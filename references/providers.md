# Provider Reference — PaperBanana

## Supported Providers

| Component | Provider | Model | Cost | Env Var |
|-----------|----------|-------|------|---------|
| VLM (planning, critique) | OpenAI | gpt-5.2 | Paid | `OPENAI_API_KEY` |
| Image Generation | OpenAI | gpt-image-1.5 | Paid | `OPENAI_API_KEY` |
| VLM (planning, critique) | Google Gemini | gemini-2.0-flash | Free | `GOOGLE_API_KEY` |
| Image Generation | Google Gemini | gemini-3-pro-image-preview | Free | `GOOGLE_API_KEY` |
| VLM + Image | OpenRouter | Any supported | Varies | `OPENROUTER_API_KEY` |
| VLM + Image | Azure OpenAI / Foundry | Same as OpenAI | Paid | `OPENAI_BASE_URL` |

## Auto-Detection Priority

The scripts check environment variables in this order:
1. `OPENAI_API_KEY` → uses OpenAI (highest quality)
2. `GOOGLE_API_KEY` → uses Gemini (free tier, good quality)
3. Neither → error with setup instructions

Azure OpenAI is auto-detected when `OPENAI_BASE_URL` is set to an Azure endpoint.

## Provider Comparison

| Aspect | OpenAI | Gemini (Free) |
|--------|--------|---------------|
| **Quality** | Highest (gpt-5.2 + gpt-image-1.5) | Good (gemini-2.0-flash + imagen-3) |
| **Cost** | ~$0.10-0.50 per diagram | Free |
| **Speed** | Fast (~30s per iteration) | Moderate (~45s per iteration) |
| **Rate Limits** | High (tier-dependent) | 15 RPM (free tier) |
| **Best For** | Final publication figures | Drafts, iteration, low-budget |

## Configuration Examples

### Gemini Only (Free)
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

### OpenAI Only (Paid, Best Quality)
```json5
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          OPENAI_API_KEY: "sk-..."
        }
      }
    }
  }
}
```

### Both (OpenAI Primary, Gemini Fallback)
```json5
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          OPENAI_API_KEY: "sk-...",
          GOOGLE_API_KEY: "AIzaSy..."
        }
      }
    }
  }
}
```

### Azure OpenAI / Foundry
```json5
{
  skills: {
    entries: {
      "paperbanana": {
        env: {
          OPENAI_API_KEY: "your-azure-key",
          OPENAI_BASE_URL: "https://your-resource.openai.azure.com/openai/v1"
        }
      }
    }
  }
}
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
