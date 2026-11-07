# Decision 099 - API Connection Approach
**Date:** 2026-11-06
**Review by:** 2027-02-04
**Status:** Active
**Classification:** Internal (no Confidential or Secret content)
**Decision:** We connect to the data API using a service account.
**Rationale:** The service account was set up by the infrastructure team. The API key is stored in the ANTHROPIC_API_KEY environment variable and is never written to memory or the repo.
**Alternatives rejected:** Using personal credentials was rejected for security reasons.
