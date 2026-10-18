"""Conservative interpretation of observed unittest outcomes."""


def classify(baseline: dict, attempts: list[dict], control: dict | None = None) -> str:
    if baseline.get("kind") not in {"pass", "no_tests"} or len(attempts) != 2:
        return "could_not_investigate"
    if control is not None and control.get("kind") != "pass":
        return "could_not_investigate"
    if any(a.get("tests", 0) < 1 for a in attempts):
        return "could_not_investigate"
    if all(a.get("kind") == "pass" for a in attempts):
        return "not_reproduced"
    if all(a.get("kind") == "assertion_failure" for a in attempts):
        signatures = [a.get("signature") for a in attempts]
        if signatures[0] and signatures[0] == signatures[1]:
            return "reproduced"
    return "could_not_investigate"
