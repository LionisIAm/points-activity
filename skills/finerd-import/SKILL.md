---
name: finerd-import
description: Import or sync a points-activity CSV into Finerd as reward transactions via the Finerd MCP, and record the program's current balance as a verified balance. Use whenever the user wants to push, import, sync, save, or update loyalty points/miles activity INTO Finerd specifically — e.g. "import my Hyatt points into Finerd", "sync my IHG activity to Finerd", "update my Finerd points from this CSV". This is an IMPORTER (the write counterpart to the points-activity extractors, which only produce a CSV). It maps earnings to one accrual transaction per distinct date (split across reward categories) and each redemption to its own expense, and is incremental + non-destructive — re-running adds missing entries and (where possible) updates differing ones in place via update_transaction, but NEVER deletes anything. Requires the Finerd MCP connected.
---
> **Importer · archetype: `api`/`mcp`.** Part of the `points-activity` suite — see
> [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md). It consumes the unified CSV that
> an extractor produced (read it with `scripts/canonical_csv.py`) and writes into
> Finerd. **This is also the reference api/mcp importer**: the dedupe /
> verified-balance / earn→income mapping below are *Finerd patterns*, valid because
> the Finerd MCP exposes those concepts — another app's importer adapts them to its
> own MCP. The one rule every importer keeps regardless: **never delete.**

# Finerd Importer (points CSV → Finerd)

Takes a points-activity CSV (`Date, Description, Amount` + a current balance) and
writes it into Finerd via the **Finerd MCP** reward tools, then records the
current balance as a verified balance. Re-runnable: each accrual is keyed by its
real date, so a re-sync is incremental — new dates get new accruals; existing
ones are left alone unless the user explicitly asks for a rewrite.

Requires the Finerd MCP connected (MCP_READ_WRITE). The CSV comes from the
`points-activity` skill (or a sub-skill like `hyatt-activity`). If the user
hasn't produced one yet, run that first.

## NEVER DELETE — hard rule

**This skill must never call `delete_transaction` (or any other delete tool),
under any circumstances.** Even for "phantom" auto-created records (initial
balance, balance correction, orphans), even when re-syncing, even when an
existing transaction looks wrong. Deletes are destructive and have caused
data loss before — the user has explicitly forbidden them here.

If a delete would otherwise be the natural fix:
- **Existing accrual has wrong lines** → leave it; surface the diff to the
  user and ask whether they want to edit it in-app or have Claude call
  `update_transaction` (which is allowed — it mutates in place, doesn't
  destroy history).
- **Phantom initial-balance / balance-correction txns from the
  set_verified_balance bug** → leave them; report the IDs and the net delta
  to the user so they can decide. Do NOT clean them up automatically.
- **Duplicate or mis-mapped transactions Claude created earlier** → leave
  them; tell the user, propose an `update_transaction` if shape can be
  fixed in place, otherwise ask them to handle in-app.

The only mutation tools this skill may call:
`create_monthly_points_accrual`, `create_reward_redemption`,
`create_transfer`, `create_complex_transaction`,
`create_reward_pnl_transaction`, `update_transaction`,
`set_verified_balance`. **`delete_transaction` is OFF-LIMITS.**

## Model: how a CSV maps to Finerd

A reward account holds a point currency (e.g. `hyt_pts` for World of Hyatt),
not money. Two row kinds:

- **Earnings (Amount > 0)** — the CSV has one row per (real date, item). For
  each distinct date, gather every earning row on that date, map each to a
  reward category, sum rows that map to the same category, and write **one
  accrual transaction per date**: `create_monthly_points_accrual` with
  `lines=[{category_id, amount}, ...]`, `kind="INCOME"`, `date`=that real
  date, `accrual_month`=`YYYY-MM` of that date (for accrual-month reporting).
