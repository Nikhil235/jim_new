"""Run Phase 1 infrastructure checks."""

from src.utils.config import load_config
from src.utils.infra import check_stack, print_stack_summary


def main() -> None:
    cfg = load_config()
    checks = check_stack(cfg)
    print_stack_summary(checks)


if __name__ == "__main__":
    main()
