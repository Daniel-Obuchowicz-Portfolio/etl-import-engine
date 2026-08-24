import asyncio

from fastapi import FastAPI, Query, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock CRM API", version="1.0.0")


def customers() -> list[dict[str, str]]:
    return [
        {
            "crm_id": f"CRM-{number:04d}",
            "customer_name": f"Mock Customer {number}",
            "mail_address": f"customer{number}@example.com",
            "telephone": f"+48100{number:06d}",
            "company": f"Mock Company {(number - 1) % 20 + 1}",
        }
        for number in range(1, 101)
    ]


@app.get("/mock/customers", response_model=None)
async def get_customers(
    mode: str = Query(default="normal", pattern="^(normal|400|500|timeout|invalid_json)$"),
) -> Response | list[dict[str, str]]:
    if mode == "400":
        return JSONResponse(status_code=400, content={"error": "simulated bad request"})
    if mode == "500":
        return JSONResponse(status_code=500, content={"error": "simulated server failure"})
    if mode == "timeout":
        await asyncio.sleep(30)
    if mode == "invalid_json":
        return Response(content="{this is not json", media_type="application/json")
    return customers()
