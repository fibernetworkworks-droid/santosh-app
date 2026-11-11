"""v0.794 ECC RULES - per-language coding rules condensed from ECC's rules/ (MIT, github.com/affaan-m/ECC). The repo's own rules always win."""

from __future__ import annotations

RULES: dict[str, str] = {
    "common": """COMMON RULES (adapted from ECC rules/common):
- Precedence: these are default good practice only. The repo's own rules (AGENTS.md, CLAUDE.md, CONTRIBUTING, linter/formatter config) and the owner's instructions always win. Match the style already used in the file you edit; do not reformat or restyle code you did not need to touch.
- Keep it simple (KISS), avoid copy-paste duplication (DRY) once repetition is real, and do not build features or abstractions before they are needed (YAGNI).
- Prefer returning new values over mutating shared objects or inputs, where the language idiom allows it; it avoids hidden side effects.
- Size: functions roughly under 50 lines, nesting no deeper than 4 levels (use early returns), source files typically 200-400 lines with ~800 as a soft ceiling. Organize code by feature/domain rather than by file type; extract helpers from oversized modules.
- Names say what a thing holds or does; booleans read as claims (isReady, hasItems); constants and types look distinct per the language convention. Replace magic numbers with named constants or config.
- Errors: handle them explicitly at each level, never swallow them silently. Show user-friendly messages in UI code; log detailed context on the server.
- Validate all input at system boundaries (user input, API responses, files, env), preferably with a schema; fail fast with a clear message. Treat external data as untrusted.
- Security: no hardcoded secrets - read them from env or a secret manager and check required ones at startup. Use parameterized queries (never string-built SQL), escape/sanitize HTML output, keep CSRF protection on state-changing requests, check authentication and authorization on the server, rate-limit sensitive endpoints, and keep error messages free of stack traces, paths, SQL or secrets. Guard file paths against traversal.
- No leftover debug output (console.log, print, debugger) in shipped code; use the project's logger.
- Performance: avoid N+1 queries (join or batch), paginate/limit unbounded queries, cache only measured hot spots.
- Data access behind a small repository/service interface so business logic can be tested with fakes. Keep API responses in one consistent shape (data, error, pagination meta).
- Testing: add or update tests for the behaviour you change; for a bug fix, add a test that fails without the fix. Use the repo's existing framework and layout. Structure tests Arrange-Act-Assert, name them after the behaviour, keep them isolated (no shared mutable state or order dependence), and assert on observable outputs and effects rather than internals. Fix the code, not the test, unless the test is wrong. Run the relevant tests before calling work done.
""",
    "python": """PYTHON RULES (adapted from ECC rules/python):
- PEP 8; type-annotate every function signature; use the repo's formatter/linter (often black or ruff, isort).
- Prefer immutable data: frozen dataclasses or NamedTuple for DTOs, tuples for fixed data; return new objects, do not mutate arguments.
- typing.Protocol for duck-typed interfaces; context managers (with) for resources; generators for lazy iteration.
- Catch specific exceptions, never bare except; chain with raise X from e.
- Secrets from os.environ or a settings object; bandit is the usual security scanner.
- FastAPI: create_app() factory; thin routers, logic in services; separate request/update/response schemas and always set response_model (never return password hashes or tokens). async def + async clients for I/O routes, no blocking calls (requests, sync DB) inside them. DB sessions and auth via Depends. Pydantic field constraints for validation. Per-environment CORS, never wildcard with credentials; check JWT exp/iss/aud/alg; redact auth headers in logs.
- Tests: pytest, test_*.py under tests/, fixtures + parametrize, pytest.mark for groups; run pytest. In FastAPI tests override the exact Depends target and clear app.dependency_overrides after.
""",
    "js": """TYPESCRIPT / JAVASCRIPT RULES (adapted from ECC rules/typescript):
- Give exported functions, shared utilities and public methods explicit parameter and return types; let inference handle obvious locals.
- interface for extendable object shapes; type for unions, tuples, mapped and utility types. Prefer string-literal unions over enum unless interop needs an enum. Name repeated inline object shapes.
- Avoid any. Take untrusted or external input as unknown and narrow it; use generics when the type depends on the caller.
- In .js files use JSDoc types where they help and keep them in sync with runtime behaviour.
- Immutable updates with spread / map / filter instead of mutating objects and arrays in place.
- async/await with try/catch; narrow caught errors (err instanceof Error) before reading properties; never leave a promise floating.
- Validate boundary data with a schema library (Zod or the repo's choice) and infer the TS type from the schema.
- No console.log in production code; use the project logger.
- Secrets only from process.env (or the platform equivalent); fail early if missing.
- Patterns: data access behind a repository interface; reusable stateful logic in custom hooks; one consistent API response shape.
- Tests: use the repo's runner (Vitest or Jest; npm test / npx vitest run). Co-locate *.test.ts or mirror src/ as the project does. Playwright for critical end-to-end flows. Assert on returned values and visible behaviour, not private internals.
""",
    "react": """REACT RULES (adapted from ECC rules/react):
- Function components only; typed props destructured in the signature; no React.FC. PascalCase components, useX hooks, onX props, isX/hasX booleans.
- Hooks at the top level only (never in loops, conditions or after returns); keep exhaustive-deps on.
- useEffect only syncs with external systems: compute derived values in render, reset state with a key, notify parents from handlers; clean up every subscription, timer and request.
- No memoization by default; useMemo/useCallback only for memo children, hook deps or measured cost. Functional setState when the next value depends on the last. No ref.current in render.
- State: local, then lifted, Context for low-frequency values, a store for hot shared state, a query cache (TanStack Query, SWR, RSC) for server data instead of fetch-in-useEffect. Never store derivable state.
- Stable keys (not the index for changing lists). An error boundary above every Suspense.
- RSC: server components by default, "use client" on line 1 only when needed, import "server-only" in secret modules; server actions validate, authenticate and authorize.
- Security: sanitize at any dangerouslySetInnerHTML; block javascript:/data: URLs; rel="noopener noreferrer" on target=_blank; NEXT_PUBLIC_/VITE_ vars are public; sessions in httpOnly cookies.
- Tests: Testing Library by role, label, text (testid last); await userEvent; findBy/waitFor, no sleeps; MSW for network; no snapshots or internal-state asserts.
""",
    "react-native": """REACT NATIVE / EXPO RULES (adapted from ECC rules/react-native):
- TS and React rules apply. Thin screens and route files: they wire params and hooks to components in components/ or features/. Web/DOM rules do not apply.
- One styling system; StyleSheet.create at module scope, no inline style objects on hot paths; colors and spacing from theme tokens.
- X.ios.tsx / X.android.tsx for big platform differences, Platform.select for small; safe-area-context, no hardcoded insets.
- Lists: FlatList/FlashList with stable keyExtractor and memoized renderItem; never map big arrays in a ScrollView.
- Server data via a query cache, validated with Zod; show loading, error and empty states. Route state in router params, not a store.
- Clean up listeners and timers; ignore async results after unmount. Reanimated / native driver for animation.
- Accessibility: role + label on every control (icon buttons too), accessibilityState, ~44pt/48dp targets, font scaling, not color alone.
- Security: the bundle is public (EXPO_PUBLIC_* too), no real secrets in it; tokens in expo-secure-store, never AsyncStorage; HTTPS; validate deep links and push payloads.
- Tests: jest-expo + @testing-library/react-native by role/label; mock Expo modules and expo-router; fresh QueryClient per test; Maestro/Detox for key flows; tsc --noEmit clean.
""",
    "vue": """VUE RULES (adapted from ECC rules/vue):
- <script setup lang="ts">, Composition API, no Options API in new code; order script, template, style scoped; PascalCase files, useXxx composables; vue-tsc clean.
- ref by default; reactive only for grouped objects, never reassigned. Never destructure reactive objects or Pinia stores without toRefs/storeToRefs.
- computed is pure. watch a getter (() => x.value); watchEffect stops tracking after its first await.
- Lifecycle hooks registered synchronously in setup; clean up in onUnmounted; DOM work after nextTick.
- Typed defineProps<Props>(), tuple defineEmits, defineModel for v-model. Stable primitive :key on v-for (not index); never v-if with v-for on one element.
- Composables take MaybeRefOrGetter + toValue. provide/inject with typed InjectionKey; expose readonly state plus an updater.
- Pinia setup stores. vue-query for server data: pass the ref itself in the key, never .value. Lazy routes.
- Security: no user templates or :is strings; no v-html on user content (DOMPurify if forced); only http/https/mailto in :href/:src; no user strings in :style or event attrs; VITE_* is public.
- Tests: Vitest + @vue/test-utils; await trigger/setValue, flushPromises; test props, emits, slots, output; createTestingPinia or fresh setActivePinia.
""",
    "nuxt": """NUXT RULES (adapted from ECC rules/nuxt):
- Vue rules apply. Check nuxt.config srcDir/dir overrides before placing files.
- Use auto-imports: no manual imports of useFetch/useState/navigateTo/defineStore; never add vue-router or hand-create app, Pinia or router.
- definePageMeta static only; reactive meta via useHead/useSeoMeta.
- nuxt.config is build-time; runtimeConfig root keys are server-only, .public and app.config.ts ship to the client (no secrets).
- useFetch/useAsyncData for first-paint data; $fetch only for events and mutations.
- Shared state via useState('key', init), JSON-serializable; never a module-scope ref() (leaks across SSR requests). One-time init in callOnce.
- Nitro: server/api/x.get.ts with defineEventHandler; throw createError({ status, statusText }); server middleware never returns a response. Route middleware uses to/from (not useRoute) and returns navigateTo/abortNavigation.
- Security: readValidatedBody / getValidatedQuery / getValidatedRouterParams with a schema; no secrets in useState or fetched payloads; forward cookies on SSR via useRequestFetch; never put user input in a server $fetch URL (SSRF).
- Tests: @nuxt/test-utils, Vitest env 'nuxt'; mountSuspended, mockNuxtImport, registerEndpoint; e2e via setup() + $fetch.
""",
    "angular": """ANGULAR RULES (adapted from ECC rules/angular):
- Check the Angular version in package.json first; verify with ng build.
- CLI naming, one artifact per file (x.component.ts/.html/.spec.ts), feature folders.
- Standalone + OnPush components; inject() over constructor injection; InjectionToken for non-class deps.
- Signals: computed for derived, linkedSignal for writable derived, resource() for async; effect only for side effects, never to sync signals. Never mutate inputs in place.
- @if/@for with track; no logic in templates beyond simple conditions.
- Keep the project's form strategy.
- Services own data and HttpClient, components delegate; presentational components only inputs/outputs. takeUntilDestroyed for subscriptions; switchMap for search, exhaustMap for submits, always catchError.
- Lazy routes, functional guards, canMatch for restricted routes, functional interceptors.
- SSR: no raw window/document/localStorage; use isPlatformBrowser or DOCUMENT.
- Security: no bypassSecurityTrust* without a documented reason; no untrusted [innerHTML] or [href]; guard every protected route (hidden UI is not access control); no secrets in environment.ts; tokens via interceptors; never log tokens.
- Tests: the configured runner; TestBed with standalone imports; setInput for signal inputs; CDK harnesses; HttpTestingController; fakeAsync/tick.
""",
    "web": """WEB / FRONTEND RULES (adapted from ECC rules/web):
- Organize by feature; semantic HTML before div stacks; design tokens as CSS custom properties, not repeated raw values.
- Animate only transform and opacity (sparingly filter/clip-path), never width/height/top/left/margin; narrow will-change; IntersectionObserver over scroll handlers; respect prefers-reduced-motion.
- Keep server state (query cache), client state, URL state (filters, sort, page, tab, search) and form state separate; never copy server data into stores; derive, do not store.
- Optimistic updates roll back with visible errors; fetch in parallel, avoid waterfalls.
- Compound components for complex widgets; containers own data, presentational parts stay pure; keyboard/ARIA/focus in the headless layer.
- Performance: images with width/height, lazy below the fold, AVIF/WebP, right-sized; max two fonts, font-display: swap; dynamic import for heavy libs; async/defer third-party scripts. Targets LCP < 2.5s, INP < 200ms, CLS < 0.1.
- Security: CSP with nonces, no unsafe-inline; never inject unsanitized HTML; SRI on CDN scripts; CSRF, rate limits and server validation on forms.
- Tests: unit-test utilities and hooks; automated a11y + keyboard checks; screenshots at key breakpoints for visual work; deterministic waits.
""",
    "dart": """DART / FLUTTER RULES (adapted from ECC rules/dart):
- dart format, trailing commas on multi-line lists; dart analyze clean.
- final locals, const constructors, unmodifiable collections from public APIs, copyWith for state.
- camelCase members, PascalCase types, snake_case files, _private.
- Avoid ! and late; use ?., ??, null checks, patterns; required for mandatory params.
- Sealed classes for closed states, exhaustive switch without a default.
- Catch specific types (on X), never Error subclasses; Result/sealed types for recoverable failures.
- await every Future or wrap in unawaited(); no async without await; Future.wait for concurrency; check context.mounted after await.
- package: imports, no ../ across features. Never edit generated .g.dart/.freezed.dart.
- Domain imports no Flutter or data packages; repositories map DTOs to entities; constructor injection.
- Security: no secrets in source (--dart-define is not secret); tokens in flutter_secure_storage, not SharedPreferences; HTTPS with timeouts; validate deep links (Uri.tryParse); parameterized SQL; WebView JS off unless needed.
- Tests: flutter test; test/unit, test/widget, integration_test/; mocktail or fakes; bloc_test; cover loading -> success and -> error.
""",
    "kotlin": """KOTLIN RULES (adapted from ECC rules/kotlin):
- Official style via the repo's ktlint/detekt.
- val over var; data classes; read-only collections in public APIs; state.copy() updates.
- camelCase members, PascalCase types, SCREAMING_SNAKE consts, no I prefix.
- Never !!; use ?., ?:, requireNotNull, ?.let; nullable returns for no result.
- Sealed types with exhaustive when, no else.
- Extensions in ReceiverExt.kt files, never on Any; scope functions at most two deep.
- Result or sealed errors, runCatching for throwing code; always rethrow CancellationException; no try/catch control flow.
- Structured concurrency (viewModelScope, coroutineScope, supervisorScope); StateFlow via stateIn(WhileSubscribed(5_000)). Repositories return Result from suspend funs and Flow streams. Constructor injection; use cases with operator invoke.
- Security: secrets from local.properties/CI, not source; EncryptedSharedPreferences/Keychain for tokens; HTTPS with timeouts; parameterized Room/SQLDelight; sanitize paths; R8 keep rules for serialized classes; WebView JS off unless needed.
- Tests: JUnit/kotlin.test, runTest, Turbine, fakes over mocks, in-memory DBs, backtick names; ./gradlew test.
""",
    "java": """JAVA RULES (adapted from ECC rules/java):
- The repo's formatter; one public top-level type per file; members ordered constants, fields, constructors, public, private.
- Records for DTOs, final fields by default, List.copyOf/Map.copyOf out of public APIs, new instances over mutation.
- PascalCase types, camelCase members, SCREAMING_SNAKE static finals, lowercase packages.
- Modern Java when available: sealed types, pattern matching, switch expressions, text blocks.
- Optional only as a finder return; map/orElseThrow, never bare get(); not for fields or params.
- Unchecked domain exceptions with context; broad catch (Exception) only at top-level handlers.
- Short streams without side effects; a loop when a pipeline gets hard to read.
- Thin controllers, logic in services, repositories behind interfaces; constructor injection only; map DTOs at boundaries.
- Security: secrets from env or a vault; PreparedStatement/parameter binding always; Bean Validation on DTOs; bcrypt/Argon2; authorize at service boundaries; never log tokens or PII; generic client errors without stack traces or SQL.
- Tests: JUnit 5 + AssertJ + Mockito, Testcontainers for DBs; src/test mirrors src/main; @ParameterizedTest; method_scenario_expected names; mvn test or ./gradlew test.
""",
    "go": """GO RULES (adapted from ECC rules/golang):
- gofmt and goimports are mandatory; go vet (and the repo's linter, e.g. golangci-lint) clean.
- Accept interfaces, return structs. Keep interfaces small (1-3 methods) and define them where they are consumed, not where implemented.
- Inject dependencies through constructor functions (NewService(repo Repo) *Service); use functional options for optional configuration.
- Errors are values: check every error, wrap with context using fmt.Errorf("doing x: %w", err), compare with errors.Is/errors.As; do not panic for expected failures.
- Pass context.Context as the first parameter of I/O functions and honour cancellation; set timeouts with context.WithTimeout and always defer cancel().
- Concurrency: every goroutine has a clear exit path; protect shared state with a mutex or channels; never leak goroutines.
- Close resources with defer right after acquiring them successfully.
- Security: secrets via os.Getenv with a startup check; parameterized database/sql queries; gosec is the usual static scanner.
- Tests: standard testing package with table-driven tests (t.Run per case) in _test.go files next to the code; use t.Helper and t.Cleanup; run go test -race ./... ; assert on returned values and errors, not on unexported internals.
""",
    "rust": """RUST RULES (adapted from ECC rules/rust):
- cargo fmt; cargo clippy -- -D warnings clean. snake_case fns, PascalCase types, SCREAMING_SNAKE consts.
- let over let mut; return new values; Cow for conditional allocation.
- Borrow by default, own only to store/consume; take &str and &[T]; impl Into<String> for owning constructors; no clones just to calm the borrow checker.
- Result + ?; thiserror in libraries, anyhow + .with_context() in apps; no unwrap()/expect() outside tests or truly unreachable code.
- Iterators for transformations, loops for complex flow. Modules by domain; private by default, pub(crate) inside, public API re-exported from lib.rs.
- Traits for repositories (in-memory impls in tests); newtypes against argument mix-ups; enum state machines, no _ arm on business enums; builders for many options.
- Security: env secrets with fail-fast; bound SQL parameters, never format!; parse input into typed structs at the boundary; minimal unsafe, each with a // SAFETY: comment; cargo audit/deny; no internal errors in responses.
- Tests: #[cfg(test)] mod tests in-file, integration tests in tests/; #[tokio::test]; rstest, proptest, mockall; names like returns_none_when_not_found; cargo test.
""",
    "swift": """SWIFT RULES (adapted from ECC rules/swift):
- The repo's SwiftFormat/SwiftLint config. Apple API Design Guidelines: clarity at the point of use, names by role, static let constants.
- let by default; structs by default, classes only for identity/reference semantics; enums with associated values for states.
- Throw specific error types (typed throws on Swift 6+) and pattern-match them; no force unwraps or try!; validate URL(string:) results.
- Strict concurrency: Sendable values across isolation, actors for shared mutable state (not locks/queues), async let and TaskGroup over loose Task {}.
- Small protocols with extension defaults; inject protocol deps with production defaults so tests pass fakes.
- Security: Keychain for tokens and keys, never UserDefaults; no secrets in source (use xcconfig/env); keep ATS on, pin critical endpoints; validate API, deep-link and pasteboard data.
- Tests: Swift Testing (@Test, #expect) for new tests, XCTest where already used; fresh state per test, nothing shared; @Test(arguments:) for cases; swift test or the Xcode scheme.
""",
    "cpp": """C++ RULES (adapted from ECC rules/cpp):
- Modern C++ (17/20/23 as the project targets); clang-format with the repo's config; clang-tidy clean.
- auto when the type is obvious, constexpr for compile-time constants, structured bindings.
- RAII everywhere: no manual new/delete or malloc/free; std::unique_ptr for ownership, std::shared_ptr only for genuinely shared ownership, make_unique/make_shared.
- Rule of Zero by default; if you define any of destructor, copy/move constructor or assignment, define all five.
- Pass small types by value, large ones by const&, return by value (RVO), move into sink parameters.
- Errors: exceptions for exceptional conditions, std::optional for maybe-absent values, std::expected or a result type for expected failures.
- Naming per project convention: PascalCase types, lowercase namespaces, consistent member suffix/prefix (name_ or m_), kConstant or UPPER_SNAKE constants.
- Memory safety: std::array/std::vector instead of C arrays, std::string instead of char*, never strcpy/strcat/sprintf (use std::string or fmt), .at() where bounds matter, avoid reinterpret_cast. Always initialize variables; avoid signed overflow and dangling pointers or references.
- Tests: GoogleTest/gmock driven by CMake/CTest (ctest --output-on-failure) or the repo's framework; run tests under AddressSanitizer and UBSan (-fsanitize=address,undefined) in CI.
""",
    "csharp": """C# RULES (adapted from ECC rules/csharp):
- Current .NET conventions, nullable reference types on, explicit access modifiers, file per primary type; dotnet format; no unused usings.
- record / record struct for immutable values, class for entities, interfaces at service boundaries; no dynamic.
- init setters, constructor params and immutable collections; do not mutate input models.
- await, never .Result/.Wait(); pass CancellationToken through public async APIs.
- Specific exceptions; structured logging properties, not concatenated strings.
- IOptions<T> for config; DI lifetimes on purpose (singleton stateless, scoped per request, transient light); split classes with too many deps.
- Security: no secrets in source or appsettings (user secrets locally, a vault in prod); parameterized EF Core/Dapper queries; allowlist dynamic sort/filter fields; validate DTOs before logic; framework auth + policies at endpoints; never log tokens or PII; no stack traces or SQL in responses.
- Tests: xUnit, fluent assertions, Moq/NSubstitute, Testcontainers; tests/ mirrors src/; WebApplicationFactory through real middleware; behaviour names; dotnet test.
""",
    "fsharp": """F# RULES (adapted from ECC rules/fsharp):
- fantomas; drop unused opens; group opens System, Microsoft, third-party, project, each sorted.
- Immutable by default, mutable only for measured performance; records with `with`; list/map/set; no ref cells in domain code.
- Discriminated unions and records over class hierarchies; single-case unions for validated primitives; classes only for interop.
- Small composable functions, |> pipelines, exhaustive pattern matching instead of if/else chains.
- Option instead of null; Result with railway composition for expected failures; computation expressions to chain them.
- task { } for .NET interop, async { } for F# workflows; pass CancellationToken.
- Focused modules with [<RequireQualifiedAccess>]; dependencies as function params or records of functions.
- Security: no secrets in source or appsettings; parameterized queries; validate into types at the boundary; framework auth; never log tokens or PII.
- Tests: xUnit + FsUnit/Unquote, FsCheck properties; tests/ mirrors src/; WebApplicationFactory; dotnet test.
""",
    "php": """PHP RULES (adapted from ECC rules/php):
- PSR-12; declare(strict_types=1); parameter, return and property types in new code. The repo's PHP-CS-Fixer/Pint and PHPStan/Psalm.
- use statements for every referenced class.
- Readonly DTOs and value objects across boundaries instead of shape-heavy arrays; value objects for money, IDs, date ranges.
- Throw exceptions, do not return false/null as a hidden error. Turn request input into validated DTOs before domain logic.
- Thin controllers (auth, validation, serialization, status); rules in services testable without HTTP. Constructor-injected narrow interfaces, no service locators. Wrap third-party SDKs in adapters.
- Security: validate at the boundary (FormRequest, Symfony Validator); escape output, justify raw HTML; prepared statements always; whitelist mass-assignable fields; secrets from env; password_hash/password_verify; regenerate session ID on login; CSRF on writes; composer audit.
- Tests: PHPUnit, or Pest if present (never both); unit tests apart from DB tests; factories over big arrays; vendor/bin/phpunit.
""",
    "ruby": """RUBY / RAILS RULES (adapted from ECC rules/ruby):
- The project's Ruby version and RuboCop config; frozen_string_literal where used; no inline cop disabling without a narrow reason.
- Plain Ruby over clever metaprogramming.
- Rails conventions first; extract service/query/form objects only when a model or controller does too much, named after the business operation.
- Controllers: auth, params, response shape. Views: rendering only.
- bin/rails, bin/rake and binstubs over global commands.
- Rescue specific exceptions; broad rescue only to re-raise with context. No puts/pp/debugger in app code.
- Security: CSRF on; strong params; secrets in credentials or env; Active Record APIs or bound params, never interpolated SQL; html_safe/raw are sensitive; validate uploads; rotate session on sign-in; jobs and webhooks are untrusted input.
- Tests: Minitest (bin/rails test) or RSpec (bundle exec rspec), whichever exists, not both. Model/service tests for logic, request tests for HTTP and auth, system tests only for critical flows. Regression test before a bug fix.
""",
    "perl": """PERL RULES (adapted from ECC rules/perl):
- use v5.36 (strict, warnings, say, signatures); subroutine signatures instead of unpacking @_; say instead of print with "\\n".
- OO with Moo (or the project's Moose): read-only attributes (is => 'ro') typed with Types::Standard; no raw blessed hashrefs.
- Format with perltidy and lint with perlcritic (including the security theme) using the repo's config.
- Modules export with Exporter 'import' and @EXPORT_OK only, never @EXPORT. Dependencies in cpanfile (carton for reproducible installs).
- Files: three-argument open with autodie (or Path::Tiny), never two-argument open; resolve user-supplied paths with Cwd::realpath and check they stay under the allowed root.
- Processes: list-form system() or IPC::Run3; never single-string system or backticks with interpolated variables. Sanitize %ENV (PATH etc.) before running commands.
- Taint mode (-T) for web-facing scripts; untaint with strict allowlist regexes, never /(.*)/.
- SQL through DBI placeholders (or DBIx::Class), never interpolated strings; data access behind a repository module.
- Tests: Test2::V0 for new tests, .t files under t/, end every file with done_testing; run with prove -lr t; Test::MockModule to mock existing modules.
""",
    "arkts": """ARKTS / HARMONYOS RULES (adapted from ECC rules/arkts):
- ArkTS is a strict TS subset; breaking it fails compilation. No any/unknown, intersection, mapped or conditional types, as const or structural typing; only Partial/Required/Readonly/Record.
- No function expressions, nested functions, generators, call/apply/bind, destructuring, delete, in, obj["key"], index signatures, var, for...in, #private, require or globalThis. Imports first; full type annotations; spread only into arrays.
- camelCase vars, PascalCase classes and component files, UPPER_SNAKE consts; one @ComponentV2 per file, under ~400 lines.
- State V2 only (@ComponentV2, @Local, @Param, @Event, @Provider/@Consumer, @Monitor, @Computed, @ObservedV2 + @Trace); never V1 (@State, @Prop, @Link, @Watch, @Component).
- Navigation + NavPathStack, never @ohos.router.
- MVVM: build() only renders, logic in ViewModels, I/O in services. LazyForEach for long lists; $r() resources.
- Animate transform/opacity, never width/height/padding.
- Security: permissions in module.json5 with reasons, runtime requests with fallback; no secrets in source, Keystore for credentials; HTTPS; validate deep links; never log tokens.
- Tests: src/ohosTest/ets/test/; mock network/system APIs; should_x_when_y names; build with hvigorw assembleHap.
""",
}
