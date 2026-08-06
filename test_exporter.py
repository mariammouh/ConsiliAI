"""
Standalone test script for course_pptx_exporter.py
Run: python test_exporter.py
"""

import os
import sys
import json

# ============================================================
# COURSE TEST DATA (from your uploaded JSON)
# ============================================================

COURSE_DATA = {
    "course_title": "Advanced Fake News Detection: From Transformer Architectures to Social Network Dynamics",
    "target_audience": "Graduate students and researchers in Data Science or AI with prior knowledge of machine learning fundamentals and basic graph theory.",
    "learning_objectives": [
        "Understand the limitations of text-only fake news detection models.",
        "Analyze how heterogeneous graph structures and social context improve detection accuracy.",
        "Evaluate the generalization capabilities of Transformer-based models across different datasets.",
        "Critically assess the robustness of current models against modern misinformation threats."
    ],
    "modules": [
        {
            "module_title": "Foundations of Fake News Detection and Generalization Challenges",
            "difficulty": "beginner",
            "problem_addressed": "The lack of fact-checking mechanisms on social media and the poor cross-domain generalization capabilities of existing detection models.",
            "solution_approach": "Systematic empirical benchmarking of 12 representative methods (from traditional ML to LLMs) across 10 heterogeneous datasets.",
            "based_on_papers": [
                {
                    "title": "An Experimental Comparison of the Most Popular Approaches to Fake News Detection",
                    "authors": "Various",
                    "year": "2024"
                }
            ],
            "lessons": [
                {
                    "lesson_title": "Foundations of Fake News Detection and Generalization Challenges",
                    "objectives_covered": [
                        "Taxonomy of fake news detection methods",
                        "The domain shift problem in social media",
                        "Benchmarking performance: F1-score, precision, and recall",
                        "Evaluating LLMs vs. traditional ML and BERT-based models"
                    ],
                    "sections": [
                        {
                            "topic": "Taxonomy of fake news detection methods",
                            "explanation": "The landscape of fake news detection is categorized into three primary tiers of complexity. First, traditional machine learning methods, such as Logistic Regression (LR), Support Vector Machines (SVM), and Naive Bayes (NB), rely on feature extraction techniques like TF-IDF to represent text. Second, deep learning architectures, including CNNs and BiLSTMs, utilize Word2Vec embeddings to capture sequential patterns. Third, modern transformer-based models and Large Language Models (LLMs) represent the state-of-the-art. This includes BERT and DeBERTa, which leverage sophisticated contextual embeddings, and generative models like Llama3-8B, Qwen3-32B, and Zephyr-7B-beta. These methods vary significantly in their architectural requirements; while traditional models are lightweight and rely on statistical word frequency, transformer-based models require fine-tuning on large pre-trained weights, and LLMs can be deployed in zero-shot or few-shot settings without requiring weight updates. Understanding this taxonomy is essential because the choice of architecture dictates how the model interprets linguistic nuances and handles the inherent noise found in social media data.",
                            "example_or_evidence": "The study systematically benchmarks 12 representative methods, ranging from traditional algorithms like NB and SVM to advanced architectures like CNN-BERT, MERMAID, and LLMs such as Llama3-8B and Qwen3-32B, providing a comprehensive view of the detection ecosystem.",
                            "key_terms": {
                                "TF-IDF": "A statistical measure used to evaluate the importance of a word in a document relative to a collection of documents.",
                                "Word2Vec": "A neural network-based technique for generating word embeddings that capture semantic relationships.",
                                "Transformer-based models": "Deep learning architectures that use self-attention mechanisms to process sequential data, such as BERT and DeBERTa.",
                                "Zero-shot setting": "A scenario where a model makes predictions on classes or tasks it has never seen during training.",
                                "Few-shot prompting": "Providing a language model with a small number of examples to guide its predictions on new tasks."
                            }
                        },
                        {
                            "topic": "The domain shift problem in social media",
                            "explanation": "The domain shift problem refers to the critical failure of detection models to maintain performance when moving from one dataset to another. In social media, fact-checking and labeling policies are highly heterogeneous; a model trained on political news may fail when applied to health-related misinformation due to differences in vocabulary, tone, and the underlying criteria for what constitutes 'fake' news. This lack of cross-domain generalization is a primary obstacle in real-world deployment. Because social media platforms lack centralized control and consistent fact-checking mechanisms, models often overfit to the specific biases or labeling styles of their training data. When these models encounter new, unseen domains, their predictive accuracy drops significantly. The study addresses this by testing models across 10 heterogeneous datasets, simulating real-world scenarios where the distribution of data is constantly changing, thereby highlighting the fragility of standard approaches that lack robust generalization capabilities.",
                            "example_or_evidence": "The research identifies a critical failure in generalization for most standard approaches, noting that while fine-tuned models perform well in-domain, they struggle significantly when evaluated in cross-domain settings, necessitating the exploration of more robust architectures.",
                            "key_terms": {
                                "Domain shift": "The degradation in model performance when applied to data from a different distribution than the training data.",
                                "Cross-domain generalization": "The ability of a model to perform well on datasets from different domains than those it was trained on.",
                                "Heterogeneous datasets": "Collections of data that vary significantly in source, format, or labeling criteria.",
                                "Overfitting": "When a model learns the training data too well, including its noise and biases, reducing performance on new data.",
                                "Labeling policies": "The rules and criteria used by different platforms or organizations to classify content as fake or real."
                            }
                        },
                        {
                            "topic": "Benchmarking performance: F1-score, precision, and recall",
                            "explanation": "To rigorously evaluate the 12 detection methods, the study employs a suite of statistical metrics, primarily focusing on F1-score, precision, and recall. Precision measures the accuracy of positive predictions, ensuring that the model does not flag legitimate news as fake, while recall assesses the model's ability to identify all instances of fake news within a dataset. The F1-score provides a harmonic mean of these two, offering a balanced view of performance, which is crucial given the potential for class imbalance in social media datasets. Beyond these core metrics, the study utilizes advanced statistical validation, including the Friedman test and the post-hoc Nemenyi test, to confirm that observed performance differences are statistically significant rather than due to random chance. This systematic benchmarking ensures that the evaluation is not merely anecdotal but grounded in robust statistical evidence, allowing for a fair comparison between vastly different model architectures.",
                            "example_or_evidence": "Statistical significance of model performance differences was confirmed via the Friedman Test (p < 0.05), followed by the post-hoc Nemenyi test, ensuring that the reported improvements in F1-score, precision, and recall are scientifically valid.",
                            "key_terms": {
                                "F1-score": "The harmonic mean of precision and recall, providing a balanced measure of a model's accuracy.",
                                "Precision": "The ratio of true positive predictions to the total number of positive predictions made.",
                                "Recall": "The ratio of true positive predictions to the total number of actual positive cases.",
                                "Friedman Test": "A non-parametric statistical test used to compare multiple models across multiple datasets.",
                                "Nemenyi test": "A post-hoc test used after the Friedman test to identify which specific models differ significantly from each other."
                            }
                        },
                        {
                            "topic": "Evaluating LLMs vs. traditional ML and BERT-based models",
                            "explanation": "The comparative evaluation reveals distinct performance tiers among the 12 methods. Traditional ML models (LR, SVM, NB) and early deep learning models (CNN, BiLSTM) often serve as baselines but lack the contextual depth of transformer-based models. BERT and DeBERTa demonstrate statistically significant improvements over these baselines, particularly when fine-tuned on specific datasets. However, the study also highlights the emergence of LLMs (Llama3-8B, Qwen3-32B, Zephyr-7B-beta) as a promising alternative. Unlike BERT-based models that require extensive fine-tuning, LLMs can be utilized in zero-shot or few-shot scenarios, offering flexibility in cross-domain tasks. The study notes that while fine-tuned models excel in-domain, cross-domain architectures like MERMAID and LLMs show superior potential for generalization. By comparing these methods, the research demonstrates that while traditional and BERT-based models are effective for static, in-domain tasks, LLMs provide a new paradigm for handling the dynamic and diverse nature of misinformation across different domains.",
                            "example_or_evidence": "Results show that BERT exhibits statistically significant differences compared to CNN and BiLSTM, while DeBERTa outperforms NB, CNN, BiLSTM, CNN-BERT, and Zephyr-7B-beta, illustrating the performance gap between traditional architectures and advanced transformer-based models.",
                            "key_terms": {
                                "Fine-tuning": "The process of adapting a pre-trained model to a specific task or dataset by updating its weights.",
                                "In-domain performance": "Model accuracy when tested on data from the same distribution as the training set.",
                                "Cross-domain architectures": "Model designs specifically optimized to generalize across different data distributions or domains.",
                                "MERMAID": "A cross-domain fake news detection architecture designed for improved generalization.",
                                "Statistical significance": "A measure indicating that observed results are unlikely to have occurred by random chance."
                            }
                        }
                    ],
                    "check_understanding": [
                        "How do the architectural requirements of traditional ML models differ from those of LLMs in the context of fake news detection?",
                        "Why does the 'domain shift' problem pose a significant challenge for models trained on social media data?",
                        "Why is it necessary to use the Friedman test alongside metrics like F1-score when benchmarking multiple models?",
                        "What is the primary advantage of using LLMs over BERT-based models when dealing with cross-domain generalization?"
                    ],
                    "summary": "This lesson explored the foundations of fake news detection by benchmarking 12 diverse methods across 10 heterogeneous datasets. We examined the taxonomy of detection methods, the challenges posed by domain shift in social media, the importance of robust statistical metrics like F1-score, and the comparative performance of traditional ML, BERT-based models, and LLMs. The study concludes that while fine-tuned models are effective in-domain, they often fail to generalize, pointing toward cross-domain architectures and LLMs as the future of resilient fake news detection."
                }
            ]
        },
        {
            "module_title": "Modeling Social Context with Heterogeneous Transformers",
            "difficulty": "intermediate",
            "problem_addressed": "The difficulty of distinguishing fake news due to the limitations of existing graph models in capturing structural representation and node heterogeneity.",
            "solution_approach": "Proposing the HetTransformer model, which uses an encoder-decoder structure to aggregate local multi-modal semantics and global structural representations.",
            "based_on_papers": [
                {
                    "title": "Fake News Detection with Heterogeneous Transformer",
                    "authors": "Research Team",
                    "year": "2024"
                }
            ],
            "lessons": [
                {
                    "lesson_title": "Modeling Social Context with Heterogeneous Transformers",
                    "objectives_covered": [
                        "Heterogeneous graph structures in social networks",
                        "Encoder-decoder architectures for news content",
                        "Integrating multi-modal semantics with structural embeddings",
                        "Random Walk with Restart (RWR) for neighbor order determination"
                    ],
                    "sections": [
                        {
                            "topic": "Heterogeneous graph structures in social networks",
                            "explanation": "Building on the generalization challenges discussed in our previous lesson, we now address the limitations of existing graph models that struggle with the complex, multi-typed nature of social networks. Social networks are inherently heterogeneous, containing diverse node types (e.g., news, users, posts) and edge types (e.g., 'posted by', 'shared by'). Traditional graph models often fail because they rely on rigid meta-path structures or struggle to model the full heterogeneity of nodes and edges, leading to poor structural representation. The HetTransformer approach addresses this by treating the social network as a heterogeneous graph where each node type has specific transformation matrices. By projecting different attribute types into a unified dimension size, the model can effectively process the diverse relationships that define how fake news propagates, moving beyond the constraints of homogeneous graph assumptions.",
                            "example_or_evidence": "The model utilizes type-specific transformation matrices M φi k to project embeddings of different attribute types into a unified dimension size d, allowing the architecture to handle the diverse node and edge types present in real-world social network datasets.",
                            "key_terms": {
                                "Heterogeneous Graph": "A graph containing multiple types of nodes and edges, such as users, posts, and news articles in a social network.",
                                "Node Heterogeneity": "The presence of different node types within a graph, each with distinct attributes and roles.",
                                "Transformation Matrix": "A mathematical matrix used to project embeddings from one dimension or type to another.",
                                "Structural Representation": "A mathematical encoding of the topology and connectivity patterns within a graph."
                            }
                        },
                        {
                            "topic": "Encoder-decoder architectures for news content",
                            "explanation": "To move beyond simple classification, the HetTransformer employs an encoder-decoder structure inspired by the Transformer architecture. In this context, the encoder is responsible for processing the news content and its associated neighborhood information, while the decoder facilitates the final classification task. This structure is critical for fake news detection because it allows the model to learn a latent representation that captures both the intrinsic content of the news and the extrinsic propagation patterns. By leveraging the Transformer's self-attention mechanism, the model can weigh the importance of different neighbors and content features dynamically. This encoder-decoder framework provides a robust mechanism for mapping complex, high-dimensional social context into a feature space suitable for distinguishing between real and fake news, addressing the limitations of earlier models that lacked this hierarchical depth.",
                            "example_or_evidence": "The implementation utilizes the encoder-decoder structure of the Transformer to classify fake news, where the model learns to aggregate structural representations through hierarchical, attention-based processing of news propagation patterns.",
                            "key_terms": {
                                "Encoder-Decoder": "A neural network architecture where an encoder processes input into a latent representation and a decoder generates output from that representation.",
                                "Self-attention": "A mechanism allowing the model to weigh the importance of different parts of the input sequence when processing each element.",
                                "Latent Representation": "A compressed, learned feature vector that captures the essential information of the input data.",
                                "Hierarchical Processing": "Processing data at multiple levels of abstraction or granularity."
                            }
                        },
                        {
                            "topic": "Integrating multi-modal semantics with structural embeddings",
                            "explanation": "A core innovation of the HetTransformer is its ability to fuse multi-modal semantics (such as text, images, or user metadata) with structural embeddings derived from the graph. While previous methods often treated content and structure as separate inputs, HetTransformer integrates them by concatenating content embeddings with positional and type-specific embeddings. This integration ensures that the model does not just look at what the news says, but also at who is sharing it and how it is spreading through the network. By combining these multi-modal features into a unified input for the Transformer, the model captures the local semantics of the news alongside the global structural context of the social network, providing a more comprehensive view of the information dissemination process.",
                            "example_or_evidence": "The model achieves this integration through the concatenation of content embeddings with positional and type embeddings, ensuring that the multi-modal semantics are enriched by the structural context of the heterogeneous graph.",
                            "key_terms": {
                                "Multi-modal Semantics": "Information derived from multiple data types, such as text, images, and metadata.",
                                "Structural Embeddings": "Vector representations that encode the topological structure of a graph.",
                                "Concatenation": "The process of joining multiple vectors or sequences end-to-end to form a single input.",
                                "Positional Embeddings": "Vectors that encode the position or location of elements within a sequence or graph."
                            }
                        },
                        {
                            "topic": "Random Walk with Restart (RWR) for neighbor order determination",
                            "explanation": "Determining the importance of neighbors in a heterogeneous graph is a significant challenge. The HetTransformer employs a Random Walk with Restart (RWR) strategy to determine the order and relevance of neighbors during the sampling process. Unlike simple neighborhood sampling, RWR allows the model to capture the proximity and influence of nodes within the graph structure more effectively. This is a one-off pre-processing step that identifies the most relevant neighbors for each node, ensuring that the subsequent Transformer layers receive high-quality, structurally significant input. By using RWR, the model can better capture the global structural representation of news propagation, as it identifies nodes that are not just immediate neighbors but are also structurally influential in the context of the news item.",
                            "example_or_evidence": "The RWR-based strategy is used as a one-off pre-processing step for heterogeneous neighbor sampling, which is essential for determining the neighbor order before the data is fed into the Transformer layers.",
                            "key_terms": {
                                "Random Walk with Restart": "A graph traversal algorithm that randomly walks from a starting node and periodically returns to it, used to measure node proximity.",
                                "Neighbor Sampling": "The process of selecting a subset of a node's neighbors for computational efficiency.",
                                "Structural Influence": "The impact a node has on the overall topology and information flow within a graph.",
                                "Pre-processing": "Data preparation steps performed before the main model training or inference."
                            }
                        }
                    ],
                    "check_understanding": [
                        "How does the use of type-specific transformation matrices help in modeling heterogeneous social networks?",
                        "Why is the encoder-decoder structure more effective for fake news detection than standard classification layers?",
                        "What is the benefit of concatenating content embeddings with positional and type embeddings?",
                        "How does the RWR strategy improve the quality of neighbor sampling compared to random selection?"
                    ],
                    "summary": "This lesson introduced the HetTransformer model, a novel approach to fake news detection that addresses the limitations of existing graph models. By utilizing an encoder-decoder Transformer architecture, the model effectively integrates multi-modal content semantics with global structural representations derived from heterogeneous social networks. Key technical components include the use of type-specific transformation matrices to handle node heterogeneity, and a Random Walk with Restart (RWR) strategy to optimize neighbor sampling. These advancements allow the model to better capture the complex propagation patterns of fake news, leading to superior performance in real-world detection tasks."
                }
            ]
        },
        {
            "module_title": "Advanced Architectural Optimization and Evaluation",
            "difficulty": "advanced",
            "problem_addressed": "The need for robust, scalable, and accurate classification models that can handle complex propagation patterns.",
            "solution_approach": "Fine-tuning pre-trained models and implementing hierarchical, attention-based graph neural networks.",
            "based_on_papers": [
                {
                    "title": "Fake News Detection with Heterogeneous Transformer",
                    "authors": "Research Team",
                    "year": "2024"
                },
                {
                    "title": "An Experimental Comparison of the Most Popular Approaches to Fake News Detection",
                    "authors": "Various",
                    "year": "2024"
                }
            ],
            "lessons": [
                {
                    "lesson_title": "Advanced Architectural Optimization and Evaluation",
                    "objectives_covered": [
                        "Fine-tuning pre-trained models (BERT, RoBERTa, T5)",
                        "Hierarchical attention-based GNNs",
                        "Type-specific transformation matrices",
                        "Performance metrics and experimental validation"
                    ],
                    "sections": [
                        {
                            "topic": "Fine-tuning pre-trained models (BERT, RoBERTa, T5)",
                            "explanation": "Building on the foundational benchmarking of BERT-based models, advanced optimization requires moving beyond standard fine-tuning to address the specific nuances of fake news propagation. While standard fine-tuning adapts pre-trained weights to a target domain, the challenge lies in the domain shift problem where models trained on one dataset fail to generalize to others. Advanced implementation involves leveraging Huggingface frameworks to perform stochastic optimization on large pre-trained models like BERT, RoBERTa, and T5. By treating these models as feature extractors or end-to-end classifiers, we can capture complex semantic patterns. However, the effectiveness of these models is highly dependent on the quality of the input embeddings and the specific fine-tuning strategy, such as stratified sampling in few-shot scenarios, which helps mitigate the performance degradation observed when models encounter heterogeneous data distributions.",
                            "example_or_evidence": "Experimental benchmarks demonstrate that BERT exhibits statistically significant performance differences compared to traditional CNN and BiLSTM architectures, while DeBERTa shows significant improvements over NB, CNN, and BiLSTM, confirming that the choice of pre-trained architecture is critical for robust detection.",
                            "key_terms": {
                                "Fine-tuning": "Adapting a pre-trained model to a specific downstream task by updating its weights on task-specific data.",
                                "Domain shift": "Performance degradation when a model encounters data from a different distribution than its training set.",
                                "Stochastic optimization": "Optimization methods that use randomness, such as stochastic gradient descent, to update model weights.",
                                "Stratified sampling": "A sampling technique that ensures each subgroup or class is proportionally represented in the training data."
                            }
                        },
                        {
                            "topic": "Hierarchical attention-based GNNs",
                            "explanation": "To overcome the limitations of existing graph models that struggle with complex propagation patterns, we implement hierarchical, attention-based Graph Neural Networks (GNNs). This approach utilizes an encoder-decoder Transformer structure to aggregate structural representations from social networks. Unlike flat graph models, this hierarchical design allows the system to model local multi-modal semantics alongside global structural representations. By employing a Random Walk with Restart (RWR) strategy, the model effectively samples neighbors to determine the order of information flow, ensuring that the most relevant structural context is prioritized. This hierarchical attention mechanism enables the model to distinguish between real and fake news by capturing the propagation dynamics that are often lost in simpler graph representations, effectively bridging the gap between content-based semantics and network-based structural features.",
                            "example_or_evidence": "The HetTransformer model utilizes this hierarchical structure to integrate multi-modal content semantics with global structural representations, which is a key advancement over previous models like HMGNN or GLAN that were constrained by rigid meta-path structures.",
                            "key_terms": {
                                "Encoder-decoder": "A neural network architecture with separate encoding and decoding components for processing and generating representations.",
                                "Random Walk with Restart": "A graph algorithm that measures node proximity by performing random walks with periodic returns to the source node.",
                                "Propagation patterns": "The characteristic ways in which information spreads through a network over time.",
                                "Structural representation": "A mathematical encoding of the connectivity and topology of a graph."
                            }
                        },
                        {
                            "topic": "Type-specific transformation matrices",
                            "explanation": "A critical component in modeling heterogeneous social networks is the use of type-specific transformation matrices, denoted as M φi k. Because social networks contain diverse node types (e.g., users, news articles, posts) and edge types, a uniform projection is insufficient. These matrices project the embedding of attribute type i from node type k into a unified dimension size d. This ensures that heterogeneous features—which may have different initial dimensions—are mapped into a common latent space where they can be compared and aggregated. By applying these matrices, the model can effectively handle the heterogeneity of nodes and edges, allowing the attention mechanism to operate on a consistent feature space. This is essential for the HetTransformer to maintain the integrity of node-specific information while performing global structural aggregation.",
                            "example_or_evidence": "Implementation notes specify that the embedding size of attribute type i from node type k (dik) is projected to a unified dimension size d using these type-specific matrices, which is a foundational step in the HetTransformer architecture.",
                            "key_terms": {
                                "Transformation matrices": "Mathematical operators that map vectors from one space to another.",
                                "Heterogeneity": "The presence of multiple distinct types or classes within a dataset or graph.",
                                "Latent space": "A compressed, learned representation space where similar items are positioned closer together.",
                                "Feature projection": "The process of mapping features from their original space to a new, often lower-dimensional, space."
                            }
                        },
                        {
                            "topic": "Performance metrics and experimental validation",
                            "explanation": "Rigorous evaluation is necessary to validate the effectiveness of advanced architectures. Beyond simple accuracy, we employ a suite of metrics including Precision, Recall, and F1-score to account for class imbalances common in fake news datasets. To ensure statistical rigor, we utilize the Friedman test to compare multiple models across heterogeneous datasets, followed by post-hoc Nemenyi tests to identify significant performance differences. This validation framework is crucial for assessing generalization capabilities, particularly in cross-domain settings where models are tested on datasets they were not trained on. By measuring metrics like the coefficient of variation and gate entropy, we can quantify the stability and reliability of the detection models, ensuring that the proposed architectural improvements translate into real-world performance gains.",
                            "example_or_evidence": "The study confirms statistical significance via the Friedman Test (p < 0.05) and post-hoc Nemenyi test, providing a robust empirical basis for claiming that models like MERMAID and HetTransformer outperform traditional approaches.",
                            "key_terms": {
                                "Friedman test": "A non-parametric statistical test for comparing multiple algorithms across multiple datasets.",
                                "Nemenyi test": "A post-hoc statistical test used to determine which specific pairs of models differ significantly after a Friedman test.",
                                "F1-score": "The harmonic mean of precision and recall, balancing both metrics.",
                                "Generalization": "A model's ability to perform well on unseen data from different distributions."
                            }
                        }
                    ],
                    "check_understanding": [
                        "How does the use of stratified sampling during fine-tuning help address the domain shift problem identified in the benchmarking study?",
                        "Why is the Random Walk with Restart (RWR) strategy essential for the hierarchical attention mechanism in the HetTransformer model?",
                        "What is the primary purpose of using type-specific transformation matrices when dealing with heterogeneous node types?",
                        "Why is the Friedman test preferred over simple accuracy comparisons when evaluating multiple fake news detection models across diverse datasets?"
                    ],
                    "summary": "This lesson explored advanced architectural strategies for fake news detection, focusing on the integration of pre-trained models with hierarchical, attention-based GNNs. We examined how type-specific transformation matrices enable the processing of heterogeneous social network data and how rigorous statistical validation, including the Friedman test, ensures that model performance is both accurate and generalizable across diverse domains."
                }
            ]
        }
    ],
    "frontier_topics": [
        {
            "topic": "Flexible Encoding for Heterogeneous Graphs",
            "addresses_gap": "Existing heterogeneous graph models are limited by rigid constraints on graph and meta-path structures.",
            "rationale": "Students will explore how to reduce reliance on predefined meta-paths to better capture the inherent heterogeneity of social network entities."
        },
        {
            "topic": "Temporal Dynamics and Multi-modal Integration",
            "addresses_gap": "Current frameworks often fail to integrate critical social context, propagation patterns, and temporal dynamics.",
            "rationale": "Focuses on implementing time-based data splits and integrating global structural representations to improve robustness against unseen misinformation."
        },
        {
            "topic": "Resilience Against Synthetic Misinformation",
            "addresses_gap": "Lack of empirical understanding regarding the robustness of transformer models against LLM-generated fake news.",
            "rationale": "Involves conducting error analysis and cross-dataset experiments to identify linguistic factors contributing to performance drops when facing synthetic content."
        },
        {
            "topic": "Generative Approaches to Misinformation Analysis",
            "addresses_gap": "Discriminative classification models struggle with the nuance of evolving misinformation narratives.",
            "rationale": "Explores moving beyond classification to using generative models for producing explanations or labels for detected fake news."
        }
    ],
    "suggested_duration": "10 weeks"
}


