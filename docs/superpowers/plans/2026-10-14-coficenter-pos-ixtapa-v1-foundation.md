# CofiCenter POS Ixtapa v1 — Staff, Cash & Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add production-ready employee authentication, POS authorization, one-register cash shifts, denomination counts, cash movements, blind closing, audit logging, and secure POS locking for CofiCenter Ixtapa.

**Architecture:** Extend the existing POS through isolated `pos_staff`, `pos_cash`, and `pos_audit` domains rather than adding financial/authentication responsibilities to `PosOrderService`. Administrator authentication remains separate. Ixtapa v1 supports one physical register and one open cash shift at a time.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, pytest, vanilla JavaScript POS/PWA, IndexedDB and Web Crypto where appropriate.

**Spec:** `docs/superpowers/specs/2026-10-14-coficenter-pos-ixtapa-v1-design.md`

## Global Constraints

- Production scope: Ixtapa only.
- One physical POS/cash drawer.
- Only one active cash shift at a time.
- Cashier and Manager use individual PINs.
- PINs are never stored in plaintext.
- Administrator continues using username + password.
- Opening and final closing require Manager authorization.
- Manual cash movements require Manager authorization.
- Opening and closing counts use MXN denominations: 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000.
- Closing is blind.
- Any cash difference requires a reason.
- POS automatically locks after 5 minutes of inactivity.
- Locking must preserve the active shift and current cart.
- Previously authorized employees may unlock offline only if the shift was already opened online.
- Opening, closing, cash movements and new authorizations require connectivity.
- Sensitive permissions are enforced server-side.
- Database changes use Alembic only.

## Review Focus

1. Concurrent opening requests must never create two active shifts.
2. Wrong/inactive PINs and Cashier PINs used as Manager approval must fail.
3. Expected cash must remain hidden before blind-count submission.
4. Repeated cash movement requests must not duplicate ledger effects.
5. Offline authentication must never cache or expose plaintext PINs.

---

## Task 1 — POS Staff Foundation

**Files**

Create:

- `backend/app/models/pos_staff.py`
- `backend/app/schemas/pos_staff.py`
- `backend/app/services/pos_staff_service.py`
- `backend/app/auth/pos_staff_security.py`
- `backend/app/api/pos_staff.py`
- `backend/tests/test_pos_staff_auth.py`

Modify:

- `backend/app/models/__init__.py`
- `backend/app/main.py`

Migration:

- `backend/alembic/versions/20261014_0001_pos_staff_cash_audit.py`

### Interfaces

`PosStaffService.verify_pin(db, *, staff_id: int, pin: str, branch_code: str) -> PosStaff`

`PosStaffService.authorize_manager(db, *, staff_id: int, pin: str, branch_code: str) -> PosStaff`

`create_pos_staff_token(*, staff: PosStaff, branch_code: str, terminal_id: str) -> str`

`get_current_pos_staff(...) -> PosStaff`

`require_pos_manager(...) -> PosStaff`

Routes:

- `POST /pos/staff/unlock`
- `GET /pos/staff/session`

### Staff model

Fields:

- id
- branch_id
- display_name
- role: `CASHIER | MANAGER`
- pin_hash
- is_active
- created_at
- updated_at

### TDD Steps

- [ ] Write `test_cashier_can_unlock_with_correct_pin`.
- [ ] Write `test_wrong_pin_is_rejected`.
- [ ] Write `test_inactive_staff_is_rejected`.
- [ ] Write `test_cashier_cannot_authorize_manager_operation`.
- [ ] Run `backend/tests/test_pos_staff_auth.py` and confirm failure.
- [ ] Resolve current Alembic head before assigning `down_revision`.
- [ ] Implement staff model and migration.
- [ ] Reuse the project's secure hashing/JWT primitives.
- [ ] Implement unlock/session routes.
- [ ] Run staff-auth tests until green.
- [ ] Commit as `feat(pos): add staff PIN authentication`.

---

## Task 2 — Persistent POS Audit Log

**Files**

Create:

- `backend/app/models/pos_audit.py`
- `backend/app/services/pos_audit_service.py`
- `backend/tests/test_pos_audit.py`

Modify:

