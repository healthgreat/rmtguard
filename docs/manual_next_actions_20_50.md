# Manual Next Actions For The RMTGuard 20-50 JIF Route

Last updated: 2026-05-04.

This checklist separates author-owned external actions from Codex-owned local
analysis work. It does not guarantee acceptance; it is a risk-control list for
raising the manuscript toward a strict Nature Methods / 20-50 JIF route.

## 1. ORCID Profile Cleanup

Status: required but not blocking for code release.

Confirmed primary ORCID:

- Chongfa Chen: https://orcid.org/0000-0001-6597-5181

Possible duplicate not currently used:

- https://orcid.org/0000-0001-7367-9972

Manual steps:

1. Open https://orcid.org/signin.
2. Log in to `0000-0001-6597-5181`.
3. Open the public preview and confirm the visible name is `Chongfa Chen`.
4. Add Employment:
   - Organization: `The Affiliated BenQ Hospital of Nanjing Medical University`
   - Department: `Pancreas Center`
   - City: `Nanjing`
   - Country: `China`
   - Visibility: `Everyone`
5. Add Works:
   - Use `Add works -> Search & link -> Crossref Metadata Search`.
   - Search by `Chongfa Chen` and import only your own papers.
   - If a paper is missing, add it by DOI.
   - Set visibility to `Everyone`.
6. If you can also log in to `0000-0001-7367-9972`, treat it as a duplicate:
   - Open https://orcid.org/account.
   - Go to `Account actions`.
   - Choose `Remove a duplicate record`.
   - Keep `0000-0001-6597-5181` as the primary account unless ORCID support advises otherwise.
7. If you cannot access the possible duplicate, do not use it in the manuscript.

## 2. Postal Code Confirmation

Status: required before final title page.

Current conflict:

- Author-provided postal code: `350000`
- Public-source candidate for the Nanjing BenQ Hospital / Hexi Street address: `210019`

Manual steps:

1. Check the hospital official English address page or internal hospital letterhead.
2. Confirm whether the journal submission metadata should use:
   - `350000`, or
   - `210019`.
3. Send the final value back to Codex with this sentence:

```text
Use postal code <FINAL_POSTAL_CODE> for both Yi Miao and Han Yan correspondence addresses.
```

Do not finalize the title page until this is confirmed.

## 3. Author Declarations

Status: required before submission.

Manual steps:

1. CRediT roles:
   - Open `metadata/credit_roles.tsv`.
   - Confirm whether each role is correct.
   - If a role is wrong, tell Codex the corrected role list for each author.
2. Funding:
   - If funded, provide exact funder names and grant numbers.
   - If not funded, confirm this sentence:

```text
This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.
```

3. Competing interests:
   - Ask all authors to confirm whether financial or non-financial conflicts exist.
   - If none, confirm:

```text
The authors declare no competing interests.
```

4. Ethics / public data:
   - Confirm that the manuscript uses only public, de-identified datasets.
   - If no private clinical data are added, confirm:

```text
This study analyzed publicly available, de-identified datasets and did not involve newly collected private clinical data or direct contact with human participants.
```

## 4. Journal Metrics, CAS Zone, And Warning List Verification

Status: required immediately before submission because metrics and warning
lists change.

Official / near-official links:

- Nature Methods metrics: https://www.nature.com/nmeth/journal-impact
- Nature Communications metrics: https://www.nature.com/ncomms/journal-impact
- Genome Biology metrics: https://genomebiology.biomedcentral.com/about
- Cell Genomics metrics: https://www.sciencedirect.com/journal/cell-genomics/about/insights
- Journal Citation Reports: https://jcr.clarivate.com
- CAS partition table login/query: https://www.fenqubiao.com
- CAS warning list portal: https://ewl.fenqubiao.com

Manual steps:

1. Use your institution library/VPN to open https://jcr.clarivate.com.
2. Search each candidate journal:
   - `Nature Methods`
   - `Nature Communications`
   - `Genome Biology`
   - `Cell Genomics`
   - `Bioinformatics`
3. Record:
   - 2024 Journal Impact Factor
   - 5-year Journal Impact Factor
   - JCR category and quartile
4. Open https://www.fenqubiao.com.
5. Search the same journals and record:
   - 中科院大类分区
   - 中科院小类分区
   - 是否 Top
6. Open https://ewl.fenqubiao.com.
7. Search the same journals and record whether they appear in the current warning list.
8. Send the verified table back to Codex. Use this template:

```text
Journal | 2024 JIF | 5-year JIF | 中科院大类 | 中科院小类 | Top? | 预警?
Nature Methods |  |  |  |  |  |
Nature Communications |  |  |  |  |  |
Genome Biology |  |  |  |  |  |
Cell Genomics |  |  |  |  |  |
Bioinformatics |  |  |  |  |  |
```

## 5. PDAC/TME Showcase Decision

Status: major scientific blocker.

Choose one route:

1. Deepen PDAC/TME as a main figure:
   - Add differential expression for stable states.
   - Add pathway enrichment / GSEA.
   - Add marker validation against published PDAC CAF, immune, or malignant ductal states.
   - Add external validation using GSE263733.
2. Demote PDAC/TME to supplementary:
   - Keep it as an example of public-data use.
   - Use a stronger ground-truth dataset as the main application.

Manual input needed from you:

```text
PDAC/TME route: deepen as main figure / demote to supplement.
```

## 6. Release Rule Going Forward

Status: important.

The public release is complete:

- GitHub: https://github.com/healthgreat/rmtguard
- GitHub Release: https://github.com/healthgreat/rmtguard/releases/tag/v0.1.0
- Zenodo DOI: https://doi.org/10.5281/zenodo.20012350

Do not move the archived `v0.1.0` tag. If major benchmark or metadata changes
are made, create a new release such as `v0.1.1` and archive it as a new Zenodo
version.

