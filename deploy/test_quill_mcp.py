#!/usr/bin/env python3
"""Test every quill MCP tool over stdio. Reports PASS/FAIL per tool.
Run: python3 test_quill_mcp.py [--fast]   (--fast skips the 2 Go API calls)"""
import asyncio
import json
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command='python3', args=['/root/manuscriptAI/deploy/quill_mcp.py'])
FAST = '--fast' in sys.argv
results = []


def ok(name, passed, detail=''):
    results.append((name, passed, detail))
    print(f"{'PASS' if passed else 'FAIL'}  {name}  {detail[:140]}", flush=True)


async def call(session, name, args, timeout=90):
    t0 = time.time()
    r = await session.call_tool(name, args)
    dt = time.time() - t0
    text = (r.content[0].text if r.content else '') if not r.isError else f'ERROR: {r.content[0].text if r.content else "?"}'
    return text, dt, r.isError


async def main():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            expected = {'packs_list', 'pack_get', 'pack_source', 'sweep', 'verify_claim',
                        'lookup_quote', 'boardcheck', 'web_search', 'canon_search',
                        'canon_read', 'canon_verify', 'parallel_args'}
            ok('tools/list', expected.issubset(set(names)),
               f'{len(names)} tools: missing={expected - set(names)}')

            # 1. packs_list
            t, dt, err = await call(session, 'packs_list', {})
            ok('packs_list', not err and 'rebirth' in t and 'what-is-jhana' in t
               and 'devas-real' in t, f'{t.count(chr(10))+1} packs, {dt}s')

            # 2. pack_get
            t, dt, err = await call(session, 'pack_get', {'slug': 'karma'})
            ok('pack_get', not err and 'Why Karma' in t and 'WEAVE.md' in t,
               f'{len(t)} chars, {dt}s')

            # 3. pack_source
            t, dt, err = await call(session, 'pack_source',
                                    {'slug': 'karma', 'name': 'WEAVE.md'})
            ok('pack_source', not err and '[K1]' in t and 'garland' in t,
               f'{len(t)} chars has K1+garland, {dt}s')

            # 4. lookup_quote (deterministic)
            t, dt, err = await call(session, 'lookup_quote',
                                    {'query': 'K15', 'pack': 'karma'})
            ok('lookup_quote', not err and 'mother' in t.lower() and 'not found' not in t.lower(),
               f'{len(t)} chars, {dt}s')

            # 5. lookup_quote miss (honest not-found)
            t, dt, err = await call(session, 'lookup_quote',
                                    {'query': 'K999', 'pack': 'karma'})
            ok('lookup_quote-miss', not err and 'Not found' in t, f'honest miss, {dt}s')

            # 6. boardcheck (bridge deterministic renderer)
            t, dt, err = await call(session, 'boardcheck', {'pack': 'rebirth'}, timeout=120)
            ok('boardcheck', not err and 'shots' in t and 'Boardcheck' in t,
               f'{t.splitlines()[0][:90] if t else "?"}, {dt}s')

            # 7. web_search (bridge → DDG)
            t, dt, err = await call(session, 'web_search',
                                    {'query': 'ajahn brahmali devas'})
            ok('web_search', not err and ('http' in t or 'No results' in t),
               f'{t.count(chr(10))//3} hits, {dt}s')

            # 8. canon_search (FoJin)
            t, dt, err = await call(session, 'canon_search',
                                    {'query': 'all beings have been mother', 'limit': 3})
            ok('canon_search', not err and 'fojin:' in t, f'{len(t)} chars with URNs, {dt}s')

            # 9. canon_read (FoJin by URN — reuse whatever canon_search returned)
            urn = ''
            for line in t.splitlines():
                if line.startswith('URN:'):
                    urn = line.split()[1]
                    break
            t2, dt2, err = await call(session, 'canon_read', {'urn': urn}) if urn else ('no urn', 0, True)
            ok('canon_read', not err and len(t2) > 50, f'{urn or "no-urn"} → {len(t2)} chars, {dt2}s')

            # 10. canon_verify (FoJin)
            t, dt, err = await call(session, 'canon_verify',
                                    {'quote': 'the deathless is unborn, unbecome, unmade, unconditioned'})
            ok('canon_verify', not err and len(t) > 20, f'{len(t)} chars, {dt}s')

            if not FAST:
                # 11. verify_claim (Go API)
                t, dt, err = await call(session, 'verify_claim', {
                    'claim': 'Jhana is perpetually being ruined by you',
                    'pack': 'what-is-jhana', 'sources': ['WEAVE.md']}, timeout=180)
                ok('verify_claim', not err and ('SUPPORT' in t.upper() or 'SILENT' in t.upper()
                   or 'CONTRADICT' in t.upper() or 'J2' in t),
                   f'verdict returned, {dt}s: {t[:80]}')

                # 12. sweep (Go API, the full copilot loop)
                section = ('[OWNER VERBATIM]\nwhat is a jhana? basically draw from nyanamoli. '
                           'The wonder is how its even a thing at all.\n\n'
                           'Jhana is not merely a ritual, but a gateway. It is the natural state.')
                t, dt, err = await call(session, 'sweep', {
                    'section_title': 'CH.1 TEST', 'section_text': section,
                    'pack': 'what-is-jhana', 'sources': ['WEAVE.md', 'ACQUIRE.md'],
                    'focus': 'banked sources only'}, timeout=240)
                ok('sweep', not err and '## Verdicts' in t and '## Implications' in t,
                   f'{len(t)} chars 4-section contract, {dt}s')
            else:
                ok('verify_claim', True, 'SKIPPED (--fast)')
                ok('sweep', True, 'SKIPPED (--fast)')

    print()
    n_pass = sum(1 for _, p, _ in results if p)
    print(f'=== {n_pass}/{len(results)} PASS ===')
    sys.exit(0 if n_pass == len(results) else 1)


if __name__ == '__main__':
    asyncio.run(main())
