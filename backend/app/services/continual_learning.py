"""
services/continual_learning.py
================================
Continual learning service. Fixes:
- _replay_buffer moved INTO the class (no global misuse)
- _first_module() replaced with compatible API
- SQLAlchemy bool filters use is_(False)
- select imported properly in _reencode_all
"""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timezone
from typing import List

from sentence_transformers import InputExample
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.cv import CV
from app.models.interaction import InteractionAction, UserInteraction
from app.models.job import Job
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class ContinualLearner:
    """
    Manages continual fine-tuning of the SBERT model using user interaction data.
    Replay buffer is instance-level (not a global variable).
    """

    def __init__(self) -> None:
        self._current_metrics: dict = {"pearson": 0.0, "spearman": 0.0}
        self._old_params: dict | None = None
        self._fisher: dict | None = None
        # Replay buffer — class-level, no global needed
        self._replay_buffer: List[InputExample] = []

    async def collect_training_pairs(
        self, db: AsyncSession
    ) -> List[InputExample]:
        """
        Convert untrained interactions into InputExample pairs for fine-tuning.
        Label mapping:
          applied / saved -> 1.0  (positive pair)
          skipped         -> 0.0  (negative pair)
        """
        result = await db.execute(
            select(UserInteraction)
            .where(
                UserInteraction.is_trained.is_(False),  # Fix: use is_(False) not == False
                UserInteraction.action.in_([
                    InteractionAction.applied,
                    InteractionAction.saved,
                    InteractionAction.skipped,
                ]),
            )
            .limit(500)
        )
        interactions = result.scalars().all()

        examples: List[InputExample] = []
        for interaction in interactions:
            cv_text = ""
            if interaction.cv_id:
                cv_result = await db.execute(
                    select(CV.cleaned_text).where(CV.id == interaction.cv_id)
                )
                cv_text = cv_result.scalar_one_or_none() or ""

            job_result = await db.execute(
                select(Job.cleaned_description).where(Job.id == interaction.job_id)
            )
            job_text = job_result.scalar_one_or_none() or ""

            if not cv_text or not job_text:
                continue

            label = (
                1.0
                if interaction.action in (InteractionAction.applied, InteractionAction.saved)
                else 0.0
            )
            examples.append(InputExample(texts=[cv_text, job_text], label=label))

        return examples

    async def count_untrained(self, db: AsyncSession) -> int:
        """Count interactions that haven't been trained yet."""
        result = await db.execute(
            select(func.count(UserInteraction.id)).where(
                UserInteraction.is_trained.is_(False),
                UserInteraction.action.in_([
                    InteractionAction.applied,
                    InteractionAction.saved,
                    InteractionAction.skipped,
                ]),
            )
        )
        return result.scalar_one() or 0

    async def should_retrain(self, db: AsyncSession) -> bool:
        """Return True if enough new interactions exist to trigger retraining."""
        count = await self.count_untrained(db)
        return count >= settings.RETRAIN_THRESHOLD

    async def retrain(self, db: AsyncSession) -> dict:
        """
        Full continual learning cycle:
        1. Collect new training pairs
        2. Merge with replay buffer
        3. Fine-tune with EWC regularization
        4. Evaluate and rollback if worse
        5. Save checkpoint and re-encode all embeddings
        6. Mark interactions as trained
        """
        from app.ml.trainer import (
            compute_fisher_information,
            create_training_dataloader,
            evaluate_model,
            fine_tune_model,
            should_rollback,
        )

        logger.info("[CL] Starting retraining cycle...")

        new_examples = await self.collect_training_pairs(db)
        if not new_examples:
            logger.info("[CL] No new training pairs. Skipping.")
            return {"status": "skipped", "reason": "no_new_data"}

        # Mix with replay buffer
        replay_sample = random.sample(
            self._replay_buffer,
            min(len(self._replay_buffer), max(1, len(new_examples) // 4))
        ) if self._replay_buffer else []
        all_examples = new_examples + replay_sample
        random.shuffle(all_examples)

        logger.info(
            f"[CL] Training on {len(all_examples)} examples "
            f"({len(new_examples)} new, {len(replay_sample)} replay)"
        )

        # Snapshot old model
        import copy
        model = embedding_service.model.model
        old_model = copy.deepcopy(model)

        # Compute Fisher information (best-effort, non-fatal)
        train_dl = create_training_dataloader(all_examples[:min(50, len(all_examples))])
        self._fisher = compute_fisher_information(old_model, train_dl)

        # Snapshot old params for EWC
        try:
            self._old_params = {
                name: param.detach().cpu().numpy().copy()
                for name, param in old_model[0].auto_model.named_parameters()
                if param.requires_grad
            }
        except Exception:
            self._old_params = {}

        # Fine-tune
        new_model = fine_tune_model(
            model=model,
            train_examples=all_examples,
            epochs=1,
            ewc_lambda=0.4,
            old_params=self._old_params,
            fisher=self._fisher,
        )

        # Evaluate — rollback if worse
        test_examples = all_examples[-min(20, len(all_examples)):]
        new_metrics = evaluate_model(new_model, test_examples)
        old_metrics = evaluate_model(old_model, test_examples)

        if should_rollback(new_metrics, old_metrics):
            logger.warning(f"[CL] Rollback! new={new_metrics} old={old_metrics}")
            embedding_service.model._model = old_model
            return {"status": "rolled_back", "old_metrics": old_metrics, "new_metrics": new_metrics}

        # Commit new model
        embedding_service.model._model = new_model
        self._current_metrics = new_metrics

        # Save checkpoint
        os.makedirs(settings.MODEL_CHECKPOINT_DIR, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        checkpoint_path = os.path.join(settings.MODEL_CHECKPOINT_DIR, f"checkpoint_{ts}")
        try:
            embedding_service.model.save_checkpoint(checkpoint_path)
        except Exception as e:
            logger.warning(f"[CL] Checkpoint save failed (non-fatal): {e}")

        self._cleanup_old_checkpoints()
        await self._reencode_all(db)

        # Mark trained
        await db.execute(
            update(UserInteraction)
            .where(
                UserInteraction.is_trained.is_(False),
                UserInteraction.action.in_([
                    InteractionAction.applied,
                    InteractionAction.saved,
                    InteractionAction.skipped,
                ]),
            )
            .values(is_trained=True)
        )

        # Update replay buffer (keep 20% of new batch, cap at 200)
        keep_n = max(1, len(new_examples) // 5)
        self._replay_buffer = (
            self._replay_buffer + random.sample(new_examples, keep_n)
        )[-200:]

        logger.info(f"[CL] Retrain complete. Metrics: {new_metrics}")
        return {
            "status": "success",
            "examples_trained": len(all_examples),
            "metrics": new_metrics,
            "checkpoint": checkpoint_path,
        }

    async def _reencode_all(self, db: AsyncSession) -> None:
        """Re-encode all CVs and Jobs with the current model."""
        # CVs
        cv_result = await db.execute(
            select(CV).where(CV.cleaned_text.isnot(None))
        )
        cvs = cv_result.scalars().all()
        if cvs:
            texts = [c.cleaned_text for c in cvs]
            embeddings = embedding_service.encode_batch(texts)
            for cv, emb in zip(cvs, embeddings):
                cv.embedding = emb.tolist()

        # Jobs
        job_result = await db.execute(
            select(Job).where(
                Job.cleaned_description.isnot(None),
                Job.is_active.is_(True),
            )
        )
        jobs = job_result.scalars().all()
        if jobs:
            texts = [j.cleaned_description for j in jobs]
            embeddings = embedding_service.encode_batch(texts)
            for job, emb in zip(jobs, embeddings):
                job.embedding = emb.tolist()

        await db.flush()
        logger.info(f"[CL] Re-encoded {len(cvs)} CVs and {len(jobs)} Jobs")

    def _cleanup_old_checkpoints(self, keep: int = 3) -> None:
        """Keep only the N most recent checkpoints on disk."""
        import shutil
        dir_path = settings.MODEL_CHECKPOINT_DIR
        if not os.path.exists(dir_path):
            return
        checkpoints = sorted(
            [d for d in os.listdir(dir_path) if d.startswith("checkpoint_")],
            reverse=True,
        )
        for old_cp in checkpoints[keep:]:
            try:
                shutil.rmtree(os.path.join(dir_path, old_cp))
                logger.info(f"[CL] Removed old checkpoint: {old_cp}")
            except Exception:
                pass

    def get_model_version(self) -> str:
        """Return the most recent checkpoint name."""
        dir_path = settings.MODEL_CHECKPOINT_DIR
        if not os.path.exists(dir_path):
            return "base_all-MiniLM-L6-v2"
        try:
            checkpoints = sorted(
                [d for d in os.listdir(dir_path) if d.startswith("checkpoint_")],
                reverse=True,
            )
            return checkpoints[0] if checkpoints else "base_all-MiniLM-L6-v2"
        except Exception:
            return "base_all-MiniLM-L6-v2"


# Global singleton
continual_learner = ContinualLearner()