- `backend/app/models/__init__.py`
- `backend/alembic/versions/20261014_0001_pos_staff_cash_audit.py`

### Interface

`PosAuditService.record(db, *, event_type: str, branch_id: int, terminal_id: str, actor_staff_id: int | None, authorizer_staff_id: int | None = None, target_type: str | None = None, target_id: str | None = None, metadata: dict | None = None) -> PosAuditEvent`

Initial events:

- `SHIFT_OPENED`
- `SHIFT_CLOSED`
- `CASH_MOVEMENT`

Audit records are append-only.

### TDD Steps

- [ ] Write `test_audit_event_records_actor_and_target`.
- [ ] Write `test_audit_metadata_round_trips`.
- [ ] Verify tests fail before implementation.
- [ ] Implement audit model and service.
- [ ] Do not expose update/delete APIs.
- [ ] Verify audit tests pass.
- [ ] Commit as `feat(pos): add persistent audit log`.


---

## Task 3 — Cash Shift Opening and Denomination Counts

**Files**

Create:

- `backend/app/models/pos_cash.py`
- `backend/app/schemas/pos_cash.py`
- `backend/app/services/pos_cash_service.py`
- `backend/app/api/pos_cash.py`
- `backend/tests/test_pos_cash_shifts.py`

Modify:

- `backend/app/models/__init__.py`
- `backend/app/main.py`
- `backend/alembic/versions/20261014_0001_pos_staff_cash_audit.py`

### Interfaces

`PosCashService.current_shift(db, *, branch_code: str, terminal_id: str) -> PosCashShift | None`

`PosCashService.open_shift(db, *, branch_code: str, terminal_id: str, opening_counts: list[CashDenominationCount], requesting_staff: PosStaff, authorizing_manager: PosStaff) -> PosCashShift`

Routes:

- `POST /pos/cash/shifts/open`
- `GET /pos/cash/shifts/current`

### Cash shift model

`PosCashShift`

Fields:

- id
- shift_uuid
- branch_id
- terminal_id
- status: `OPEN | CLOSING | CLOSED`
- opened_by_staff_id
- opening_authorized_by_staff_id
- opening_total
- opened_at
- closing fields nullable until closing

### Denomination model

`PosCashDenominationCount`

Fields:

- shift_id
- stage: `OPENING | CLOSING`
- denomination_cents
- quantity
- amount_cents

Valid MXN denomination values in cents:

- 100
- 200
- 500
- 1000
- 2000
- 5000
- 10000
- 20000
- 50000
- 100000

The system calculates totals from denomination quantities.

No default opening cash amount is allowed.

### TDD Steps

- [ ] Write `test_open_shift_calculates_total_from_denominations`.
- [ ] Write `test_second_open_shift_is_rejected`.
- [ ] Write `test_manager_authorization_is_required_to_open_shift`.
- [ ] Write `test_opening_rejects_unknown_denomination`.
- [ ] Write a concurrency regression test proving two simultaneous opening attempts cannot both commit.
- [ ] Run `backend/tests/test_pos_cash_shifts.py` and confirm failure.
- [ ] Implement cash shift and denomination models.
- [ ] Add database constraints/indexes preventing concurrent active Ixtapa shifts.
- [ ] Implement row locking/transaction protection in `open_shift`.
- [ ] Create `SHIFT_OPENED` audit event in the same transaction.
- [ ] Verify tests pass.
- [ ] Commit as `feat(pos): add cash shift opening`.

---

## Task 4 — Cash Ledger and Manager-Authorized Cash Movements

**Files**

Modify:

- `backend/app/models/pos_cash.py`
- `backend/app/schemas/pos_cash.py`
- `backend/app/services/pos_cash_service.py`
- `backend/app/api/pos_cash.py`
- `backend/alembic/versions/20261014_0001_pos_staff_cash_audit.py`

Create:

- `backend/tests/test_pos_cash_movements.py`

### Interfaces

`PosCashService.record_movement(db, *, shift_uuid: str, direction: str, category: str, amount: Decimal, note: str, idempotency_key: str, requesting_staff: PosStaff, authorizing_manager: PosStaff) -> PosCashMovement`

