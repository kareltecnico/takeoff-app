from __future__ import annotations

import importlib
import pkgutil


def test_domain_imports_do_not_pull_application_or_infrastructure() -> None:
    """
    Importing all domain modules should not pull application/infrastructure.

    If a domain module imports application or infrastructure, the import may create
    unwanted side effects and break the layering rules.
    """
    pkg = importlib.import_module("app.domain")
    for m in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(m.name)