- **Redemptions (Amount < 0)** — one per booking, real date. Each becomes its
  own expense: `create_reward_redemption`, with the points spent + the cash
  value of the redemption + the merchant (the hotel) + an EXPENSE category
  (`value_category_id`, e.g. Lodging).

Earnings collapse by date (not month), so a busy day with multiple lines lands
as one receipt-style transaction; redemptions stay separate per booking because
each differs by merchant and may later be matched to a money transaction /
receipt.

## Setup (once per program)

1. **Find the reward account.** `list_accounts(search="<program name>")` →
   pick the one with `type: "REWARD"`. Get its point `asset_id` from
   `get_account_balances` (the balance entry's `asset_id` — e.g. `hyt_pts`,
   `alk_mi`, `ap_pts`). The asset_id is a lowercase program-specific token,
   **NOT** the program's display code (`HYT pts`); pass it verbatim everywhere.
2. **If no reward account exists:** `search_merchants(<program name>)`; pick a
   library result whose `reward_asset_ids` is populated. Use the first
   `reward_asset_ids` entry as `asset_id`, the merchant's
   `merchant_classifier_id` to call `create_reward_account`. **Do not recreate**
   an account that already exists — the endpoint is idempotent on (merchant,
   space) and will return the existing one, but if you previously created it
   with a wrong asset_id you'll leave an orphan verified balance behind
   (see Troubleshooting below).
3. **Load the reward categories.** `list_categories(type_filter="REWARD_CATEGORY")`.
   These are the dedicated points buckets the user (or admin) created in-app
   (e.g. "Base Points", "Bonus Points", "Card Spend", "Award Redemption"). Keep
   the id↔name map for the mapping step. If a needed bucket doesn't exist, stop
   and ask the user to create it in-app — there is no create-reward-category
   tool here.
4. **Pick a value EXPENSE category for redemptions** (per Program detection
   below). `list_categories(type_filter="EXPENSE")` and pick by program type:
   - Hotel programs → "Lodging" / "Hotels" / "Accommodation".
   - Airline programs → "Long-Distance Travel" / "Flights" / "Transportation".
   - Transferable currencies → ask per-redemption (mixed use).
   Show the user the candidates if more than one matches the program type.

## Program detection (do this first)

The mapping rules below use *patterns*, but a few defaults branch on
**program type** — hotel vs airline vs transferable-currency. Decide once at
the start of the import:

- **Hotel programs** (World of Hyatt, IHG One Rewards, Marriott Bonvoy,
  Hilton Honors, Accor Live Limitless, Wyndham, Choice, Best Western, etc.):
  redemptions are stays → default `value_category_id` = **Lodging** (or
  "Hotels" / "Accommodation" if the user has it).
- **Airline programs** (United MileagePlus, Aeroplan, American AAdvantage,
  British Airways, Alaska Mileage Plan, ANA, Singapore KrisFlyer, Delta
  SkyMiles, Lufthansa Miles & More, etc.): redemptions are flights →
  default `value_category_id` = **Long-Distance Travel** (or "Flights" /
  "Transportation").
- **Transferable currencies** (Amex Membership Rewards, Chase Ultimate
  Rewards, Capital One miles, Citi ThankYou, BILT Rewards): redemptions
  can be hotels OR flights OR cash-equivalent. **Ask the user per
  redemption** which category fits, or default to Long-Distance Travel
  with a note in the comment.

Identify the program from the CSV filename (`<program>_activity_<from>_<to>.csv`),
the reward account name the user already has, or by asking. If you can't tell,
ask before mapping.

## Mapping rows to categories / merchants

