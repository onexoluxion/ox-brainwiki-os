# Third-party notices and rights

Runtime dependency: Basic Memory 1.0.0, Basic Machines, AGPL-3.0-or-later, https://github.com/basicmachines-co/basic-memory. Installed distribution license retained in the isolated environment. No Basic Memory source is vendored; CLI integration is original glue. Distribution licensing and corresponding-source obligations must be resolved before public packaging; this candidate grants no new public license over upstream work.

FastMCP 4.1.3 provides protocol handling. Full transitive artifacts/versions/hashes are in uv.lock. Dependency license inventory, vulnerability triage and embedding model artifact/license review remain release gates. Model weights are downloaded by upstream FastEmbed, not distributed here.

MCPVault, copyright Mauricio Wolff, MIT, https://github.com/bitbonsai/mcpvault: architecture inspiration only, no copied code. No private Cabinet or Calibrate skill assets copied. No endorsement implied.


## Final qualification evidence

Tested model: Qdrant/bge-small-en-v1.5-onnx-Q revision aa8f8b060edb00e03bfdd08813a2949946c8ba55, derived from BAAI/bge-small-en-v1.5. MODEL_PROVENANCE.json records tested artifact hashes. Snapshot has no license file; repository metadata changed historically, so redistribution remains unresolved. Weights are not committed. FastEmbed downloads by name, not immutable revision. Receipts detect local changes but do not make fresh downloads reproducible.
