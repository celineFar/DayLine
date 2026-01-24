
# Sleep Considerations
- [x] User accidentally presses the same button again
  - [x] Pressing Sleep twice may overwrite the original start time or create duplicate records
  - [x] Pressing Wake Up twice may end the session prematurely or create multiple wake events
- [X] User forgets to press Wake Up
- [x] User presses Wake Up without recording Sleep first
- [x] User records sleep or wake up at the wrong time (manual error)


### Notes
- Reminder shouldn't buzz when we there's already record sleep
- User input error handling
- Reminder should have record wake up now
- Remove settings file from git history
- the back in each menu is only back to home
---

# 💤 Sleep / Wake Tracking – To-Do List

## 🔥 Critical (Do First)

* [X] **Cancel reminder jobs properly**

  * Cancel existing `sleep_reminder_job` before scheduling a new one
  * Cancel reminder job inside `cleanup_sleep_state`
  * Prevent “ghost” reminders after sleep ends

* [X] **Validate time ordering**

  * Reject wake times `<= sleep_start_dt`
  * Decide policy for same-day vs next-day wake times
  * Ensure duration-based end produces `end_dt > start_dt`

* [ ] **Prevent overlapping sleep sessions**

  * Block new sleep start if an active session exists
  * Validate manual start/end against existing records
  * Enforce constraints inside `sleep_service.record_sleep_end`

* [ ] **Handle invalid user input safely**

  * Wrap `datetime.strptime`, `float()`, and range parsing in try/except
  * Show user-friendly error messages
  * Re-prompt instead of silently failing or crashing

---

## ⚠️ High Priority

* [ ] **Clear conflicting state flags**

  * Reset all `awaiting_*` flags before setting a new one
  * Ensure only one input mode is active at a time

* [ ] **Guard against double-tap / duplicate actions**

  * Make `sleep_start_now` idempotent
  * Make `confirm_overwrite` idempotent
  * Ignore repeated callbacks once state is resolved

* [ ] **Validate manual sleep start times**

  * Prevent sleep start far in the future
  * Optionally allow small future grace window (e.g. +15 min)

* [ ] **Validate sleep duration input**

  * Reject negative or zero values
  * Cap maximum duration (e.g. 16–24h)
  * Handle non-numeric input

---

## 🧠 Medium Priority

* [ ] **Fix reminder logic**

  * Ensure reminder delay matches message text (“10 hours ago”)
  * Prevent reminder if sleep already ended
  * Handle bot restart with dangling sleep sessions

* [ ] **Improve pending action handling**

  * Prevent `pending_action` from being silently overwritten
  * Clear pending actions on navigation or cancel

* [ ] **Harden custom preview ranges**

  * Support alternative formats (`-`, `→`, etc.)
  * Validate date parsing and ordering
  * Handle malformed input gracefully

---

## 🌍 Time & Locale Improvements

* [ ] **Introduce timezone awareness**

  * Store all timestamps in UTC
  * Convert to user timezone for display
  * Handle DST transitions safely

* [ ] **Avoid naive `datetime.now()`**

  * Use timezone-aware `now()`
  * Centralize “current time” helper

---

## 🧩 UX / Feature Gaps

* [ ] **Add explicit “Cancel sleep session” action**

  * Allow user to discard accidental sleep start
  * Cancel reminder and reset state cleanly

* [ ] **Add confirmation for manual entries**

  * Show parsed time and ask user to confirm
  * Reduce accidental wrong inputs

* [ ] **Improve error messaging**

  * Explain *why* input was rejected
  * Suggest correct formats and examples

---

## 🧪 Testing & Reliability

* [ ] **Add tests for edge cases**

  * Wake before sleep
  * Overlapping sessions
  * Double-tap callbacks
  * Invalid date / duration input

* [ ] **Test bot restart behavior**

  * Active sleep session survives restart
  * Reminder jobs rehydrated or safely skipped

---

## 🧱 Optional Refactors

* [ ] **Refactor to explicit state machine**

  * Single `state.mode` instead of multiple booleans
  * Enforce valid transitions only

* [ ] **Persist sleep session state**

  * Store active sleep session in DB
  * Reconstruct state on bot startup

---

If you want, I can next:

* Turn this into **GitHub issues**
* Break it into **PR-sized tasks**
* Provide **code snippets** for each critical fix
* Or design a **proper finite state machine**

