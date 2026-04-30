# betgenius-backend/routers/match_center.py

import os
import math
import logging
import urllib.parse
import pandas as pd
import numpy as np
import httpx
from scipy.stats import poisson
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, RedirectResponse

from core.database import db

logger = logging.getLogger(__name__)

# Agrupamos todas as rotas de exploração de jogos neste router central
router = APIRouter(tags=["Match Center & Data"])

# =====================================================================
# FUNÇÕES MATEMÁTICAS E DE FORMATAÇÃO (Isoladas das rotas)
# =====================================================================
def format_form(rows, target_id):
    res = []
    for r in rows:
        is_home = r['home_team_id'] == target_id
        if r['home_goals'] == r['away_goals']: w = 'D'
        elif is_home and r['home_goals'] > r['away_goals']: w = 'W'
        elif not is_home and r['away_goals'] > r['home_goals']: w = 'W'
        else: w = 'L'
        adv = r['away_name'] if is_home else r['home_name']
        res.append({
            "res": w, 
            "data": r['match_date'].strftime('%d/%m'), 
            "adv": adv, 
            "placar": f"{r['home_goals']}-{r['away_goals']}"
        })
    return res

def format_wage(pct):
    if not pct or pct == 0.5: return "Desconhecido"
    if pct <= 0.10: return "Elite (Top 10%)"
    if pct <= 0.35: return "Alto Escalão"
    if pct <= 0.65: return "Meio de Tabela"
    if pct <= 0.85: return "Baixo Orçamento"
    return "Risco (Fundo)"

# =====================================================================
# 1. ROTA: JOGOS DE HOJE (Agenda Inteligente)
# =====================================================================
@router.get("/api/v1/matches/today")
async def get_matches_today():
    """
    Motor S-Tier de Agenda: Exibe apenas jogos que já possuem liquidez 
    e Odds de Mercado (Pinnacle/Bet365) rastreadas.
    """
    query = """
        SELECT DISTINCT ON (m.match_date, m.id) 
               m.id, COALESCE(l.name, m.sport_key) as campeonato, m.match_date as data,
               th.canonical_name as casa, ta.canonical_name as fora,
               m.status, m.home_goals, m.away_goals, p.is_value_bet as has_value
        FROM core.matches_history m
        JOIN core.teams th ON m.home_team_id = th.id
        JOIN core.teams ta ON m.away_team_id = ta.id
        JOIN core.market_odds mo ON m.id = mo.match_id  -- Filtro de Liquidez
        LEFT JOIN core.leagues l ON th.league_id = l.id
        LEFT JOIN quant_ml.predictions p ON m.id = p.match_id
        WHERE m.status IN ('SCHEDULED', 'IN_PROGRESS') 
          AND m.match_date >= CURRENT_DATE 
          AND m.match_date < CURRENT_DATE + INTERVAL '2 days'
        ORDER BY m.match_date ASC, m.id ASC
    """
    async with db.pool.acquire() as conn:
        try:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Erro ao buscar agenda do dia com odds: {e}")
            return []

