"""PandaSI offline evidence-policy prototype. No LLM, networking or signer."""
import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

POLICY = {
    'version': 'prototype-v1', 'chain_id': 56,
    'market_max_age_seconds': 60, 'security_max_age_seconds': 300,
    'min_liquidity_usd': 100000, 'max_order_usd': 100,
    'max_impact_bps': 100, 'max_slippage_bps': 100,
    'max_tax_bps': 500, 'max_top10_pct': 40,
}
NUMERIC = ['liquidity_usd', 'order_usd', 'price_impact_bps', 'slippage_bps',
           'buy_tax_bps', 'sell_tax_bps', 'classified_top10_pct']
BOOLEAN = ['source_verified', 'sell_simulation_passed', 'permissions_reviewed',
           'dangerous_permissions', 'provider_conflict', 'finalized']


def evaluate(packet, now=None):
    """ABSTAIN on invalid, stale, conflicting or incomplete critical evidence.

    RESEARCH means policy checks passed for an illustrative research packet;
    it never means approved to trade. Production needs portfolio and exact-intent gates.
    """
    now = now or datetime.now(timezone.utc)
    reasons = []
    if not isinstance(packet, dict):
        return result(None, [], ['Packet must be an object'], 0)
    address = packet.get('token_address')
    if not isinstance(address, str) or not re.fullmatch(r'0x[0-9a-fA-F]{40}', address):
        reasons.append('Invalid token address')
    if type(packet.get('chain_id')) is not int or packet['chain_id'] != POLICY['chain_id']:
        reasons.append('Unsupported chain')
    refs = packet.get('evidence_ids')
    if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or not x.strip() for x in refs):
        reasons.append('Missing valid evidence IDs')
        refs = []
    for field in NUMERIC:
        v = packet.get(field)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            reasons.append(f'Missing or invalid {field}')
    for field in BOOLEAN:
        if type(packet.get(field)) is not bool:
            reasons.append(f'Missing or invalid {field}')
    for field, max_age in [('market_observed_at', POLICY['market_max_age_seconds']),
                           ('security_observed_at', POLICY['security_max_age_seconds'])]:
        try:
            raw = packet[field]
            if not isinstance(raw, str):
                raise ValueError()
            observed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            if observed.tzinfo is None:
                raise ValueError()
            age = (now - observed).total_seconds()
            if age < 0 or age > max_age:
                reasons.append(f'Stale or future {field}')
        except (KeyError, ValueError, TypeError):
            reasons.append(f'Missing or invalid {field}')
    valid_numbers = all(type(packet.get(k)) in (int, float) and math.isfinite(packet[k]) and packet[k] >= 0 for k in NUMERIC)
    if valid_numbers:
        checks = [
            (packet['liquidity_usd'] < POLICY['min_liquidity_usd'], 'Liquidity below floor'),
            (not 0 < packet['order_usd'] <= POLICY['max_order_usd'], 'Order outside allowed range'),
            (packet['price_impact_bps'] > POLICY['max_impact_bps'], 'Excessive price impact'),
            (packet['slippage_bps'] > POLICY['max_slippage_bps'], 'Excessive slippage'),
            (max(packet['buy_tax_bps'], packet['sell_tax_bps']) > POLICY['max_tax_bps'], 'Excessive token tax'),
            (packet['classified_top10_pct'] > POLICY['max_top10_pct'], 'Holder concentration above ceiling'),
        ]
        reasons += [msg for failed, msg in checks if failed]
    for field in ['source_verified', 'sell_simulation_passed', 'permissions_reviewed', 'finalized']:
        if packet.get(field) is False:
            reasons.append(f'Required check failed: {field}')
    for field in ['dangerous_permissions', 'provider_conflict']:
        if packet.get(field) is True:
            reasons.append(f'Risk veto: {field}')
    required = NUMERIC + BOOLEAN + ['market_observed_at', 'security_observed_at', 'evidence_ids', 'chain_id', 'token_address']
    # Presence coverage is deliberately distinct from evidence truth or trustworthiness.
    coverage = sum(packet.get(k) is not None for k in required) / len(required)
    return result(f"{packet.get('chain_id')}:{address}" if address else None, refs, reasons, round(coverage, 3))


def result(token, refs, reasons, coverage):
    return {
        'token_key': token, 'evidence_ids': refs, 'policy_version': POLICY['version'],
        'decision': 'ABSTAIN' if reasons else 'RESEARCH',
        'blocked_reasons': reasons, 'field_presence_coverage': coverage,
        'summary': 'Missing, invalid or vetoed evidence blocks further action.' if reasons else 'Prototype checks passed; continue research. No execution is authorized.',
        'uncertainties': ['Offline input is not independently verified.', 'Portfolio limits and live quote/intent validation are outside this prototype.'],
        'invalidation': ['Evidence expires or changes', 'Liquidity or permissions change'],
        'execution_authorized': False,
    }


def demo_packet(now=None):
    now = now or datetime.now(timezone.utc)
    return {'chain_id': 56, 'token_address': '0x'+'1'*40, 'evidence_ids': ['fixture:jade'],
            'market_observed_at': now.isoformat(), 'security_observed_at': now.isoformat(),
            'liquidity_usd': 420000, 'order_usd': 50, 'price_impact_bps': 30,
            'slippage_bps': 50, 'buy_tax_bps': 0, 'sell_tax_bps': 0,
            'classified_top10_pct': 38, 'source_verified': True,
            'sell_simulation_passed': True, 'permissions_reviewed': True,
            'dangerous_permissions': False, 'provider_conflict': False, 'finalized': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='JSON evidence packet; otherwise use a fictional fresh fixture')
    args = parser.parse_args()
    try:
        packet = json.loads(args.input.read_text()) if args.input else demo_packet()
        output = evaluate(packet)
    except (OSError, json.JSONDecodeError) as e:
        output = result(None, [], [f'Input error: {e}'], 0)
    print(json.dumps(output, indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
