#!/usr/bin/env python3
"""
Quick diagnostic script to test LM Studio connectivity and performance.
Tests small, medium, and large payloads to find where it breaks.
"""

import httpx
import time
import sys
import os

# Load env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

LMSTUDIO_URL = os.environ.get("LMSTUDIO_API_URL", "http://localhost:1234/v1/chat/completions")

def test_connectivity():
    """Test basic connectivity to LM Studio."""
    print(f"Testing: {LMSTUDIO_URL}")
    print(f"Base URL: {LMSTUDIO_URL.rsplit('/v1/', 1)[0]}/v1/models")
    print()

    # List models
    base = LMSTUDIO_URL.rsplit("/v1/", 1)[0]
    try:
        r = httpx.get(f"{base}/v1/models", timeout=5)
        models = r.json().get("data", [])
        print(f"[OK] Connected! Models loaded: {len(models)}")
        for m in models:
            print(f"     - {m['id']}")
        print()
    except Exception as e:
        print(f"[FAIL] Cannot reach LM Studio: {e}")
        return False
    return True


def test_request(label: str, prompt: str, model: str = "google/gemma-3-12b", max_tokens: int = 200):
    """Send a test request and measure response time."""
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": "You are a data extraction assistant. Return JSON only."},
            {"role": "user", "content": prompt},
        ],
    }

    prompt_chars = len(prompt)
    print(f"[{label}] Sending {prompt_chars:,} chars to {model}...")

    start = time.perf_counter()
    try:
        r = httpx.post(LMSTUDIO_URL, json=payload, timeout=300)
        elapsed = time.perf_counter() - start
        r.raise_for_status()
        data = r.json()

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        content = data["choices"][0]["message"]["content"][:200]

        print(f"[OK]  {elapsed:.1f}s | prompt_tokens={prompt_tokens} | completion_tokens={completion_tokens}")
        print(f"      Response preview: {content[:100]}...")
        print()
        return elapsed
    except httpx.TimeoutException:
        elapsed = time.perf_counter() - start
        print(f"[TIMEOUT] Timed out after {elapsed:.1f}s")
        print()
        return None
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"[FAIL] Error after {elapsed:.1f}s: {e}")
        print()
        return None


def main():
    print("=" * 60)
    print("LM Studio Diagnostic Test")
    print("=" * 60)
    print()

    if not test_connectivity():
        sys.exit(1)

    # Test 1: Tiny request (should be instant)
    test_request(
        "TINY (100 chars)",
        'Extract companies: Acme Corp (AI), Foo Inc (Fintech). Return JSON array.',
    )

    # Test 2: Small request (~2K chars)
    small_prompt = "Extract all company names from this portfolio page:\n\n" + "\n".join(
        f"- Company{i} is a {sector} startup founded in {2015+i%10}"
        for i, sector in enumerate(["AI", "Fintech", "SaaS", "Healthcare", "DeepTech"] * 20)
    )
    test_request("SMALL (2K chars)", small_prompt)

    # Test 3: Medium request (~10K chars)
    medium_prompt = "Extract all portfolio companies from this HTML:\n\n" + "\n".join(
        f"<div class='company'><h3>Company{i}</h3><p>{sector} startup, founded {2015+i%10}, "
        f"raised ${i*2}M, based in San Francisco. CEO: John Doe{i}.</p></div>"
        for i, sector in enumerate(["AI", "Fintech", "SaaS", "Healthcare", "DeepTech", "Climate", "Crypto"] * 30)
    )
    test_request("MEDIUM (10K chars)", medium_prompt[:10_000])

    # Test 4: Large request (~30K chars)
    test_request("LARGE (30K chars)", medium_prompt[:30_000], max_tokens=4096)

    # Test 5: XL request (~50K chars)
    xl_prompt = medium_prompt * 5
    test_request("XL (50K chars)", xl_prompt[:50_000], max_tokens=4096)

    print("=" * 60)
    print("Done! If LARGE/XL timeout, reduce MAX_HTML_CHARS or use cloud fallback.")
    print("=" * 60)


if __name__ == "__main__":
    main()
