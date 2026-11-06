# Linked references

The nine public sources listed in the builder pack's `Public_Research` sheet, each summarised in its own folder. All were read on 2026-11-06.

| # | Source | Pack's "design implication" | Use it for |
|---|---|---|---|
| [1](01-valmet-valve-digital-services/README.md) | Valmet: Valve digital services | Predictive valve monitoring, prioritisation, installed-base docs | Worst-first ranking of valves; what an asset panel should show |
| [2](02-valmet-valve-diagnostics-blog-2026/README.md) | Valmet blog (19 Mar 2026): AI-assisted valve diagnostics | Fleet analysis, diagnostic categories, prioritisation | Five-category valve fault taxonomy; algorithm score + expert judgment |
| [3](03-valmet-virtual-mill/README.md) | Valmet Virtual Mill | Immersive digital twin for maintenance | Pitch framing: our splat walkthrough is a cheap "virtual mill" |
| [4](04-valmet-virtual-maintenance-hub/README.md) | Valmet Virtual Maintenance Hub | Mobile work orders, notifications, RCA | Shape of the work-order draft the copilot produces |
| [5](05-valmet-condition-monitoring/README.md) | Valmet Condition Monitoring | Vibration monitoring, analysis, diagnosis | Symptom → cause → action reasoning for pumps and motors |
| [6](06-opc-ua-asset-administration-shell/README.md) | OPC Foundation: OPC UA for AAS | Semantic, interoperable asset representation | One digital shell per asset; our asset JSON model |
| [7](07-opc-cloud-corner-june-2026/README.md) | OPC Foundation: Cloud Corner, June 2026 | AI-ready semantic onboarding | Argument for structured models over flat tags (Builder Q-07) |
| [8](08-khronos-gltf-gaussian-splatting/README.md) | Khronos: glTF Gaussian Splatting (3 Feb 2026) | Open baseline for splats in glTF | Export path and the splat attribute model |
| [9](09-nvidia-openusd-particle-fields/README.md) | NVIDIA Omniverse: Gaussian Splats (Particle Fields) | Native particle fields, PLY → USD | Omniverse route if we choose it; USD-style scene paths |

## Themes across all nine

- **Prioritise, don't just detect.** Valmet's own products (1, 2, 5) rank the worst assets and pair an algorithm score with expert review. Our copilot should rank and explain, then hand off to a human.
- **One asset, one identity.** AAS (6) and the OPC Cloud work (7) both push stable IDs and structured models. That matches `DOC-3D-MAPPING` in the pack.
- **The maintenance output is a work order.** (4) shows that the end of the workflow is a notification or work order, which is why the pack has `POST /api/work-orders/draft`.
- **Splats are becoming a standard format.** (8) and (9) show glTF and OpenUSD both adding Gaussian splats in 2026, so a splat-based twin is not a toy format.
