"""Source ingestion: loading structured inputs and normalizing question records."""

from .normalize import normalize_bank, normalize_question  # noqa: F401
from .loaders import load_source, parse_text_exam  # noqa: F401
