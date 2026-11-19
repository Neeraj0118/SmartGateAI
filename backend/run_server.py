"""
Local server runner for SmartGateAI FastAPI backend.
Strictly enforces localhost-only network binding (127.0.0.1) for security.
"""

import sys
import argparse
import uvicorn
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description="Run SmartGateAI FastAPI Server (Localhost Only)")
    parser.add_argument(
        "--host",
        type=str,
        default=settings.SERVER_HOST,
        help="Host IP address (strictly restricted to 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.SERVER_PORT,
        help="Port to listen on (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )

    args = parser.parse_args()

    # Enforce strict localhost binding security rule
    if args.host not in ("127.0.0.1", "localhost"):
        print(f"SECURITY ERROR: Binding to '{args.host}' is prohibited.")
        print("SmartGateAI is strictly configured to bind to 127.0.0.1 only during development.")
        sys.exit(1)

    # Verify that admin API key is configured before starting
    try:
        _ = settings.ADMIN_API_KEY
    except RuntimeError as e:
        print(f"\n{e}\n")
        sys.exit(1)

    print("=" * 65)
    print("  SmartGateAI Backend Server Starting (Secure Localhost Mode)")
    print(f"  Bound Address: http://127.0.0.1:{args.port}")
    print(f"  Swagger UI:    http://127.0.0.1:{args.port}/docs")
    print(f"  Health Check:  http://127.0.0.1:{args.port}/health")
    print("=" * 65)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
