# Panda Agent

<p align="center">
  <img src="docs/figures/pandasi-logo.png" alt="PandaSI" width="440">
</p>

<p align="center">
  <img src="docs/figures/wordmark.png" alt="PANDASI" width="280">
</p>

Panda Agent is the evidence-policy checker for PandaSI. It reads one JSON packet about a BNB Smart Chain token and returns either `RESEARCH` or `ABSTAIN`. A passing result means the packet is complete enough to keep studying. It does not authorize a trade, a signature, or a transfer.

The program in this repository is deterministic. It uses the Python standard library only. It does not open a network connection, does not hold a key, and does not call a remote model. `execution_authorized` is `false` on every path, including a clean fixture and a broken file.

<p align="center">
  <img src="docs/figures/mark.png" alt="Panda mark" width="88">
</p>

| | |
| --- | --- |
| Policy | `prototype-v1` |
| Chain | BNB Smart Chain, integer `chain_id` 56 |
| Decisions | `RESEARCH` or `ABSTAIN` |
| Execution | Always unauthorized |
| Runtime | Python 3.9 or newer, standard library |
| Entry point | `panda_agent.py` |

```text
python panda_agent.py
python panda_agent.py --input example_missing_evidence.json
python -m unittest -v
```

