import requests
import time
import statistics

# -----------------------------
# CONFIGURATION
# -----------------------------
SEARCH_SERVICE_NAME = "<your-search-service-name>"   # e.g., mysearchsvc
INDEX_NAME = "<your-index-name>"                     # e.g., documents-index
API_KEY = "<your-api-key>"                           # query key or admin key
API_VERSION = "2023-07-01-Preview"

# Sample query for RAG-style testing
QUERY = "test query for latency measurement"

# Number of requests to run
NUM_REQUESTS = 100

# -----------------------------
# BUILD REQUEST
# -----------------------------
url = f"https://{SEARCH_SERVICE_NAME}.search.windows.net/indexes/{INDEX_NAME}/docs/search?api-version={API_VERSION}"

headers = {
    "Content-Type": "application/json",
    "api-key": API_KEY
}

payload = {
    "search": QUERY,
    "top": 5
}

# -----------------------------
# RUN LATENCY TEST
# -----------------------------
total_latencies = []
service_latencies = []
network_latencies = []

print(f"Running {NUM_REQUESTS} requests...\n")

for i in range(NUM_REQUESTS):
    start = time.time()

    response = requests.post(url, headers=headers, json=payload)

    end = time.time()
    total_latency_ms = (end - start) * 1000

    # Extract Azure Search service execution time
    # Header name can vary: "elapsed-time" or "x-ms-elapsed-time"
    service_time_ms = None

    if "elapsed-time" in response.headers:
        service_time_ms = float(response.headers["elapsed-time"])
    elif "x-ms-elapsed-time" in response.headers:
        service_time_ms = float(response.headers["x-ms-elapsed-time"])

    if service_time_ms is not None:
        network_time_ms = total_latency_ms - service_time_ms
        service_latencies.append(service_time_ms)
        network_latencies.append(network_time_ms)

    total_latencies.append(total_latency_ms)

    print(f"Request {i+1}: Total={total_latency_ms:.2f} ms | "
          f"Service={service_time_ms:.2f if service_time_ms else -1} ms")

# -----------------------------
# SUMMARY STATS
# -----------------------------
def summarize(name, arr):
    if len(arr) == 0:
        return f"{name}: No data"
    return (
        f"{name}:\n"
        f"  Avg:  {statistics.mean(arr):.2f} ms\n"
        f"  P50:  {statistics.median(arr):.2f} ms\n"
        f"  P95:  {sorted(arr)[int(len(arr)*0.95)-1]:.2f} ms\n"
        f"  Min:  {min(arr):.2f} ms\n"
        f"  Max:  {max(arr):.2f} ms\n"
    )

print("\n==================== RESULTS ====================\n")
print(summarize("Total Latency (End-to-End)", total_latencies))
print(summarize("Service Latency (Azure AI Search)", service_latencies))
print(summarize("Network Latency (Derived)", network_latencies))

print("================================================\n")