# =====================================================================
# 2. ROTA: MATCH CENTER (O Coração da Inferência Preditiva)
# =====================================================================
@router.get("/api/v1/match-center/{match_id}")
async def get_match_center(match_id: int, request: Request):
    """Constrói o relatório quântico completo para uma partida."""
    async with db.pool.acquire() as conn:
        # Busca Dinâmica de Partida
        if match_id == 0:
            match = await conn.fetchrow("""
                SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name
                FROM core.matches_history m
                JOIN core.teams th ON m.home_team_id = th.id
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE m.match_date >= CURRENT_DATE AND m.status = 'SCHEDULED'
                ORDER BY m.match_date ASC LIMIT 1
            """)
            if not match: raise HTTPException(404, "Nenhum jogo futuro disponível na base.")
            match_id = match['id']
        else:
            match = await conn.fetchrow("""
                SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name
                FROM core.matches_history m 
                JOIN core.teams th ON m.home_team_id = th.id 
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE m.id = $1
            """, match_id)
            if not match: raise HTTPException(404, "Partida não encontrada.")

        h_id, a_id = match['home_team_id'], match['away_team_id']
        
        # 1. Feature Store (A Matrix)
        feats = await conn.fetchrow("SELECT * FROM quant_ml.feature_store WHERE match_id = $1", match_id)
        
        # Fallback de Sobrevivência (Caso a rotina de ETL não tenha passado para este jogo ainda)
        if not feats:
            logger.warning(f"⚠️ Matrix ausente para {match_id}. Construindo Tensores On-The-Fly...")
            feats_dict = {}
            elo_h = await conn.fetchval("SELECT current_elo FROM core.team_current_elo WHERE team_id = $1", h_id) or 1500.0
            elo_a = await conn.fetchval("SELECT current_elo FROM core.team_current_elo WHERE team_id = $1", a_id) or 1500.0
            feats_dict['home_elo_before'] = float(elo_h)
            feats_dict['away_elo_before'] = float(elo_a)
            feats_dict['delta_elo'] = float(elo_h) - float(elo_a)
            
            # Puxa o xG projetado do próprio match se existir
            feats_dict['home_xg_for_ewma_macro'] = float(match.get('proj_xg_90_home') or 1.45)
            feats_dict['away_xg_for_ewma_macro'] = float(match.get('proj_xg_90_away') or 1.25)
            feats_dict['home_xg_for_ewma_micro'] = feats_dict['home_xg_for_ewma_macro']
            feats_dict['away_xg_for_ewma_micro'] = feats_dict['away_xg_for_ewma_macro']
            
            feats_dict['delta_market_respect'] = 0.0
            feats_dict['home_tension_index'] = 0.5
            feats_dict['away_tension_index'] = 0.5
            feats_dict['home_aggression_ewma'] = 10.0
            feats_dict['away_aggression_ewma'] = 10.0
            feats_dict['home_wage_pct'] = 0.5
            feats_dict['away_wage_pct'] = 0.5
            feats = feats_dict
        else:
            feats = dict(feats)

        odds_db = await conn.fetch("SELECT * FROM core.market_odds WHERE match_id = $1", match_id)

        # 2. Dados Históricos e Forma
        h2h_rows = await conn.fetch("""
            SELECT match_date, home_goals, away_goals, 
                   (SELECT canonical_name FROM core.teams WHERE id=home_team_id) as home_name, 
                   (SELECT canonical_name FROM core.teams WHERE id=away_team_id) as away_name, 
                   home_team_id, away_team_id 
            FROM core.matches_history 
            WHERE ((home_team_id=$1 AND away_team_id=$2) OR (home_team_id=$2 AND away_team_id=$1)) 
            AND status='FINISHED' ORDER BY match_date DESC LIMIT 15
        """, h_id, a_id)
        
        h_form = await conn.fetch("""
            SELECT match_date, home_goals, away_goals, home_team_id, away_team_id, 
                   (SELECT canonical_name FROM core.teams WHERE id=away_team_id) as away_name, 
                   (SELECT canonical_name FROM core.teams WHERE id=home_team_id) as home_name 
            FROM core.matches_history 
            WHERE (home_team_id=$1 OR away_team_id=$1) AND status='FINISHED' 
            ORDER BY match_date DESC LIMIT 15
        """, h_id)
        
        a_form = await conn.fetch("""
            SELECT match_date, home_goals, away_goals, home_team_id, away_team_id, 
                   (SELECT canonical_name FROM core.teams WHERE id=away_team_id) as away_name, 
                   (SELECT canonical_name FROM core.teams WHERE id=home_team_id) as home_name 
            FROM core.matches_history 
            WHERE (home_team_id=$1 OR away_team_id=$1) AND status='FINISHED' 
            ORDER BY match_date DESC LIMIT 15
        """, a_id)

        cards_query = """
            SELECT 
                AVG(CASE WHEN home_team_id = $1 THEN home_yellow ELSE away_yellow END) as y, 
                AVG(CASE WHEN home_team_id = $1 THEN home_red ELSE away_red END) as r 
            FROM (
                SELECT home_team_id, away_team_id, home_yellow, away_yellow, home_red, away_red
                FROM core.matches_history
                WHERE (home_team_id = $1 OR away_team_id = $1) AND status = 'FINISHED'
                ORDER BY match_date DESC LIMIT 15
            ) sub
        """
        cards_h = await conn.fetchrow(cards_query, h_id)
        cards_a = await conn.fetchrow(cards_query, a_id)

        # 3. Inferência do Modelo (A Busca Pelo EV+)
        markets_payload = []
        oracles = getattr(request.app.state, 'oracles', {})
        
        if oracles:
            tensor_df = pd.DataFrame([feats])
            
            def append_value_market(vue_cat, vue_name, prob, db_cat_filter, db_name_filters):
                if prob <= 0.01: return
                fair_odd = 1.0 / prob
                for o in odds_db:
                    db_nome_mercado = str(o.get('nome_mercado', '')).lower()
                    db_categoria = str(o.get('categoria', '')).lower()
                    match_name = any(str(f).lower() in db_nome_mercado for f in db_name_filters if f)
                    
                    if db_categoria == db_cat_filter.lower() and match_name:
                        bookie_odd = float(o['current_odd'] or 0)
                        if bookie_odd <= 1.0: continue
                        
                        open_odd = float(o['opening_odd']) if o['opening_odd'] else bookie_odd
                        ev = (prob * bookie_odd) - 1.0
                        
                        # Filtro de Apresentação (Garante que só vemos o que importa)
                        markets_payload.append({
                            "categoria": vue_cat, "nome": vue_name, "prob": f"{prob*100:.1f}", 
                            "fair": f"{fair_odd:.2f}", "openOdd": f"{open_odd:.2f}", 
                            "bookie": f"{bookie_odd:.2f}", "ev": f"{ev*100:.1f}", 
                            "casaNome": str(o['bookmaker']).capitalize()
                        })
                        break 

            try:
                if 'alpha' in oracles:
                    X_alpha = pd.DataFrame(columns=oracles['alpha'].feature_names_in_)
                    for col in X_alpha.columns: X_alpha.at[0, col] = float(feats.get(col, 0))
                    preds_alpha = oracles['alpha'].predict_proba(X_alpha)[0]
                    append_value_market("match_odds", "Visitante Vence", preds_alpha[0], "h2h", ["2", "away", match['away_name']])
                    append_value_market("match_odds", "Empate", preds_alpha[1], "h2h", ["x", "draw", "empate"])
                    append_value_market("match_odds", "Mandante Vence", preds_alpha[2], "h2h", ["1", "home", match['home_name']])

                if 'beta' in oracles:
                    X_beta = pd.DataFrame(columns=oracles['beta'].feature_names_in_)
                    for col in X_beta.columns: X_beta.at[0, col] = float(feats.get(col, 0))
                    preds_beta = oracles['beta'].predict_proba(X_beta)[0]
                    append_value_market("goals", "Under 2.5 Gols", preds_beta[0], "totals", ["under", "<", "menos"])
                    append_value_market("goals", "Over 2.5 Gols", preds_beta[1], "totals", ["over", ">", "mais"])

                if 'gamma' in oracles:
                    X_gamma = pd.DataFrame(columns=oracles['gamma'].feature_names_in_)
                    for col in X_gamma.columns: X_gamma.at[0, col] = float(feats.get(col, 0))
                    preds_gamma = oracles['gamma'].predict_proba(X_gamma)[0]
                    append_value_market("btts", "Ambas Marcam (Não)", preds_gamma[0], "btts", ["no", "não", "nao"])
                    append_value_market("btts", "Ambas Marcam (Sim)", preds_gamma[1], "btts", ["yes", "sim"])

                if 'epsilon' in oracles:
                    X_eps = pd.DataFrame(columns=oracles['epsilon'].feature_names_in_)
                    for col in X_eps.columns: X_eps.at[0, col] = float(feats.get(col, 0))
                    exp_corners = np.clip(oracles['epsilon'].predict(X_eps)[0], 1.0, 25.0)
                    p_o95 = 1.0 - poisson.cdf(9, exp_corners)
                    append_value_market("corners", "Under 9.5 Escanteios", 1.0 - p_o95, "corners", ["under", "<"])
                    append_value_market("corners", "Over 9.5 Escanteios", p_o95, "corners", ["over", ">"])

                if 'zeta' in oracles:
                    X_zeta = pd.DataFrame(columns=oracles['zeta'].feature_names_in_)
                    for col in X_zeta.columns: X_zeta.at[0, col] = float(feats.get(col, 0))
                    exp_cards = np.clip(oracles['zeta'].predict(X_zeta)[0], 0.5, 12.0)
                    p_o45 = 1.0 - poisson.cdf(4, exp_cards)
                    append_value_market("cards", "Under 4.5 Cartões", 1.0 - p_o45, "cards", ["under", "<"])
                    append_value_market("cards", "Over 4.5 Cartões", p_o45, "cards", ["over", ">"])

                # Ordena pelo maior EV+ para o topo do Dashboard
                markets_payload = sorted(markets_payload, key=lambda x: float(x['ev']), reverse=True)
            except Exception as e:
                logger.error(f"Erro durante a Inferência S-Tier (Tensores de Sobrevivência): {e}")

        # 4. Dinâmica Poisson e Probabilidade Exata
        xg_h = float(feats.get('home_xg_for_ewma_macro', 1.35) or 1.35)
        xg_a = float(feats.get('away_xg_for_ewma_macro', 1.15) or 1.15)
        elo_h = float(feats.get('home_elo_before', 1500) or 1500)
        elo_a = float(feats.get('away_elo_before', 1500) or 1500)
        
        adj_xg_h = max(0.1, xg_h * (1 + ((elo_h - elo_a) / 1500))) * 1.10
        adj_xg_a = max(0.1, xg_a * (1 - ((elo_h - elo_a) / 1500))) * 0.90
        
        poisson_matrix = []
        for h_g in range(4):
            for a_g in range(4):
                try: 
                    prob = ((math.exp(-adj_xg_h) * (adj_xg_h**h_g)) / math.factorial(h_g)) * ((math.exp(-adj_xg_a) * (adj_xg_a**a_g)) / math.factorial(a_g))
                except: prob = 0
                poisson_matrix.append({"h": h_g, "a": a_g, "prob": round(prob * 100, 1)})

        # 5. Modelagem de Player Props (FBref)
        players_query = """
            SELECT player_name, team_id, minutes_played, goals, assists, 
                   shots_per_90, xg_per_90, fouls_committed, yellow_cards, red_cards
            FROM fbref_player.comprehensive_stats
            WHERE team_id IN ($1, $2) AND minutes_played > 180
        """
        p_props = {"chutes": [], "gols": [], "assists": [], "faltas": [], "escanteios": [], "cartoes": []}
        
        try:
            players_data = await conn.fetch(players_query, h_id, a_id)

            def_fragility_h = max(0.5, float(feats.get('away_xg_against_ewma_micro', 1.35) or 1.35) / 1.35)
            def_fragility_a = max(0.5, float(feats.get('home_xg_against_ewma_micro', 1.35) or 1.35) / 1.35)

            for p in players_data:
                p_team_id = p['team_id']
                is_home_player = (p_team_id == h_id)
                opp_fragility = def_fragility_h if is_home_player else def_fragility_a
                team_name = match['home_name'] if is_home_player else match['away_name']
                mins = max(1, p['minutes_played'] or 1)
                play_time_factor = 0.88
                
                def calc_prop(metric_per_90, avg_baseline):
                    try: metric_val = float(metric_per_90 or 0)
                    except: metric_val = 0.0
                        
                    lam = metric_val * opp_fragility * play_time_factor
                    if lam <= 0.01: return 0, 0, 0
                    prob_1_or_more = 1.0 - math.exp(-lam)
                    fair = 1.0 / prob_1_or_more if prob_1_or_more > 0 else 0
                    war = (lam - avg_baseline) * 0.5
                    return round(prob_1_or_more * 100, 1), round(fair, 2), round(war, 2)

                sh_prob, sh_fair, sh_war = calc_prop(p.get('shots_per_90', 0), 1.5)
                if sh_prob > 10: p_props['chutes'].append({"nome": p['player_name'], "time": team_name, "prob": f"{sh_prob:.1f}", "war": f"{sh_war:+.2f}", "fair": f"{sh_fair:.2f}"})
                
                gl_prob, gl_fair, gl_war = calc_prop(p.get('xg_per_90', 0), 0.3)
                if gl_prob > 5: p_props['gols'].append({"nome": p['player_name'], "time": team_name, "prob": f"{gl_prob:.1f}", "war": f"{gl_war:+.2f}", "fair": f"{gl_fair:.2f}"})
                
                ast_90 = (float(p.get('assists', 0) or 0) / mins) * 90
                ast_prob, ast_fair, ast_war = calc_prop(ast_90, 0.15)
                if ast_prob > 5: p_props['assists'].append({"nome": p['player_name'], "time": team_name, "prob": f"{ast_prob:.1f}", "war": f"{ast_war:+.2f}", "fair": f"{ast_fair:.2f}"})

                fls_90 = (float(p.get('fouls_committed', 0) or 0) / mins) * 90
                fls_prob, fls_fair, fls_war = calc_prop(fls_90, 1.0)
                if fls_prob > 10: p_props['faltas'].append({"nome": p['player_name'], "time": team_name, "prob": f"{fls_prob:.1f}", "war": f"{fls_war:+.2f}", "fair": f"{fls_fair:.2f}"})

                crd_90 = (float((p.get('yellow_cards', 0) or 0) + (p.get('red_cards', 0) or 0)) / mins) * 90
                crd_prob, crd_fair, crd_war = calc_prop(crd_90, 0.15)
                if crd_prob > 5: p_props['cartoes'].append({"nome": p['player_name'], "time": team_name, "prob": f"{crd_prob:.1f}", "war": f"{crd_war:+.2f}", "fair": f"{crd_fair:.2f}"})

            for key in p_props.keys():
                p_props[key] = sorted(p_props[key], key=lambda x: float(x['prob']), reverse=True)[:15]
        except Exception:
            pass

        gs_payload = [
            {"time": match['home_name'], "vencendo": f"{(adj_xg_h * 0.8):.2f}", "empatando": f"{adj_xg_h:.2f}", "perdendo": f"{(adj_xg_h * 1.3):.2f}"},
            {"time": match['away_name'], "vencendo": f"{(adj_xg_a * 0.7):.2f}", "empatando": f"{adj_xg_a:.2f}", "perdendo": f"{(adj_xg_a * 1.4):.2f}"}
        ]

        payload = {
            "partida": {
                "id": match['id'], "casa": match['home_name'], "fora": match['away_name'],
                "corCasa": "#10B981", "corFora": "#3B82F6",
                "folhaCasa": format_wage(float(feats.get('home_wage_pct', 0.5) or 0.5)),
                "folhaFora": format_wage(float(feats.get('away_wage_pct', 0.5) or 0.5)),
                "posCasa": feats.get('pos_tabela_home', 0) or 0, "posFora": feats.get('pos_tabela_away', 0) or 0,
                "placarCasa": match.get('home_goals') if match.get('home_goals') is not None else "-", 
                "placarFora": match.get('away_goals') if match.get('away_goals') is not None else "-",
                "isLive": match['status'] == 'IN_PROGRESS', "tempo": match.get('current_minute', 0) or 0,
                "hora": match['match_date'].strftime('%H:%M') if match['match_date'] else "--:--",
                "xgCasa": f"{adj_xg_h:.2f}", "xgFora": f"{adj_xg_a:.2f}",
                "formCasa": [f['res'] for f in format_form(h_form, h_id)], 
                "formFora": [f['res'] for f in format_form(a_form, a_id)],
                "indFormCasa": format_form(h_form, h_id),
                "indFormFora": format_form(a_form, a_id),
                "historico": [{"data": r['match_date'].strftime('%d/%m'), "casa": r['home_name'], "fora": r['away_name'], "placar": f"{r['home_goals']}-{r['away_goals']}", "win": "casa" if (r['home_goals']>r['away_goals'] and r['home_team_id']==h_id) else "fora" if (r['away_goals']>r['home_goals'] and r['away_team_id']==h_id) else "empate"} for r in h2h_rows],
                "disciplina": {
                    "h_y": f"{float(cards_h['y'] or 0):.1f}", "h_r": f"{float(cards_h['r'] or 0):.2f}",
                    "a_y": f"{float(cards_a['y'] or 0):.1f}", "a_r": f"{float(cards_a['r'] or 0):.2f}"
                },
                "quantMetrics": [
                    {"nome": "Elo Rating Global", "casa": int(elo_h), "fora": int(elo_a), "sufixo": "", "desc": "Força Base Institucional"},
                    {"nome": "Tension Index", "casa": f"{float(feats.get('home_tension_index', 0.5) or 0.5)*100:.0f}", "fora": f"{float(feats.get('away_tension_index', 0.5) or 0.5)*100:.0f}", "sufixo": "%", "desc": "Pressão de Tabela"},
                    {"nome": "Market Respect", "casa": f"{float(feats.get('home_market_respect', 0.3) or 0.3)*100:.0f}", "fora": f"{float(feats.get('away_market_respect', 0.3) or 0.3)*100:.0f}", "sufixo": "%", "desc": "Volume Sharp"},
                    {"nome": "Aggression EWMA", "casa": f"{float(feats.get('home_aggression_ewma', 10) or 10):.1f}", "fora": f"{float(feats.get('away_aggression_ewma', 10) or 10):.1f}", "sufixo": "", "desc": "Intensidade"}
                ],
                "poisson": poisson_matrix,
                "mercados": markets_payload,
                "gameState": gs_payload 
            },
            "playerProps": p_props 
        }
        return payload

