"""
EmbodiedOS — Curated high-value open-source target list.

The campaign runner round-robins through this list during a continuous
hunt.  Every entry is a real, large-blast-radius open-source project
that downstream ecosystems depend on heavily.  Finding a P1/P2 here
means the fix protects a long tail of dependents — exactly the
profile the operator wants for the 30-day investor demonstration.

Selection criteria:
  * High dependency fan-out (used by 1k+ downstream packages or
    deployed at scale in production infrastructure).
  * Active maintenance in the last 12 months (so PRs and disclosures
    actually get reviewed).
  * Public security policy or accepted CVE history (so responsible
    disclosure has a known channel).

This list is metadata only — the runner clones each repo INTO THE
SANDBOX before doing anything with it.  Nothing here triggers an
outbound action by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Target:
    name:        str            # "owner/repo"
    url:         str            # canonical clone URL
    stack:       tuple[str, ...]  # ("c", "linux") / ("typescript",) etc.
    category:    str            # "kernel" | "runtime" | "web" | ...
    why:         str            # one-line rationale
    bounty:      str   = ""     # platform/handle if there is a public programme
    extra_tags:  tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# The curated list — real, well-known, high-impact OSS repos.
# Grouped by category for readability; the runner flattens them.
# ---------------------------------------------------------------------------

KERNELS_AND_OS = [
    Target("torvalds/linux",          "https://github.com/torvalds/linux.git",
           ("c", "linux"), "kernel",
           "Linux kernel — the largest blast-radius OSS in existence."),
    Target("openbsd/src",             "https://github.com/openbsd/src.git",
           ("c", "openbsd"), "kernel",
           "OpenBSD base system — the security-research gold standard."),
    Target("freebsd/freebsd-src",     "https://github.com/freebsd/freebsd-src.git",
           ("c", "freebsd"), "kernel",
           "FreeBSD base system — powers a large slice of cloud infra."),
    Target("illumos/illumos-gate",    "https://github.com/illumos/illumos-gate.git",
           ("c",), "kernel",
           "Illumos / Solaris descendant — used by SmartOS, OmniOS, Joyent."),
]

LANGUAGE_RUNTIMES = [
    Target("nodejs/node",             "https://github.com/nodejs/node.git",
           ("c++", "javascript"), "runtime",
           "Node.js runtime — every npm package depends on it.",
           bounty="HACKERONE/nodejs"),
    Target("microsoft/TypeScript",    "https://github.com/microsoft/TypeScript.git",
           ("typescript",), "compiler",
           "TypeScript compiler — every TS codebase depends on it."),
    Target("denoland/deno",           "https://github.com/denoland/deno.git",
           ("rust", "typescript"), "runtime",
           "Deno runtime — secure-by-default JS/TS runtime."),
    Target("python/cpython",          "https://github.com/python/cpython.git",
           ("c", "python"), "runtime",
           "CPython interpreter — runs most Python in production.",
           bounty="HACKERONE/python"),
    Target("PyPy/pypy",               "https://github.com/pypy/pypy.git",
           ("python", "rpython"), "runtime",
           "PyPy JIT — alternative Python with large user base."),
    Target("golang/go",               "https://github.com/golang/go.git",
           ("go",), "runtime",
           "Go toolchain + stdlib — runs cloud infra everywhere.",
           bounty="HACKERONE/golang"),
    Target("rust-lang/rust",          "https://github.com/rust-lang/rust.git",
           ("rust",), "compiler",
           "Rust compiler — memory-safety claim depends on its correctness."),
    Target("ruby/ruby",               "https://github.com/ruby/ruby.git",
           ("c", "ruby"), "runtime",
           "MRI Ruby interpreter — every Rails app depends on it.",
           bounty="HACKERONE/ruby"),
    Target("php/php-src",             "https://github.com/php/php-src.git",
           ("c", "php"), "runtime",
           "PHP interpreter — runs ~75% of the public web.",
           bounty="HACKERONE/php"),
    Target("openjdk/jdk",             "https://github.com/openjdk/jdk.git",
           ("java",), "runtime",
           "OpenJDK — the JVM most enterprises ship."),
    Target("dotnet/runtime",          "https://github.com/dotnet/runtime.git",
           ("c#",), "runtime",
           ".NET runtime — Microsoft + enterprise stack.",
           bounty="HACKERONE/dotnet"),
    Target("erlang/otp",              "https://github.com/erlang/otp.git",
           ("erlang",), "runtime",
           "Erlang/OTP — telecoms + WhatsApp + Discord."),
    Target("elixir-lang/elixir",      "https://github.com/elixir-lang/elixir.git",
           ("elixir",), "runtime",
           "Elixir on BEAM — modern Erlang with growing prod use."),
]

WEB_FRAMEWORKS = [
    Target("expressjs/express",       "https://github.com/expressjs/express.git",
           ("javascript",), "web",
           "Express — most-used Node web framework."),
    Target("vercel/next.js",          "https://github.com/vercel/next.js.git",
           ("typescript",), "web",
           "Next.js — production React meta-framework.",
           bounty="HACKERONE/vercel"),
    Target("facebook/react",          "https://github.com/facebook/react.git",
           ("javascript",), "ui",
           "React — UI library powering most modern web apps."),
    Target("vuejs/core",              "https://github.com/vuejs/core.git",
           ("typescript",), "ui", "Vue 3 reactive UI framework."),
    Target("sveltejs/svelte",         "https://github.com/sveltejs/svelte.git",
           ("typescript",), "ui", "Svelte compiler-as-framework."),
    Target("django/django",           "https://github.com/django/django.git",
           ("python",), "web",
           "Django — batteries-included Python web framework."),
    Target("pallets/flask",           "https://github.com/pallets/flask.git",
           ("python",), "web", "Flask — micro-framework, huge install base."),
    Target("fastapi/fastapi",         "https://github.com/fastapi/fastapi.git",
           ("python",), "web", "FastAPI — modern async Python API framework."),
    Target("rails/rails",             "https://github.com/rails/rails.git",
           ("ruby",), "web",
           "Ruby on Rails — basecamp/shopify/github heritage.",
           bounty="HACKERONE/rails"),
    Target("laravel/framework",       "https://github.com/laravel/framework.git",
           ("php",), "web", "Laravel — dominant modern PHP framework."),
    Target("symfony/symfony",         "https://github.com/symfony/symfony.git",
           ("php",), "web", "Symfony — enterprise PHP framework."),
    Target("WordPress/WordPress",     "https://github.com/WordPress/WordPress.git",
           ("php",), "cms",
           "WordPress core — runs ~40% of the public web.",
           bounty="HACKERONE/wordpress"),
    Target("spring-projects/spring-framework",
           "https://github.com/spring-projects/spring-framework.git",
           ("java",), "web", "Spring — enterprise Java backbone."),
    Target("spring-projects/spring-boot",
           "https://github.com/spring-projects/spring-boot.git",
           ("java",), "web", "Spring Boot — opinionated Spring runner."),
    Target("netty/netty",             "https://github.com/netty/netty.git",
           ("java",), "network", "Netty — async network framework, used by everyone."),
    Target("apache/tomcat",           "https://github.com/apache/tomcat.git",
           ("java",), "web", "Tomcat — Servlet container, ubiquitous."),
    Target("eclipse-jetty/jetty.project",
           "https://github.com/eclipse/jetty.project.git",
           ("java",), "web", "Jetty — embeddable Servlet container."),
    Target("gin-gonic/gin",           "https://github.com/gin-gonic/gin.git",
           ("go",), "web", "Gin — most-used Go web framework."),
    Target("actix/actix-web",         "https://github.com/actix/actix-web.git",
           ("rust",), "web", "Actix-Web — high-throughput Rust web framework."),
]

WEB_SERVERS_AND_PROXIES = [
    Target("nginx/nginx",             "https://github.com/nginx/nginx.git",
           ("c",), "server", "nginx — most-deployed web server."),
    Target("apache/httpd",            "https://github.com/apache/httpd.git",
           ("c",), "server", "Apache httpd — original incumbent web server."),
    Target("envoyproxy/envoy",        "https://github.com/envoyproxy/envoy.git",
           ("c++",), "proxy",
           "Envoy — service-mesh data plane (Istio, AWS App Mesh)."),
    Target("haproxy/haproxy",         "https://github.com/haproxy/haproxy.git",
           ("c",), "proxy", "HAProxy — load balancer, edge proxy."),
    Target("caddyserver/caddy",       "https://github.com/caddyserver/caddy.git",
           ("go",), "server", "Caddy — modern HTTPS-by-default web server."),
    Target("traefik/traefik",         "https://github.com/traefik/traefik.git",
           ("go",), "proxy", "Traefik — cloud-native edge proxy."),
]

DATABASES = [
    Target("postgres/postgres",       "https://github.com/postgres/postgres.git",
           ("c",), "db", "PostgreSQL — gold-standard open-source RDBMS."),
    Target("mysql/mysql-server",      "https://github.com/mysql/mysql-server.git",
           ("c++",), "db", "MySQL — most-deployed RDBMS in absolute terms."),
    Target("MariaDB/server",          "https://github.com/MariaDB/server.git",
           ("c++",), "db", "MariaDB — community MySQL fork, distro default."),
    Target("redis/redis",             "https://github.com/redis/redis.git",
           ("c",), "db", "Redis — ubiquitous in-memory store."),
    Target("mongodb/mongo",           "https://github.com/mongodb/mongo.git",
           ("c++",), "db", "MongoDB — leading document database."),
    Target("sqlite/sqlite",           "https://github.com/sqlite/sqlite.git",
           ("c",), "db",
           "SQLite — most-deployed database period (every phone)."),
    Target("elastic/elasticsearch",   "https://github.com/elastic/elasticsearch.git",
           ("java",), "db", "Elasticsearch — search & analytics backbone."),
    Target("apache/cassandra",        "https://github.com/apache/cassandra.git",
           ("java",), "db", "Cassandra — wide-column store at scale."),
    Target("clickhouse/ClickHouse",   "https://github.com/ClickHouse/ClickHouse.git",
           ("c++",), "db", "ClickHouse — fastest open OLAP DB."),
    Target("etcd-io/etcd",            "https://github.com/etcd-io/etcd.git",
           ("go",), "db", "etcd — Kubernetes' source of truth."),
]

INFRASTRUCTURE = [
    Target("kubernetes/kubernetes",   "https://github.com/kubernetes/kubernetes.git",
           ("go",), "orchestrator",
           "Kubernetes — container orchestration standard.",
           bounty="HACKERONE/kubernetes"),
    Target("moby/moby",               "https://github.com/moby/moby.git",
           ("go",), "container", "Docker engine."),
    Target("containerd/containerd",   "https://github.com/containerd/containerd.git",
           ("go",), "container", "containerd — runtime under K8s + Docker."),
    Target("opencontainers/runc",     "https://github.com/opencontainers/runc.git",
           ("go",), "container", "runc — OCI low-level container runtime."),
    Target("hashicorp/terraform",     "https://github.com/hashicorp/terraform.git",
           ("go",), "iac", "Terraform — IaC standard."),
    Target("hashicorp/vault",         "https://github.com/hashicorp/vault.git",
           ("go",), "secrets",
           "Vault — secrets management at enterprise scale.",
           bounty="HACKERONE/hashicorp"),
    Target("ansible/ansible",         "https://github.com/ansible/ansible.git",
           ("python",), "iac", "Ansible — agentless config management."),
    Target("helm/helm",               "https://github.com/helm/helm.git",
           ("go",), "iac", "Helm — K8s package manager."),
    Target("istio/istio",             "https://github.com/istio/istio.git",
           ("go",), "mesh", "Istio — service mesh control plane."),
    Target("prometheus/prometheus",   "https://github.com/prometheus/prometheus.git",
           ("go",), "observability", "Prometheus — metrics + alerting standard."),
    Target("grafana/grafana",         "https://github.com/grafana/grafana.git",
           ("typescript", "go"), "observability",
           "Grafana — observability dashboards.",
           bounty="HACKERONE/grafana"),
]

CRYPTO_AND_SECURITY = [
    Target("openssl/openssl",         "https://github.com/openssl/openssl.git",
           ("c",), "crypto",
           "OpenSSL — TLS for half the internet.  Heartbleed legacy."),
    Target("libressl-portable/portable",
           "https://github.com/libressl-portable/portable.git",
           ("c",), "crypto", "LibreSSL — OpenBSD's TLS fork."),
    Target("openssh/openssh-portable",
           "https://github.com/openssh/openssh-portable.git",
           ("c",), "ssh", "OpenSSH — SSH for the entire internet."),
    Target("curl/curl",               "https://github.com/curl/curl.git",
           ("c",), "client", "curl/libcurl — HTTP client baked into everything.",
           bounty="HACKERONE/curl"),
    Target("wolfSSL/wolfssl",         "https://github.com/wolfSSL/wolfssl.git",
           ("c",), "crypto", "wolfSSL — embedded TLS stack."),
    Target("apple/swift-crypto",      "https://github.com/apple/swift-crypto.git",
           ("swift",), "crypto", "Apple's Swift Crypto."),
    Target("FiloSottile/age",         "https://github.com/FiloSottile/age.git",
           ("go",), "crypto", "age — modern file encryption tool."),
]

CRYPTOCURRENCY = [
    Target("bitcoin/bitcoin",         "https://github.com/bitcoin/bitcoin.git",
           ("c++",), "crypto-currency",
           "Bitcoin Core — reference implementation, hundreds of $B at risk."),
    Target("ethereum/go-ethereum",    "https://github.com/ethereum/go-ethereum.git",
           ("go",), "crypto-currency",
           "Geth — most-used Ethereum execution client."),
    Target("paritytech/polkadot-sdk", "https://github.com/paritytech/polkadot-sdk.git",
           ("rust",), "crypto-currency", "Polkadot SDK."),
    Target("solana-labs/solana",      "https://github.com/solana-labs/solana.git",
           ("rust",), "crypto-currency", "Solana validator."),
    Target("monero-project/monero",   "https://github.com/monero-project/monero.git",
           ("c++",), "crypto-currency", "Monero — privacy-coin reference impl."),
]

MULTIMEDIA_AND_PARSERS = [
    Target("FFmpeg/FFmpeg",           "https://github.com/FFmpeg/FFmpeg.git",
           ("c",), "media",
           "FFmpeg — multimedia processing, huge fuzzing surface."),
    Target("videolan/vlc",            "https://github.com/videolan/vlc.git",
           ("c", "c++"), "media", "VLC — most-used media player."),
    Target("ImageMagick/ImageMagick", "https://github.com/ImageMagick/ImageMagick.git",
           ("c",), "media", "ImageMagick — image processing, classic CVE-rich."),
    Target("libjpeg-turbo/libjpeg-turbo",
           "https://github.com/libjpeg-turbo/libjpeg-turbo.git",
           ("c",), "media", "libjpeg-turbo — JPEG codec."),
    Target("libarchive/libarchive",   "https://github.com/libarchive/libarchive.git",
           ("c",), "parser", "libarchive — archive format parser."),
    Target("madler/zlib",             "https://github.com/madler/zlib.git",
           ("c",), "compression", "zlib — compression library, baked into everything."),
]

MESSAGE_QUEUES = [
    Target("apache/kafka",            "https://github.com/apache/kafka.git",
           ("java",), "queue", "Kafka — distributed streaming."),
    Target("rabbitmq/rabbitmq-server","https://github.com/rabbitmq/rabbitmq-server.git",
           ("erlang",), "queue", "RabbitMQ — AMQP broker."),
    Target("nats-io/nats-server",     "https://github.com/nats-io/nats-server.git",
           ("go",), "queue", "NATS — high-perf messaging."),
    Target("apache/pulsar",           "https://github.com/apache/pulsar.git",
           ("java",), "queue", "Pulsar — Yahoo-origin pub-sub."),
]

PACKAGE_MANAGERS_AND_BUILD = [
    Target("npm/cli",                 "https://github.com/npm/cli.git",
           ("javascript",), "package-mgr", "npm CLI — supply-chain entry point."),
    Target("yarnpkg/berry",           "https://github.com/yarnpkg/berry.git",
           ("typescript",), "package-mgr", "Yarn — JS package manager."),
    Target("pnpm/pnpm",               "https://github.com/pnpm/pnpm.git",
           ("typescript",), "package-mgr", "pnpm — efficient JS package manager."),
    Target("pypa/pip",                "https://github.com/pypa/pip.git",
           ("python",), "package-mgr", "pip — Python's package installer."),
    Target("rubygems/rubygems",       "https://github.com/rubygems/rubygems.git",
           ("ruby",), "package-mgr", "RubyGems — Ruby package manager."),
    Target("composer/composer",       "https://github.com/composer/composer.git",
           ("php",), "package-mgr", "Composer — PHP package manager."),
    Target("apache/maven",            "https://github.com/apache/maven.git",
           ("java",), "build", "Maven — Java build + dependency tool."),
    Target("gradle/gradle",           "https://github.com/gradle/gradle.git",
           ("java",), "build", "Gradle — modern JVM build tool."),
    Target("bazelbuild/bazel",        "https://github.com/bazelbuild/bazel.git",
           ("java",), "build", "Bazel — polyglot hermetic builds."),
]

DEV_TOOLS = [
    Target("git/git",                 "https://github.com/git/git.git",
           ("c",), "vcs", "Git — version control everywhere."),
    Target("microsoft/vscode",        "https://github.com/microsoft/vscode.git",
           ("typescript",), "ide", "VSCode — leading code editor.",
           bounty="HACKERONE/microsoft"),
    Target("neovim/neovim",           "https://github.com/neovim/neovim.git",
           ("c",), "ide", "Neovim — modern vim fork."),
    Target("emacs-mirror/emacs",      "https://github.com/emacs-mirror/emacs.git",
           ("c", "elisp"), "ide", "GNU Emacs."),
]

# ---------------------------------------------------------------------------

ALL_TARGETS: tuple[Target, ...] = tuple(
    KERNELS_AND_OS
    + LANGUAGE_RUNTIMES
    + WEB_FRAMEWORKS
    + WEB_SERVERS_AND_PROXIES
    + DATABASES
    + INFRASTRUCTURE
    + CRYPTO_AND_SECURITY
    + CRYPTOCURRENCY
    + MULTIMEDIA_AND_PARSERS
    + MESSAGE_QUEUES
    + PACKAGE_MANAGERS_AND_BUILD
    + DEV_TOOLS
)


def by_stack(*stacks: str) -> list[Target]:
    s = {x.lower() for x in stacks}
    return [t for t in ALL_TARGETS if any(x in s for x in t.stack)]


def by_category(*categories: str) -> list[Target]:
    c = {x.lower() for x in categories}
    return [t for t in ALL_TARGETS if t.category.lower() in c]


def with_bounty() -> list[Target]:
    return [t for t in ALL_TARGETS if t.bounty]


__all__ = [
    "Target",
    "ALL_TARGETS",
    "by_stack",
    "by_category",
    "with_bounty",
]
