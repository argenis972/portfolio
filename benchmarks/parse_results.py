import json
import statistics

def parse_k6_results(file_path):
    scenarios = {}

    with open(file_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('metric') == 'health_latency_ms':
                    scenario = data['data']['tags']['scenario']
                    value = data['data']['value']
                    if scenario not in scenarios:
                        scenarios[scenario] = []
                    scenarios[scenario].append(value)
            except:
                continue

    for scenario, values in scenarios.items():
        if values:
            p95 = statistics.quantiles(values, n=20)[18] # 19th 5-percentile is p95
            p99 = statistics.quantiles(values, n=100)[98]
            print(f"Scenario: {scenario}")
            print(f"  Count: {len(values)}")
            print(f"  Avg: {sum(values)/len(values):.2f}ms")
            print(f"  P95: {p95:.2f}ms")
            print(f"  P99: {p99:.2f}ms")
            print(f"  Max: {max(values):.2f}ms")

if __name__ == "__main__":
    parse_k6_results('benchmarks/results/3775843/health.json')
