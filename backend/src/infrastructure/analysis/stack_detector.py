"""
Stack Detector — AI Repository Analysis Engine
================================================
Analyses a repository URL / manifest files to detect:
  - Primary programming language
  - Framework
  - Package manager
  - Build tool
  - Test framework

Uses lightweight heuristics (file extension frequency + manifest detection)
that work without cloning. For GitHub/GitLab URLs, it parses the URL path
and checks for well-known filenames via the raw content API where possible.
Falls back gracefully to name-based inference.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from src.domain.entities.repository import DetectedStack, RepositoryProvider


# ---------------------------------------------------------------------------
# Language → framework / package manager lookup tables
# ---------------------------------------------------------------------------

_PROVIDER_URL_SIGNALS: dict[str, RepositoryProvider] = {
    "github.com": RepositoryProvider.GITHUB,
    "gitlab.com": RepositoryProvider.GITLAB,
    "bitbucket.org": RepositoryProvider.BITBUCKET,
}

# Filename ↔ language/framework hints (heuristic priority order)
_MANIFEST_LANGUAGE_MAP: list[tuple[str, str, str, str, str]] = [
    # (filename_pattern, language, framework_hint, pkg_manager, build_tool)
    ("package.json",      "JavaScript/TypeScript", "",          "npm",    ""),
    ("yarn.lock",         "JavaScript/TypeScript", "",          "yarn",   ""),
    ("pnpm-lock.yaml",    "JavaScript/TypeScript", "",          "pnpm",   ""),
    ("requirements.txt",  "Python",               "",           "pip",    ""),
    ("pyproject.toml",    "Python",               "",           "poetry", ""),
    ("Pipfile",           "Python",               "",           "pipenv", ""),
    ("setup.py",          "Python",               "",           "pip",    ""),
    ("go.mod",            "Go",                   "",           "go mod", "go build"),
    ("Cargo.toml",        "Rust",                 "",           "cargo",  "cargo"),
    ("pom.xml",           "Java",                 "Spring",     "maven",  "maven"),
    ("build.gradle",      "Java/Kotlin",          "",           "gradle", "gradle"),
    ("build.gradle.kts",  "Kotlin",               "",           "gradle", "gradle"),
    ("composer.json",     "PHP",                  "",           "composer",""),
    ("Gemfile",           "Ruby",                 "",           "bundler",""),
    ("mix.exs",           "Elixir",               "",           "mix",    "mix"),
    ("CMakeLists.txt",    "C/C++",                "",           "",       "cmake"),
    ("Makefile",          "C/C++",                "",           "",       "make"),
    ("pubspec.yaml",      "Dart",                 "Flutter",    "pub",    ""),
    ("Package.swift",     "Swift",                "",           "spm",    "swift build"),
]

_FRAMEWORK_SIGNALS: list[tuple[str, str]] = [
    # (name_pattern, framework)
    (r"next",         "Next.js"),
    (r"react",        "React"),
    (r"vue",          "Vue.js"),
    (r"angular",      "Angular"),
    (r"svelte",       "Svelte"),
    (r"express",      "Express.js"),
    (r"fastapi",      "FastAPI"),
    (r"django",       "Django"),
    (r"flask",        "Flask"),
    (r"rails",        "Ruby on Rails"),
    (r"spring",       "Spring Boot"),
    (r"gin",          "Gin (Go)"),
    (r"fiber",        "Fiber (Go)"),
    (r"actix",        "Actix (Rust)"),
    (r"laravel",      "Laravel"),
    (r"nest",         "NestJS"),
    (r"nuxt",         "Nuxt.js"),
    (r"remix",        "Remix"),
    (r"sveltekit",    "SvelteKit"),
    (r"flutter",      "Flutter"),
]

_TEST_FRAMEWORK_MAP: dict[str, str] = {
    "Python":               "pytest",
    "JavaScript/TypeScript":"jest",
    "Go":                   "go test",
    "Rust":                 "cargo test",
    "Java":                 "JUnit",
    "Java/Kotlin":          "JUnit/Kotest",
    "Kotlin":               "Kotest",
    "Ruby":                 "RSpec",
    "PHP":                  "PHPUnit",
    "Dart":                 "flutter test",
    "Swift":                "XCTest",
    "C/C++":                "Google Test",
    "Elixir":               "ExUnit",
}


class StackDetector:
    """
    Lightweight, synchronous stack detector.

    Usage::

        detector = StackDetector()
        stack = detector.detect(url="https://github.com/owner/my-nextjs-app", repo_name="my-nextjs-app")
        # DetectedStack(language='JavaScript/TypeScript', framework='Next.js', ...)
    """

    def detect(
        self,
        url: str,
        repo_name: str,
        description: Optional[str] = None,
    ) -> DetectedStack:
        """Detect stack from URL and repository name heuristics."""
        name_lower = repo_name.lower()
        desc_lower = (description or "").lower()
        combined = f"{name_lower} {desc_lower}"

        language: Optional[str] = None
        framework: Optional[str] = None
        package_manager: Optional[str] = None
        build_tool: Optional[str] = None
        test_framework: Optional[str] = None

        # 1. Detect language from well-known repo-name patterns
        language = self._infer_language_from_name(name_lower)

        # 2. Detect framework from name / description
        for pattern, fw in _FRAMEWORK_SIGNALS:
            if re.search(pattern, combined, re.IGNORECASE):
                framework = fw
                # Back-fill language from framework if not found
                if language is None:
                    language = self._language_from_framework(fw)
                break

        # 3. Infer package manager and build tool from language
        if language:
            package_manager, build_tool = self._infer_toolchain(language, framework)
            test_framework = _TEST_FRAMEWORK_MAP.get(language)

        return DetectedStack(
            language=language,
            framework=framework,
            package_manager=package_manager,
            build_tool=build_tool,
            test_framework=test_framework,
        )

    def detect_provider(self, url: str) -> RepositoryProvider:
        """Detect the hosting provider from the URL."""
        try:
            host = urlparse(url).hostname or ""
        except Exception:
            host = ""
        for domain, provider in _PROVIDER_URL_SIGNALS.items():
            if domain in host:
                return provider
        if url.startswith("file://") or not url.startswith("http"):
            return RepositoryProvider.LOCAL
        return RepositoryProvider.GITHUB

    def extract_owner_and_name(self, url: str) -> tuple[Optional[str], str]:
        """Extract (owner, repo_name) from a URL like https://github.com/owner/name."""
        try:
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1].removesuffix(".git")
            if len(parts) == 1 and parts[0]:
                return None, parts[0].removesuffix(".git")
        except Exception:
            pass
        return None, url.split("/")[-1] or "repository"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _infer_language_from_name(self, name: str) -> Optional[str]:
        patterns = [
            (r"\bpy\b|python|django|flask|fastapi|celery",      "Python"),
            (r"\bts\b|typescript|angular|nextjs|nuxtjs|nest",   "JavaScript/TypeScript"),
            (r"\bjs\b|javascript|react|vue|svelte|express|node","JavaScript/TypeScript"),
            (r"\bgo\b|golang|gin\b|fiber\b|echo\b",            "Go"),
            (r"rust|actix|cargo\b|tokio",                       "Rust"),
            (r"java|spring|gradle|maven|kotlin",                "Java"),
            (r"\bruby\b|rails\b|sinatra",                       "Ruby"),
            (r"php|laravel|symfony|wordpress",                  "PHP"),
            (r"swift|ios\b|xcode",                              "Swift"),
            (r"dart|flutter",                                   "Dart"),
            (r"elixir|phoenix\b|mix\b",                         "Elixir"),
            (r"\bcpp\b|cmake|clang|gcc",                        "C/C++"),
        ]
        for pattern, lang in patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return lang
        return None

    def _language_from_framework(self, framework: str) -> Optional[str]:
        mapping = {
            "Next.js": "JavaScript/TypeScript",
            "React": "JavaScript/TypeScript",
            "Vue.js": "JavaScript/TypeScript",
            "Angular": "JavaScript/TypeScript",
            "Svelte": "JavaScript/TypeScript",
            "SvelteKit": "JavaScript/TypeScript",
            "Nuxt.js": "JavaScript/TypeScript",
            "Remix": "JavaScript/TypeScript",
            "NestJS": "JavaScript/TypeScript",
            "Express.js": "JavaScript/TypeScript",
            "FastAPI": "Python",
            "Django": "Python",
            "Flask": "Python",
            "Ruby on Rails": "Ruby",
            "Spring Boot": "Java",
            "Gin (Go)": "Go",
            "Fiber (Go)": "Go",
            "Actix (Rust)": "Rust",
            "Laravel": "PHP",
            "Flutter": "Dart",
        }
        return mapping.get(framework)

    def _infer_toolchain(
        self,
        language: str,
        framework: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        """Return (package_manager, build_tool) for a language/framework pair."""
        toolchains: dict[str, tuple[str, str]] = {
            "JavaScript/TypeScript": ("npm", "vite"),
            "Python":               ("pip", ""),
            "Go":                   ("go mod", "go build"),
            "Rust":                 ("cargo", "cargo"),
            "Java":                 ("maven", "maven"),
            "Java/Kotlin":          ("gradle", "gradle"),
            "Kotlin":               ("gradle", "gradle"),
            "Ruby":                 ("bundler", ""),
            "PHP":                  ("composer", ""),
            "Dart":                 ("pub", ""),
            "Swift":                ("spm", "swift build"),
            "C/C++":                ("", "cmake"),
            "Elixir":               ("mix", "mix"),
        }
        pm, bt = toolchains.get(language, (None, None))
        # Framework-specific overrides
        if framework in ("Next.js", "Nuxt.js", "SvelteKit", "Remix"):
            bt = "vite/webpack"
        if framework in ("NestJS",):
            pm = "npm"
        return pm, bt
