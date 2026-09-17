import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.database.connection import SessionLocal
from backend.app.evaluation.benchmark import BenchmarkEvaluator

def main():
    print("=" * 80)
    print("       SIH26108: AI-POWERED INDIAN STANDARDS RECOMMENDATION BENCHMARK")
    print("=" * 80)
    
    db = SessionLocal()
    evaluator = BenchmarkEvaluator(db)
    metrics = evaluator.run_benchmark()
    db.close()

    print("\n--- SUMMARY IR EVALUATION METRICS ---")
    print(f"  • Total Evaluation Scenarios : {metrics['total_queries_evaluated']}")
    print(f"  • Precision @ 1 (P@1)        : {metrics['mean_precision_at_1'] * 100:.2f}%")
    print(f"  • Precision @ 3 (P@3)        : {metrics['mean_precision_at_3'] * 100:.2f}%")
    print(f"  • Precision @ 5 (P@5)        : {metrics['mean_precision_at_5'] * 100:.2f}%")
    print(f"  • Recall @ 5 (R@5)           : {metrics['mean_recall_at_5'] * 100:.2f}%")
    print(f"  • Mean Reciprocal Rank (MRR) : {metrics['mean_reciprocal_rank_mrr']:.4f}")
    print(f"  • Normalized DCG (nDCG@5)    : {metrics['mean_ndcg_at_5']:.4f}")
    print(f"  • Average Latency per Query  : {metrics['avg_latency_ms']:.2f} ms")
    print(f"  • Hallucination Rate         : {metrics['hallucination_rate']}")
    
    print("\n--- SAMPLE QUERY BREAKDOWN ---")
    for r in metrics["detailed_query_results"][:5]:
        print(f"\n[Query #{r['id']}]: {r['query']}")
        print(f"  Expected  : {', '.join(r['expected'])}")
        print(f"  Retrieved : {', '.join(r['retrieved'])}")
        print(f"  P@1: {r['p_at_1']} | MRR: {r['mrr']} | Latency: {r['latency_ms']}ms")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