# =====================================================================
# 3. ROTA: TEAM SHIELD (Proxy Visual)
# =====================================================================
@router.get("/api/v1/teams/shield/{team_name}")
async def get_team_shield(team_name: str):
    """Bypassa o CORS da API-Football e serve a imagem nativamente."""
    target_url = None
    
    async with db.pool.acquire() as conn:
        await conn.execute("ALTER TABLE core.teams ADD COLUMN IF NOT EXISTS logo_url TEXT;")
        team = await conn.fetchrow("SELECT id, logo_url FROM core.teams WHERE canonical_name = $1", team_name)
        
        if team and team['logo_url']: 
            target_url = team['logo_url']
        else:
            api_key = os.getenv("API_FOOTBALL_KEY")
            if api_key:
                try:
                    async with httpx.AsyncClient() as client:
                        safe_team_name = urllib.parse.quote(team_name)
                        resp = await client.get(
                            f"https://v3.football.api-sports.io/teams?search={safe_team_name}", 
                            headers={"x-apisports-key": api_key, "x-apisports-host": "v3.football.api-sports.io"}, 
                            timeout=10.0
                        )
                        if resp.status_code == 200 and resp.json().get('response'):
                            target_url = resp.json()['response'][0]['team']['logo']
                            if team: 
                                await conn.execute("UPDATE core.teams SET logo_url = $1 WHERE id = $2", target_url, team['id'])
                except Exception: 
                    pass

    if not target_url:
        words = team_name.strip().split(' ')
        initials = (words[0][0] + words[1][0]).upper() if len(words) >= 2 else team_name[:2].upper()
        target_url = f"https://ui-avatars.com/api/?name={initials}&background=121927&color=10B981&size=128&bold=true&format=svg"

    try:
        async with httpx.AsyncClient() as client:
            img_resp = await client.get(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15.0)
            
            if img_resp.status_code == 200:
                content_type = img_resp.headers.get("content-type", "image/png")
                return Response(
                    content=img_resp.content, 
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cross-Origin-Resource-Policy": "cross-origin",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
    except Exception as e:
        logger.error(f"Falha no Proxy de Imagem para {team_name}: {e}")

    return RedirectResponse(target_url, status_code=302)