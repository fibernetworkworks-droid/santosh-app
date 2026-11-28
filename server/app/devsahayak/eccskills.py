"""v0.999 ECC SKILLS in Hoola Code (owner: 'GO 1 TO 5' after the ECC check: Hoola Code had 63 of ECC's agents and all
22 of its rule sets, but none of its 328 skills).

Source: github.com/affaan-m/ECC (MIT, Copyright (c) 2026 Affaan Mustafa), commit 4adeee67. The skill files in
`ecc_skills/` are ECC's own SKILL.md files, copied unchanged (the licence allows it; its notice is in
THIRD_PARTY_NOTICES.md). Taken: the 87 language / framework / database / infrastructure skills and 45 general coding
skills. Left out (about 196): skills that set up Claude Code or ECC itself (hooks, plugins, ~/.claude), skills that need
outside services Hoola Code's locked box does not have, and the ones that are not coding (healthcare, logistics,
investors, home networks, marketing - Hoola's other desks).

How Hoola Code uses them:
- the skills that fit THIS repo are found from its files (extensions, marker files, the dependency names in its
  package.json / requirements / pyproject / go.mod / Cargo.toml / pom.xml / build.gradle / Gemfile / composer.json /
  Package.swift) and listed with what they are for in the fixed prompt (stable for the session, so cached);
- general skills that fit HER words this round are named with her message;
- the skill tool reads one whole (`ecc:<name>`), with a short note on how ECC's Claude Code words map to Hoola Code's
  tools. A skill is guidance: her words, the repo's rules and Hoola's safety rules come first.
Switch: `dev_ecc_skills` (default on).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DIR = Path(__file__).with_name("ecc_skills")
CREDIT = "ECC (affaan-m/ECC, MIT)"
_CACHE: dict[str, dict[str, str]] = {}

# skill -> (file paths regex, manifest words regex). Either one matching = the skill fits the repo.
F, W = "f", "w"
REPO: dict[str, dict[str, str]] = {
    "android-clean-architecture": {F: r"(^|/)AndroidManifest\.xml$", W: r"com\.android\.(application|library)"},
    "angular-developer": {F: r"(^|/)angular\.json$", W: r'"@angular/core"'},
    "bun-runtime": {F: r"(^|/)(bun\.lockb?|bunfig\.toml)$"},
    "compose-multiplatform-patterns": {W: r"org\.jetbrains\.compose|compose-multiplatform"},
    "cpp-coding-standards": {F: r"\.(cc|cpp|cxx|hpp|hh)$|(^|/)CMakeLists\.txt$"},
    "cpp-testing": {F: r"\.(cc|cpp|cxx|hpp|hh)$|(^|/)CMakeLists\.txt$"},
    "csharp-testing": {F: r"\.cs$|\.csproj$"},
    "dotnet-patterns": {F: r"\.csproj$|\.sln$|\.fsproj$"},
    "dart-flutter-patterns": {F: r"(^|/)pubspec\.yaml$"},
    "flutter-dart-code-review": {F: r"(^|/)pubspec\.yaml$"},
    "django-patterns": {F: r"(^|/)manage\.py$", W: r"\bdjango\b"},
    "django-security": {F: r"(^|/)manage\.py$", W: r"\bdjango\b"},
    "django-tdd": {F: r"(^|/)manage\.py$", W: r"\bdjango\b"},
    "django-verification": {F: r"(^|/)manage\.py$", W: r"\bdjango\b"},
    "django-celery": {W: r"\bcelery\b"},
    "fastapi-patterns": {W: r"\bfastapi\b"},
    "fsharp-testing": {F: r"\.(fs|fsx|fsproj)$"},
    "godot-patterns": {F: r"(^|/)project\.godot$|\.gd$"},
    "godot-testing": {F: r"(^|/)project\.godot$|\.gd$"},
    "golang-patterns": {F: r"(^|/)go\.mod$"},
    "golang-testing": {F: r"(^|/)go\.mod$"},
    "java-coding-standards": {F: r"\.java$"},
    "jpa-patterns": {W: r"jakarta\.persistence|javax\.persistence|hibernate|spring-boot-starter-data-jpa"},
    "mybatis-patterns": {W: r"mybatis"},
    "kotlin-patterns": {F: r"\.kts?$"},
    "kotlin-testing": {F: r"\.kts?$"},
    "kotlin-coroutines-flows": {W: r"kotlinx-coroutines|kotlinx\.coroutines"},
    "kotlin-exposed-patterns": {W: r"org\.jetbrains\.exposed|exposed-core"},
    "kotlin-ktor-patterns": {W: r"io\.ktor|ktor-server"},
    "laravel-patterns": {F: r"(^|/)artisan$", W: r"laravel/framework"},
    "laravel-security": {F: r"(^|/)artisan$", W: r"laravel/framework"},
    "laravel-tdd": {F: r"(^|/)artisan$", W: r"laravel/framework"},
    "laravel-verification": {F: r"(^|/)artisan$", W: r"laravel/framework"},
    "laravel-plugin-discovery": {W: r"laravel/framework"},
    "nestjs-patterns": {W: r'"@nestjs/core"'},
    "nextjs-turbopack": {F: r"(^|/)next\.config\.(js|mjs|ts)$", W: r'"next"\s*:'},
    "nuxt4-patterns": {F: r"(^|/)nuxt\.config\.(ts|js|mjs)$"},
    "perl-patterns": {F: r"\.(pl|pm|t)$"},
    "perl-security": {F: r"\.(pl|pm)$"},
    "perl-testing": {F: r"\.(pl|pm|t)$"},
    "prisma-patterns": {F: r"(^|/)schema\.prisma$", W: r'"prisma"|"@prisma/client"'},
    "python-patterns": {F: r"\.py$"},
    "python-testing": {F: r"\.py$"},
    "pytorch-patterns": {W: r"\btorch\b|\bpytorch\b"},
    "quarkus-patterns": {W: r"io\.quarkus|quarkus-"},
    "quarkus-security": {W: r"io\.quarkus|quarkus-"},
    "quarkus-tdd": {W: r"io\.quarkus|quarkus-"},
    "quarkus-verification": {W: r"io\.quarkus|quarkus-"},
    "rails-patterns": {F: r"(^|/)config/routes\.rb$", W: r"gem ['\"]rails['\"]"},
    "rails-security": {F: r"(^|/)config/routes\.rb$", W: r"gem ['\"]rails['\"]"},
    "react-native-patterns": {W: r'"react-native"\s*:'},
    "react-patterns": {W: r'"react"\s*:'},
    "react-performance": {W: r'"react"\s*:'},
    "react-testing": {W: r'"react"\s*:'},
    "rust-patterns": {F: r"(^|/)Cargo\.toml$"},
    "rust-testing": {F: r"(^|/)Cargo\.toml$"},
    "springboot-patterns": {W: r"spring-boot|org\.springframework\.boot"},
    "springboot-security": {W: r"spring-boot|org\.springframework\.boot"},
    "springboot-tdd": {W: r"spring-boot|org\.springframework\.boot"},
    "springboot-verification": {W: r"spring-boot|org\.springframework\.boot"},
    "swift-actor-persistence": {F: r"\.swift$"},
    "swift-concurrency-6-2": {F: r"\.swift$"},
    "swift-protocol-di-testing": {F: r"\.swift$"},
    "swiftui-patterns": {F: r"\.swift$"},
    "tinystruct-patterns": {W: r"tinystruct"},
    "typescript-patterns": {F: r"\.(ts|tsx|mts|cts)$|(^|/)tsconfig\.json$"},
    "vite-patterns": {F: r"(^|/)vite\.config\.(js|ts|mjs|mts)$", W: r'"vite"\s*:'},
    "vue-patterns": {F: r"\.vue$", W: r'"vue"\s*:'},
    "clickhouse-io": {W: r"clickhouse"},
    "database-migrations": {F: r"(^|/)(migrations?|alembic|db/migrate)/|(^|/)alembic\.ini$|flyway|liquibase"},
    "deployment-patterns": {F: r"(^|/)(Dockerfile|fly\.toml|vercel\.json|netlify\.toml|render\.yaml|app\.yaml|Procfile)$"},
    "docker-patterns": {F: r"(^|/)(Dockerfile|docker-compose\.ya?ml|compose\.ya?ml)$"},
    "flox-environments": {F: r"(^|/)\.flox/"},
    "kubernetes-patterns": {F: r"(^|/)(Chart\.yaml|kustomization\.ya?ml)$|(^|/)(k8s|kubernetes|helm)/"},
    "mysql-patterns": {W: r"\bmysql2?\b|pymysql|mysqlclient|mysql-connector"},
    "postgres-patterns": {W: r'\bpsycopg|"pg"\s*:|postgres|\bpgx\b|sqlx.*postgres'},
    "redis-patterns": {W: r"\bredis\b|ioredis"},
    "terraform-patterns": {F: r"\.tf$"},
}
# skill -> words in HER request that make it fit this round (general skills; language skills also have a few)
WORDS: dict[str, str] = {
    "accessibility": r"accessib|a11y|wcag|screen ?reader|aria\b",
    "frontend-a11y": r"accessib|a11y|wcag|screen ?reader|aria\b",
    "agent-harness-construction": r"agent harness|tool definitions?|action space",
    "agent-security-hardening": r"(agent|llm).{0,30}(secur|untrusted|injection)|prompt injection",
    "ai-regression-testing": r"ai regression|regression tests? for (the )?(ai|llm)",
    "api-connector-builder": r"\b(connector|integration|provider) for\b|new (api )?(connector|integration|provider)",
    "api-design": r"\b(rest|http) api\b|api design|endpoint design|pagination|status codes?|versioning",
    "architecture-decision-records": r"\badr\b|architecture decision|decision record",
    "backend-patterns": r"\bbackend\b|server.side|caching layer|n\+1",
    "benchmark": r"benchmark|core web vitals|\blcp\b|baseline performance|regressions? in (speed|performance)",
    "change-impact": r"impact (analysis|of (this|the) change)|what (else )?(will|would) (this|it) break|blast radius",
    "click-path-audit": r"button (does nothing|not working)|click path|every button",
    "code-tour": r"code ?tour|walkthrough of the code",
    "codebase-onboarding": r"onboard|explain (this|the) (repo|codebase)|how is (this|the) (repo|codebase) organi[sz]ed|architecture map",
    "coding-standards": r"coding standards?|code style|naming conventions?|clean up the code",
    "context-and-decisions": r"domain (terms|glossary)|context\.md",
    "contract-first": r"openapi|graphql schema|api contract|contract.first|protobuf",
    "cost-aware-llm-pipeline": r"llm (cost|budget)|model routing|cheaper (model|llm)",
    "dashboard-builder": r"grafana|signoz|monitoring dashboard",
    "design-system": r"design system|design tokens?|visual consisten",
    "e2e-testing": r"\be2e\b|end.to.end|playwright|cypress",
    "error-handling": r"error handling|retr(y|ies)|error boundar|typed errors?|exceptions? handling",
    "frontend-patterns": r"\bfrontend\b|state management|react performance|next\.?js",
    "generating-python-installer": r"\binstaller\b|nuitka|pyinstaller|\.exe for windows",
    "hexagonal-architecture": r"hexagonal|ports (and|&) adapters|clean architecture",
    "i18n-sync": r"\bi18n\b|translat|locale files?|locali[sz]",
    "inherit-legacy-style": r"legacy|old code ?base|keep the existing style",
    "intent-driven-development": r"acceptance criteria|ambiguous|unclear requirements?",
    "make-interfaces-feel-better": r"polish|feel (better|nicer)|ui details|spacing",
    "mcp-dependency-review": r"mcp (config|dependenc)|\.mcp\.json",
    "mcp-server-patterns": r"\bmcp server\b|model context protocol",
    "module-governance": r"new module|module (owner|boundar)",
    "module-regression": r"cross.module|regression\.md|downstream consumers",
    "motion-advanced": r"animation|framer motion|gesture|drag (and|&) drop",
    "motion-foundations": r"animation|motion tokens|spring",
    "motion-patterns": r"animation|page transitions?|stagger",
    "platform-factory": r"\bsbom\b|provenance|oci image|reproducible (image|build)",
    "production-audit": r"production.ready|pre.launch|launch checklist|what breaks in production",
    "prompt-caching-strategy": r"prompt cach|cache hit rate",
    "regex-vs-llm-structured-text": r"\bparse\b.{0,40}(invoice|receipt|form|quiz|table)|regex or (an )?llm",
    "search-first": r"existing (library|package|tool)|is there a (library|package)|don'?t reinvent",
    "security-review": r"secur|auth(entication|ori[sz]ation)?\b|secrets?|injection|xss|csrf|password",
    "test-collaboration": r"test (plan|assets|strategy|inventory)",
    "windows-desktop-e2e": r"\bwpf\b|winforms|win32|pywinauto|windows desktop app",
    "living-docs-governance": r"docs? (rot|out of date|governance)|keep (the )?docs (current|up to date)",
    "database-migrations": r"migration|schema change|alter table|alembic",
    "latency-critical-systems": r"latency|low.latency|p99|real.time",
    "content-hash-cache-pattern": r"content hash|cache by hash",
    "data-throughput-accelerator": r"throughput|batch(ing)? speed|bulk load",
    "uncloud": r"\buncloud\b",
    "nodejs-keccak256": r"keccak",
    "foundation-models-on-device": r"foundation ?models|on.device (model|llm|ai)",
    "liquid-glass-design": r"liquid glass",
    "ios-icon-gen": r"app icons?\b",
    "ui-to-vue": r"(to|into) vue\b|convert .{0,30}vue",
}


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_ecc_skills", True))


def skills() -> dict[str, dict[str, str]]:
    """Every ECC skill shipped: {name: {description, body, kind}} - kind 'repo' (language / framework / data) or 'general'."""
    if _CACHE:
        return _CACHE
    for f in sorted(DIR.glob("*.md")):
        txt = f.read_text("utf-8")
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
        head, body = (m.group(1), m.group(2)) if m else ("", txt)
        d = re.search(r"(?ms)^description:\s*(>-?|\|-?)?\s*\n?(.*?)(?=^\w[\w-]*:|\Z)", head)
        desc = " ".join((d.group(2) if d else "").split()).strip("'\"")
        _CACHE[f.stem] = {"description": desc, "body": body.strip(), "kind": "repo" if f.stem in REPO else "general"}
    return _CACHE


def get(name: str) -> dict[str, str] | None:
    n = str(name or "").strip().lower()
    n = n.split(":", 1)[1] if n.startswith("ecc:") else n
    return skills().get(n)


MANIFESTS = re.compile(r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|Pipfile|setup\.py|setup\.cfg|go\.mod|"
                       r"Cargo\.toml|pom\.xml|build\.gradle(\.kts)?|settings\.gradle(\.kts)?|Gemfile|composer\.json|"
                       r"Package\.swift|libs\.versions\.toml)$")


def for_repo(repo: Path, paths: list[str]) -> list[str]:
    """The language / framework / data skills that fit this repo, from its files and its dependency lists."""
    paths = [p for p in paths if "node_modules/" not in p and not p.startswith(".git/")][:20000]
    text = ""
    for p in [p for p in paths if MANIFESTS.search(p)][:30]:
        try:
            text += (Path(repo) / p).read_text("utf-8", errors="ignore")[:200_000].lower() + "\n"
        except OSError:
            pass
    joined = "\n".join(paths)
    out = []
    for name, rule in REPO.items():
        if rule.get(F) and re.search(rule[F], joined, re.M):
            out.append(name)
        elif rule.get(W) and re.search(rule[W], text, re.I):
            out.append(name)
    return [n for n in out if n in skills()]


def for_words(words: str, have: list[str] | None = None) -> list[str]:
    """General skills (and a few narrow language ones) her words this round point at."""
    w = str(words or "")
    have = set(have or [])
    return [n for n, rx in WORDS.items() if n not in have and n in skills() and re.search(rx, w, re.I)][:6]


def system_block(repo: Path, paths: list[str]) -> str:
    """Fixed for the session: the skills that fit this repo, each with what it is for."""
    if not on():
        return ""
    names = for_repo(repo, paths)[:24]
    sk = skills()
    lines = [f"- ecc:{n}: {sk[n]['description'][:180]}" for n in names]
    gen = [n for n, v in sk.items() if v["kind"] == "general"]
    return ("ECC'S SKILLS (" + CREDIT + ") - read one whole with the skill tool (name=ecc:<name>) before work it fits; "
            "they are guidance, never above her words, the repo's own rules or Hoola's safety rules.\n"
            + ("For this repo's languages and frameworks:\n" + "\n".join(lines) + "\n" if lines else "")
            + "General coding skills: " + ", ".join("ecc:" + n for n in gen) + ".")


def round_note(words: str, have: list[str] | None = None) -> str:
    """With her message: the general skills her words point at this round (names + what they are for)."""
    if not on():
        return ""
    names = for_words(words, have)
    if not names:
        return ""
    sk = skills()
    return ("<ecc_skills_that_fit>\nECC skills that fit this request (read the ones you use with the skill tool first):\n"
            + "\n".join(f"- ecc:{n}: {sk[n]['description'][:160]}" for n in names) + "\n</ecc_skills_that_fit>")


MAP_NOTE = ("(An ECC skill, written for Claude Code. In Hoola Code: Read / Grep / Glob / Bash / Edit / Write = read / grep / "
            "glob / bash / edit / write; Task or a subagent = the agent tool; `skill: name` = skill name=ecc:name. Skip "
            "steps that install plugins or hooks, change ~/.claude, or need the internet unless this repo's network allows "
            "it. Hoola records commits itself - never commit, push or rewrite history from bash. It is guidance: her words, "
            "the repo's rules and Hoola's safety rules come first.)")


def read(name: str) -> str | None:
    sk = get(name)
    if sk is None:
        return None
    n = str(name).split(":")[-1].strip().lower()
    return f'<skill name="ecc:{n}" from="{CREDIT}">\n{MAP_NOTE}\n\n{sk["body"][:40000]}\n</skill>'


def listing() -> list[str]:
    sk = skills()
    return [f"- ecc:{k} (ECC, {v['kind']}): {v['description'][:160]}" for k, v in sk.items()]
