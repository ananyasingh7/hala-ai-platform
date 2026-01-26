import asyncio
import os

from hala_orchestrator import Agent, MissionState, agent, get_logger

from services.hala_ws import query_hala

HALA_TIMEOUT_SEC = float(os.getenv("HALA_ORCH_HALA_TIMEOUT", "3.0"))


async def _safe_hala_call(
    prompt: str,
    state: MissionState,
    system_prompt: str,
    logger,
    start_session: bool,
    max_tokens: int = 120,
):
    try:
        return await asyncio.wait_for(
            query_hala(
                prompt,
                session_id=state.mission_id,
                system_prompt=system_prompt,
                include_history=False,
                start_session=start_session,
                max_tokens=max_tokens,
            ),
            timeout=HALA_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning("HalaAI call timed out after %ss", HALA_TIMEOUT_SEC)
    except Exception as exc:
        logger.warning("HalaAI call failed: %s", exc)
    return None

@agent(name="NewsAgent", description="Collects relevant market headlines.")
class NewsAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        logger = get_logger(self.name, mission_id=state.mission_id, agent=self.name)
        tool = self.get_tool("news")

        try:
            headlines = await tool.run(query=state.objective) if tool else []
        except Exception as exc:
            logger.warning("News tool failed: %s", exc)
            headlines = []

        if not headlines:
            headlines = ["Fed rates holding steady."]

        state.data["news"] = headlines
        state.findings.extend(headlines)

        prompt = (
            "You are a market analyst. Here is mock news data to analyze:\n"
            f"{headlines}\n\n"
            "Provide a 1-2 sentence market context summary."
        )
        response = await _safe_hala_call(
            prompt,
            state,
            system_prompt="You summarize mock market data.",
            logger=logger,
            start_session=True,
        )
        if response:
            state.data["news_llm"] = response

        return state


@agent(name="CryptoAgent", description="Analyzes crypto pricing and context.")
class CryptoAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        logger = get_logger(self.name, mission_id=state.mission_id, agent=self.name)
        tool = self.get_tool("price")

        price = None
        try:
            price = await tool.run(symbol="BTC") if tool else None
        except Exception as exc:
            logger.warning("Price tool failed: %s", exc)

        if price is None:
            price = 98000

        state.data["btc_price"] = price

        if any("rate" in item.lower() for item in state.findings):
            state.findings.append("Stable rates usually support risk assets like BTC.")

        prompt = (
            "You are a crypto analyst. Here is mock crypto data:\n"
            f"BTC price: {price}\n"
            f"Headlines: {state.data.get('news', [])}\n\n"
            "Provide a 1-2 sentence crypto insight."
        )
        response = await _safe_hala_call(
            prompt,
            state,
            system_prompt="You summarize mock crypto data.",
            logger=logger,
            start_session=False,
        )
        if response:
            state.data["crypto_llm"] = response

        return state


@agent(name="WriterAgent", description="Synthesizes the final briefing.")
class WriterAgent(Agent):
    async def run(self, state: MissionState) -> MissionState:
        headlines = state.data.get("news", [])
        btc_price = state.data.get("btc_price")
        insights = [item for item in state.findings if item not in headlines]
        news_llm = state.data.get("news_llm")
        crypto_llm = state.data.get("crypto_llm")

        lines = [
            "# Market Briefing",
            "",
            "## Key Headlines",
        ]

        if headlines:
            lines.extend([f"- {item}" for item in headlines])
        else:
            lines.append("- No headlines collected.")

        lines.append("")
        lines.append("## Crypto Snapshot")
        if btc_price is not None:
            lines.append(f"- BTC: ${btc_price:,.0f}")
        else:
            lines.append("- BTC: N/A")

        if insights:
            lines.append("")
            lines.append("## Notes")
            lines.extend([f"- {item}" for item in insights])

        if news_llm or crypto_llm:
            lines.append("")
            lines.append("## HalaAI Notes")
            if news_llm:
                lines.append(f"- News: {news_llm}")
            if crypto_llm:
                lines.append(f"- Crypto: {crypto_llm}")

        report = "\n".join(lines)
        state.final_output = report
        state.data["report"] = report
        return state
