import logging
import httpx
import csv
from io import StringIO
from datetime import datetime, timedelta
from typing import Any

from app.db.session import SessionLocal
from app.engine.bhavcopy_engine import BhavCopyEngine
from app.collectors.market_data.demo import DEFAULT_SYMBOLS

logger = logging.getLogger(__name__)

def fetch_latest_bhavcopy() -> None:
    """
    Finds the latest available NSE SECBHAVDATA (Bhavcopy) file, downloads it,
    parses the Delivery Percentage for all F&O stocks, and saves it into the database.
    """
    logger.info("Starting NSE Bhavcopy Delivery Data Scraper...")
    
    target = datetime.today()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
    }
    
    # Try up to 10 days backwards to find the latest valid bhavcopy (skipping weekends)
    csv_data = None
    target_date_obj = None
    
    for _ in range(10):
        if target.weekday() <= 4:  # Monday to Friday
            date_str = target.strftime('%d%m%Y')
            url = f'https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv'
            
            try:
                r = httpx.get(url, headers=headers, timeout=20.0)
                if r.status_code == 200:
                    csv_data = r.text
                    target_date_obj = target.date()
                    logger.info(f"Successfully downloaded Bhavcopy for {target_date_obj}")
                    break
                elif r.status_code == 404:
                    logger.debug(f"Bhavcopy not found for {target_date_obj}, trying previous day.")
                else:
                    logger.warning(f"Failed to fetch Bhavcopy for {target_date_obj} (Status {r.status_code})")
            except Exception as e:
                logger.error(f"Error fetching Bhavcopy: {e}")
                
        target -= timedelta(days=1)
        
    if not csv_data:
        logger.error("Could not download any recent Bhavcopy from NSE.")
        return
        
    # Parse CSV data
    f = StringIO(csv_data)
    reader = csv.DictReader(f)
    
    # Normalize headers by stripping whitespace
    if reader.fieldnames:
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
    else:
        logger.error("Invalid CSV structure.")
        return
        
    records_to_insert: list[dict[str, Any]] = []
    
    for row in reader:
        symbol = row.get('SYMBOL', '').strip()
        series = row.get('SERIES', '').strip()
        
        # Only process active F&O tracked symbols in EQ series
        if symbol in DEFAULT_SYMBOLS and series == 'EQ':
            try:
                delivery_pct_raw = row.get('DELIV_PER', '0').strip()
                delivery_pct_raw = delivery_pct_raw.replace('-', '0')
                deliv_pct = float(delivery_pct_raw)
                
                volume_raw = row.get('TTL_TRD_QNTY', '0').strip()
                volume = int(volume_raw)
                
                deliv_qty_raw = row.get('DELIV_QTY', '0').strip()
                deliv_qty_raw = deliv_qty_raw.replace('-', '0')
                deliv_qty = int(deliv_qty_raw)
                
                records_to_insert.append({
                    "symbol": symbol,
                    "date": target_date_obj,
                    "open": float(row.get('OPEN_PRICE', 0)),
                    "high": float(row.get('HIGH_PRICE', 0)),
                    "low": float(row.get('LOW_PRICE', 0)),
                    "close": float(row.get('CLOSE_PRICE', 0)),
                    "volume": volume,
                    "delivery_qty": deliv_qty,
                    "delivery_pct": deliv_pct,
                    "oi": 0  # OI is fetched from derivatives feed, not cash bhavcopy
                })
            except Exception as e:
                logger.debug(f"Error parsing row for {symbol}: {e}")
                
    if not records_to_insert:
        logger.warning("No tracked symbols found in the downloaded Bhavcopy.")
        return
        
    # Save into DB
    db = SessionLocal()
    try:
        engine = BhavCopyEngine(db)
        
        # Check if we already have records for this date
        from sqlalchemy import select
        from app.db.models.bhavcopy import BhavCopyDaily
        
        existing = db.scalars(
            select(BhavCopyDaily).where(BhavCopyDaily.date == target_date_obj).limit(1)
        ).first()
        
        if existing:
            logger.info(f"Bhavcopy records for {target_date_obj} already exist in DB. Skipping insert.")
        else:
            engine.process_bhavcopy_data(records_to_insert)
            logger.info(f"Successfully saved {len(records_to_insert)} Bhavcopy delivery records into database.")
    except Exception as e:
        logger.error(f"Database error during Bhavcopy insert: {e}")
    finally:
        db.close()