`PosCashService.append_ledger_entry(db, *, shift_id: int, entry_type: str, amount: Decimal, idempotency_key: str, reference_type: str | None = None, reference_id: str | None = None) -> PosCashLedgerEntry`

Route:

- `POST /pos/cash/shifts/{shift_uuid}/movements`

### Cash movement model

`PosCashMovement`

Fields:

- id
- movement_uuid
- shift_id
- direction
- category
- amount
- note
- requesting_staff_id
- authorizing_staff_id
- idempotency_key
- created_at

Directions:

- `INFLOW`
- `OUTFLOW`

Categories:

- `CHANGE`
- `EXPENSE`
- `SAFE_WITHDRAWAL`
- `DEPOSIT`
- `CORRECTION`
- `OTHER`

### Cash ledger

`PosCashLedgerEntry` is the canonical financial-effect ledger for the cash drawer.

It will later receive entries from:

- cash sales
- cash tips
- cash refunds
- manual cash inflows/outflows

Fields:

- id
- shift_id
- entry_type
- amount
- idempotency_key
- reference_type
- reference_id
- created_at

`idempotency_key` must be unique.

Manual inflows write a positive ledger amount.

Manual outflows write a negative ledger amount.

### TDD Steps

- [ ] Write `test_manager_authorized_inflow_increases_expected_cash`.
- [ ] Write `test_manager_authorized_outflow_reduces_expected_cash`.
- [ ] Write `test_cash_movement_requires_note`.
- [ ] Write `test_cashier_cannot_authorize_cash_movement`.
- [ ] Write `test_movement_is_rejected_when_shift_is_not_open`.
- [ ] Write `test_repeated_idempotency_key_does_not_duplicate_movement`.
- [ ] Run `backend/tests/test_pos_cash_movements.py` and confirm failure.
- [ ] Implement cash movement and ledger models.
- [ ] Implement idempotent `append_ledger_entry`.
- [ ] Implement Manager-authorized `record_movement`.
- [ ] Write movement, ledger entry and `CASH_MOVEMENT` audit event atomically.
- [ ] Verify movement tests pass.
- [ ] Re-run cash-shift and audit tests.
- [ ] Commit as `feat(pos): add cash movement ledger`.


---

## Task 5 — Blind Closing and Final Manager Authorization

**Files**

Modify:

- `backend/app/models/pos_cash.py`
- `backend/app/schemas/pos_cash.py`
- `backend/app/services/pos_cash_service.py`
- `backend/app/api/pos_cash.py`

Create:

- `backend/tests/test_pos_cash_close.py`

### Interfaces

`PosCashService.submit_closing_count(db, *, shift_uuid: str, closing_counts: list[CashDenominationCount], staff: PosStaff) -> PosCashReconciliation`

`PosCashService.authorize_close(db, *, shift_uuid: str, manager: PosStaff, difference_note: str | None = None) -> PosCashShift`

Routes:

- `POST /pos/cash/shifts/{shift_uuid}/closing-count`
- `POST /pos/cash/shifts/{shift_uuid}/close`

### Reconciliation

Canonical formula:

`expected_cash = opening_total + sum(cash_ledger_entries.amount)`

The cash ledger will later receive effects from:

- cash sales
- cash tips
- cash refunds
- manual cash movements

Closing count is calculated only from denomination quantities.

### Blind-close rules

Before physical count submission:

- current-shift API must not expose `expected_cash`
- must not expose calculated difference
- must not expose ledger-derived expected balance

After count submission:

- denomination snapshot is persisted
- counted total is calculated server-side
- shift transitions from `OPEN` to `CLOSING`
- reconciliation becomes available
- expected cash is returned
- difference is returned

Final close requires Manager authorization.

If:

`counted_cash != expected_cash`

then `difference_note` is mandatory.

If:

`counted_cash == expected_cash`

no difference note is required.

After final authorization:

- shift becomes `CLOSED`
- `closed_at` is stored
- closing Manager is stored
- reconciliation values are frozen
- `SHIFT_CLOSED` audit event is written

Closed shifts are immutable through normal application APIs.

### TDD Steps

