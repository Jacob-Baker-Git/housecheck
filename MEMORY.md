# MEMORY.md: HouseCheck working notes (Open Agent Hackathon 2026)

**Deadline: Tue 27 Oct, 23:45. Target submit 20:00.** Solo build (Jacob). Submit: public GitHub repo, 1–4 min video, slide deck, sponsor-tech write-up.

## Zetaris criteria (from "Build with Zetaris evaluation criteria" PDF)
1a use case + 3+ sources → docs/usl/USE_CASE.md ✅ drafted
1b onboard + 2–3 queries per source → `housecheck usl run` (sql/01, sql/02) ⏳ needs live run
1c USL + DDL, 2–3 queries showing it active, 1 DQ rule executed → sql/04, sql/05 ⏳ needs live run
2a time saved vs hand-coded (+bonus hand-coded part) → docs/usl/REFLECTION.md + scripts/handcoded_council_check.py ⏳ fill numbers
2b would it help my work (+forecast) → REFLECTION.md ⏳ fill numbers
2c PM requirement (+mock feature/USL) → REFLECTION.md ✅ drafted (parameterised REST sources)

## Order of work today
1. `housecheck doctor` → fix until all PASS (Zetaris first, then Nightshift).
2. `housecheck usl run "<3 real postcodes>"` → fix failures → commit sql/ and docs/usl/RESULTS.md.
3. `housecheck compare ...` live → commit data/samples/.
4. Fill ⟨fill⟩ numbers in REFLECTION.md.
5. 12:00 freeze. Deck, video, push to GitHub (public), submit.

## Known unknowns
- Zetaris REST: `POST {ZETARIS_REST_URL}/sql-editor/sqls/run`, Bearer key, X-Org-ID, port 8888 `/api/v1.0` (copied from other teams' repos).
- USL syntax copied from a team whose run passed: COMPILE USL ... DEPLOY NAMESPACE ... DDL, ACTIVATE USL TABLE, REGISTER DQ, RUN DQ TABLE. Column named `text` is rejected.
- Nightshift default `http://127.0.0.1:8088/v1`. WSL → Windows needs mirrored networking or run on Windows.
- Cursor: recommended, not (as far as we found) required. Built with Claude; disclosed in README.

## Machine notes
- Zetaris in WSL Ubuntu on D:, `~/zetaris-platform`. Stop/start: `docker compose stop` / `start`. **Never `down -v`.**
