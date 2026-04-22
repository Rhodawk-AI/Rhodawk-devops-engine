---
name: container-escape
domain: container
triggers:
  asset_types:  [docker, k8s, container, lxc, runc]
tools:          [deepce, cdk, amicontained, kubectl, dockle]
severity_focus: [P1, P2]
---

# Container Escape & Isolation Bypass

## When to load
Any sandboxed job runner, CI worker, multi-tenant SaaS using containers.

## Escape primitives
* **Mounted Docker socket** — `/var/run/docker.sock` inside container ⇒
  trivial host RCE.
* **Privileged container** — `--privileged` flag ⇒ access to host devices,
  `unshare`/`mount`/`/dev`.
* **Capabilities** — `CAP_SYS_ADMIN`, `CAP_DAC_READ_SEARCH`, `CAP_SYS_PTRACE`
  → host file access via `open_by_handle_at`.
* **K8s service account token** — `system:serviceaccount:default:default`
  with `cluster-admin` mistakenly bound.
* **runC CVE-2019-5736 / CVE-2024-21626 family** — overwrite host runc.
* **cgroup release_agent** — write to `release_agent` (pre-cgroup v2) for
  host RCE.

## Procedure
1. Inside the container: `amicontained` → enumerate caps and mounts.
2. `cat /proc/self/status | grep -i cap` and decode.
3. `mount` → look for `docker.sock`, `/`, `proc`, sensitive bind mounts.
4. If K8s pod: `cat /var/run/secrets/kubernetes.io/serviceaccount/token`,
   then `kubectl auth can-i --list`.
5. Attempt the appropriate escape primitive; verify host RCE with a marker
   file.

## Reporting
Provide the exact command sequence, the host-level proof (`hostname` of host
vs container), and remediation (drop caps, run unprivileged, switch to gVisor
or Kata).