- [ ] Write `test_open_shift_response_does_not_expose_expected_cash`.
- [ ] Write `test_closing_count_calculates_total_from_denominations`.
- [ ] Write `test_closing_count_reveals_reconciliation_only_after_submission`.
- [ ] Write `test_closing_count_transitions_shift_to_closing`.
- [ ] Write `test_difference_requires_note_before_final_close`.
- [ ] Write `test_matching_count_does_not_require_difference_note`.
- [ ] Write `test_cashier_cannot_finalize_close`.
- [ ] Write `test_manager_can_finalize_close`.
- [ ] Write `test_closed_shift_rejects_additional_cash_movements`.
- [ ] Write `test_closed_shift_cannot_be_closed_twice`.
- [ ] Run `backend/tests/test_pos_cash_close.py` and confirm failure.
- [ ] Implement closing-count snapshot.
- [ ] Implement server-side reconciliation.
- [ ] Ensure expected cash is unavailable before count submission.
- [ ] Implement `OPEN -> CLOSING -> CLOSED`.
- [ ] Require Manager authorization for final close.
- [ ] Require difference note only when difference is non-zero.
- [ ] Persist `SHIFT_CLOSED` audit event atomically with final close.
- [ ] Run close tests until green.
- [ ] Re-run staff, audit, shift and movement tests.
- [ ] Commit as `feat(pos): add blind cash closing`.

---

## Task 5 Verification Matrix

Run:

`backend/tests/test_pos_staff_auth.py`

`backend/tests/test_pos_audit.py`

`backend/tests/test_pos_cash_shifts.py`

`backend/tests/test_pos_cash_movements.py`

`backend/tests/test_pos_cash_close.py`

Expected:

- all tests pass
- one active shift maximum remains enforced
- closing does not break movement ledger calculations
- Manager permissions remain server-enforced
- no reconciliation information leaks before physical count


---

## Task 6 — POS Staff Locking, Shift UI and Offline Unlock

**Files**

Create:

- `pos/js/staff-session.js`
- `pos/js/cash-shift.js`
- `pos/tests/staff-lock.test.js`
- `pos/tests/cash-shift-ui.test.js`
- `pos/tests/staff-offline-auth.test.js`

Modify:

- `pos/index.html`
- `pos/js/app.js`
- `pos/js/api.js`
- `pos/js/db.js`
- POS CSS only where required by the new screens/states

### Interfaces

`CofiPosStaffSession.unlock(staffId, pin)`

`CofiPosStaffSession.lock()`

`CofiPosStaffSession.current()`

`CofiPosStaffSession.resetActivityTimer()`

`CofiPosStaffSession.canUnlockOffline(staffId, pin)`

`CofiPosCashShift.loadCurrent()`

`CofiPosCashShift.open(openingCounts, managerCredentials)`

`CofiPosCashShift.recordMovement(payload, managerCredentials)`

`CofiPosCashShift.submitClosingCount(closingCounts)`

`CofiPosCashShift.finalizeClose(managerCredentials, differenceNote)`

### Operational login screen

When the POS has no active staff session:

- show employee PIN unlock screen
- do not expose Administrator login as operational employee authentication
- do not allow sale interaction until employee unlock succeeds

After successful unlock display:

- employee display name
- employee role
- active shift state
- connectivity state

### Quick Lock

Provide an explicit Lock action.

Locking:

- removes active operational authentication from the visible POS session
- preserves active shift
- preserves current cart
- preserves unsent local orders
- does not cancel Kitchen/Bar activity
- does not close the register

The next authorized employee can unlock and continue.

### Automatic Lock

Inactivity timeout:

`5 minutes`

Activity that resets the timer includes normal POS interaction such as:

- pointer/touch input
- keyboard input
- product/cart interaction
- payment workflow interaction

The timer must not close the shift.

The timer must not clear the cart.

### Offline staff verifier

A staff member may unlock offline only if:

- that employee previously authenticated successfully online on this terminal
- employee was active at last successful authorization
- there was already an active shift before connectivity was lost

Never store:

- plaintext PIN
- reversible PIN
- raw server password/PIN hash
- reusable server authentication secret

Use a terminal-local salted verifier generated with Web Crypto or an equivalent secure browser-native KDF.

