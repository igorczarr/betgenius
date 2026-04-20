# betgenius-backend/scripts/genesis_seed.py
import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.database import db

async def seed_genesis():
    await db.connect()
    leagues = [
        ('soccer_epl', 'Premier League', 1, 'England'),
        ('soccer_spain_la_liga', 'La Liga', 1, 'Spain'),
        ('soccer_italy_serie_a', 'Serie A', 1, 'Italy'),
        ('soccer_germany_bundesliga', 'Bundesliga', 1, 'Germany'),
        ('soccer_brazil_campeonato', 'Série A', 2, 'Brazil'),
    ]
    
    async with db.pool.acquire() as conn:
        for l_key, l_name, l_tier, l_country in leagues:
            await conn.execute("""
                INSERT INTO core.leagues (sport_key, name, tier, country)
                VALUES ($1, $2, $3, $4) ON CONFLICT (sport_key) DO NOTHING
            """, l_key, l_name, l_tier, l_country)
    
    print("✅ Gênesis: Ligas base inseridas com sucesso.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_genesis())