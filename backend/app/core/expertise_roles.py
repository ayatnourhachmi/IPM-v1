"""Default delivery-role taxonomy used when callers omit ``allowed_roles``."""

# Canonical spellings returned in API responses — must align with prompting examples.
DEFAULT_ALLOWED_EXPERTISE_ROLES: tuple[str, ...] = (
    "Data Scientist",
    "AI Engineer",
    "ML Engineer",
    "Cloud Architect",
    "Solution Architect",
    "Data Engineer",
    "DevOps Engineer",
    "Platform Engineer",
    "Security Architect",
    "Business Analyst",
    "Product Owner",
    "Scrum Master",
    "Technical Lead",
)