Persist only enough information to verify the entered PIN locally.

### Offline restrictions

Offline unlock does not grant permission to perform server-required sensitive actions.

While offline:

Allowed later in the complete POS:

- existing-authorized staff unlock
- cash-only sales during an already-open shift
- local receipt generation
- local persistence/synchronization queue

Not allowed in this plan:

- opening shift
- final closing
- manual cash movements
- new employee authorization
- permission changes
- Manager authorization for a new sensitive operation

### Shift opening UI

Opening screen shows denomination rows for:

- $1
- $2
- $5
- $10
- $20
- $50
- $100
- $200
- $500
- $1,000

Each row accepts quantity.

UI calculates total from quantities.

There must be:

- no predefined opening total
- no suggested opening amount
- no editable manual total that bypasses denomination calculation

Opening requires Manager PIN authorization.

### Cash Movement UI

When online and shift is OPEN:

Manager-authorized movement form includes:

- direction
- category
- amount
- required note
- requesting employee
- Manager PIN authorization

Categories displayed in Spanish:

- Cambio
- Gasto
- Retiro a caja fuerte
- Depósito
- Corrección
- Otro

### Blind Closing UI

Before physical count submission:

Do not display:

- expected cash
- expected difference
- ledger-derived cash balance

Show denomination input only.

After successful count submission show:

- opening cash
- cash ledger activity
- expected cash
- counted cash
- difference

If difference is non-zero:

- require explanation field

Final close requires Manager PIN.

### Connectivity UX

Display clear state:

- `En línea`
- `Sin conexión`

If an operation requires connectivity, disable it with a clear reason rather than silently failing.

### TDD Steps

- [ ] Write `staff-lock.test.js` proving manual lock preserves the cart.
- [ ] Write `staff-lock.test.js` proving inactivity locks after exactly 5 minutes.
- [ ] Write `staff-lock.test.js` proving activity resets the inactivity timer.
- [ ] Write `staff-offline-auth.test.js` proving previously authorized staff can unlock offline.
- [ ] Write `staff-offline-auth.test.js` proving unseen staff cannot unlock offline.
- [ ] Write `staff-offline-auth.test.js` proving plaintext PIN is not persisted.
- [ ] Write `staff-offline-auth.test.js` proving offline unlock is rejected if no previously-open shift exists.
- [ ] Write `cash-shift-ui.test.js` proving opening has no default cash amount.
- [ ] Write `cash-shift-ui.test.js` proving denomination quantities calculate the displayed total.
- [ ] Write `cash-shift-ui.test.js` proving Manager authorization is required to open.
- [ ] Write `cash-shift-ui.test.js` proving expected cash is hidden before closing-count submission.
- [ ] Write `cash-shift-ui.test.js` proving reconciliation appears only after count submission.
- [ ] Write `cash-shift-ui.test.js` proving difference note is required when needed.
- [ ] Run targeted frontend tests and verify they fail before implementation.
- [ ] Implement staff-session state without coupling it to Administrator auth.
- [ ] Implement 5-minute inactivity timer.
- [ ] Implement secure terminal-local offline verifier.
- [ ] Implement denomination opening UI.
- [ ] Implement cash movement UI.
- [ ] Implement blind closing UI.
- [ ] Implement connectivity restrictions.
- [ ] Run targeted tests until green.
- [ ] Run the complete existing POS frontend suite.
- [ ] Commit as `feat(pos): add staff and cash shift UI`.

---

## Task 6 Security Review

Before accepting Task 6 verify:

- browser storage contains no plaintext PIN
- browser storage contains no reusable server-side PIN hash
- offline verifier is terminal-specific
- inactive staff cache can be invalidated on next successful online synchronization
- operational PIN authentication cannot create Administrator privileges
- lock screen cannot expose sensitive shift reconciliation values
- page refresh does not silently unlock the POS
- offline mode cannot open or close a shift


---

## Task 7 — Phase 1 Integration Verification

**Purpose**

Prove that Staff, Cash and Audit work together without regressing the existing POS, Kiosk, Kitchen, Bar, hotspot, payments or receipt behavior.

Do not add unrelated features during this task.

### Migration Verification

Before applying migrations:

