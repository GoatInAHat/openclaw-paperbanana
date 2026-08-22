# Security Policy

## Reporting a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/GoatInAHat/openclaw-paperbanana/security/advisories/new). Do not include provider keys, private datasets, unpublished papers, or exploit details in a public issue.

## Data and execution boundary

Prompts, selected files, images, and plotting data are sent to the configured model provider. Statistical plotting uses model-generated Python. This skill validates that code against a plotting-only AST policy, launches it with no provider credentials in the environment, isolates its working directory, and applies time/resource limits where supported. This is defense in depth, not a kernel sandbox; run the skill in an OpenClaw sandbox when handling untrusted input.

Only the latest release is supported with security fixes.
