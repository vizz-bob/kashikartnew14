# Implementation Plan Progress - Keyword Sync & 20min Timer

**Status:** Approved ✅ In Progress

**Steps:**
- [ ] 1. Fix asyncio import in source_service.py (NameError fix)
- [ ] 2. Update scheduler.py tender_sync_job to 20min interval
- [ ] 3. Add keyword filter logic in source_service.py fetch_from_source (filter tenders by active admin keywords)
- [ ] 4. Update dashboard.py sync endpoint nextSyncIn calculation for 20min
- [ ] 5. Restart backend servers
- [ ] 6. Test: Add keywords, verify filtered fetching, 20min timer on dashboard
- [ ] 7. Verify auto-sync no errors, frontend countdown shows ~20min

**Current Issues Fixed:** Backend port sync, login, dashboard loads.

**Next:** Complete step 1-2 edits → restart → test → step 3-4.
