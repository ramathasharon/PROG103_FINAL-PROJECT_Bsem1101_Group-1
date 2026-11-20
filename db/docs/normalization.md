# Normalization of the Permit database (up to 3NF)

Normalization means arranging data so that each fact is stored **once**.
Think of a school timetable pinned on a wall: if the teacher's phone number
is written next to every lesson and the number changes, you must fix it in
twenty places and will probably miss one. Normalization puts the phone number
in one place and lets every lesson point to it.

## Step 0: the un-normalized table (what a paper form looks like)

`PERMIT_FORM`

| permit_id | applicant_id | applicant_name | phone | district | region | kind | type_name | base_fee | validity_years | details | status | office_name | office_kinds | date_applied | issue_date | expiry_date |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PRM-001 | APP-001 | Aminata Kamara | +232 76 123456 | Western Area Urban | Western Area | business | Business License | 500 | 1 | Kamara General Stores | Approved | Business Licensing Unit | business | ... | ... | ... |
| PRM-008 | APP-005 | Mariama Jalloh | +232 76 567890 | Port Loko | North West | building | Building Permit | 1500 | 3 | Guest house extension | Approved | Building Control Unit | building | ... | ... | ... |

Problems: the fee and validity of a permit type are repeated on every row; the
applicant's name and phone are repeated for every permit they file; the region is
repeated for every applicant in a district; `office_kinds` can hold a list.
Changing a fee, or fixing a phone number, means editing many rows (**update
anomaly**); deleting the last permit of a type also deletes the fee information
(**deletion anomaly**).

## First Normal Form (1NF): atomic values, no repeating groups

Rule: every column holds one value, and there are no lists or repeating groups.

* `office_kinds` could hold a list such as `business, general`. We replace it by
  one row per (office, kind) pair. (Our first prototype used a PostgreSQL array
  `TEXT[]` for this; arrays are not atomic, so we moved to a proper table.)
* All other columns already hold single values (name, phone, one date, and so on).

Result: the pair `(office_name, kind)` becomes its own table.

## Second Normal Form (2NF): no partial dependency on part of a composite key

Rule: in a table with a composite key, every non-key column must depend on the
**whole** key.

After 1NF the office/kind pairs have the composite key `(office_name, kind)`.
That table contains **only** the two key columns, so nothing depends on just
part of the key: it is in 2NF. The `permits` table has the single-column key
`permit_id`, so it is automatically in 2NF.

Result: `office_permit_types(office_name, kind)` with a composite primary key,
and `permits` with primary key `permit_id`.

## Third Normal Form (3NF): no transitive dependency

Rule: a non-key column must depend on the key and **nothing but the key**
(not on another non-key column).

| Transitive dependency found in `permits` | Fix |
|---|---|
| `permit_id -> applicant_id -> full_name, phone, district` | table `applicants` |
| `applicant_id -> district -> region` | table `districts` |
| `permit_id -> kind -> type_name, details_label, base_fee, validity_years` | table `permit_types` |
| `permit_id -> office_name` (an office is described by its name only) | table `offices` |

Every table now has a primary key, and every other column describes that key.

## Final tables

| Table | Primary key | Foreign keys |
|---|---|---|
| `districts` | `district_name` | none |
| `permit_types` | `kind` | none |
| `offices` | `name` | none |
| `office_permit_types` | `(office_name, kind)` | `office_name`, `kind` |
| `applicants` | `applicant_id` | `district` |
| `permits` | `permit_id` | `applicant_id`, `kind`, `office_name` |
| `permit_history` | `history_id` | `permit_id` |

## Deliberate decisions

* `permits.status` stays a column with a CHECK constraint (five fixed values)
  instead of its own table, because the status list is part of the program's
  workflow and is enforced by a trigger as well.
* `permits.issue_date` and `expiry_date` are stored (not calculated every time)
  because the **fee and validity rules may change later**: a permit approved
  under last year's rules must keep its original expiry date.
* No national ID number, address or photo is stored anywhere (DPG data
  minimisation).
