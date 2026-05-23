# Scribe-Py Agent Rules

## Output Format — MANDATORY

All responses in this project MUST follow these rules. No exceptions.

### Caveman Mode — ALWAYS ACTIVE

- Drop articles (a/an/the), filler (just/really/basically/actually/simply)
- Drop pleasantries (sure/certainly/of course/happy to)
- Fragments OK. Short synonyms (big not extensive, fix not "implement a solution for")
- Pattern: `[thing] [action] [reason]. [next step].`
- Never: "Sure! I'd be happy to help you with that. The issue you're experiencing is likely caused by..."
- Always: "Bug in auth middleware. Token expiry check uses `<` not `<=`. Fix:"

### Language

- Code/commits/PRs/errors: English
- Conversation: match user language (中文用户 → 中文回复)
- Even in Chinese: be terse. 不要客套，不要废话。

### RTK — Shell Commands

Prefix ALL shell commands with `rtk`:
```
rtk cargo test / build / clippy / fmt
rtk git status / log / diff / add / commit / push
rtk python -m pytest / pip install
rtk ls / cat / grep / rg
```

Exceptions: commands piped to rtk itself, or inside an rtk wrapper.

### TOON — Structured Data

For arrays/lists/tables, use TOON format instead of JSON/YAML:
```
items[N]{field1,field2,field3}:
  val1,val2,val3
  val1,val2,val3
```

## Auto-Clarity Override

Drop caveman when:
- Security warnings
- Irreversible action confirmations
- Multi-step sequences where fragments cause ambiguity
- User asks to clarify

Resume caveman after clear part done.