- confirm current branch
- confirm working tree state
- inspect Alembic heads
- confirm exactly one expected head

Run:

`git branch --show-current`

`git status --short`

`docker compose exec -T api alembic heads`

Expected:

- branch is the intended implementation branch
- no unexplained working-tree changes
- one Alembic head

Then apply:

`docker compose exec -T api alembic upgrade head`

Expected:

- migration succeeds
- no duplicate head
- no manual schema changes required

### Backend Verification

Run targeted tests:

`backend/tests/test_pos_staff_auth.py`

`backend/tests/test_pos_audit.py`

`backend/tests/test_pos_cash_shifts.py`

`backend/tests/test_pos_cash_movements.py`

`backend/tests/test_pos_cash_close.py`

Then run the complete existing backend pytest suite using the repository's established test command.

Expected:

- all new tests pass
- all existing tests remain green

### Frontend Verification

Before running frontend tests, inspect the repository's existing package scripts and CI/test configuration and use the established command rather than inventing a new runner.

Run targeted tests for:

- staff lock
- cash shift UI
- offline staff authentication

Then run the complete existing POS frontend test suite.

Expected:

- all new tests pass
- all existing POS/Kiosk/receipt/station tests remain green

### Build Verification

Run the repository's established frontend/build validation.

Expected:

- no syntax errors
- no missing imports
- no broken static assets
- no PWA regression

### Docker Verification

Rebuild using the current production-candidate Compose workflow.

Verify container status.

Verify API health endpoint.

Expected:

- API healthy
- PostgreSQL healthy
- frontend remains available
- no unexpected restart loop

### Existing Flow Smoke Tests

Verify that these pre-existing flows still load and function:

- main POS
- Kitchen station
- Bar station
- customer display if enabled
- Ixtapa kiosk/self-order
- existing receipt rendering
- existing order history

### Manual Ixtapa Acceptance — Staff

Verify:

1. Cashier can unlock with correct PIN.
2. Wrong PIN is rejected.
3. Inactive employee is rejected.
4. Cashier cannot perform Manager authorization.
5. Manager can authorize Manager-only operation.
6. Quick Lock hides operational POS.
7. Cart survives Quick Lock.
8. Another authorized employee can unlock.
9. POS auto-locks after 5 minutes.
10. Activity resets the 5-minute timer.

### Manual Ixtapa Acceptance — Opening

Verify:

1. No default opening amount appears.
2. Opening denominations are exactly:
   - $1
   - $2
   - $5
   - $10
   - $20
   - $50
   - $100
   - $200
   - $500
   - $1,000
3. Total is calculated from denomination quantities.
4. Manager authorization is required.
5. Opening cannot be completed offline.
6. Second active shift cannot be opened.

### Manual Ixtapa Acceptance — Cash Movements

Verify:

1. IN and OUT movements work.
2. Categories display correctly.
3. Note is mandatory.
4. Manager authorization is mandatory.
5. Movement affects expected cash correctly.
6. Repeating the same idempotency key does not duplicate the effect.
7. Movement cannot be added to CLOSED shift.
8. Movement cannot be created offline.

### Manual Ixtapa Acceptance — Blind Closing

Verify:

1. Closing screen initially shows denomination entry only.
2. Expected cash is hidden.
3. Difference is hidden.
4. Physical count is calculated from denominations.
5. After count submission reconciliation becomes visible.
6. Matching count requires no variance note.
7. Non-zero variance requires explanation.
8. Cashier cannot finalize close.
9. Manager can finalize close.
10. Closed shift cannot be closed again.
11. Closed shift cannot accept normal cash mutations.

### Manual Ixtapa Acceptance — Offline Staff

With an already-open shift:

1. Authenticate employee online once.
2. Disconnect network.
3. Lock POS.
4. Previously authorized employee can unlock.
5. Unknown employee cannot unlock.
6. Plaintext PIN is not visible in browser storage.
7. Refresh does not silently unlock POS.
8. Opening/closing/movements remain unavailable offline.

### Database Integrity Verification

Inspect database state after acceptance tests.

Confirm:

