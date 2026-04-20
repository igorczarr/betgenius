# betgenius-backend/workers/fbref/network/stealth_client.py
import asyncio
import logging
import nodriver as uc
import random

logger = logging.getLogger(__name__)

class StealthClient:
    """
    Motor de Rede S-Tier (Arquitetura 'Ghost Monitor').
    Soluciona o impasse do Headless vs Cloudflare. Roda o Chrome visível para 
    obter a assinatura WebGL autêntica, mas arremessa a janela para fora 
    das coordenadas do monitor (Invisível para o usuário).
    """
    def __init__(self):
        self.browser = None

    async def _init_browser(self):
        if not self.browser:
            logger.info("🛡️ Iniciando Motor Crawler (Modo 'Ghost Monitor')...")
            self.browser = await uc.start(
                # A SOLUÇÃO S-TIER: Falso Headless.
                # Mantemos o navegador VISÍVEL para o SO para burlar o WAF,
                # mas o escondemos do usuário humano. Na nuvem, usaremos Xvfb.
                headless=False,
                browser_args=[
                    "--window-position=-32000,-32000", # Joga a janela para o vazio
                    "--window-size=1920,1080",
                    "--disable-notifications",
                    "--no-sandbox",
                    "--disable-popup-blocking",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

    async def fetch_html(self, url: str, max_retries: int = 3) -> str:
        await self._init_browser()
        
        # Rate Limit rígido de Wall Street
        await asyncio.sleep(4.5)

        for attempt in range(max_retries):
            tab = None
            try:
                tab = await self.browser.get(url, new_tab=True)
                
                passed = False
                for i in range(15):
                    await asyncio.sleep(2.0)
                    html_content = await tab.get_content()
                    
                    # A Prova de Vida: A tabela carregou?
                    if "stats_squads" in html_content or "Standard Stats" in html_content:
                        passed = True
                        break
                        
                    # Trata a Barreira (O Loop Infinito do Turnstile)
                    elif "Just a moment" in html_content or "Cloudflare" in html_content or "cf-turnstile" in html_content:
                        if i % 3 == 0:
                            logger.info("🛡️ CF WAF detectado. Injetando biometria sintética (Mouse/Scroll)...")
                            # O Turnstile muitas vezes precisa de eventos DOM para liberar o cookie.
                            # Injetamos rolagem e movimentos de mouse diretamente no motor V8.
                            await tab.evaluate(f"window.scrollBy(0, {random.randint(100, 300)});")
                            await tab.evaluate(f"document.dispatchEvent(new MouseEvent('mousemove', {{clientX: {random.randint(200, 700)}, clientY: {random.randint(200, 700)}}}));")
                        continue
                        
                    # Checagem de Erro 404 (Copas que não aconteceram no ano)
                    elif "404 Not Found" in html_content or "Page Not Found" in html_content:
                        logger.debug(f"Página 404: {url}")
                        await tab.close()
                        return None
                        
                    # Checagem de Rate Limit da API nativa deles
                    elif "429 Too Many Requests" in html_content:
                        sleep_time = 60 * (attempt + 1)
                        logger.warning(f"⚠️ RATE LIMIT. O alvo pediu arrego. Congelando por {sleep_time}s...")
                        await asyncio.sleep(sleep_time)
                        break 

                if passed:
                    # Sucesso: HTML consolidado e extraído
                    final_html = await tab.get_content()
                    await tab.close()
                    return final_html
                else:
                    logger.warning(f"⛔ Tempo esgotado na barreira. Retentando ({attempt+1}/{max_retries})...")
                    if tab: await tab.close()

            except Exception as e:
                logger.error(f"Falha de CDP no alvo {url}: {e}")
                if tab: await tab.close()
                await asyncio.sleep(5)

        return None

    async def close(self):
        """Mata os processos pendentes do Chrome."""
        if self.browser:
            self.browser.stop()
            self.browser = None