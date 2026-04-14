# Email Notification Diagnosis Progress Tracker

From approved plan - breakdown:

## Completed:
- [x] Step 1: SMTP test script verified, manual run instructions updated in TODO.md

## Pending:
- [ ] Step 2: Check user settings - Run `check_users.py` to list users. Extend to query notification_settings table (enable_email?).
- [ ] Step 3: Add logging to `app/notifications/email_sender.py` (_send_email func).
- [ ] Step 4: Restart server (`uvicorn app.main:app --reload`?).
- [ ] Step 5: Trigger test notification (use test_notifications.py or API).
- [ ] Step 6: Review logs/emails.
- [ ] Step 7: Fix based on results (Gmail app pass, code changes).

**Current action**: Need SMTP test output from manual run.

