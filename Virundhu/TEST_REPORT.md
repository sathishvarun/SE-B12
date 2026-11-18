# Virundhu - what's built and how it was tested

Run on 16 Nov 2026. Automated: 65 backend tests (pytest, real PostgreSQL + Redis) and 1 browser test (Playwright).
Frontend: ESLint and TypeScript strict checks pass.

## 1. What is built and what isn't

| Feature | Status | How it works |
|---|---|---|
| Admin console (all restaurants, plans, trials, reviews per platform, money collected, AI cost) | Built | Admin login only |
| Owner sign-up (email or Google), 14-day trial, read-only after trial | Built | |
| Review intake: paste one review, upload CSV/Excel | Built | Owner does it |
| Google reviews in, every 10 minutes | Built | Needs Google's Business Profile API approval |
| Reply posted to Google in one click | Built | Same approval |
| AI reads every review (English, Tamil, Tanglish): feeling, topic, urgency, summary, reply draft | Built | OpenAI `gpt-4.1-mini` |
| Food-safety safety net (works even if the AI fails) | Built | Keyword rules can only raise urgency |
| Retry reviews the AI couldn't read | Built | Every 5 minutes, for 7 days |
| Instant alerts (bell + email) | Built | Email needs SMTP settings, otherwise logged |
| Dashboard, trends per outlet | Built | |
| Ask Virundhu chat (Priority 1, 2, 3) | Built | |
| Plan and billing with Dodo Payments + FIRST10 code | Built | Test mode |
| Zomato/Swiggy: "Copy reply and open Zomato/Swiggy" | Built | Copies the reply and opens the partner site in a new tab; the owner pastes |
| Zomato/Swiggy reviews in automatically | **Not possible** | No public API. Owner pastes/uploads |
| Zomato/Swiggy reply posted automatically | **Not possible** | No public API |
| Google auto-pilot (auto-reply to happy Google reviews) | Built | Automation page; posting needs Google approval |
| QR feedback link on bill/packaging | Built | Automation page → Download QR. Guests can use it once the site is on your domain |
| WhatsApp alerts | Built, off | Turns on when a WhatsApp Business (Meta Cloud API) token is added |
| Deploy to VPS, push to GitHub | **Not done** | Waiting for owner approval |

## 2. How "one click to Zomato/Swiggy" works

There is no connection to Zomato or Swiggy. The button does two things in the browser:

1. Copies the reply text (as edited by the owner) to the clipboard.
2. Opens `https://www.zomato.com/partners` or `https://partner.swiggy.com` in a new tab.

The owner finds the review in their partner dashboard, pastes (Cmd+V) and sends, then clicks **Mark as replied** in
Virundhu. The partner site uses the owner's own login; Virundhu never sees or stores it.

## 3. Test results

### Automated backend tests (65 of 65 passed)

