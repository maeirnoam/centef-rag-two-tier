# Dynamic Retrieval Strategy Guide

## Overview

The retriever now **automatically analyzes queries** and adapts its behavior based on query characteristics. This includes:

1. **Dynamic result counts** - adjust number of chunks/summaries based on query complexity
2. **Selective search strategies** - choose which optimizations to apply
3. **Metadata filtering** - automatically filter by organization, document type, or topic
4. **Search method selection** - decide whether to search chunks, summaries, or both

---

## Query Analysis

### Query Types Detected

The system identifies 5 query types:

#### 1. **Factual Queries**
- **Triggers:** "what is", "define", "definition", "meaning of"
- **Strategy:** 
  - Fewer results needed (precise answers)
  - Chunks only (no summaries)
  - No query expansion (reduces noise)
- **Result counts:** 5 chunks, 2 summaries
- **Example:** "What is a Politically Exposed Person (PEP)?"

#### 2. **Comparative Queries**
- **Triggers:** "compare", "difference", "versus", "vs", "contrast"
- **Strategy:**
  - Balanced chunks and summaries
  - Query expansion enabled (find different perspectives)
  - Higher summary count (need overviews of multiple topics)
- **Result counts:** 8 chunks, 6 summaries
- **Example:** "Compare AML requirements in EU vs US"

#### 3. **Procedural Queries**
- **Triggers:** "how to", "steps", "process", "procedure", "protocol"
- **Strategy:**
  - More chunks (need step-by-step details)
  - Fewer summaries (procedures are in chunks)
  - No query expansion (procedures need precision)
- **Result counts:** 12 chunks, 3 summaries
- **Example:** "How to file a suspicious activity report?"

#### 4. **Analytical Queries**
- **Triggers:** "analyze", "analysis", "evaluate", "assess", "examine"
- **Strategy:**
  - High result counts (need comprehensive evidence)
  - Query expansion enabled (find multiple angles)
  - Both chunks and summaries (need evidence + context)
- **Result counts:** 15 chunks, 7 summaries
- **Example:** "Analyze the effectiveness of FATF recommendations on terrorism financing"

#### 5. **Exploratory Queries**
- **Triggers:** "overview", "about", "tell me about", "explain", "describe"
- **Strategy:**
  - Balanced approach
  - Query expansion enabled (explore broadly)
  - Both chunks and summaries
- **Result counts:** 10 chunks, 5 summaries
- **Example:** "Tell me about trade-based money laundering"

---

## Query Complexity Detection

### Simple Queries (< 5 words)
- **Effect:** Reduce result counts by 40%
- **Example:** "FATF recommendations"
- **Adjusted counts:** 3-5 chunks, 2-3 summaries

### Moderate Queries (5-15 words)
- **Effect:** Standard result counts
- **Example:** "What are the key AML obligations for financial institutions?"
- **Adjusted counts:** 10 chunks, 5 summaries

### Complex Queries (> 15 words or contains "comprehensive", "detailed", "thorough", "in-depth")
- **Effect:** Increase result counts by 50%
- **Example:** "Provide a comprehensive overview of the evolution of FATF recommendations from 2012 to 2024"
- **Adjusted counts:** 15-20 chunks, 7-10 summaries

---

## Query Scope Detection

### Narrow Scope
- **Triggers:** "specific", "particular", "exact", "precise"
- **Effect:** Reduce results by 30%
- **Example:** "Specific requirements for customer due diligence on wire transfers"

### Medium Scope
- **Default behavior**
- **Example:** "Customer due diligence requirements"

### Broad Scope
- **Triggers:** "all", "every", "comprehensive", "complete", "entire", "global"
- **Effect:** Increase results by 30%
- **Example:** "All FATF recommendations related to virtual assets"

---

## Metadata Filtering

The system automatically detects filter hints in queries and applies them to Vertex AI Search.

### Available Filter Fields

**Fields in both chunks and summaries:**
- `source_id`: Unique document identifier
- `filename`: Original filename
- `title`: Document title
- `author`: Document author name
- `organization`: Authoring organization (e.g., "FATF", "World Bank")
- `date`: ISO date string (YYYY-MM-DD)
- `publisher`: Publisher name
- `tags`: Array of topic keywords (e.g., ["virtual_assets", "sanctions"])

**Fields in chunks only:**
- `mimetype`: Content type (e.g., "application/pdf", "video/mp4")
- `page_number` / `page`: Page number reference
- `start_sec` / `end_sec`: Video/audio timestamps
- `content`: Chunk text content

### Organization Filters
**Detected organizations:** FATF, FIU, UN, IMF, World Bank, Egmont Group, Wolfsberg Group, Basel Committee, OECD

**Example queries:**
- "FATF guidance on virtual assets" → Filter: `organization: "FATF"`
- "World Bank report on AML effectiveness" → Filter: `organization: "World Bank"`
- "IMF assessment" → Filter: `organization: "IMF"`

### Topic/Tag Filters

