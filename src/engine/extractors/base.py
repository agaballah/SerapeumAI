import abc
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ExtractionResult:
    records: List[Dict[str, Any]] = field(default_factory=list) # Raw staging records
    diagnostics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True

class BaseExtractor(abc.ABC):
    """
    Contract for V02 Extractors.
    Must be deterministic and stateless relative to the file version.
    """
    
    @property
    @abc.abstractmethod
    def id(self) -> str:
        pass
        
    @property
    @abc.abstractmethod
    def version(self) -> str:
        # Semver e.g. "1.0.0"
        pass
        
    @property
    @abc.abstractmethod
    def supported_extensions(self) -> List[str]:
        pass

    @abc.abstractmethod
    def extract(self, file_path: str, context: Dict[str, Any] = None) -> ExtractionResult:
        """
        :param file_path: Absolute path to the file content (the versioned blob)
        :param context: Optional execution context (logging, etc)
        """
        pass