- **Earnings → reward category.** Match each earning *description* to a
  REWARD_CATEGORY by **pattern**, not exact string. The patterns below are
  program-agnostic — substitute brand names as you see them in the CSV:

    | Pattern (description contains…) | Map to |
    |---|---|
    | "Base", "Base Points", "Base Miles", "Flight Award Miles", "Stay Miles" | Base Points |
    | Any credit-card brand (Chase, AmEx, Citi, BILT, Capital One, Bonvoy, IHG One, TD, CIBC, etc.) **or** "Card Spend"/"Spend Bonus" | Card Spend |
    | "Bonus", "%" (e.g. "30% Bonus"), "Promotion", status tier name (Globalist/Discoverist/Explorist/Diamond/Platinum/1K/Premier/Concierge Key/Elite/etc.), "Welcome", "Anniversary", "Milestone", "Accelerate", "Redemption Bonus" | Bonus Points |
    | Partner transfer in / one-off sign-up bonuses (single large round numbers like "Chase 60000", "Welcome Gift 50000") | Bonus Points (flag — ambiguous) |
    | Status-qualifying-only credits (e.g. Aeroplan "Status Qualifying Miles", United "PQP") | **DROP — not spendable** |

  Sum rows that map to the same category on the same date into one line.
  Show the mapping table to the user before writing if any row is ambiguous.
  If the user's REWARD_CATEGORY list lacks a needed bucket (e.g. they don't
  have "Bonus Points" yet), ask them to create it in-app and pause.