The system recognizes common AML/CTF topics and maps them to standardized tags:

| Query Keywords | Tag Value | Examples |
|---------------|-----------|----------|
| crypto, virtual asset, VASP, cryptocurrency | `virtual_assets` | "crypto AML requirements" |
| sanction, sanctions, embargo | `sanctions` | "sanctions screening" |
| beneficial ownership, UBO | `beneficial_ownership` | "ultimate beneficial owner" |
| CDD, KYC, customer due diligence | `customer_due_diligence` | "KYC procedures" |
| EDD, enhanced due diligence | `enhanced_due_diligence` | "EDD for high-risk customers" |
| PEP, politically exposed person | `peps` | "PEP screening requirements" |
| risk assessment, risk-based | `risk_assessment` | "risk-based approach to AML" |
| transaction monitoring | `transaction_monitoring` | "suspicious transaction detection" |
| SAR, STR, suspicious activity | `suspicious_activity_reporting` | "filing a SAR" |
| wire transfer, remittance | `wire_transfers` | "wire transfer regulations" |
| TBML, trade-based money laundering | `trade_based_money_laundering` | "trade finance risks" |
| correspondent banking | `correspondent_banking` | "correspondent bank due diligence" |
| DNFBP, casino, real estate | `dnfbps` | "DNFBP compliance" |
| NPO, non-profit, charity | `non_profit_organizations` | "NPO terrorism financing risks" |
| terrorism financing, CTF | `terrorism_financing` | "counter-terrorism financing" |
| money laundering, AML | `money_laundering` | "anti-money laundering framework" |
| proliferation financing, WMD | `proliferation_financing` | "WMD financing controls" |

**Example queries:**
- "Crypto AML requirements" → Filter: `tags: ANY("virtual_assets")`
- "Sanctions screening procedures" → Filter: `tags: ANY("sanctions")`
- "PEP due diligence" → Filter: `tags: ANY("peps")`

### Filter Syntax

Vertex AI Search filter expressions support:

```
# String exact match
organization: "FATF"

# Array contains (ANY operator)
tags: ANY("virtual_assets")
tags: ANY("sanctions", "terrorism_financing")  # OR logic

# Multiple conditions (OR)
organization: "FATF" OR organization: "World Bank"

# Multiple conditions (AND) 
organization: "FATF" AND tags: ANY("virtual_assets")

# Date comparisons
date > "2020-01-01"
date >= "2023-01-01" AND date <= "2023-12-31"
```

**Current implementation:** Multiple filters are combined with OR logic (matches any criterion)

---

## Search Strategy Selection

### Query Expansion
**When enabled:**
- Complex queries (analytical, exploratory, comparative)
- Broad scope queries

**When disabled:**
- Simple factual queries (reduces noise)
- Procedural queries (precision needed)
- Simple queries (< 5 words)

**What it does:** Generates 2-3 alternative query phrasings using LLM

### Reranking
**Always enabled** - Generally beneficial for all query types

**What it does:** Re-scores results based on relevance to original query using LLM

### Deduplication
**Always enabled** - Removes duplicate or highly similar results

**What it does:** Identifies and removes results with same source_id + page or high content overlap

### Selective Search (Chunks vs Summaries)

| Query Type | Chunks | Summaries | Reason |
|-----------|---------|-----------|--------|
| Factual | ✓ | ✗ | Definitions in chunks |
| Procedural | ✓ | ✗ | Steps in chunks |
| Comparative | ✓ | ✓ | Need both perspectives |
| Analytical | ✓ | ✓ | Need evidence + context |
| Exploratory | ✓ | ✓ | Balanced exploration |

---

## Usage Examples

### Automatic Adaptive Strategy (Default)

```python
from apps.agent_api.retriever_optimized import search_two_tier_optimized

# Fully automatic - analyzes query and adapts everything
result = search_two_tier_optimized(
    query="What is beneficial ownership?",
    use_adaptive_strategy=True  # Default
)

# Returns:
# - query_characteristics: {...}
# - chunks: [...] (5 chunks - reduced for factual query)
# - summaries: [...] (2 summaries - minimal for definitions)
# - optimizations_applied: {query_expansion: False, ...}
```

### Manual Override

```python
# Override automatic decisions
result = search_two_tier_optimized(
    query="What is beneficial ownership?",
    max_chunk_results=20,  # Force 20 chunks (overrides auto-determination)
    enable_query_expansion=True,  # Force expansion (overrides auto-decision)
    use_adaptive_strategy=True  # Still use adaptive for other decisions
)
```

### Disable Adaptive Strategy

```python
# Traditional fixed behavior
result = search_two_tier_optimized(
    query="What is beneficial ownership?",
    max_chunk_results=10,
    max_summary_results=5,
    enable_query_expansion=True,
    enable_reranking=True,
    enable_deduplication=True,
    use_adaptive_strategy=False  # Disable all adaptive behavior
)
```

---

## Result Metadata