# ============================================================
# MAIN TEST
# ============================================================

def main():
    print("=" * 60)
    print("COURSE PPTX EXPORTER - STANDALONE TEST")
    print("=" * 60)

    # Determine output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nOutput directory: {output_dir}")
    print(f"Course title: {COURSE_DATA.get('course_title', 'N/A')}")
    print(f"Modules: {len(COURSE_DATA.get('modules', []))}")

    total_lessons = sum(len(m.get('lessons', [])) for m in COURSE_DATA.get('modules', []))
    print(f"Total lessons: {total_lessons}")

    # Import the exporter
    try:
        from course_pptx_exporter import export_course_to_pptx_per_lesson
        print("\n✓ Exporter imported successfully")
    except ImportError as e:
        print(f"\n✗ Failed to import exporter: {e}")
        print("Make sure course_pptx_exporter.py is in the same directory as this script.")
        sys.exit(1)

    # Run the export
    print("\nGenerating presentations...")
    try:
        generated_files = export_course_to_pptx_per_lesson(COURSE_DATA, output_dir)
        print(f"\n✓ Export complete!")
        print(f"  Generated {len(generated_files)} file(s):")
        for f in generated_files:
            size_kb = os.path.getsize(f) / 1024
            print(f"    • {os.path.basename(f)} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("TEST PASSED - All presentations generated successfully")
    print("=" * 60)
    print(f"\nOpen the files in: {output_dir}")


if __name__ == "__main__":
    main()
