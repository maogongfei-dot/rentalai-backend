from backend.services.unified_short_rent_service import (
    get_final_short_rent_recommendations,
)


def get_short_rent_recommendations_api(filters: dict = None) -> dict:
    try:
        results = get_final_short_rent_recommendations(filters)
        return {
            "success": True,
            "data": results,
            "count": len(results),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0,
        }
