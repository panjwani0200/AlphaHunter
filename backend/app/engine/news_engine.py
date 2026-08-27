import hashlib
from datetime import datetime
from app.domain.contracts import NewsResult

def analyze_news_sentiment(symbol: str, observed_at: datetime) -> NewsResult:
    # Since there is no live news API hooked up, we will generate a simulated 
    # but deterministic sentiment score based on the symbol and the current hour.
    
    time_key = observed_at.strftime("%Y-%m-%d-%H")
    hash_input = f"{symbol}-{time_key}".encode("utf-8")
    hash_val = int(hashlib.md5(hash_input).hexdigest(), 16)
    
    score_seed = hash_val % 100
    
    if score_seed >= 70:
        return NewsResult(news_sentiment="BULLISH", score=85 + (score_seed % 15))
    elif score_seed <= 30:
        return NewsResult(news_sentiment="BEARISH", score=85 + (score_seed % 15))
    else:
        return NewsResult(news_sentiment="NEUTRAL", score=50)
