"""Fine-grained observation types for ii-agent."""

from .files import FileReadObservation, FileWriteObservation, FileEditObservation

__all__ = [
    "FileReadObservation",
    "FileWriteObservation",
    "FileEditObservation", 
]