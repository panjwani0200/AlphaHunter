from fastapi import APIRouter, HTTPException, Path
from app.outperform.models import OutperformDashboardResponse, OutperformAnalysisResponse
from app.outperform.scoring_engine import generate_dashboard
from app.outperform.analysis_engine import generate_stock_analysis

router = APIRouter()

@router.get("/dashboard", response_model=OutperformDashboardResponse)
async def get_outperform_dashboard():
    """
    Returns the Outperform Today master dashboard with Market Health and Top AI Picks.
    """
    try:
        return await generate_dashboard()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")

@router.get("/analysis/{symbol}", response_model=OutperformAnalysisResponse)
async def get_outperform_analysis(symbol: str = Path(..., min_length=1, max_length=20)):
    """
    Returns the comprehensive 18-engine analysis for a specific stock.
    """
    try:
        return await generate_stock_analysis(symbol.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis for {symbol}: {str(e)}")
