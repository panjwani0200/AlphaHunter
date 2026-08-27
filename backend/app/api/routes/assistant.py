import re
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.trading_service import trading_service

router = APIRouter(prefix="/assistant")

class QueryRequest(BaseModel):
    query: str

def parse_symbol_from_query(query: str) -> str | None:
    query_upper = query.upper()
    
    # Common mappings
    mappings = {
        "RELIANCE": "RELIANCE",
        "INFOSYS": "INFY",
        "INFY": "INFY",
        "HDFC BANK": "HDFCBANK",
        "HDFCBANK": "HDFCBANK",
        "TATA MOTORS": "TATAMOTORS",
        "TATAMOTORS": "TATAMOTORS",
        "BHEL": "BEL",
        "BEL": "BEL",
        "NIFTY": "NIFTY",
        "BANKNIFTY": "BANKNIFTY",
        "CDSL": "CDSL",
        "ADANIPOWER": "ADANIPOWER"
    }
    
    for term, sym in mappings.items():
        if term in query_upper:
            return sym
            
    # Priority 1: Check for exact match against known active watchlist symbols
    words = re.findall(r'[A-Z0-9&-]+', query_upper)
    for w in words:
        clean_w = w.strip("-&")
        if clean_w in trading_service._active_symbols:
            return clean_w

    # Stop words to ignore
    stop_words = {
        "WHY", "THE", "AND", "FOR", "BUY", "HAS", "GET", "ASK", "HOW", "RUN", "OUT",
        "SHOW", "VERDICT", "ANALYZE", "ANALYSIS", "STOCK", "STOCKS", "REPORT",
        "BULLISH", "BEARISH", "SIDEWAYS", "STATUS", "PRICING", "PRICE", "TODAY",
        "WHAT", "WHEN", "WHERE", "WHO", "WHICH", "THAT", "THIS", "THEM", "THEIR",
        "ABOUT", "QUERY", "PLEASE", "TELL", "LOOK", "CHART", "SIGNAL", "TIER",
        "EXPLAIN", "EXPLAINING", "DETAILS", "INFO", "INFORMATION", "VIEW", "CHECK"
    }
    
    # Extract uppercase words that look like tickers (can include numbers, hyphens, ampersands)
    for w in words:
        if len(w) >= 3 and w not in stop_words:
            clean_w = w.strip("-&")
            if len(clean_w) >= 2:
                return clean_w
            
    return None

@router.post("/ask")
async def ask_assistant(req: QueryRequest):
    symbol = parse_symbol_from_query(req.query)
    if not symbol:
        return {
            "reply": "I couldn't identify the ticker symbol in your query. Please specify a symbol like: 'Why is RELIANCE bullish?' or 'Show me CDSL details.'"
        }
        
    # Generate the scanner candidate on the fly
    quotes = trading_service.get_live_quotes([symbol])
    if not quotes:
        return {
            "reply": f"Sorry, I couldn't find live market data for symbol '{symbol}'."
        }
        
    try:
        # Retrieve snapshots if available in active cache
        scanner_results = await trading_service.get_snapshots()
        
        # Build explanation
        from app.engine.scoring import score_candidate
        from app.engine.technicals import analyze_technicals
        
        # Find corresponding snapshot
        target_snap = None
        for s in scanner_results:
            if s.symbol.upper() == symbol.upper():
                target_snap = s
                break
                
        if not target_snap:
            # Dynamically fetch 1y historical candles for the symbol on the fly
            try:
                target_snap = trading_service.collector.snapshot_for(symbol)
            except Exception:
                target_snap = quotes[0]
            
        # Get candles and technicals
        candles = target_snap.candles if hasattr(target_snap, "candles") and target_snap.candles else []
        tech = analyze_technicals(symbol, candles) if candles else None
        
        if not tech:
            return {
                "reply": f"The stock {symbol} is currently showing neutral trends. Historical candle history could not be downloaded."
            }
            
        candidate = score_candidate(target_snap, tech)
        
        # Check if user requested the full analyst tear-down report
        query_upper = req.query.upper()
        is_analyst_report = any(w in query_upper for w in ("REPORT", "TEAR", "DIMENSIONS", "EQUITY RESEARCH", "VERDICT", "DNA"))
        if is_analyst_report:
            from app.ai.analyst import generate_equity_research_report
            reply = generate_equity_research_report(candidate)
            return {"reply": reply}
            
        # Build rich AI reply
        ev = candidate.evidence or {}
        reasons_list = "\n".join(f"- {r}" for r in (candidate.reasons or [])) if candidate.reasons else "- Neutral momentum"
        conflicts_list = "\n".join(f"- {c}" for c in (candidate.conflicts or [])) if candidate.conflicts else "- No critical execution risks identified"
        
        reply = (
            f"### 🤖 {symbol} // TIER {candidate.signal_tier} // {candidate.regime}\n\n"
            f"**Alpha Score**: {candidate.score:.0f}/100\n\n"
            f"#### 🟢 BULLISH CONFLUENCES\n"
            f"{reasons_list}\n\n"
            f"#### 🔴 EXECUTION RISKS\n"
            f"{conflicts_list}\n\n"
            f"#### 📊 PATTERN MEMORY\n"
            f"- **20-Day Matches**: {ev.get('pattern_matches', 0)} historical footprints\n"
            f"- **Win Rate**: **{ev.get('pattern_success_rate', 0.5)*100:.0f}%** (Avg return: {ev.get('pattern_avg_return_5d', 0.0):+.2f}%)\n"
            f"- **Max Drawdown**: {ev.get('pattern_max_drawdown', 0.0):.2f}%\n\n"
            f'<div style="border: 1px solid var(--green); background: rgba(0, 240, 118, 0.05); padding: 8px; border-radius: var(--radius); font-weight: 700; margin-top: 10px; text-align: center; font-size: 13px;">'
            f'🎯 VERDICT: {candidate.signal_type.value.upper()} // {candidate.score:.0f}/100 ALPHA SCORE'
            f'</div>'
        )
        
        return {"reply": reply}
    except Exception as e:
        return {
            "reply": f"Sorry, I encountered an error while analyzing {symbol}: {str(e)}"
        }
