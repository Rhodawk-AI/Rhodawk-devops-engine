---
name: smart-contract-audit
domain: web3
triggers:
  languages:    [solidity, vyper, yul, move, cairo]
  frameworks:   [hardhat, foundry, truffle, brownie, anchor]
  asset_types:  [evm, contract, dapp, defi]
tools:          [slither, mythril, echidna, foundry, manticore, halmos]
severity_focus: [P1, P2]
---

# Smart-Contract Audit (EVM-first)

## When to load
Any Solidity / Vyper / Yul source file, deployed bytecode, ABI, or DeFi
protocol scope. Auto-loads on `*.sol`, `hardhat.config.*`, `foundry.toml`,
`forge.lock`, or anything inside `contracts/`.

## High-payout bug classes
1. **Reentrancy** — single-function, cross-function, cross-contract, read-only
   reentrancy via view callbacks. Always treat external calls as untrusted.
2. **Flash-loan price manipulation** — TWAP not used, single-block oracle,
   borrowing → swap → liquidate / mint → repay in one transaction.
3. **Access-control gaps** — missing `onlyOwner`, init function callable
   twice, `delegatecall` to attacker-controlled implementation.
4. **Arithmetic** — pre-0.8 overflow / underflow, `unchecked` blocks abused,
   rounding direction favouring attacker, decimals mismatch (18 vs 6).
5. **Signature replay** — missing nonce, missing `chainid`, EIP-712 typehash
   collision, ecrecover returning `address(0)` accepted.
6. **Token non-standard behaviour** — ERC-20 fee-on-transfer, deflationary,
   rebasing, ERC-777 hook callbacks, USDT not returning `bool`.
7. **Storage collisions** — proxy + implementation slot overlap, `delegatecall`
   into incompatible layout, EIP-1967 violated.
8. **MEV / front-running** — slippage = 0, deadline = `type(uint256).max`,
   commit-reveal absent on auctions and lotteries.
9. **Governance attacks** — flash-loaned voting power, timelock bypass via
   delegatecall, signature aggregation.
10. **Bridge & cross-chain** — message replay across chains, validator-set
    rotation race, finality assumptions broken on reorgs.

## Methodology
1. `slither <repo> --print human-summary` — fast triage.
2. `forge build && forge test` — confirm baseline.
3. `slither <repo> --detect all` then triage by impact, not detector severity.
4. Hand-write Foundry invariants for: total-supply conservation, monotone
   accounting, "no user can drain another user".
5. `echidna-test <contract> --config echidna.yaml` — property fuzz the
   invariants.
6. `halmos --function <fn>` — symbolic for arithmetic-heavy functions.
7. Write PoC as a Foundry test that ends with `assertGt(attacker.bal, 0)`.

## Reporting tone
Bridges and lending markets pay P1 only for confirmed economic loss; phrase
the impact as USD at risk and reference the affected pool.
