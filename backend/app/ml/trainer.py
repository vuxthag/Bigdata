"""
ml/trainer.py
=============
Fine-tuning utilities for continual learning with EWC regularization.
"""
from __future__ import annotations

import copy
import logging
from typing import Dict, List

import numpy as np
from sentence_transformers import InputExample, SentenceTransformer, losses
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


def create_training_dataloader(
    examples: List[InputExample], batch_size: int = 16
) -> DataLoader:
    """Create a DataLoader from InputExample list."""
    return DataLoader(examples, shuffle=True, batch_size=batch_size)


def compute_fisher_information(
    model: SentenceTransformer, dataloader: DataLoader
) -> Dict[str, np.ndarray]:
    """
    Compute Fisher Information Matrix diagonal approximation.
    Used for EWC regularization to penalize large changes to important weights.
    """
    import torch

    fisher: Dict[str, np.ndarray] = {}
    model_module = model._first_module()

    # Zero gradients
    for param in model_module.parameters():
        if param.requires_grad:
            param.grad = None

    # Accumulate squared gradients (Fisher approximation)
    for batch in dataloader:
        try:
            if not batch:
                continue
            model_module.zero_grad()
            # Simple pass to get gradient signal
            for example in batch if isinstance(batch, list) else [batch]:
                try:
                    texts = example.texts if hasattr(example, 'texts') else []
                    if texts:
                        emb = model.encode(texts[0], convert_to_tensor=True)
                        loss = emb.norm()
                        loss.backward()
                except Exception:
                    continue

            for name, param in model_module.named_parameters():
                if param.requires_grad and param.grad is not None:
                    if name not in fisher:
                        fisher[name] = param.grad.data.cpu().numpy() ** 2
                    else:
                        fisher[name] += param.grad.data.cpu().numpy() ** 2
        except Exception:
            continue

    return fisher


def fine_tune_model(
    model: SentenceTransformer,
    train_examples: List[InputExample],
    epochs: int = 1,
    ewc_lambda: float = 0.0,
    old_params: Dict[str, np.ndarray] | None = None,
    fisher: Dict[str, np.ndarray] | None = None,
    warmup_steps: int = 10,
) -> SentenceTransformer:
    """
    Fine-tune the Sentence-BERT model with CosineSimilarityLoss.

    Parameters
    ----------
    model : SentenceTransformer
    train_examples : List[InputExample]  — [{texts: [cv, job], label: 1.0/0.0}]
    epochs : int
    ewc_lambda : float — EWC regularization strength (0 = disabled)
    old_params : dict — parameter values before fine-tuning (for EWC)
    fisher : dict — Fisher information diagonal (for EWC)
    """
    if not train_examples:
        logger.warning("No training examples provided. Skipping fine-tuning.")
        return model

    dataloader = create_training_dataloader(train_examples, batch_size=16)
    train_loss = losses.CosineSimilarityLoss(model)

    model.fit(
        train_objectives=[(dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        show_progress_bar=False,
    )

    # EWC regularization: manually adjust weights if params provided
    if ewc_lambda > 0 and old_params and fisher:
        try:
            import torch
            model_module = model._first_module()
            with torch.no_grad():
                for name, param in model_module.named_parameters():
                    if name in old_params and name in fisher:
                        old_val = torch.tensor(old_params[name]).to(param.device)
                        fi = torch.tensor(fisher[name]).to(param.device)
                        # Nudge param back toward old value proportionally to Fisher importance
                        correction = ewc_lambda * fi * (param - old_val)
                        param.sub_(correction * 0.001)
        except Exception as e:
            logger.warning(f"EWC correction failed: {e}")

    return model


def evaluate_model(
    model: SentenceTransformer, test_examples: List[InputExample]
) -> Dict[str, float]:
    """
    Evaluate model by computing correlation between predicted and true similarity.
    """
    from scipy.stats import pearsonr, spearmanr

    if not test_examples:
        return {"pearson": 0.0, "spearman": 0.0}

    true_scores, pred_scores = [], []
    for ex in test_examples:
        if len(ex.texts) < 2:
            continue
        embs = model.encode(ex.texts, normalize_embeddings=True)
        pred = float(np.dot(embs[0], embs[1]))
        true_scores.append(ex.label)
        pred_scores.append(pred)

    if len(true_scores) < 2:
        return {"pearson": 0.0, "spearman": 0.0}

    pearson, _ = pearsonr(true_scores, pred_scores)
    spearman, _ = spearmanr(true_scores, pred_scores)
    return {"pearson": round(float(pearson), 4), "spearman": round(float(spearman), 4)}


def should_rollback(new_metrics: Dict[str, float], old_metrics: Dict[str, float]) -> bool:
    """
    Return True if new model performs > 5% worse on pearson correlation.
    """
    old_p = old_metrics.get("pearson", 0.0)
    new_p = new_metrics.get("pearson", 0.0)
    if old_p == 0.0:
        return False
    return (old_p - new_p) / abs(old_p) > 0.05
