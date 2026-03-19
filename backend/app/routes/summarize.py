from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.summarize_service import summarize_sql_result

router = APIRouter()

class SummarizeRequest(BaseModel):
    db_name: str
    sql_query: str

@router.post("/")
def summarize_query(request: SummarizeRequest):
    try:
        result = summarize_sql_result(request.sql_query, request.db_name)
        if "error" in result:
            # Handle quota exceeded errors with appropriate status code
            if result.get("quota_exceeded"):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": result.get("error", "API quota exceeded"),
                        "details": result.get("details", ""),
                        "quota_exceeded": True
                    }
                )
            # Other errors return 500
            raise HTTPException(status_code=500, detail=result["error"])
        return {"status": "success", **result}
    except HTTPException:
        # Re-raise HTTP exceptions (like 429) as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")