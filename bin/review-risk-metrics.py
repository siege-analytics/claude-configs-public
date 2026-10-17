#!/usr/bin/env python3
"""Generate freshness-checked proportional review policy metrics."""
import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"catalog/review-risk-metrics.json"
spec=importlib.util.spec_from_file_location("review_risk",ROOT/"bin/review-risk.py");m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
policy=json.loads((ROOT/"catalog/review-risk-policy.json").read_text())
fixtures={
 "trivial_docs":["README.md"],
 "standard_skill":["skills/python/SKILL.md"],
 "standard_advisory_log_helper":["hooks/lib/log-block.sh"],
 "high_risk_gate":["hooks/git/self-review.sh"],
 "high_risk_scope_helper":["hooks/lib/scope-check.sh"],
 "high_risk_infrastructure_guard":["hooks/infrastructure/catalog-guard.sh"],
 "high_risk_authority_checker":["bin/generated-source-authority.py"],
 "high_risk_runtime_generator":["bin/build.py"],
 "mixed":["README.md","bin/install.sh"],
}
data={"schema_version":1,"policy_characters":len((ROOT/"catalog/review-risk-policy.json").read_text()),"classifier_characters":len((ROOT/"bin/review-risk.py").read_text()),"fixture_tiers":{name:m.classify(policy,paths)["computed_tier"] for name,paths in fixtures.items()},"required_evidence_counts":{tier:len(meta["required_evidence"]) for tier,meta in policy["tiers"].items()},"legacy_minimum_artifact_for_all_tiers":True,"load_set_change":0}
text=json.dumps(data,indent=2,sort_keys=True)+"\n"
if "--check" in sys.argv:
 if not OUT.exists() or OUT.read_text()!=text:print("review risk metrics stale; run python3 bin/review-risk-metrics.py",file=sys.stderr);raise SystemExit(1)
 print("review risk metrics: current");raise SystemExit(0)
OUT.write_text(text);print(f"wrote {OUT.relative_to(ROOT)}")
