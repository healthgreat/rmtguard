# Manual Author Execution Steps

Last updated: 2026-05-04.

This checklist separates author-owned actions from Codex-owned local work. It is intentionally conservative: no manuscript or software release should be described as submission-ready until the blocking rows below are resolved.

## Current Author-Provided Information

The following fields have been recorded in `metadata/author_metadata.tsv`, `CITATION.cff`, and `.zenodo.json`:

- Authors currently listed: Chongfa Chen, MD; Han Yan, MD, PhD; Yi Miao, MD, PhD.
- Affiliation: Pancreas Center, The Affiliated BenQ Hospital of Nanjing Medical University, Nanjing, China.
- Corresponding author 1: Yi Miao, MD, PhD, FACS, FRCS, FICS(Hon); `miaoyi@njmu.edu.cn`; ORCID `https://orcid.org/0000-0003-2542-8663`.
- Corresponding author 2: Han Yan, MD, PhD; `carrick8862@163.com`; ORCID `https://orcid.org/0000-0002-2041-3115`.
- Corresponding author order is confirmed as Yi Miao first, Han Yan second.
- Chongfa Chen ORCID remains unverified. Two name-matched public ORCID records exist, but neither has public employment or works to confirm identity.
- Postal code remains unresolved: author provided `350000`, but public sources for the same hospital/street address list `210019`.

## Remaining Manual Items

### 1. Confirm The Resolved Feihu Sun Authorship Boundary

Current decision: Feihu Sun is not an author on this manuscript.

Codex has removed the equal-contribution footnote from the active RMTGuard metadata. Before submission, verify that the manuscript title page, cover letter, CRediT contribution form, `CITATION.cff`, `.zenodo.json`, and journal submission system all use only the three-author list:

- Chongfa Chen, MD
- Han Yan, MD, PhD
- Yi Miao, MD, PhD

Do not include any equal-contribution sentence naming Feihu Sun.

### 2. Confirm Final Author Metadata

Send Codex the following final confirmations:

- Final author order.
- Chongfa Chen ORCID ownership, or explicit confirmation that no ORCID should be used.
- Final postal code: `350000` or `210019`.
- Approval or correction of `metadata/credit_roles.tsv`.
- Funding statement: exact grant details, or explicit confirmation of no specific funding.
- Competing interests statement: confirm `The authors declare no competing interests.` or provide disclosures.
- Ethics / public-data statement: confirm the project remains public-data-only with no private clinical data.

### 3. Public GitHub Repository

Completed: the public GitHub repository exists at `https://github.com/healthgreat/rmtguard`.

Still pending: code push, GitHub Release, Zenodo archive, and DOI verification. Codex should not push until the source-only release audit and intentional commit/tag scope are checked.

### 4. Complete The External Software Archive Step

After Codex pushes the release candidate and tag:

1. Open the GitHub repository Releases page.
2. Create a release from the approved version tag.
3. Connect or use Zenodo GitHub integration to archive the release.
4. Confirm the Zenodo record is public.
5. Send Codex the DOI in the form `10.5281/zenodo.<id>`.

Do not write `DOI archived`, `publicly released`, or `available at GitHub` in the manuscript until Codex verifies the live URL and DOI.

### 5. External Reproduction Check

After GitHub and Zenodo are public:

1. Ask one external reviewer or another AI environment to clone the repository from GitHub.
2. Run the documented smoke tests and at least one benchmark reproduction script.
3. Return any errors, missing files, unclear instructions, and runtime/memory notes to Codex.

This is required before targeting a 20-50 JIF methods or genomics journal.

## Codex-Owned Follow-Up After Author Inputs

After the author sends the missing items above, Codex should:

- Update `CITATION.cff`, `.zenodo.json`, author metadata tables, manuscript title page, cover letter, and Code/Data Availability.
- Regenerate `manuscript/current_article_external_review_packet.md`.
- Rerun claim boundary lint, claim traceability, release audit, unit tests, and journal-route gates.
- Rebuild the Gantt/progress figure and refresh the 20-50 JIF gap assessment.
