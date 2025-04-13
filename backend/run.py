"""
Start the FastAPI server with proper configuration.
This ensures the server is running on the right interface.
"""

import uvicorn

if __name__ == "__main__":
    # Run on 127.0.0.1 to explicitly use IPv4
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )