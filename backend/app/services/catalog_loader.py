import os
from typing import Any, Dict, List

import pandas as pd

from app.services.maturity_scoring import normalize_maturity as norm_catalog_maturity

CATALOG_PATH = os.path.join(os.path.dirname(__file__), '../data/catalog.xlsx')

# Workbook has merged title rows; real headers are row 3 in Excel → header index 2.
_CATALOG_HEADER_ROW = 2


def _normalize_column_key(raw: Any) -> str:
    """Map Excel headings (Title Case / spaces) to snake_case pandas keys."""
    s = str(raw).strip().lower().replace(" ", "_").replace("/", "_").replace("__", "_")
    return "".join(c for c in s if c.isalnum() or c == "_")


def _normalize_catalog_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    renamed: dict[Any, str] = {}
    for col in df.columns:
        key = _normalize_column_key(col)
        if key == "" or key == "#":
            key = "_row_index"
        renamed[col] = key
    out = df.rename(columns=renamed)
    if "key_features" in out.columns and "features" not in out.columns:
        out = out.rename(columns={"key_features": "features"})
    return out


class Solution:
    def __init__(self, row: pd.Series):
        self.solution_name = _scalar(row.get("solution_name", "")).strip()
        self.description = _scalar(row.get("description", "")).strip()
        self.domain = _scalar(row.get("domain", "")).strip()
        self.target_objective = _scalar(row.get("target_objective", "")).strip()
        self.maturity = self._normalize_maturity(row.get("maturity", ""))
        self.deployments = _int_safe(row.get("deployments"))
        self.client_sectors = self._split_and_strip(row.get('client_sectors', ''))
        self.features = self._split_and_strip(row.get('features', ''))
        self.limitations = self._split_and_strip(row.get('limitations', ''))
        self.complexity = self._normalize_complexity(row.get("complexity", ""))
        self.ipm_stage = _scalar(row.get("ipm_stage", "")).strip()

    def _split_and_strip(self, value: Any) -> List[str]:
        if pd.isna(value):
            return []
        return [v.strip() for v in str(value).split('|') if v.strip()]

    def _normalize_maturity(self, value: Any) -> str:
        if pd.isna(value):
            return ""
        raw = str(value).strip()
        canon = norm_catalog_maturity(raw)
        if canon is not None:
            return canon
        return raw.lower()

    def _normalize_complexity(self, value: Any) -> str:
        if pd.isna(value):
            return ""
        v = str(value).strip().lower()
        if v in {"low", "medium", "high"}:
            return v
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


def _scalar(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _int_safe(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return 0
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


class CatalogLoader:
    def __init__(self, path: str = CATALOG_PATH):
        self.path = path
        self.solutions: List[Solution] = []
        self.load_catalog()

    def load_catalog(self):
        df = pd.read_excel(
            self.path,
            sheet_name="AI Portfolio Catalog",
            header=_CATALOG_HEADER_ROW,
        )
        df = _normalize_catalog_dataframe(df)
        self.solutions = []
        for _, row in df.iterrows():
            sol = Solution(row)
            if sol.solution_name or sol.description:
                self.solutions.append(sol)

    def get_solutions(self) -> List[Solution]:
        return self.solutions

    def get_solution_dicts(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.solutions]

# Singleton instance
catalog_loader = CatalogLoader()
