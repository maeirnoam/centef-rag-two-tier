# Format Detection Guide

## Overview

The synthesizer now automatically detects the desired output format from user queries and adapts the response structure, length, temperature, and style accordingly.

## Supported Output Formats

### 1. Brief Summary (150-250 tokens)
**Triggers:** "brief", "summarize", "summary", "key points", "quick overview"

**Characteristics:**
- Structure: Bullet points with key facts
- Temperature: 0.15 (very focused)
- Style: Concise, factual
- Citations: Minimum 3

**Example Queries:**
- "Give me a brief summary of FATF recommendations"
- "What are the key points about cryptocurrency regulations?"
- "Quick overview of suspicious activity indicators"

---

### 2. Social Media / Tweet (150 tokens)
**Triggers:** "tweet", "twitter", "social media", "post"

**Characteristics:**
- Structure: Single engaging paragraph
- Temperature: 0.3 (creative but focused)
- Style: Engaging, accessible, shareable
- Citations: Optional (format-appropriate)

**Example Queries:**
- "Write a tweet about money laundering red flags"
- "Create a social media post about FATF updates"
- "Draft a Twitter-length summary of the report"

---

### 3. Blog Post / Article (1500-2000 tokens)
**Triggers:** "blog", "article", "post", "write about", "explain in detail"

**Characteristics:**
- Structure: Sections with headings, introduction, body, conclusion
- Temperature: 0.35 (creative but informative)
- Style: Conversational, engaging, informative
- Citations: Minimum 5

**Example Queries:**
- "Write a blog post about emerging AML technologies"
- "Create an article explaining beneficial ownership requirements"
- "Write about the impact of the 2023 FATF updates"

---

### 4. Newsletter (1000-1500 tokens)
**Triggers:** "newsletter", "update", "digest", "bulletin"

**Characteristics:**
- Structure: Section headings, scannable paragraphs
- Temperature: 0.3 (professional but approachable)
- Style: Professional, approachable, scannable
- Citations: Minimum 5

**Example Queries:**
- "Create a newsletter about recent CTF developments"
- "Draft a monthly update on regulatory changes"
- "Write a compliance bulletin about new sanctions"

---

### 5. Outline / Presentation (800-1200 tokens)
**Triggers:** "outline", "presentation", "talk", "speech", "structure", "bullets"

**Characteristics:**
- Structure: Hierarchical bullet points (main → sub-topics → details)
- Temperature: 0.25 (organized, clear)
- Style: Structured, hierarchical, clear
- Citations: Minimum 5

**Example Queries:**
- "Create an outline for a presentation on trade-based money laundering"
- "Give me talking points for an interview about sanctions compliance"
- "Structure a speech about virtual asset regulations"

---

### 6. Protocol / Procedure (1000-1500 tokens)
**Triggers:** "protocol", "procedure", "process", "steps", "how to", "guide"

**Characteristics:**
- Structure: Numbered steps with prerequisites
- Temperature: 0.15 (precise, authoritative)
- Style: Formal, precise, authoritative
- Citations: Minimum 5

**Example Queries:**
- "What's the protocol for filing a suspicious activity report?"
- "Describe the procedure for customer due diligence"
- "How to conduct enhanced due diligence for high-risk customers"

---

### 7. Formal Report (2000-3000 tokens)
**Triggers:** "report", "analysis", "findings", "assessment"

**Characteristics:**
- Structure: Executive summary, findings, analysis, conclusions
- Temperature: 0.2 (objective, formal)
- Style: Objective, formal, structured
- Citations: Minimum 7

**Example Queries:**
- "Generate a report on money laundering trends in 2023"
- "Provide an analysis of compliance gaps in the banking sector"
- "Create a risk assessment report for virtual assets"

---

### 8. Comprehensive Analysis (3000-4000 tokens)
**Triggers:** "comprehensive", "in-depth", "detailed analysis", "thorough", "complete"

**Characteristics:**
- Structure: Main sections, subsections, thorough coverage
- Temperature: 0.25 (balanced depth)
- Style: Academic, thorough, multi-faceted
- Citations: Minimum 10

**Example Queries:**
- "Provide a comprehensive analysis of global AML frameworks"
- "Give me an in-depth examination of terrorist financing methods"
- "Thoroughly analyze the evolution of FATF recommendations"

---

### 9. Factual Answer (800-1500 tokens)
**Triggers:** "what is", "what are", "define", "explain"

**Characteristics:**
- Structure: Clear paragraphs with logical flow
- Temperature: 0.2 (factual, precise)
- Style: Clear, informative, educational
- Citations: Minimum 5

**Example Queries:**
- "What are the FATF 40 recommendations?"
- "Explain the concept of beneficial ownership"
- "Define trade-based money laundering"

---

