import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "../data/catalog.xlsx")


class DXCContext:
    def __init__(self, path: str = CATALOG_PATH):
        self.path = path
        self.context: Dict[str, List[str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            import pandas as pd

            df = pd.read_excel(self.path, sheet_name="DXC Capability Context")
            for col in df.columns:
                self.context[col.strip()] = self._split_and_strip(df[col].dropna().tolist())
            logger.info("DXC capability context loaded from %s", self.path)
        except FileNotFoundError:
            logger.warning("DXC catalog not found at %s — context will be empty.", self.path)
        except Exception as exc:
            logger.warning("Failed to load DXC capability context (non-fatal): %s", exc)

    def _split_and_strip(self, values: List[Any]) -> List[str]:
        result = []
        for v in values:
            if isinstance(v, str):
                result.extend([x.strip() for x in v.split("|") if x.strip()])
            else:
                result.append(str(v).strip())
        return [x for x in result if x]

    def get_context(self) -> Dict[str, List[str]]:
        return self.context


# Singleton — empty dict if catalog is missing, never crashes on import.
DXC_CONTEXT: Dict[str, List[str]] = DXCContext().get_context()