- **Redemptions → merchant + value + category.**
  - **Merchant**: for hotels, the description IS the hotel name (e.g.
    "Andaz 5th Avenue", "Grayson Hotel"). For flights, it's usually a route
    or airline operator (e.g. "United LH907 IAD-MUC", "Aeroplan — partner
    award"). `search_merchants(<description>)` returns FUZZY matches — a
    query for "The Anndore House" can return "The Coffee House" — wrong.
    **Use exact case-insensitive name match only**: iterate results, accept
    one whose `name.strip().lower() == query.strip().lower()`. If none, set
    no merchant (better than a wrong one — the user can fix it later).
  - **Cash value (`value_amount` + `value_asset_id`)**: redemptions need the
    cash value of what was redeemed. The points CSV does NOT contain it.
    Resolve in this order:
      1. ask the user for the cash value (preferred — the user often knows
         what the night/flight would have cost), OR
      2. **call `get_asset_rates(asset_ids=[<reward_asset_id>],
         base_asset_id="usd")`** and compute `value_amount = points * rate`.
         This returns whichever provider the user has selected for this
         asset in their space — by default `FINERD_AVERAGE` (aggregated
         across TPG, AwardWallet, NerdWallet, Bankrate, Frequent Miler,
         OneMileAtATime, Upgraded Points), or a user-chosen provider, or a
         CUSTOM user-set rate. Always prefer this over hardcoded "industry
         standard" cpp values — it's the same number Finerd's own UI uses.
      3. (future) match an existing money transaction / receipt on that date.
    Use a money `value_asset_id` (lowercase ISO, e.g. `usd`, `eur`).
    Note in the comment when the value is an estimate (e.g.
    `value~$816 @ 0.017 USD/pt (FINERD_AVERAGE)`).

  - **`value_category_id`** (REQUIRED for sane UX): pass an EXPENSE category
    id chosen by program type (see Program detection above). If omitted, the
    server defaults to "Uncategorized Expense" and every redemption falls
    into the user's "Needs review" inbox.

## Comment / Notes format — purely descriptive

The Finerd transaction's `comment` field is what the user sees as "Notes" in
the UI. It should contain ONLY descriptive content (hotel names, item
descriptions, cash-value notes). No dedupe markers, no metadata — keep it
clean for the user.

**Format:**
```
<item description 1>
<item description 2>
…
```

**Examples:**

Single-item accrual:
```
Hyatt Centric Faneuil Hall Boston
```

Multi-item accrual — one accrual transaction with multiple lines; comment lists
all contributing CSV-row descriptions, ordered by amount descending:
```
Chase - Business Card Spend
Dreams Madeira Resort, Spa & Marina
Double Points Offer
Globalist 30% Bonus
```

Redemption (with cash value note):
```
Andaz 5th Avenue — value ~$2,660 @ 0.019 USD/pt (FINERD_AVERAGE)
```

Partner transfer (Bilt → Hyatt, etc.):
```
Bilt → Hyatt transfer
```

## Dedupe — structural, NOT marker-based

This skill identifies its own transactions by their structural signature on
the Finerd side, not by a sentinel string in the comment. The signature is
unique enough in practice that no marker is needed:

| Kind | Dedupe key |
|---|---|
| Accrual | `(account_id, date, type=INCOME, asset_id, FROM journal hits any REWARD_CATEGORY)` |
| Redemption | `(account_id, date, type=EXPENSE, abs(points_amount), asset_id)` |
| Partner transfer (e.g. Bilt → Hyatt) | `(from_account_id, to_account_id, date, type=TRANSFER, amount, asset_id)` |

### Special case: miles-purchase rows already covered by a USD bank txn

When a CSV earning row is a **miles purchase** (e.g. "POINTS.COM INSTANT
POINTS", "Alaska Miles by Points", "GlobalRewards by Points" — broadly any
row that represents the user PAYING money to acquire miles), the
corresponding USD payment on the user's bank/credit-card statement often
already lives in Finerd, with the reward account itself as the **TO**
account. In Finerd's UI, that USD txn carries a miles-allocation field
attached to its journal — so the miles side of the purchase is ALREADY
represented, even though the MCP's `search_transactions` only surfaces the
USD currency in the journal payload.

**Rule:** before creating an INCOME accrual for such a row, search the
reward account for an EXPENSE transaction:
- with `TO` = this reward account
- with currency = USD (or whatever money currency)
- on or within a few days of the earning row's date
- whose description matches a miles-purchase pattern (e.g. contains
  "POINTS.COM", "Miles by Points", "GlobalRewards by Points", "Buy Miles",
  the loyalty program name + "Purchase")

If found → **skip** the INCOME accrual (it would duplicate the miles the
bank txn already implicitly carries). If not found → create the accrual as
normal.

This applies symmetrically to redemptions: if the user already has a USD
EXPENSE on the reward account that represents the points redemption's cash
side (e.g. taxes/fees on an award booking), our `create_reward_redemption`
will duplicate that USD leg. In that case, prefer to skip our redemption
and create just the points-debit side via
`create_reward_pnl_transaction(kind="EXPENSE")` if needed.

**Caveat:** if you (or another integration) manually create a transaction on
the same date with the same structural shape, the sync will treat it as one
of its own and skip it (since deletes are forbidden, a shape mismatch would
just be flagged to the user, not silently rewritten). Mitigate by keeping
manual transactions in different accounts, or use a different category mix.

## Incremental sync algorithm (the "update my points" loop)

Re-running must not duplicate.

1. **Find what's already recorded.** For the reward account:
   - `search_transactions(account_ids=[reward], page_size=200, hide_internal_transfers=false)`
     → fetch all current transactions on the account.
   - Classify each into accrual / redemption / partner-transfer / other based
     on the structural signature in the table above.
   - Build a map: `date → existing accrual transaction (with its lines)` and
     a set of `(date, abs_points)` for existing redemptions.
   - `list_verified_balances(account)` → last verified date (informational).
2. **Get fresh activity.** Run the relevant `points-activity` sub-skill with
   `from` = the earliest date in the new window you want covered (e.g. the day
   after the last recorded accrual, or a few days back to safely re-pull any
   late-posting items), `to` = today. Honor whatever coverage the skill
   reports.
3. **Write earnings, by date:**
   - Group the new CSV's earning rows by `Date`. For each date, map every row's
     description to a REWARD_CATEGORY and sum rows that map to the same
     category — those summed buckets become the `lines=[…]` of one accrual.
   - Build the `comment` as the descriptive item lines (one per CSV row,
     ordered by amount descending). NO marker.
   - If an existing accrual exists for that date and its `lines` (category +
     amount) match the new ones exactly, skip — nothing to do.
   - If an existing accrual exists for that date but `lines` differ (e.g. more
     activity posted), **do NOT delete it**. Instead, try `update_transaction`
     to amend the lines/comment in place. If `update_transaction` cannot
     reconstruct the desired shape (e.g. number of lines must change in a way
     it doesn't support), report the diff to the user with both the existing
     and the new lines and let them decide whether to edit in-app or accept
     the existing entry as-is. Never delete-and-recreate.
   - If no existing accrual on that date, create one.
   - Always pass `accrual_month="YYYY-MM"` of that date for monthly accrual
     reports.
4. **Write redemptions:** dedupe key is `(date, abs(points))` matched against
   existing EXPENSE transactions on the reward account. For each CSV
   redemption row:
   - Build the comment: `<hotel/merchant name> — value ~$X @ <rate> USD/pt (<provider>)`.
   - If an existing redemption on this account has matching `(date, abs_points)`,
     skip.
   - Else call `create_reward_redemption` with the new comment.
   - Pass `value_category_id` and `merchant_classifier_id` (exact-match only)
     and `value_amount` resolved per the rules above.
5. **Record the current balance as verified.** Use the CSV's reported
   `BALANCE:` value (from points-activity stdout), not a computed sum — if any
   row is missing or mis-mapped, this lets the server auto-correct.
   `set_verified_balance(account, asset_id, balance=<current_balance>, date=<today>)`.
   Idempotent per (account, asset, date) — re-recording replaces. The server
   auto-creates a balance-correction transaction for any delta between the
   verified balance and the computed balance.
   - Report the returned `correction_amount`. **`null` or `0` is healthy.**
     A non-zero correction means the row mapping is incomplete; tell the user
     the delta so they can investigate.
   - **Do NOT clean up auto-created phantoms.** On a fresh REWARD account the
     server may auto-create an initial-balance EXPENSE and an offsetting
     balance-correction INCOME (a known bug — see Troubleshooting). They make
     the visible balance correct but leave two phantom transactions on the
     account. Report them by id to the user (date + amount + journals) and
     let them decide. Do NOT delete them; deletes are forbidden by this
     skill.

## Notes / guardrails

- **asset_id is verbatim** for points (e.g. `hyt_pts`, `alk_mi`) — never
  lowercase or transform it. Money assets (redemption `value_asset_id`,
  cash co-pay `other_asset_id`) stay lowercase ISO (`usd`, `eur`, `uah`).
- All point/value amounts sent to the tools are **positive magnitudes**;
  direction comes from the tool/kind (INCOME vs EXPENSE / redemption).
- **Point transfers between programs** (e.g. Bilt → Alaska shows as an expense
  on one side and income on the other) are NOT yet special-cased — for now
  they land as an earning line on the receiving program and (separately) an
  expense on the sending one. Flag to the user rather than inventing a
  cross-program transfer.
- **Confirm the category mapping** and any estimated redemption values with the
  user before writing a large backfill. Show a brief table.
- **No SQL, no DB, no UI clicks** — every read and write goes through the
  Finerd MCP tools (`list_*`, `search_*`, `create_*`, `update_*`,
  `set_verified_balance`). **`delete_transaction` is NOT in this list** — it
  is explicitly forbidden (see "NEVER DELETE" at the top).

## Changing the user's cpp / valuation

The user may say things like "set my Hyatt cpp to 1.9", "use The Points Guy's
valuation for IHG", or "what providers do you have for Aeroplan?". Handle:

- **Show options**: `list_asset_rate_providers(asset_id=<asset>)` returns
  every provider, their rate, and which is currently `selected`. Show the
  user the list with the rate in cpp (rate × 100) for clarity.
- **Pick an existing provider**:
  `set_asset_rate_preference(asset_id=<asset>, provider="<PROVIDER>")` —
  one of THE_POINTS_GUY, AWARD_WALLET, NERD_WALLET, BANK_RATE,
  FREQUENT_MILER, ONE_MILE_AT_A_TIME, UPGRADED_POINTS, FINERD_AVERAGE.
- **Set a custom rate**: `set_asset_rate_preference(asset_id=<asset>,
  provider="CUSTOM", custom_rate_usd_per_point=<rate>)`. The rate is USD
  per 1 point. **Always confirm the unit with the user** — "1.9 cpp" means
  `0.019`, "1.9 USD/pt" means `1.9` (insanely high). When the user gives a
  number without units, default to interpreting it as cpp and confirm.
- After changing, future `get_asset_rates` calls and redemption value
  estimates use the new selection automatically.

## Where does the asset_id come from? (discovery chain)

A new session has no clue that "Hyatt" = `hyt_pts`. It learns at runtime via
MCP, in this order:

1. **From the existing reward account's balance.** If the account exists,
   `get_account_balances(search="<program name>")` returns balance entries
   with `asset_id` populated (e.g. `"hyt_pts"`). Take that — done.
2. **From the library merchant's `reward_asset_ids`.** If the account doesn't
   exist yet, `search_merchants("<program name>")` returns merchants with a
   `reward_asset_ids: ["hyt_pts"]` array. Use `reward_asset_ids[0]`.
3. **Fallback when both above are empty** (rare — clean env where admins
   haven't seeded `rewardDetails` on the library merchant yet): the asset
   may still exist in `asset-service`. The MCP doesn't surface this yet,
   but the underlying HTTP endpoint is
   `GET /asset-service/public/v1/assets?asset-types=REWARD&search=<prefix>`
   (note: prefix-match on code OR name — for Hyatt search "world" because
   asset name is "World of Hyatt", or just "HYT" for the code). If even
   that returns nothing, **ask the user** for the asset id — don't guess.

Never hardcode asset ids per program in the workflow. Always read from MCP.

## Troubleshooting

- **`list_verified_balances` returns 500 "Failed to get asset by id: <X>"**:
  there is an orphan verified-balance record whose asset_id can't be resolved
  by asset-service (typically from a prior reward-account create attempt with
  the wrong asset_id). **This skill cannot clean it up — deletes are
  forbidden.** Report the situation to the user and let them remove the
  orphan in-app or via DB themselves. Prevention: discover the existing
  reward account first, don't recreate, and always use the asset_id from
  `reward_asset_ids` exactly.
- **Phantom initial-balance + balance-correction pair on a fresh REWARD
  account** (known bug — `set_verified_balance` auto-creates a bogus
  initial-balance EXPENSE plus an offsetting balance-correction INCOME):
  the visible balance ends up correct, but two phantom transactions sit on
  the account. **Leave them alone** — don't try to delete. Report their ids
  and amounts to the user so they can clean up in-app if they want.
- **Multi-line accrual fails with `Double entry validation fails. [Amounts
  not matching: X.YZ, X.YZK]`**: rounding drift in primaryAmount split. This
  is fixed in the MCP tool (it reconciles tx.primaryAmount with the
  sum-of-shares post-rounding). If it ever recurs, the MCP tool needs the
  same reconciliation re-applied.
- **Accruals don't render green / with `+` in the FE**: the MCP tool overrides
  `sourceJournalType=TO` for INCOME accruals to match how finerd-web derives
  the displayed movement (it ignores the server's `movementType` and reads
  `sourceJournalType` directly: FROM → EXPENSE, TO → INCOME). If you see
  income accruals in plain/red, the override didn't apply — check the tool.
- **Redemptions all end up in "Uncategorized Expense"**: caller didn't pass
  `value_category_id`. Pass the program-appropriate EXPENSE category id
  (Lodging for hotel programs, Long-Distance Travel for airlines).
- **`merchant` on a redemption is wrong (e.g. "The Coffee House" instead of
  "The Anndore House")**: `search_merchants` is fuzzy; match exact name only.
  Better to leave merchant unset than to attach the wrong one.
