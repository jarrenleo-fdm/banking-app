"""MCP server entry point."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "banking_app.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import django  # noqa: E402

django.setup()

from .server import mcp  # noqa: E402, F401


def main():
    mcp.run()


if __name__ == "__main__":
    main()
