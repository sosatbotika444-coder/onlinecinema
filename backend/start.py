import os
import sys

import uvicorn


def main() -> None:
    port_raw = os.getenv("PORT", "8000")
    try:
        port = int(port_raw)
    except ValueError:
        print(f"Invalid PORT={port_raw!r}; falling back to 8000", flush=True)
        port = 8000

    print(
        "Starting SexParty API "
        f"on 0.0.0.0:{port} "
        f"(ENVIRONMENT={os.getenv('ENVIRONMENT', 'development')}, "
        f"PYTHON={sys.version.split()[0]})",
        flush=True,
    )
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
