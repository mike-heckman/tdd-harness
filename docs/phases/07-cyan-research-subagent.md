# Phase 07: Cyan (Research Sub-Agent)

## Description
Unlike the sequential lifecycle phases, Cyan is not an autonomous "Agent" with tools. It is a strictly deterministic **Orchestration Pipeline** executed by the Harness. The LLM is only called for semantic NLP tasks (query extraction, URL selection, summarization).

Cyan serves two distinct asynchronous roles:
1. **Documentation Provisioning (Triggered by Amber)**: When Amber installs dependencies, the Harness fetches the external documentation, writes it to `./docs/reference/{library_name}/`, and triggers `jDocMunch.index_local()`.
2. **Research Pipeline (Triggered by Execution Phases)**: Dynamically invoked when a primary agent calls `ask_researcher(search_keywords)`. The Harness executes the following strict sequence:
   1. Harness queries `jDocMunch` using the provided keywords.
   2. If not found, Harness executes native `search_web` using the same keywords.
   3. Harness asks OpenAI to pick the best URL from snippets.
   5. Harness executes native `download_to_reference` and `jDocMunch.index_local()`.
   6. Harness queries `jDocMunch` for the indexed page.
   7. Harness asks OpenAI to summarize the markdown.
   Returns the summary to protect the primary token budget.

## Permissions
- `src/`: Read-Only (`ro`)
- `test/`: Read-Only (`ro`)
- `docs/reference/`: Read-Write (`rw`) *(Required during Provisioning to save fetched documentation)*

## Context Payload
*(Note: This payload is completely isolated from the primary agent's history)*
1. The explicit `search_keywords` string provided by the primary agent.
2. A System Prompt instructing it to return a concise, 3-4 sentence technical summary of its findings.

## Execution Path: Orchestrated Cache Miss Recovery
Below is the explicit deterministic sequence executed by the Harness when a primary agent queries for an unindexed API.

1. **Primary Agent (Green Phase):**
   - **OpenAI Tool Call:** `ask_researcher(search_keywords="Stripe charge API JSON payload")`
2. **Harness Intervention:**
   - Primary agent suspended.
3. **Harness Orchestration Pipeline (Cyan):**
   - **Harness Action:** Queries `jdocmunch_search_sections(query="Stripe charge API JSON payload")`.
   - **Result:** `{"matches": []}` *(Cache Miss: Not found locally)*
   - **Harness Action:** Executes native Python headless web search using the exact keywords. Gets 5 URLs and snippets.
   - **Harness Action:** Executes OpenAI API call: *"Which of these URLs contains the official documentation?"*
   - **OpenAI Response:** `"https://stripe.com/docs/api/charges/create"`
   - **Harness Action:** Executes native `download_to_reference`. Saves Markdown to disk.
   - **Harness Action:** Executes `jdocmunch_index_local(path="./docs/reference")`.
   - **Harness Action:** Queries `jdocmunch_search_sections(query="Stripe charge API JSON payload")` against the new index.
   - **Result:** Returns the newly indexed markdown block detailing the parameters.
   - **Harness Action:** Executes OpenAI API call: *"Summarize this markdown to answer the original query..."*
   - **OpenAI Response:** *"The Stripe charge API requires a JSON payload with `amount` (integer), `currency` (string), and `source` (string/token). Example payload: `{"amount": 2000, "currency": "usd", "source": "tok_visa"}`"*
4. **Harness Return:**
   - Harness injects the OpenAI summarization text as the `tool_result` for the original `ask_researcher` call.
   - Harness resumes the Primary Agent.
