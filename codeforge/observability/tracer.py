"""Small JSON trace collector for agent workflow observability."""
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Span:
    span_id: str
    name: str
    span_type: str = "internal"
    attributes: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

class TraceCollector:
    def __init__(self, trace_dir: str = "./traces", trace_id: Optional[str] = None):
        self.trace_id = trace_id or f"tr_{uuid.uuid4().hex[:12]}"
        self.trace_dir = trace_dir
        self.spans: List[Span] = []

    def start_span(self, name: str, span_type: str = "internal", attributes: Optional[Dict[str, Any]] = None) -> Span:
        span = Span(uuid.uuid4().hex[:12], name, span_type, attributes or {})
        self.spans.append(span)
        return span

    def end_span(self, span_id: str) -> None:
        for span in reversed(self.spans):
            if span.span_id == span_id:
                span.ended_at = time.time()
                return

    def export_json(self, path: Optional[str] = None) -> str:
        os.makedirs(self.trace_dir, exist_ok=True)
        output = path or os.path.join(self.trace_dir, f"{self.trace_id}.json")
        payload = {"trace_id": self.trace_id, "spans": [s.__dict__ for s in self.spans]}
        with open(output, "w", encoding="utf-8") as f: json.dump(payload, f, indent=2, default=str)
        return output
