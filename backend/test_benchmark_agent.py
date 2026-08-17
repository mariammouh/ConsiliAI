from agents.tools import generate_benchmark_evaluation, extract_literature_results
import json

experiment = {
    "title": "Scalability Analysis of Heterogeneous Transformer for Fake News Detection",
    "dataset": {"name": "PolitiFact", "grounded": True},
    "baseline_methods": ["Transformer decoder", "Self-attentions + BiLSTM"],
    "evaluation_metrics": ["Accuracy", "F1 Score", "Inference Time (ms per sample)", "Training Time (seconds per epoch)"],
    "expected_outcome_or_hypothesis": "HetTransformer is expected to achieve superior Accuracy/F1 as reported in the literature, but may incur higher computational cost than the baselines.",
    "related_paper_evidence": [
        {
            "paper": "Fake News Detection with Heterogeneous Transformer",
            "claim": "The paper reports superior performance (e.g., Accuracy of 0.913, F1 Score of 0.927 on PolitiFact) but does not discuss computational complexity, inference time, or scalability challenges."
        }
    ],
}

papers_with_analysis = [
    {
        "title": "Fake News Detection with Heterogeneous Transformer",
        "analysis": {
            "results": {
                "metrics": "Accuracy, F1 Score",
                "baselines_compared": "Transformer decoder, Self-attentions + BiLSTM",
                "reported_numbers": (
    "HetTransformer achieved Accuracy of 0.913 and F1 Score of 0.927 on PolitiFact. "
    "Transformer decoder achieved Accuracy of 0.87 and F1 Score of 0.88 on PolitiFact. "
    "Self-attentions + BiLSTM achieved Accuracy of 0.85 and F1 Score of 0.86 on PolitiFact. "
    "HetTransformer inference time: 38 ms per sample, training time: 95 seconds per epoch."
),
                "key_improvements": "HetTransformer outperforms baselines by combining structural and content embeddings.",
            }
        },
    }
]

# deliberately mixed: HetTransformer underperforms vs paper (lower), Transformer decoder
# nearly matches (match), inference/training time have no literature counterpart at all
# (no_literature_match) — exercises all three delta_direction branches.
submission_text = """
Experiment Report — HetTransformer Scalability Test

We reproduced HetTransformer and the two baseline models on the PolitiFact dataset.

Results:
- HetTransformer: Accuracy 91.0%, F1 Score 92.5%
- Transformer decoder: Accuracy 87.1%, F1 Score 88.3%
- Self-attentions + BiLSTM: Accuracy 84.6%, F1 Score 85.9%

Timing (measured on a single RTX 3060):
- HetTransformer inference time: 45 ms per sample
- HetTransformer training time: 120 seconds per epoch
"""

print("--- raw literature extraction ---")
print(papers_with_analysis[0]["analysis"]["results"]["reported_numbers"])
print(json.dumps(extract_literature_results(papers_with_analysis[0]), indent=2))
print("--- full evaluation ---")

result = generate_benchmark_evaluation(experiment, papers_with_analysis, submission_text)
print(json.dumps(result, indent=2))