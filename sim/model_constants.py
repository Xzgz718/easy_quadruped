LEG_SPECS = (
    ("fr", 0, "0.90 0.30 0.30 1"),
    ("fl", 1, "0.30 0.90 0.30 1"),
    ("br", 2, "0.30 0.30 0.90 1"),
    ("bl", 3, "0.90 0.90 0.30 1"),
)

JOINT_NAMES = tuple(
    name
    for prefix, _, _ in LEG_SPECS
    for name in (f"{prefix}_abad", f"{prefix}_hip", f"{prefix}_knee")
)

FOOT_SITE_NAMES = tuple(f"{prefix}_foot" for prefix, _, _ in LEG_SPECS)