- one active shift maximum
- denomination snapshots persisted
- audit events persisted
- ledger entries match manual movements
- idempotency keys are unique
- CLOSED shifts retain frozen close data
- PIN hashes are not plaintext

### Audit Verification

Confirm events exist for:

- `SHIFT_OPENED`
- `CASH_MOVEMENT`
- `SHIFT_CLOSED`

Each relevant event must identify:

- branch
- terminal
- actor
- authorizer when applicable
- target
- timestamp

### Regression Rule

If any existing test fails:

1. stop
2. determine whether failure is caused by this phase
3. add a regression test when applicable
4. make the smallest fix
5. rerun targeted test
6. rerun full relevant suite

Do not weaken or delete an existing test merely to make the suite pass.

### Final Verification Commands

Before declaring Phase 1 complete:

`git diff --check`

`git status --short`

`git log --oneline --decorate -10`

Run full backend tests.

Run full frontend tests.

Run build.

Run Docker health checks.

Expected:

- no whitespace errors
- only intentional files changed
- tests green
- build green
- containers healthy

If verification itself requires a legitimate regression fix, commit it separately as:

`test(pos): verify Ixtapa cash foundation`

---

# Phase 1 Definition of Done

Phase 1 is complete only when all of the following are true:

- Staff PIN authentication works.
- PIN plaintext is never persisted.
- CASHIER and MANAGER permissions are enforced server-side.
- Administrator authentication remains separate.
- Operational session identifies employee, role, branch and terminal.
- One and only one Ixtapa cash shift may be active.
- Opening cash is counted by denomination.
- No default opening amount exists.
- Opening requires Manager authorization.
- Manual cash movements require Manager authorization.
- Cash movement notes are mandatory.
- Cash ledger effects are idempotent.
- Opening generates `SHIFT_OPENED`.
- Cash movements generate `CASH_MOVEMENT`.
- Closing is blind.
- Expected cash is unavailable before count submission.
- Difference requires explanation.
- Final close requires Manager authorization.
- Closing generates `SHIFT_CLOSED`.
- Closed shifts are immutable through normal application APIs.
- POS can be manually locked.
- POS locks automatically after 5 minutes.
- Locking preserves the active cart.
- Locking preserves the active shift.
- Previously authorized staff can unlock offline during an existing shift.
- Unknown staff cannot unlock offline.
- Offline unlock does not enable sensitive online-only operations.
- Audit events are persisted.
- Existing POS behavior remains functional.
- Existing Kitchen behavior remains functional.
- Existing Bar behavior remains functional.
- Existing Kiosk/self-order behavior remains functional.
- Existing receipt behavior remains functional.
- Alembic has one clean head.
- Backend tests pass.
- Frontend tests pass.
- Build passes.
- Docker health checks pass.
- Manual Ixtapa acceptance passes.

---

# Phase 1 Commit Sequence

Expected implementation commits:

1. `feat(pos): add staff PIN authentication`
2. `feat(pos): add persistent audit log`
3. `feat(pos): add cash shift opening`
4. `feat(pos): add cash movement ledger`
5. `feat(pos): add blind cash closing`
6. `feat(pos): add staff and cash shift UI`
7. Optional only if needed:
   `test(pos): verify Ixtapa cash foundation`

Each commit must leave its own targeted tests green.

---

# Following Plans

After Phase 1 is complete and verified:

## Phase 2

`docs/superpowers/plans/2026-10-14-coficenter-pos-ixtapa-v1-payments.md`

Scope:

- payment lifecycle
- cash payments
- external card payments
- mixed Cash + Card
- tips
- predefined discounts
- Manager-authorized manual discounts
- cash-ledger integration

## Phase 3

Cancellation, refunds and Kitchen/Bar cancellation behavior.

## Phase 4

Finished-product inventory.

Port the useful work from `feature/cofi-pos-inventory` deliberately.

Do not blindly merge that branch.

## Phase 5

Reporting, offline hardening, complete production acceptance and rollout readiness.

---

# Implementation Boundary

This plan implements only:

- Staff
- Cash
- Audit
- POS locking
- Offline employee unlock

It does not implement:

- mixed payments
- Clip
- refunds
- finished-product inventory
- recipes
- ingredients
- CFDI

Those belong to subsequent plans.

