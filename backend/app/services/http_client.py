from itertools import count
import httpx


async def fetch_demo_users():
    """Fetch users from the existing fixed demo endpoint."""
    url = "https://jsonplaceholder.typicode.com/users"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        return {
            "status_code": response.status_code,
            "data": response.json(),
        }


    
    except httpx.TimeoutException as error:
        return {
            "error_type": "timeout",
            "message": str(error),
        }

    except httpx.HTTPError as error:
        return {
            "error_type": "http_error",
            "message": str(error),
        }
   
    

async def fetch_demo_user_count():
    """Return the number of users from the fixed demo endpoint."""
    result = await fetch_demo_users()

    if "error_type" in result:
        return result

    return {
        "count": len(result["data"])
    }

def format_user_count(count: int, label: str)-> dict[str, int | str]:
    return {
        "label": label,
        "count": count,
    }
   

