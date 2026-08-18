"""Cybersecurity-focused recommendation engine.

Analyzes KPI signals and produces contextual, actionable recommendations
for MSSP SOC leadership. Rule-based intelligence engine designed as a drop-in
for a HuggingFace cybersecurity LLM (e.g. CySecBERT/SecureBERT).
"""
from typing import List, Dict


def _tag(priority: str) -> Dict:
    return {
        "P1": {"label": "Critical", "color": "danger"},
        "P2": {"label": "High", "color": "warning"},
        "P3": {"label": "Medium", "color": "primary"},
        "P4": {"label": "Advisory", "color": "success"},
    }[priority]


def generate(exec_data: dict, soc: dict, det: dict, ti: dict, soar: dict) -> List[Dict]:
    recs = []

    sla = exec_data["sla_compliance"]
    mttr = exec_data["mttr_hours"]
    det_cov = exec_data["detection_coverage"]
    auto = exec_data["automation_rate"]
    fp = soc["detection_health"]["false_positive_rate"]

    if sla < 95:
        recs.append({
            "priority": "P1",
            "tag": _tag("P1"),
            "area": "SLA",
            "title": f"SLA compliance at {sla}% — below 95% target",
            "insight": (
                f"Response SLA at {soc['sla']['response_sla']}% and resolution SLA at "
                f"{soc['sla']['resolution_sla']}%. Top breach cause: "
                f"{soc['sla']['breach_causes'][0]['cause']}."
            ),
            "action": "Re-balance L1 shift coverage and enable auto-escalation playbook after 15 min queue time.",
        })

    if mttr > 60:
        recs.append({
            "priority": "P2",
            "tag": _tag("P2"),
            "area": "Speed",
            "title": f"MTTR trending high at {mttr}h",
            "insight": (
                f"Investigation time averaging {soc['speed_metrics']['investigation_time_hours']}h. "
                f"Queue time at {soc['speed_metrics']['queue_time_min']} min."
            ),
            "action": "Deploy enrichment playbook (IOC + Asset + Identity context) at incident create-time to shave investigation.",
        })

    if fp > 25:
        recs.append({
            "priority": "P2",
            "tag": _tag("P2"),
            "area": "Detection",
            "title": f"False-positive rate at {fp}% — tune noisy rules",
            "insight": (
                f"{soc['detection_health']['top_rules'][0]['rule']} triggers "
                f"{soc['detection_health']['top_rules'][0]['triggers']} times with "
                f"{soc['detection_health']['top_rules'][0]['fp_rate']}% FP."
            ),
            "action": "Tune top-3 high-FP rules with allowlist enrichment; expected 30–40% noise reduction.",
        })

    if det_cov < 80:
        recs.append({
            "priority": "P3",
            "tag": _tag("P3"),
            "area": "Coverage",
            "title": f"MITRE ATT&CK coverage at {det_cov}% — expand detection surface",
            "insight": (
                f"{det['gap_analysis']['techniques_missing']} techniques uncovered. "
                f"Top opportunity: {det['gap_analysis']['new_opportunities'][0]}."
            ),
            "action": "Prioritize Initial Access & Credential Access tactic gaps; ship 3 new rules this sprint.",
        })

    if auto < 70:
        recs.append({
            "priority": "P3",
            "tag": _tag("P3"),
            "area": "Automation",
            "title": f"Automation rate at {auto}% — automate top manual flows",
            "insight": (
                f"Manual closures at {soar['efficiency']['manual_closures']}. "
                f"ROI on existing automation: {soar['efficiency']['automation_roi_pct']}%."
            ),
            "action": "Convert 'Phishing Triage' and 'Failed Login Cooldown' to full auto-remediation.",
        })

    top_actor = ti["landscape"]["threat_actors"][0]
    recs.append({
        "priority": "P2",
        "tag": _tag("P2"),
        "area": "Threat Intel",
        "title": f"{top_actor['name']} activity elevated",
        "insight": (
            f"{ti['landscape']['total_advisories']} advisories this period. "
            f"IOC hit-rate at {ti['effectiveness']['ioc_match_rate']}%."
        ),
        "action": "Push actor TTP hunt-pack to detection engineering + notify high-risk clients in briefing.",
    })

    if exec_data["risk_score"] > 40:
        recs.append({
            "priority": "P1",
            "tag": _tag("P1"),
            "area": "Risk",
            "title": f"Composite risk elevated ({exec_data['risk_score']})",
            "insight": (
                f"Health score at {exec_data['health_score']}. Top targeted asset: "
                f"{exec_data['top_targeted_asset']}."
            ),
            "action": "Convene weekly risk review; freeze non-critical changes on top-3 assets.",
        })

    # Positive advisory
    if sla >= 97 and auto >= 70:
        recs.append({
            "priority": "P4",
            "tag": _tag("P4"),
            "area": "Health",
            "title": "SOC operating within all executive KPIs",
            "insight": f"SLA {sla}% · Automation {auto}% · Coverage {det_cov}%.",
            "action": "Maintain cadence. Reallocate 10% capacity to proactive threat hunting.",
        })

    return recs