### 10. General Answer (Default: 1000-2000 tokens)
**Triggers:** Other queries not matching specific formats

**Characteristics:**
- Structure: Paragraphs with logical flow
- Temperature: 0.25 (balanced)
- Style: Formal, professional, thorough
- Citations: Minimum 5

**Example Queries:**
- Any query that doesn't match specific format triggers

---

## How Format Detection Works

### Detection Process

1. **Query Analysis:** The `detect_output_format()` function analyzes the user's query for format indicators
2. **Pattern Matching:** Looks for specific keywords and phrases that indicate desired format
3. **Format Characteristics:** Returns a dictionary with:
   - `format_type`: Category of output
   - `length`: "brief", "medium", "long", "comprehensive"
   - `structure`: "bullet_points", "paragraphs", "sections", "numbered_steps", "hierarchical"
   - `temperature`: 0.15-0.5 (controls creativity vs. precision)
   - `max_tokens`: 150-4000 (controls output length)
   - `style`: "formal", "conversational", "engaging", "authoritative", etc.

### Prompt Customization

The `build_optimized_synthesis_prompt()` function uses format_info to:

1. **Add format-specific instructions** for structure and style
2. **Adjust citation requirements** (e.g., social media posts need fewer citations)
3. **Provide output examples** appropriate to the format
4. **Set length expectations** based on max_tokens

### Adaptive Parameters

The synthesizer automatically adjusts:

- **Temperature:** Lower (0.15-0.25) for factual/formal content, higher (0.3-0.5) for creative content
- **Max Tokens:** From 150 (tweets) to 4000 (comprehensive analyses)
- **Citation Style:** Formal citations for reports/protocols, flexible for blogs/newsletters

---

## API Integration

### Using in Chat Endpoint

```python
from apps.agent_api.synthesizer_optimized import synthesize_answer_optimized

# Automatic format detection
result = synthesize_answer_optimized(
    query="Write a blog post about FATF updates",
    summary_results=summaries,
    chunk_results=chunks,
    enable_adaptive_temperature=True  # Enables format-based temperature
)

# Access format information
format_info = result['format_info']
print(f"Detected format: {format_info['format_type']}")
print(f"Used temperature: {result['temperature']}")
print(f"Output length: {format_info['max_tokens']} tokens")
```

### Override Automatic Detection

```python
# Manual override if needed
result = synthesize_answer_optimized(
    query="Write a blog post about FATF updates",
    summary_results=summaries,
    chunk_results=chunks,
    temperature=0.4,  # Override detected temperature
    max_output_tokens=3000  # Override detected max_tokens
)
```

---

## Testing Different Formats

### Test Query Examples

```python
# Brief Summary
"Give me a brief summary of the 2023 FATF mutual evaluation"

# Tweet
"Write a tweet about new AML regulations"

# Blog Post
"Write a blog post explaining cryptocurrency AML risks"

# Newsletter
"Create a newsletter update on sanctions compliance changes"

# Outline
"Outline a presentation on trade-based money laundering indicators"

# Protocol
"What's the protocol for enhanced due diligence on PEPs?"

# Report
"Generate a report on money laundering typologies in real estate"

# Comprehensive Analysis
"Provide a comprehensive analysis of global CTF frameworks"

# Factual Answer
"What are the key components of a risk-based approach to AML?"
```

---

## Benefits

### For Users
- **Natural Language:** Just describe what you want in plain language
- **Appropriate Length:** Automatically gets the right level of detail
- **Format-Appropriate Style:** Tweets are engaging, reports are formal
- **Flexible Usage:** Same system handles everything from tweets to comprehensive reports

### For System
- **Single Codebase:** One synthesizer handles all formats
- **Consistent Quality:** All formats follow best practices
- **Token Efficiency:** Shorter formats use fewer tokens
- **Better Results:** Format-specific prompts produce better outputs

---

## Configuration

All format detection parameters can be tuned in `detect_output_format()`:

```python
# In synthesizer_optimized.py
def detect_output_format(query: str) -> Dict[str, Any]:
    # Adjust keywords, token limits, temperatures
    # based on your specific needs
```

---

## Future Enhancements

Potential additions:
1. **Custom Formats:** User-defined format templates
2. **Multi-Format Responses:** Generate multiple formats for same query
3. **Format Metadata:** Track format performance and user preferences
4. **Format Suggestions:** Recommend best format based on query complexity
5. **Language-Specific Formats:** Adapt formats for different languages

---

## See Also

- [RAG_OPTIMIZATION_README.md](RAG_OPTIMIZATION_README.md) - Full optimization system documentation
- [synthesizer_optimized.py](apps/agent_api/synthesizer_optimized.py) - Implementation details
- [USER_PROMPTS.md](USER_PROMPTS.md) - Example user queries and prompts
