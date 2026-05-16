"""Utilities for deriving naming rules from SQLAlchemy MetaData.naming_convention."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy import MetaData


@dataclass
class NamingConventionRules:
    """Naming rules derived from a SQLAlchemy naming_convention dict."""

    index_prefixes: list[str] = field(default_factory=list)
    index_suffixes: list[str] = field(default_factory=list)
    fk_prefixes: list[str] = field(default_factory=list)
    fk_suffixes: list[str] = field(default_factory=list)
    check_prefixes: list[str] = field(default_factory=list)
    check_suffixes: list[str] = field(default_factory=list)
    uq_prefixes: list[str] = field(default_factory=list)
    uq_suffixes: list[str] = field(default_factory=list)
    pk_prefixes: list[str] = field(default_factory=list)
    pk_suffixes: list[str] = field(default_factory=list)


def _extract_prefix(template: str) -> str | None:
    """Return the literal prefix before the first template placeholder, or None."""
    idx = template.find("%(")
    if idx < 0:
        return None
    prefix = template[:idx]
    return prefix if prefix else None


def _extract_suffix(template: str) -> str | None:
    """Return the literal suffix after the last template placeholder, or None."""
    idx = template.rfind(")s")
    if idx < 0:
        return None
    suffix = template[idx + 2 :]
    return suffix if suffix else None


_CONVENTION_KEY_MAP = {
    "ix": ("index_prefixes", "index_suffixes"),
    "fk": ("fk_prefixes", "fk_suffixes"),
    "ck": ("check_prefixes", "check_suffixes"),
    "uq": ("uq_prefixes", "uq_suffixes"),
    "pk": ("pk_prefixes", "pk_suffixes"),
}


# SQLAlchemy always ships with this single-entry default; it is not a
# user-defined convention and should not override the gauntlet's own defaults.
_SQLALCHEMY_DEFAULT_CONVENTION: frozenset[str] = frozenset({"ix"})


def rules_from_metadata(metadata: MetaData) -> NamingConventionRules:
    """Derive :class:`NamingConventionRules` from ``metadata.naming_convention``.

    Only literal prefixes and suffixes are extracted — fully dynamic templates
    (no literal prefix or suffix) are silently ignored.

    The SQLAlchemy built-in default convention (``{"ix": "ix_%(column_0_label)s"}``)
    is ignored; only user-supplied conventions are considered.

    Args:
        metadata: SQLAlchemy ``MetaData`` instance.

    Returns:
        :class:`NamingConventionRules` with lists populated from the convention.
        Fields for which no literal prefix/suffix could be extracted are empty.
    """
    convention = getattr(metadata, "naming_convention", {}) or {}
    if set(convention.keys()) == _SQLALCHEMY_DEFAULT_CONVENTION:
        return NamingConventionRules()
    rules = NamingConventionRules()

    for key, (prefix_attr, suffix_attr) in _CONVENTION_KEY_MAP.items():
        template = convention.get(key)
        if not isinstance(template, str):
            continue

        prefix = _extract_prefix(template)
        suffix = _extract_suffix(template)

        if prefix:
            getattr(rules, prefix_attr).append(prefix)
        if suffix:
            getattr(rules, suffix_attr).append(suffix)

    return rules