| Area | Test | What it proves | Result |
|---|---|---|---|
| Foundation | health_reports_database_and_redis | API, database and Redis are up | Pass |
| | public_config_has_no_secrets | No key is ever sent to the browser | Pass |
| | password_hashing_roundtrip | Passwords are stored hashed | Pass |
| | access_token_roundtrip_and_type_check | Login tokens can't be swapped or forged | Pass |
| | opaque_token_only_hash_is_stored | Refresh tokens stored only as hashes | Pass |
| | all_tables_registered | Every database table exists | Pass |
| Sign-in | admin_login_and_profile | Admin can sign in | Pass |
| | wrong_password_gives_clear_message | Clear error, no hint which part was wrong | Pass |
| | protected_routes_need_sign_in | Nothing is visible without signing in | Pass |
| | register_refresh_and_isolation | A new restaurant sees only its own data | Pass |
| Roles | admin_is_not_inside_a_restaurant | Admin lands in the Admin console only | Pass |
| | admin_panel_is_admin_only_and_can_open_any_restaurant | Owners can't open the admin console; admin can open any restaurant | Pass |
| | trial_end_makes_account_read_only | Expired trial can look but not change | Pass |
| | outlet_manager_sees_only_their_outlet | Outlet-level access (kept in the backend) | Pass |
| Pricing | pricing_rules | Outlet tiers, 1/3/6/9/12-month discounts and free months; refuses 0 or 501 outlets and 2 months | Pass |
| | public_quote_endpoint | The website calculator gets the same price as the server | Pass |
| | underpaid_payment_is_refused | A payment below the price never activates a plan | Pass |
| Chains | outlet_details_and_own_qr_link | Outlet address/district/manager saved; each outlet has its own QR link; bad pincode refused | Pass |
| | upload_creates_outlets_named_in_the_file | Branch names in an uploaded file become outlets | Pass |
| Automation | three_star_autoreply_and_holding_reply | 3★ auto-reply; safe holding reply only after the chosen hours, with the phone, no refund promise | Pass |
| Growth | outlets_from_a_file | Branches uploaded from CSV; same name updates; bad pincode row skipped | Pass |
| | phone_numbers_are_cleaned | Indian mobiles normalised; landlines and junk refused | Pass |
| | review_requests_give_links_and_never_ask_twice | Consent required; wa.me links; masked numbers; 30-day cooldown | Pass |
| | weekly_summary_names_the_outlet_to_fix_first | District/outlet lines, unhappy count, "Start with ..." | Pass |
| | reviews_from_a_screenshot | Reviews added from a screenshot; repeats skipped; non-images refused | Pass |
| | launch_checklist_for_admin_only | Launch checklist flags localhost; owners can't open it | Pass |
| Extras | billing_software_hook | Wrong key refused; off by default; needs WhatsApp; sends once, then skips | Pass |
| | nearby_competitors | Off without a key; your rating vs nearby and the area average; cached for a day | Pass |
| | testimonials_only_published_and_admin_only | Only published show publicly; only the admin can add | Pass |
| | tripadvisor_and_instagram_reviews | Tripadvisor, Instagram and Facebook reviews accepted | Pass |
| Admin | admin_sees_activity | Sign-up, password change and account deletion show in the admin Activity log and bell; owners can't see it | Pass |
| Reviews | upload_reads_reviews_and_fires_instant_alert | Upload → read → urgent alert created | Pass |
| | bad_file_gives_clear_message | Wrong file gives a plain-English error | Pass |
| | single_review_and_connections | Paste one review; the old fake test feed no longer exists | Pass |
| | live_try_uses_safety_net | Food-safety words always become urgent | Pass |
| | dashboard_numbers_match_database | Dashboard counts equal the database | Pass |
| Google | google_sync_imports_live_reviews | Google reviews come in and map to outlets (Google mocked) | Pass |
| | google_access_not_approved_is_explained | Clear message while Google approval is pending | Pass |
| Ask Virundhu | empty_restaurant_gets_a_plain_answer | No reviews → tells the owner what to do | Pass |
| | priorities_use_computed_data | Counts come from the database, not the AI (AI mocked) | Pass |
| | another_restaurant_never_leaks | One restaurant's reviews never reach another's chat | Pass |
| Payments | dodo_checkout_and_confirm | Server picks the product; plan turns on only after Dodo says "succeeded"; another restaurant's payment is refused (Dodo mocked) | Pass |
| | pay_monthly_and_plan_turns_on | Razorpay path: amount set by server, fake signature refused, same payment counted once | Pass |
| | webhook_activates_and_ignores_repeats | Forged webhook refused; repeat webhook ignored | Pass |
| | expired_paid_plan_is_read_only_but_billing_still_opens | Expired plan blocks changes; billing page still works | Pass |
| | payments_off_without_keys | Clear message when payment keys are missing | Pass |
| Automation | settings_turn_on_autopilot_and_give_feedback_link | Owner can switch auto-pilot on, gets a feedback link; bad WhatsApp numbers refused | Pass |
| | autopilot_replies_only_to_happy_google_reviews | 5★ happy review replied; 2★ angry and 4★ hygiene left for the owner; switched off = nothing posted (Google mocked) | Pass |
| | autopilot_failure_leaves_review_for_owner | If Google fails, the review stays unreplied for the owner | Pass |
| | qr_feedback_link_creates_a_direct_review | Guest page works without sign-in; low rating needs a comment; every guest gets the Google invite; bot field ignored; wrong link = 404 | Pass |
| | whatsapp_alert_sent_once_per_number | Urgent review → one WhatsApp per number, never twice (Meta mocked) | Pass |
| | no_whatsapp_without_keys | Nothing is sent until WhatsApp is set up | Pass |
| Website | contact_form_creates_a_lead_admin_can_see | Contact form needs a phone or email, saves a lead, only the admin can see and update it | Pass |
| Account | signup_needs_consent_and_records_it | No account without ticking Terms + Privacy; time saved | Pass |
| | forgot_and_reset_password | Same answer for real and unknown emails; link single-use; old password and old sessions stop working | Pass |
| | change_password | Wrong current password refused; change works | Pass |
| | export_and_delete_everything | CSV has the reviews (Tamil included); delete needs the exact name + password; then the restaurant, reviews and login are gone | Pass |
| | security_headers | nosniff, no framing, no caching on API answers | Pass |
| Other | demo_is_read_only, one_click_demo, team_invite_and_accept | Older features kept in the backend | Pass |

