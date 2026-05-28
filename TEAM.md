# Team Assignments

| Name | Primary responsibility                         | Main files                                                                                                                                                                |
| ---- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 張茗崴 | Relational schema + relational query functions | `databases/relational/schema.sql`, `databases/relational/queries.py`, `skeleton/seed_postgres.py`                                                                         |
| 吳絃紘 | Graph schema + graph query functions           | `databases/graph/seed.cypher`, `databases/graph/queries.py`, `skeleton/seed_neo4j.py`                                                                                     |
| 施竑宇 | Vector policy documents + integration testing  | `train-mock-data/refund_policy.json`, `train-mock-data/ticket_types.json`, `train-mock-data/booking_rules.json`, `train-mock-data/travel_policies.json`, final UI testing |

## Current Workflow Rule

Before implementing query functions, the team must agree on the database schema first.

## Current Decisions

* Relational schema owner: 施竑宇
* Graph schema owner: 同學 B
* Vector / RAG and integration testing owner: 同學 C
* LLM provider for local testing: Ollama
* Vector dimension for Ollama: `vector(768)`

## Notes

* Do not modify or commit `.env`.
* Do not commit `.venv/`.
* If `schema.sql` changes, reset and reseed the database.
* If policy JSON files change, run `python skeleton/seed_vectors.py` again.
* If graph seed files change, run `python skeleton/seed_neo4j.py` again.
