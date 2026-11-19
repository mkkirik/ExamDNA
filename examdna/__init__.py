"""ExamDNA — reverse-engineer exams, mutate questions, compile new assessments.

The package is the deterministic engine of the ExamDNA Agent Skill. It never
calls a language model: semantic work (reading documents, writing candidate
questions, making semantic judgements) is performed by the host agent and
handed to this package as structured JSON.
"""

__version__ = "0.1.0"
SCHEMA_VERSION = "0.1.0"

__all__ = ["__version__", "SCHEMA_VERSION"]
