# LLM Call Tracking System

Comprehensive tracking system for all LLM and AI API calls in the CENTEF RAG pipeline, enabling detailed usage analysis, cost monitoring, and performance optimization.

## Overview

This system provides centralized tracking of all AI API calls across your RAG pipeline, including:

- **Generative AI**: Gemini models for chat answers and summarization
- **Speech-to-Text**: Google Cloud Speech API for audio/video transcription
- **Translation**: Google Cloud Translation API
- **Vision API**: Google Cloud Vision for OCR
- **Search/Retrieval**: Vertex AI Search (Discovery Engine)

All calls are logged to a master JSONL file with comprehensive metadata for analysis.

## Architecture

### Components

1. **`shared/llm_tracker.py`** - Core tracking system
   - `LLMTracker` class for logging calls
   - `track_llm_call()` context manager for easy integration
   - Thread-safe JSONL writing
   - Automatic token counting and latency tracking

2. **`shared/llm_usage_analyzer.py`** - Analysis utilities
   - `LLMUsageAnalyzer` class for querying logs
   - Calculate usage by user, session, source, or time period
   - Generate reports and statistics
   - Export user reports to JSON

3. **`analyze_llm_usage.py`** - Command-line tool
   - Query usage from the command line
   - Generate reports for users, sessions, sources
   - List all tracked entities
   - Export reports

## Tracked Information

Each LLM call records:

| Field | Description |
|-------|-------------|
| `id` | Unique call identifier (UUID) |
| `timestamp` | ISO 8601 timestamp |
| `source_function` | Function that made the call |
| `api_provider` | Provider (gemini, google_speech, google_translate, etc.) |
| `api_type` | Type (generative, speech_to_text, translation, ocr, search) |
| `model` | Specific model used |
| `operation` | Operation type (chat_answer, summarization, transcription, etc.) |
| `input_tokens` | Number of input tokens |
| `output_tokens` | Number of output tokens |
| `total_tokens` | Total tokens |
| `latency_ms` | Call latency in milliseconds |
| `status` | Call status (success, error, timeout) |
| `error_message` | Error details if failed |
| `user_id` | User ID (for chat operations) |
| `session_id` | Chat session ID |
| `source_id` | Document/source ID (for processing operations) |
| `temperature` | Temperature parameter |
| `max_tokens` | Max output tokens |
| `additional_params` | Other parameters as JSON |
| `cost_estimate` | Estimated cost in USD |

## Configuration

### Environment Variables

```bash
# Directory for tracking logs (default: ./logs/llm_tracking)
LLM_TRACKING_DIR=/path/to/logs

# Log file name (default: master_llm_calls.jsonl)
LLM_TRACKING_FILE=master_llm_calls.jsonl
```

### Directory Structure

```
logs/
└── llm_tracking/
    └── master_llm_calls.jsonl
```

The system automatically creates the directory if it doesn't exist.

## Usage

### In Code - Context Manager Pattern

The recommended way to track LLM calls is using the context manager:

```python
from shared.llm_tracker import track_llm_call

# Track a Gemini call
with track_llm_call(
    source_function="my_function",
    api_provider="gemini",
    api_type="generative",
    model="gemini-2.0-flash-exp",
    operation="chat_answer",
    user_id="user123",
    session_id="session456",
    temperature=0.2,
    max_tokens=2048
) as call:
    # Make your API call
    response = model.generate_content(prompt)

    # Update token counts
    call.update_tokens(
        input_tokens=response.usage_metadata.prompt_token_count,
        output_tokens=response.usage_metadata.candidates_token_count
    )

    # If there's an error, it's automatically tracked
    # Or manually set error: call.set_error("error message")
```

### In Code - Direct Logging

For cases where you can't use the context manager:

```python
from shared.llm_tracker import get_tracker

tracker = get_tracker()
tracker.log_call(
    source_function="my_function",
    api_provider="gemini",
    api_type="generative",
    model="gemini-2.0-flash-exp",
    operation="summarization",
    input_tokens=1000,
    output_tokens=500,
    latency_ms=1234.5,
    status="success",
    source_id="doc_123"
)
```

### Command-Line Analysis

```bash
# Get overall usage summary
python analyze_llm_usage.py --summary

# Get user usage
python analyze_llm_usage.py --user user_123

# Get session usage
python analyze_llm_usage.py --session session_456

# Get source processing usage
python analyze_llm_usage.py --source source_789

# Get usage for last 7 days
python analyze_llm_usage.py --days 7

# Export detailed user report
python analyze_llm_usage.py --user user_123 --export user_report.json

# List all users
python analyze_llm_usage.py --list-users

# List all sessions for a user
python analyze_llm_usage.py --list-sessions --user user_123

# List all processed sources
python analyze_llm_usage.py --list-sources
```

### Programmatic Analysis