The response now includes rich metadata about the adaptive decisions:

```python
{
    "query": "Analyze FATF effectiveness on terrorism financing",
    "query_characteristics": {
        "query_type": "analytical",
        "complexity": "complex",
        "scope": "medium",
        "needs_chunks": true,
        "needs_summaries": true,
        "filter_hints": [
            ["organization", "FATF"],
            ["topic", "terrorism_financing"]
        ]
    },
    "expanded_queries": [
        "Analyze FATF effectiveness on terrorism financing",
        "Evaluate Financial Action Task Force counter-terrorism financing impact",
        "Assess FATF CFT measures effectiveness"
    ],
    "chunks": [...],  # 15 chunks (increased for analytical + complex)
    "summaries": [...],  # 7 summaries (increased for analytical)
    "total_chunks": 15,
    "total_summaries": 7,
    "optimizations_applied": {
        "query_expansion": true,
        "reranking": true,
        "deduplication": true,
        "adaptive_strategy": true,
        "metadata_filter": true
    }
}
```

---

## Configuration

### Environment Variables

Add to `.env` to tune adaptive behavior:

```env
# Query expansion model (default: gemini-2.0-flash-exp)
QUERY_EXPANSION_MODEL=gemini-2.0-flash-exp

# Reranking model (default: gemini-2.0-flash-exp)
RERANKING_MODEL=gemini-2.0-flash-exp
```

### Customizing Detection Logic

Edit `retriever_optimized.py`:

```python
def analyze_query_characteristics(query: str) -> Dict[str, Any]:
    # Add your custom detection logic
    if 'your_keyword' in query.lower():
        characteristics['query_type'] = 'custom_type'
    
    # Add custom filters
    if 'custom_org' in query.lower():
        characteristics['filter_hints'].append(('organization', 'CUSTOM_ORG'))
    
    return characteristics
```

---

## Benefits

### 1. **Better Precision**
- Factual queries get fewer, more precise results
- Procedural queries focus on step-by-step chunks
- No wasted tokens on irrelevant content

### 2. **Better Recall**
- Analytical queries get comprehensive coverage
- Complex queries use expansion for thoroughness
- Comparative queries get balanced perspectives

### 3. **Cost Efficiency**
- Simple queries use fewer resources
- Query expansion only when beneficial
- Reduced LLM calls for straightforward queries

### 4. **Improved Relevance**
- Metadata filters narrow results to relevant documents
- Selective search (chunks vs summaries) targets right content type
- Reranking prioritizes most relevant results

---

## Testing Different Query Types

### Test Suite

```python
test_queries = {
    "factual": "What is a Suspicious Activity Report?",
    "procedural": "How to conduct enhanced due diligence on PEPs?",
    "comparative": "Compare risk-based approach vs rules-based approach to AML",
    "analytical": "Analyze the impact of FATF grey listing on a country's financial sector",
    "exploratory": "Tell me about trade-based money laundering methods",
    "simple": "FATF recommendations",
    "complex": "Provide a comprehensive analysis of the evolution of international AML standards from 2000 to 2024",
}

for qtype, query in test_queries.items():
    result = search_two_tier_optimized(query)
    print(f"\n{qtype.upper()}:")
    print(f"  Query: {query}")
    print(f"  Type: {result['query_characteristics']['query_type']}")
    print(f"  Complexity: {result['query_characteristics']['complexity']}")
    print(f"  Chunks: {result['total_chunks']}")
    print(f"  Summaries: {result['total_summaries']}")
    print(f"  Query Expansion: {result['optimizations_applied']['query_expansion']}")
```

---

## Troubleshooting

### Issue: Getting too many/few results

**Solution:** Override with explicit counts
```python
result = search_two_tier_optimized(
    query="your query",
    max_chunk_results=15,  # Force specific count
    max_summary_results=8
)
```

### Issue: Query expansion adding noise

**Solution:** Disable for specific query
```python
result = search_two_tier_optimized(
    query="your query",
    enable_query_expansion=False  # Disable expansion
)
```

### Issue: Metadata filter too restrictive

**Solution:** Disable adaptive strategy
```python
result = search_two_tier_optimized(
    query="your query",
    use_adaptive_strategy=False  # No auto-filtering
)
```

---

## Future Enhancements

Potential improvements:
1. **User feedback loop** - Learn from which result counts work best
2. **Time-based filtering** - Detect date references in queries
3. **Language detection** - Filter by document language
4. **Jurisdiction filtering** - Detect country/region mentions
5. **Custom query profiles** - User-defined retrieval preferences
6. **A/B testing framework** - Compare adaptive vs fixed strategies

---

## See Also

- [RAG_OPTIMIZATION_README.md](RAG_OPTIMIZATION_README.md) - Full optimization system
- [FORMAT_DETECTION_GUIDE.md](FORMAT_DETECTION_GUIDE.md) - Synthesizer format adaptation
- [retriever_optimized.py](apps/agent_api/retriever_optimized.py) - Implementation
