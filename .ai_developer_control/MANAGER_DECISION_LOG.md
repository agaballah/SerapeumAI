[actual full content of MANAGER_DECISION_LOG.md here]

---

### [2026-09-02] | Decision: Standardized Local Developer Engine on Kilo Code

- **Context**: Local developer engine previously ran on a legacy CLI executor with a non-Nara endpoint. Owner directed standardization on the Kilo Code GUI executor backed by the Nara API for high-throughput development.
- **Decision**: Standardized local execution engine on Kilo Code GUI using Nara API with key `vscode-kilo-dev`.
- **Rationale**: High-throughput development using 7M daily token allocation and automated terminal verification.
- **Files affected**: `.ai_developer_control/DEVELOPER_RUNTIME_CONFIG.md`, `.ai_developer_control/MANAGER_BOOTSTRAP.md`, `.ai_developer_control/CURRENT_TASK.md`, `.ai_developer_control/MANAGER_DECISION_LOG.md`
- **Owner approval required**: YES (owner issued the directive)
- **Outcome**: COMPLETED

---

### [2026-09-03] | Decision: TASK-029-R Governance Provenance Recovery

- **Context**: TASK-029 Phase 1 (read-only audit) discovered that the pre-existing v6 governance authority (the AI Developer Contract, the immutable-constitution hash file, the Manager bootstrap, and the Owner approval queue) had been operating from untracked working-tree files in the original `D:\SerapeumAI` worktree. None of these four files had ever been committed on the `openhands/iteration1-controlled` branch. The only tracked `.ai_developer_control/` files at HEAD `6adba92` were four broken placeholders (`APPLICATION_ARCHITECTURE.md`, `DEVELOPMENT_LOG.md`, `MANAGER_DECISION_LOG.md`, `PROJECT_STATE.md`). TASK-029 Phase 2 fail-closed on this condition.
- **Decision**: Owner/Manager-authorised provenance-recovery operation. Five pre-existing governance files were copied byte-for-byte from the original worktree into a clean sibling worktree at `D:\SerapeumAI_review_task029_recovery` on branch `task/task-029-governance-provenance-recovery`, based on HEAD `6adba92`. The original dirty worktree remained untouched.
- **Files preserved (source SHA-256, destination SHA-256)**:
  - `.ai_developer_control/SerapeumAI_AI_Developer_Contract.md`: `86C41C06532A29ADB32DD64C953B52902EE1A158F57A1241BA0839F778AA959A` == `86C41C06532A29ADB32DD64C953B52902EE1A158F57A1241BA0839F778AA959A` (MATCH, previously untracked)
  - `.ai_developer_control/CONTRACT_CORE_HASH.txt`: `E8CE128562DE329204EFBBE4DB0BCD6FF83CA2866040DF528458C1C45E3FD038` == `E8CE128562DE329204EFBBE4DB0BCD6FF83CA2866040DF528458C1C45E3FD038` (MATCH, previously untracked)
  - `.ai_developer_control/MANAGER_BOOTSTRAP.md`: `78EBDF03D8F86DC5188B0805C825F5D325BFBF6B1862C8A625AF481143125095` == `78EBDF03D8F86DC5188B0805C825F5D325BFBF6B1862C8A625AF481143125095` (MATCH, previously untracked)
  - `.ai_developer_control/OWNER_APPROVAL_QUEUE.md`: `26629467A4E877C830B3723D91FB4C8A316325D79AFC5312222E59DB393CAF0C` == `26629467A4E877C830B3723D91FB4C8A316325D79AFC5312222E59DB393CAF0C` (MATCH, previously untracked)
  - `.ai_developer_control/MANAGER_DECISION_LOG.md`: `3451B07C551F6477CDAC32FCE575F599FCD98E39675259DB1D68CE56A2C1D0C5` == `3451B07C551F6477CDAC32FCE575F599FCD98E39675259DB1D68CE56A2C1D0C5` (MATCH, previously tracked at HEAD as 25-line stub with TASK-002 entry; working-tree version differs by the literal stub header line 1 and is the operating-authority version)
- **Provenance gap recorded transparently**: this commit does NOT retroactively prove that the four previously-untracked governance files were ever historically tracked. It records the gap. It establishes a Git-visible preservation checkpoint for the files that were in actual use at the TASK-029 recovery moment.
- **Anomaly preserved (not silently rewritten)**: the `CONTRACT_CORE_HASH.txt` file declares LF-normalized SHA-256 of the IMMUTABLE_CONSTITUTION as `330ec9c73d51b5e8f4a451affeca4d8f128a8938316bbcded1ce859f71c98253`, while the live v6 contract file's SHA-256 (Windows CRLF) is `86C41C06532A29ADB32DD64C953B52902EE1A158F57A1241BA0839F778AA959A`. The LF vs CRLF drift is preserved as historical evidence. No silent fix.
- **Manager bootstrap re-print note**: the `MANAGER_BOOTSTRAP.md` preserved here contains a re-print of the v6 constitution text. Its tool-name reference (`Nara + Kilo Code (Nara API)`) does not match the live v6 contract's tool-name reference (`Nara + Aider`). This pre-existing internal inconsistency is preserved as part of the historical snapshot.
- **Scope discipline**: exactly five files were copied. No recursive copy of `.ai_developer_control/`. The three broken placeholders (`PROJECT_STATE.md`, `DEVELOPMENT_LOG.md`, `APPLICATION_ARCHITECTURE.md`) were NOT touched. The original `D:\SerapeumAI` worktree remained READ-ONLY (branch `openhands/iteration1-controlled`, HEAD `6adba92`, 68 porcelain entries, zero mutations).
- **Owner approval required**: YES (Owner directive TASK-029-R, 2026-09-03)
- **Outcome**: COMPLETED (provenance recovery). TASK-029 v7 adoption remains a separate, future, Owner-authorised task.