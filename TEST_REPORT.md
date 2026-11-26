# Test Report — DeepGuard AI

## Test Execution Summary

| Metric | Value |
|---|---|
| **Date** | 2026-11-26 |
| **Total Tests** | 77 |
| **Passed** | 77 |
| **Failed** | 0 |
| **Pass Rate** | 100% |
| **Test Isolation** | Temporary directory (`tempfile.TemporaryDirectory`) for SQLite DB, uploads, and frames |
| **Test File** | `tests.py` |

## Test Phases and Results

### Phase 1: Database Tests (15 tests) — ✅ All Passed
| Test | Status |
|---|---|
| Users table exists | ✅ |
| Scans table exists | ✅ |
| Contact_messages table exists | ✅ |
| Create user returns ID | ✅ |
| Get user by ID | ✅ |
| User data correct | ✅ |
| Get user by username | ✅ |
| Get user by email | ✅ |
| Non-existent user returns None | ✅ |
| Save contact message | ✅ |
| Create scan returns ID | ✅ |
| Get scan by ID and user | ✅ |
| Scan data correct | ✅ |
| Scan not returned for wrong user | ✅ |
| Get scans for user | ✅ |

### Phase 2: Route & Page Tests (11 tests) — ✅ All Passed
| Test | Status |
|---|---|
| Home page returns 200 | ✅ |
| Home page has content | ✅ |
| Login page returns 200 | ✅ |
| Login page has form | ✅ |
| Signup page returns 200 | ✅ |
| Signup page has form | ✅ |
| Contact page returns 200 | ✅ |
| Contact page has form | ✅ |
| 404 returns correct status | ✅ |
| 404 has error page content | ✅ |
| Upload redirects to login when unauthenticated | ✅ |

### Phase 3: Authentication Tests (13 tests) — ✅ All Passed
| Test | Status |
|---|---|
| Signup success | ✅ |
| Signup rejects empty username | ✅ |
| Signup rejects short password | ✅ |
| Signup rejects invalid phone | ✅ |
| Signup rejects invalid email | ✅ |
| Signup rejects duplicate username | ✅ |
| Login success | ✅ |
| Upload page accessible when logged in | ✅ |
| Upload page has upload form | ✅ |
| Upload rejects no file | ✅ |
| Logout works | ✅ |
| Login rejects wrong password | ✅ |
| Login rejects empty fields | ✅ |

### Phase 4: Contact Form Tests (3 tests) — ✅ All Passed
| Test | Status |
|---|---|
| Contact form submission success | ✅ |
| Contact form rejects empty name | ✅ |
| Contact form rejects invalid email | ✅ |

### Phase 5: Security Tests (5 tests) — ✅ All Passed
| Test | Status |
|---|---|
| SESSION_COOKIE_HTTPONLY enabled | ✅ |
| SESSION_COOKIE_SAMESITE set | ✅ |
| MAX_CONTENT_LENGTH set | ✅ |
| Result page requires auth | ✅ |
| Upload page requires auth | ✅ |

### Phase 6: Detector Module Tests (5 tests) — ✅ All Passed
| Test | Status |
|---|---|
| Face cascade loads successfully | ✅ |
| Laplacian variance computed | ✅ |
| HF ratio computed | ✅ |
| Forensics with face box works | ✅ |
| No Keras model loaded (expected) | ✅ |

### Phase 7: File Structure Tests (11 tests) — ✅ All Passed
| Test | Status |
|---|---|
| app.py exists | ✅ |
| database.py exists | ✅ |
| detector.py exists | ✅ |
| requirements.txt exists | ✅ |
| .env.example exists | ✅ |
| templates/base.html exists | ✅ |
| templates/error.html exists | ✅ |
| static/uploads dir exists | ✅ |
| static/frames dir exists | ✅ |
| static/css/style.css exists | ✅ |
| static/js/main.js exists | ✅ |

## How to Run Tests

```bash
python tests.py
```

Expected output: `RESULTS: 77 passed, 0 failed`
