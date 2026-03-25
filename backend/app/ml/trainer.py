"""
ml/trainer.py
=============
Fine-tuning utilities for continual learning.
Compatible with sentence-transformers >= 2.2.0 and CPU-only environments.
"""
from __future__ import annotations

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
    Uses a simplified gradient-proxy approach compatible with current sentence-transformers.
    Returns empty dict on any failure (EWC becomes optional).
    """
    import torch

    fisher: Dict[str, np.ndarray] = {}
    try:
        # Access the underlying transformer module safely
        # sentence-transformers >= 2.3 uses model[0] instead of _first_module()
        try:
            transformer_module = model[0]
        except (TypeError, KeyError):
            return fisher

        transformer_module.zero_grad()

        for batch in dataloader:
            try:
                # batch from DataLoader of InputExample is a list of InputExample objects
                if not batch:
                    continue
                if isinstance(batch, list) and hasattr(batch[0], 'texts'):
                    texts = [ex.texts[0] for ex in batch if ex.texts]
                else:
                    continue

                if not texts:
                    continue

                # Encode and compute a proxy loss
                with torch.enable_grad():
                    embs = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)
                    proxy_loss = embs.norm(dim=1).mean()
                    proxy_loss.backward()

                for name, param in transformer_module.auto_model.named_parameters():
                    if param.requires_grad and param.grad is not None:
                        grad_sq = param.grad.detach().cpu().numpy() ** 2
                        if name not in fisher:
                            fisher[name] = grad_sq
                        else:
                            fisher[name] += grad_sq

                transformer_module.zero_grad()
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Fisher computation failed (EWC disabled): {e}")

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
    Uses model.fit() API compatible with sentence-transformers >= 2.2.
    """
    if not train_examples:
        logger.warning("No training examples provided. Skipping fine-tuning.")
        return model

    dataloader = create_training_dataloader(train_examples, batch_size=16)
    train_loss = losses.CosineSimilarityLoss(model)

    try:
        model.fit(
            train_objectives=[(dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            show_progress_bar=False,
        )
    except Exception as e:
        logger.error(f"Fine-tuning failed: {e}")
        return model

    # Optional EWC weight correction
    if ewc_lambda > 0 and old_params and fisher:
        try:
            import torch
            try:
                transformer_module = model[0]
                named_params = transformer_module.auto_model.named_parameters()
            except Exception:
                named_params = iter([])

            with torch.no_grad():
                for name, param in named_params:
                    if name in old_params and name in fisher:
                        old_val = torch.tensor(old_params[name], dtype=param.dtype).to(param.device)
                        fi = torch.tensor(fisher[name], dtype=param.dtype).to(param.device)
                        correction = ewc_lambda * fi * (param.data - old_val)
                        param.data.sub_(correction * 0.001)
        except Exception as e:
            logger.warning(f"EWC correction failed (non-fatal): {e}")

    return model


def evaluate_model(
    model: SentenceTransformer, test_examples: List[InputExample]
) -> Dict[str, float]:
    """
    Evaluate model correlation between predicted and true similarity scores.
    """
    try:
        from scipy.stats import pearsonr, spearmanr
    except ImportError:
        return {"pearson": 0.0, "spearman": 0.0}

    if not test_examples:
        return {"pearson": 0.0, "spearman": 0.0}

    true_scores: list = []
    pred_scores: list = []
    for ex in test_examples:
        if len(ex.texts) < 2:
            continue
        try:
            embs = model.encode(ex.texts, normalize_embeddings=True, show_progress_bar=False)
            pred = float(np.dot(embs[0], embs[1]))
            true_scores.append(float(ex.label))
            pred_scores.append(pred)
        except Exception:
            continue

    if len(true_scores) < 2:
        return {"pearson": 0.0, "spearman": 0.0}

    try:
        pearson, _ = pearsonr(true_scores, pred_scores)
        spearman, _ = spearmanr(true_scores, pred_scores)
        return {
            "pearson": round(float(pearson), 4),
            "spearman": round(float(spearman), 4),
        }
    except Exception:
        return {"pearson": 0.0, "spearman": 0.0}


def should_rollback(new_metrics: Dict[str, float], old_metrics: Dict[str, float]) -> bool:
    """Return True if new model performs > 5% worse on pearson correlation."""
    old_p = old_metrics.get("pearson", 0.0)
    new_p = new_metrics.get("pearson", 0.0)
    if old_p == 0.0:
        return False
    return (old_p - new_p) / abs(old_p) > 0.05
