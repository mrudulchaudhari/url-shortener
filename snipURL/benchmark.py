"""
Simple benchmark tool to measure redirect latency.
Run: python benchmark.py
"""
import time
import statistics
import requests
from urllib.parse import urljoin

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your production URL
SHORT_CODE = "1"  # Change to an actual short code
NUM_REQUESTS = 100

def measure_redirect_time(url):
    """Measure time to get redirect response (not following redirect)."""
    start = time.time()
    try:
        # Don't follow redirects, just get the 302 response
        response = requests.get(url, allow_redirects=False, timeout=5)
        duration = (time.time() - start) * 1000  # Convert to milliseconds

        if response.status_code == 302:
            return duration, True
        else:
            return duration, False
    except Exception as e:
        print(f"Error: {e}")
        return None, False

def run_benchmark():
    """Run benchmark and display results."""
    print("=" * 60)
    print("SnipURL Redirect Latency Benchmark")
    print("=" * 60)
    print(f"Target: {BASE_URL}/{SHORT_CODE}")
    print(f"Requests: {NUM_REQUESTS}")
    print("-" * 60)

    latencies = []
    successful = 0
    failed = 0

    print("\nRunning benchmark", end="", flush=True)

    for i in range(NUM_REQUESTS):
        if i % 10 == 0:
            print(".", end="", flush=True)

        url = urljoin(BASE_URL, SHORT_CODE)
        duration, success = measure_redirect_time(url)

        if success and duration:
            latencies.append(duration)
            successful += 1
        else:
            failed += 1

    print(" Done!\n")

    if not latencies:
        print("❌ All requests failed!")
        return

    # Calculate statistics
    mean = statistics.mean(latencies)
    median = statistics.median(latencies)
    min_time = min(latencies)
    max_time = max(latencies)

    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

    # Display results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Successful requests:  {successful}/{NUM_REQUESTS}")
    print(f"Failed requests:      {failed}/{NUM_REQUESTS}")
    print()

    print("Latency Statistics (milliseconds):")
    print("-" * 60)
    print(f"  Minimum:            {min_time:>8.2f} ms")
    print(f"  Mean:               {mean:>8.2f} ms")
    print(f"  Median:             {median:>8.2f} ms")
    print(f"  Maximum:            {max_time:>8.2f} ms")
    print()
    print(f"  50th percentile:    {p50:>8.2f} ms")
    print(f"  95th percentile:    {p95:>8.2f} ms")
    print(f"  99th percentile:    {p99:>8.2f} ms")
    print()

    # Performance rating
    if mean < 10:
        rating = "🚀 EXCELLENT - Lightning fast!"
    elif mean < 50:
        rating = "✅ GOOD - Very fast"
    elif mean < 100:
        rating = "👍 ACCEPTABLE - Fast enough"
    elif mean < 200:
        rating = "⚠️  SLOW - Could be better"
    else:
        rating = "❌ VERY SLOW - Needs optimization"

    print(f"Performance Rating: {rating}")
    print()

    # Cache analysis
    if len(latencies) > 1:
        first_request = latencies[0]
        avg_subsequent = statistics.mean(latencies[1:])

        print("Cache Performance:")
        print("-" * 60)
        print(f"  First request:      {first_request:>8.2f} ms (cold)")
        print(f"  Subsequent avg:     {avg_subsequent:>8.2f} ms (warm)")
        print(f"  Cache speedup:      {first_request/avg_subsequent:>8.2f}x")
        print()

    # Requests per second
    total_time = sum(latencies) / 1000  # Convert to seconds
    rps = NUM_REQUESTS / total_time if total_time > 0 else 0
    print(f"Throughput:         {rps:>8.2f} requests/second")
    print()

    # Comparison with industry
    print("Industry Comparison:")
    print("-" * 60)
    print(f"  Your server:        {mean:>8.2f} ms")
    print(f"  bit.ly (~average):  {30:>8} ms")
    print(f"  tinyurl (~average): {40:>8} ms")
    print()

    if mean < 30:
        print("🎉 You're faster than most commercial URL shorteners!")
    elif mean < 50:
        print("✅ You're competitive with commercial services!")
    else:
        print("⚠️  Room for improvement - check LATENCY_ANALYSIS.md")

    print("=" * 60)

if __name__ == "__main__":
    try:
        run_benchmark()
    except KeyboardInterrupt:
        print("\n\n❌ Benchmark cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("Make sure:")
        print("  1. Server is running")
        print("  2. BASE_URL is correct")
        print("  3. SHORT_CODE exists")
        print("  4. Install requests: pip install requests")
