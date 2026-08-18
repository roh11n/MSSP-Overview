"""Tenant-aware mock data adapter.

Applies deterministic per-tenant modifiers to the base mock_data functions so
each QRadar domain shows its own KPI profile.
"""
import hashlib
import random
from datetime import datetime, timezone

import mock_data


DEFAULT_TENANTS = [
    {
        "id": "all",
        "domain": "ALL",
        "name": "All Tenants",
        "description": "Aggregated across every QRadar domain",
        "primary_color": "#3B82F6",
        "logo_url": None,
        "created_at": None,
        "risk_modifier": 1.0,
        "volume_modifier": 1.0,
        "seed": False,
    },
    {
        "id": "acme-corp",
        "domain": "ACME_CORP",
        "name": "Acme Corporation",
        "description": "Enterprise manufacturing · QRadar Domain 12",
        "primary_color": "#EA580C",
        "logo_url": None,
        "created_at": None,
        "risk_modifier": 1.15,
        "volume_modifier": 1.3,
        "seed": True,
    },
    {
        "id": "globalbank",
        "domain": "GLOBALBANK_FIN",
        "name": "GlobalBank Financial",
        "description": "Tier-1 bank · QRadar Domain 07",
        "primary_color": "#0EA5E9",
        "logo_url": None,
        "created_at": None,
        "risk_modifier": 0.85,
        "volume_modifier": 0.75,
        "seed": True,
    },
]


def _tenant_factor(tenant: dict, key: str) -> float:
    if not tenant or tenant.get("id") in (None, "all"):
        return 1.0
    h = hashlib.md5(f"{tenant['id']}:{key}".encode()).hexdigest()
    jitter = (int(h[:6], 16) % 200 - 100) / 1000.0  # ±10%
    return tenant.get("volume_modifier", 1.0) * (1 + jitter)


def _apply_num(v, factor):
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return max(0, int(round(v * factor)))
    if isinstance(v, float):
        return round(v * factor, 2)
    return v


def _scale_dict(d: dict, factor: float, skip_keys=("period", "top_threat_actor", "top_targeted_asset")):
    out = {}
    for k, v in d.items():
        if k in skip_keys:
            out[k] = v
        elif isinstance(v, dict):
            out[k] = _scale_dict(v, factor, skip_keys)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = _apply_num(v, factor)
        else:
            out[k] = v
    return out


def executive_overview(period: str, tenant: dict):
    base = mock_data.executive_overview(period)
    if not tenant or tenant.get("id") == "all":
        return base
    f_vol = _tenant_factor(tenant, "vol")
    f_risk = tenant.get("risk_modifier", 1.0)
    base["incidents"] = _apply_num(base["incidents"], f_vol)
    base["offenses"] = _apply_num(base["offenses"], f_vol)
    base["mttr_hours"] = round(base["mttr_hours"] * f_risk, 1)
    base["risk_score"] = round(min(100, base["risk_score"] * f_risk), 1)
    base["health_score"] = round(max(0, base["health_score"] / f_risk if f_risk else base["health_score"]), 1)
    base["sla_compliance"] = round(min(100, base["sla_compliance"] / (f_risk ** 0.2)), 1)
    base["advisories"] = _apply_num(base["advisories"], f_vol)
    base["tenant"] = {"id": tenant["id"], "name": tenant["name"], "domain": tenant["domain"]}
    return base


def soc_manager(period: str, tenant: dict):
    base = mock_data.soc_manager(period)
    if not tenant or tenant.get("id") == "all":
        return base
    f = _tenant_factor(tenant, "soc")
    base["incident_ops"] = _scale_dict(base["incident_ops"], f)
    base["sla"]["breaches"] = _apply_num(base["sla"]["breaches"], f)
    return base


def client_executive(period: str, tenant: dict):
    base = mock_data.client_executive(period)
    if not tenant or tenant.get("id") == "all":
        return base
    f = _tenant_factor(tenant, "client")
    base["business_risk"]["phishing_incidents"] = _apply_num(base["business_risk"]["phishing_incidents"], f)
    base["business_risk"]["repeat_incidents"] = _apply_num(base["business_risk"]["repeat_incidents"], f)
    return base


def detection_engineering(period: str, tenant: dict):
    return mock_data.detection_engineering(period)


def threat_intelligence(period: str, tenant: dict):
    return mock_data.threat_intelligence(period)


def soar_automation(period: str, tenant: dict):
    return mock_data.soar_automation(period)


def all_dashboards(period: str, tenant: dict):
    """Return every dashboard payload for PPTX / email generation."""
    return {
        "executive": executive_overview(period, tenant),
        "soc_manager": soc_manager(period, tenant),
        "client": client_executive(period, tenant),
        "detection": detection_engineering(period, tenant),
        "threat_intel": threat_intelligence(period, tenant),
        "soar": soar_automation(period, tenant),
    }
