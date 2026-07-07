# User Manual

## Creating an account

Go to `/register`, enter your name, email, and a password (at least 8
characters). You'll be signed in automatically after registering.

## Uploading data

1. Go to **Upload** in the sidebar.
2. (Optional) Give the batch a name, like "March Payroll Import".
3. Drag files onto the dropzone, or click it to browse. You can add
   multiple CSV/Excel/JSON/TXT files to one upload.
4. Click **Upload**. You'll see a progress bar, then a summary showing
   how many records were processed, how many duplicates were found, and
   how many are unique.

## Reviewing duplicates

Click **Review** next to any file with duplicates found (or navigate
there from the upload summary). Each duplicate finding shows:

- Which row in your new file matched an existing record
- Which field triggered the match (name, email, address, etc.)
- Which algorithm found it (exact match, Levenshtein, phonetic, etc.) and
  its confidence score

For each one, choose an action:

| Action | What it does |
|---|---|
| **Merge** | Combines the two records, keeping whichever has more complete data |
| **Replace** | Your new record overwrites the existing one |
| **Keep latest** | Keeps whichever record is more recent |
| **Keep oldest** | Keeps whichever record is older |
| **Ignore** | Leaves both records as-is (useful if the algorithm was wrong) |
| **Delete** | Discards the new (duplicate) record |

Click **Auto-resolve high confidence** to automatically resolve every
duplicate the system is highly confident about (95%+ match), leaving only
the ambiguous ones for you to review by hand.

## Understanding the dashboard

- **Uploaded Files / Total Records / Duplicates Found / Unique Records**:
  running totals across everything you've ever uploaded.
- **Storage Saved**: an estimate of disk space you avoided using by not
  storing duplicate records.
- **Duplicates by Detection Method**: which algorithms are catching the
  most duplicates in your data — useful for understanding what kind of
  "messiness" your data tends to have (typos vs. exact re-uploads vs.
  differently-spelled names).
- **Recent Uploads**: your upload history at a glance.

## Managing your account

- **Profile**: update your name from the profile page.
- **Change password**: requires your current password.
- **Forgot password**: requests a reset link (in this local/demo setup, no
  email server is configured — see `Docs/deployment_guide.md` for wiring
  up real email sending).
- **Log out**: revokes your current session token immediately.
