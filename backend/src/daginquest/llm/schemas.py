from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "IMPORT_ERROR", "SCHEMA_SQL", "TRANSIENT_NETWORK", "CONFIG_SECRET",
    "RESOURCE", "UPSTREAM_DATA", "INCONCLUSIVE",
]


class RCAResult(BaseModel):
    category: Category
    root_cause: str = Field(description="One or two sentences, grounded in the log")
    confidence: float = Field(ge=0.0, le=1.0)
    cited_lines: list[str] = Field(
        default_factory=list, description="Exact log lines that support the conclusion"
    )
