"""Digital Assets (F11 of docs/FINANCE_GLOBAL_PLAN.md) tool: `digital_assets`. Crypto gains from buys, sells, swaps, income and fees in 6
countries' methods, wallet and address safety (checksums, poisoning, drainer signs), stablecoin payments and pegs, reserve coverage,
custody reconciliation, travel-rule fields, token due diligence, trade surveillance, licensing-return counts. It never holds a key,
signs or sends a transaction."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ['gains', 'wallet', 'stablecoin', 'reserve', 'custody', 'travel_rule', 'token_dd', 'surveillance', 'returns', 'methods']

DIGIASSET_TOOLS = [
    {"name": "digital_assets", "description": (
        "Digital assets for a person up to a crypto firm, any country; never holds a key, signs or sends; never asks for a seed"
        " phrase; not advice. gains: country GB|US|IN|DE|AU|CA (or method fifo|average|uk_share_id), events [{date, type "
        "buy|sell|swap|income|fee|transfer, asset, qty, value (in her currency on the day), get_asset, get_qty, kind}]. wallet:"
        " address, chain bitcoin|ethereum|tron|solana, known [her addresses], message. stablecoin: invoice, rate, network_fee; "
        "prices [{at, price}], peg, tolerance_pct. reserve: supply, assets [{type, value, held_at}], eligible [types], "
        "max_per_holder_pct. custody: ledger [{client, asset, qty}], wallets [{asset, balance}]. travel_rule: threshold, "
        "transfers [{id, value, originator_name, originator_account, originator_address_or_id, beneficiary_name, "
        "beneficiary_account}]. token_dd: supply, top_holders [{qty}], max_top10_pct, mint_authority_open, "
        "freeze_authority_open, upgradeable, audited, team_known, liquidity_locked. surveillance: trades [{id, time, asset, "
        "qty, buyer, seller}], linked [[accounts]], window_minutes, spike_multiple. returns: transactions [{date, type, "
        "value}], period quarter|month."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS}, "country": {"type": "string"}, "method": {"type": "string"},
         "events": {"type": "array", "items": {"type": "object"}}, "address": {"type": "string"}, "chain": {"type": "string"},
         "known": {"type": "array", "items": {"type": "string"}}, "message": {"type": "string"}, "invoice": {"type": "number"},
         "rate": {"type": "number"}, "network_fee": {"type": "number"}, "prices": {"type": "array", "items": {"type": "object"}},
         "peg": {"type": "number"}, "tolerance_pct": {"type": "number"}, "supply": {"type": "number"},
         "assets": {"type": "array", "items": {"type": "object"}}, "eligible": {"type": "array", "items": {"type": "string"}},
         "max_per_holder_pct": {"type": "number"}, "ledger": {"type": "array", "items": {"type": "object"}},
         "wallets": {"type": "array", "items": {"type": "object"}}, "threshold": {"type": "number"},
         "transfers": {"type": "array", "items": {"type": "object"}},
         "top_holders": {"type": "array", "items": {"type": "object"}}, "max_top10_pct": {"type": "number"},
         "mint_authority_open": {"type": "boolean"}, "freeze_authority_open": {"type": "boolean"},
         "upgradeable": {"type": "boolean"}, "audited": {"type": "boolean"}, "team_known": {"type": "boolean"},
         "liquidity_locked": {"type": "boolean"}, "trades": {"type": "array", "items": {"type": "object"}},
         "linked": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
         "window_minutes": {"type": "integer"}, "spike_multiple": {"type": "number"},
         "transactions": {"type": "array", "items": {"type": "object"}}, "period": {"type": "string"}},
         "required": ["action"]}},
]
DIGIASSET_LABELS = {"digital_assets": "Working on the digital assets"}


def _work(ctx: Ctx, action: str, a: dict[str, Any]):
    from ..fin import core
    from ..fin.desks import digital as DG
    tenant = getattr(ctx, "tenant_id", "") or "default"
    actor = getattr(ctx, "actor", "owner") or "owner"
    return core.run_tool(tenant, actor, "digital_assets", action, a, lambda: DG.run(tenant, action, a, actor))


async def _digital_assets(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("This work is not for customers.")
    if action not in _ACTIONS:
        raise ToolError(f"action: {', '.join(_ACTIONS)}")
    try:
        return await asyncio.to_thread(_work, ctx, action, a)
    except PermissionError as e:
        raise ToolError(str(e))
    except ValueError as e:
        raise ToolError(str(e))


DIGIASSET_HANDLERS = {"digital_assets": _digital_assets}