```python
from shared.llm_usage_analyzer import LLMUsageAnalyzer

analyzer = LLMUsageAnalyzer()

# Get user usage
user_stats = analyzer.get_user_usage("user_123")
print(f"Total tokens: {user_stats.total_tokens}")
print(f"Total calls: {user_stats.total_calls}")
print(f"Avg latency: {user_stats.avg_latency_ms} ms")

# Get session usage
session_stats = analyzer.get_session_usage("session_456")

# Get source processing usage
source_stats = analyzer.get_source_usage("source_789")

# Get time-based usage
last_week = analyzer.get_usage_by_time_period(days=7)

# Get overall summary
summary = analyzer.get_usage_summary()
print(f"Total users: {summary['unique_counts']['users']}")
print(f"Total sessions: {summary['unique_counts']['sessions']}")
print(f"Total tokens: {summary['overall_stats']['total_tokens']}")

# Export user report
report = analyzer.export_user_report("user_123", output_file="report.json")
```

## Integration Points

### Currently Integrated

1. **Chat Synthesizer** ([apps/agent_api/synthesizer.py:450-512](apps/agent_api/synthesizer.py#L450-L512))
   - Tracks all Gemini calls for answer generation
   - Includes user_id and session_id
   - Tracks token usage and model fallbacks

2. **Summarization** ([tools/processing/summarize_chunks.py:122-248](tools/processing/summarize_chunks.py#L122-L248))
   - Tracks Gemini calls for document summarization
   - Includes source_id for document tracking
   - Tracks retries and fallbacks

### Ready for Integration

The following API calls are identified and ready for tracking integration:

3. **Speech-to-Text** ([tools/processing/ingest_video.py:71-122](tools/processing/ingest_video.py#L71-L122))
   - Google Cloud Speech API for transcription
   - Track by source_id

4. **Translation** ([tools/processing/ingest_video.py:125-146](tools/processing/ingest_video.py#L125-L146))
   - Google Cloud Translation API
   - Track by source_id

5. **Vision API (OCR)** ([tools/processing/process_image.py:78-110](tools/processing/process_image.py#L78-L110))
   - Google Cloud Vision for text extraction
   - Track by source_id

## Example Integration

Here's how the tracking is integrated into the chat synthesizer:

```python
from shared.llm_tracker import track_llm_call

def synthesize_answer(query, summary_results, chunk_results,
                     temperature=0.2, max_output_tokens=2048,
                     user_id=None, session_id=None):

    # ... prepare prompt ...

    for model_name in FALLBACK_MODELS:
        # Track this LLM call
        with track_llm_call(
            source_function="synthesize_answer",
            api_provider="gemini",
            api_type="generative",
            model=model_name,
            operation="chat_answer",
            user_id=user_id,
            session_id=session_id,
            temperature=temperature,
            max_tokens=max_output_tokens
        ) as call:
            try:
                model = GenerativeModel(model_name)
                response = model.generate_content(prompt, generation_config=config)

                # Update tracking with actual token counts
                if hasattr(response, 'usage_metadata'):
                    call.update_tokens(
                        input_tokens=response.usage_metadata.prompt_token_count,
                        output_tokens=response.usage_metadata.candidates_token_count,
                        total_tokens=response.usage_metadata.total_token_count
                    )

                return process_response(response)

            except Exception as e:
                # Error is automatically tracked by context manager
                logger.warning(f"Model {model_name} failed: {e}")
                continue
```

## Reports and Analytics

### Usage Statistics Object

The `UsageStats` object provides:

```python
stats = analyzer.get_user_usage("user_123")

# Overall metrics
stats.total_calls          # Total number of API calls
stats.successful_calls     # Number of successful calls
stats.failed_calls         # Number of failed calls
stats.total_input_tokens   # Sum of input tokens
stats.total_output_tokens  # Sum of output tokens
stats.total_tokens         # Sum of all tokens
stats.avg_latency_ms       # Average latency in milliseconds
stats.total_cost_estimate  # Estimated total cost

# Breakdown by model
stats.by_model = {
    "gemini-2.0-flash-exp": {
        "calls": 100,
        "input_tokens": 50000,
        "output_tokens": 25000,
        "total_tokens": 75000
    },
    # ...
}

# Breakdown by operation
stats.by_operation = {
    "chat_answer": {
        "calls": 80,
        "input_tokens": 40000,
        "output_tokens": 20000,
        "total_tokens": 60000
    },
    # ...
}
```

### User Report Export

Exported user reports include:

```json
{
  "user_id": "user_123",
  "generated_at": "2025-01-15T10:30:00Z",
  "overall_stats": {
    "total_calls": 150,
    "successful_calls": 145,
    "failed_calls": 5,
    "total_input_tokens": 100000,
    "total_output_tokens": 50000,
    "total_tokens": 150000,
    "avg_latency_ms": 1250.5,
    "total_cost_estimate": 0.75,
    "by_model": { ... },
    "by_operation": { ... }
  },
  "last_30_days": {
    "total_calls": 100,
    "total_tokens": 100000,
    "total_cost_estimate": 0.50
  },
  "total_sessions": 25,
  "sessions": {
    "session_456": {
      "total_calls": 10,
      "total_tokens": 5000,
      "total_cost_estimate": 0.025
    }
  }
}
```

## Performance Considerations

- **Thread-Safe**: File writing uses locks to ensure thread safety
- **Asynchronous**: Tracking happens in the same thread but is very fast (<1ms overhead)
- **Minimal Overhead**: Context manager pattern adds minimal latency
- **JSONL Format**: Easy to parse, append-only, handles large files well
- **No Database Required**: Simple file-based storage

## Cost Estimation

To add cost estimation, you can extend the `CallTracker.set_cost_estimate()` method:

```python
# Define pricing (example rates)
PRICING = {
    "gemini-2.0-flash-exp": {
        "input": 0.075 / 1_000_000,   # $0.075 per 1M input tokens
        "output": 0.30 / 1_000_000     # $0.30 per 1M output tokens
    }
}

# In your tracking code
with track_llm_call(...) as call:
    response = model.generate_content(prompt)

    # Calculate cost
    input_cost = input_tokens * PRICING[model_name]["input"]
    output_cost = output_tokens * PRICING[model_name]["output"]
    call.set_cost_estimate(input_cost + output_cost)
```

## Monitoring and Alerts

### Daily Usage Monitoring

```python
from datetime import datetime
from shared.llm_usage_analyzer import LLMUsageAnalyzer

analyzer = LLMUsageAnalyzer()

# Get today's usage
stats = analyzer.get_usage_by_time_period(days=1)

# Check thresholds
if stats.total_tokens > 1_000_000:
    send_alert(f"High token usage: {stats.total_tokens:,} tokens today")

if stats.failed_calls > 100:
    send_alert(f"High error rate: {stats.failed_calls} failed calls")

if stats.avg_latency_ms > 5000:
    send_alert(f"High latency: {stats.avg_latency_ms:.2f} ms average")
```

### User Quota Management

```python
# Check user's monthly usage
from datetime import datetime, timedelta

user_id = "user_123"
start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

stats = analyzer.get_user_usage(
    user_id=user_id,
    start_date=start_of_month
)

USER_MONTHLY_LIMIT = 100_000  # tokens

if stats.total_tokens > USER_MONTHLY_LIMIT * 0.9:
    notify_user(user_id, "You've used 90% of your monthly quota")
```

## Best Practices

1. **Always use context manager** when possible for automatic error tracking
2. **Include user_id and session_id** for chat operations
3. **Include source_id** for document processing operations
4. **Update token counts** from actual API response metadata
5. **Set cost estimates** when you have pricing information
6. **Monitor failed calls** to identify API issues early
7. **Archive old logs** periodically (e.g., monthly) to keep files manageable
8. **Back up logs** to cloud storage for long-term analysis

## Log Rotation and Archiving

For production deployments, consider implementing log rotation:

```python
import os
import shutil
from datetime import datetime

def rotate_logs():
    """Rotate log file monthly."""
    log_file = Path("logs/llm_tracking/master_llm_calls.jsonl")

    if log_file.exists():
        # Archive with timestamp
        archive_name = f"master_llm_calls_{datetime.now().strftime('%Y%m')}.jsonl"
        archive_path = log_file.parent / "archive" / archive_name
        archive_path.parent.mkdir(exist_ok=True)

        # Move to archive
        shutil.move(str(log_file), str(archive_path))

        # Optionally compress
        import gzip
        with open(archive_path, 'rb') as f_in:
            with gzip.open(f"{archive_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(archive_path)
```

## Troubleshooting

### No logs appearing

1. Check that `LLM_TRACKING_DIR` exists and is writable
2. Verify the tracking code is being executed
3. Check for exceptions in the logs

### Missing token counts

1. Ensure you're calling `call.update_tokens()` with actual values from API response
2. Some APIs may not return token counts - check API documentation

### High latency overhead

1. The tracking itself should add <1ms overhead
2. If seeing high overhead, check disk I/O performance
3. Consider using a separate thread for writing (future enhancement)

## Future Enhancements

Potential improvements:

- [ ] Asynchronous log writing for zero latency impact
- [ ] Built-in log rotation
- [ ] Database backend option (PostgreSQL, MongoDB)
- [ ] Real-time dashboards (Grafana, custom UI)
- [ ] Automated cost calculation with configurable pricing
- [ ] Alert system for quota management
- [ ] Integration with Google Cloud Billing API
- [ ] ML-based anomaly detection

## API Reference

See the inline documentation in:
- [shared/llm_tracker.py](shared/llm_tracker.py) - Core tracking API
- [shared/llm_usage_analyzer.py](shared/llm_usage_analyzer.py) - Analysis API

## License

Part of the CENTEF RAG system.
