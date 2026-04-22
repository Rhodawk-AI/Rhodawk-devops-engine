---
name: cloud-security
domain: cloud
triggers:
  asset_types:  [aws, gcp, azure, k8s, lambda, s3, ec2, iam]
tools:          [scoutsuite, prowler, kube-hunter, kube-bench, pacu]
severity_focus: [P1, P2]
---

# Cloud Security

## When to load
Any cloud-hosted asset: AWS / GCP / Azure consoles, exposed metadata
services, Kubernetes clusters, serverless functions.

## Key vulnerability classes
* **IMDS abuse** — SSRF reaches `169.254.169.254` → steal IAM credentials.
* **Public S3 / GCS / blob** — `aws s3 ls s3://bucket --no-sign-request`.
* **Sub-domain takeover** — CNAME → unclaimed S3/Heroku/GitHub Pages.
* **Over-permissive IAM** — `iam:PassRole *`, `*:*` policies, role chaining.
* **K8s** — default service-account token mounted; `system:anonymous` allowed
  to list pods; exposed kubelet `:10255`/`:10250`; etcd `:2379` no auth.
* **Lambda** — environment variables leaking secrets, runtime API SSRF.
* **Cloud-native CI** — leaked OIDC tokens, GitHub Actions `pull_request_target`
  abuse.

## Procedure
1. Recon: `cloud_enum -k <target>`, `bucket_finder`, `gcpbucketbrute`.
2. Validate IMDS reachability via every SSRF primitive found.
3. For K8s: `kube-hunter --remote <ip>`, `kube-bench`.
4. For IAM: `pacu` automated escalation modules; print proof of higher
   privilege after exploitation.
5. For sub-domain takeover: confirm DNS NXDOMAIN / unclaimed registration
   before claiming.

## Reporting
Include cloud-side evidence (CLI command + exact output), affected resource
ARN / URI, blast-radius assessment.