### Browser test: Zomato/Swiggy button (Playwright)

| Step | Zomato | Swiggy |
|---|---|---|
| Owner opens a 2-star review in the Inbox and edits the reply | Done | Done |
| Clicks "Copy reply and open ..." | New tab opened at zomato.com/partners | New tab opened at partner.swiggy.com |
| Clipboard contains exactly the edited reply | Yes | Yes |

### Checked in a browser (desktop and mobile)
Sign-up blocked until Terms + Privacy are ticked; Settings → Account and privacy (change password, download, delete);
Privacy, Security pages; footer with Trust links and contact details.
Public website: all 5 pages at 1440px and 375px wide with no sideways scrolling; before/after toggle, the six-step
review story, the calculator, the mobile menu and the contact form (thank-you shown) all work.
Admin console, owner dashboard, alerts list on top of the page, Plan and billing, Ask Virundhu, Automation page with the
QR code. Guest QR page on a phone-size screen: rated 2 stars with a comment, saw the thank-you and the Google invite, and
the review appeared in the owner's Inbox as "QR feedback" with the guest's name and phone.

### Not tested yet (needs your Mac or real accounts)
| What | Why not | How to test |
|---|---|---|
| Real AI answers (OpenAI) | No key in the build workspace | Upload `samples/virundhu_sample_reviews.xlsx`, wait a minute, check the Inbox and Ask Virundhu |
| Real Dodo payment | Dodo isn't reachable from the build workspace | Pay with card 4242 4242 4242 4242 or UPI success@upi |
| Real Google sync and reply | Needs Google's API approval | After approval: Connections → Connect Google |
| Real email alerts | No SMTP set | Add a Gmail app password in `.env` |
| Real auto-pilot posting | Needs Google approval | After approval, turn auto-pilot on and wait for a happy Google review |
| Real WhatsApp message | Needs a Meta WhatsApp Business account | GETTING_STARTED.md Part 7 |
| QR code scanned from a guest's phone | `localhost` only works on your Mac | After deploying, the QR points to your domain |

## 4. How to run the tests yourself

```bash
cd "/Users/sathishvarun/Downloads/SE-B12/Offline Session Task/Virundhu/backend"
source .venv/bin/activate
SEED_DEMO_RESTAURANT=true python -m app.seed   # test data
pytest -v
python -m app.seed                              # removes the test data again
```


## Browser and mobile check (17 Nov 2026)

`tools/qa/browser_sweep.py` opens 25 pages (website, sign-in, QR feedback page, every owner page, admin console) on a desktop
(1440 px), an iPhone (390 px) and an Android phone (360 px), scrolls each page so every animation runs, and records console errors
and warnings, failed network requests, HTTP errors, sideways scrolling and text left invisible.

| Check | Result (75 page views) |
|---|---|
| Console errors or warnings | 0 |
| Failed requests / HTTP errors | 0 |
| Sideways scrolling on phones | 0 |
| Text hidden after animations | 0 |
| Retention clean-up test | Pass |

| Password not visible in the page's HTML (all password boxes) | Pass |
| Trial reminders at 5/4/2/1 days and a suspension email when ended, once each, not at night | Pass (test) |
| Admin Excel download, test-account clean-up (real accounts protected) | Pass (test + browser) |
| Test runs leave no data behind | Pass |
| Session token in an HttpOnly cookie; nothing secret in browser storage; session survives reload; sign-out clears it | Pass (browser) |
| 5 wrong passwords lock the email; weak and name-based passwords refused | Pass (test) |
| Every new trial is exactly 14 days; no way to extend | Pass (test) |
| Revenue dashboard numbers after a payment (total, month, renewals due, latest payments) | Pass (test) |
| npm audit / pip-audit | 0 known vulnerabilities |
