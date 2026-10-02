import os


class OriginMissing(RuntimeError):
    pass


def resolve_origin(cli_value: str | None = None) -> str:
    if cli_value:
        return cli_value
    env = os.environ.get("INVARIANTTAP_ORIGIN")
    if env:
        return env
    raise OriginMissing(
        "origin not set. Provide --origin, set INVARIANTTAP_ORIGIN, "
        "or declare it in config. Refusing to mint without an origin."
    )
