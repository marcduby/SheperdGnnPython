from __future__ import annotations

import math
from typing import Callable

import torch
from torch import nn


def _masked_softmax(scores: torch.Tensor, mask: torch.BoolTensor | None) -> torch.Tensor:
    if mask is None:
        return torch.softmax(scores, dim=-1)
    while mask.dim() < scores.dim():
        mask = mask.unsqueeze(1)
    masked_scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
    return torch.softmax(masked_scores, dim=-1)


class DotProductAttention(nn.Module):
    def __init__(self, normalize: bool = True):
        super().__init__()
        self.normalize = normalize

    def forward(
        self, vector: torch.Tensor, matrix: torch.Tensor, matrix_mask: torch.BoolTensor | None = None
    ) -> torch.Tensor:
        scores = torch.bmm(matrix, vector.unsqueeze(-1)).squeeze(-1)
        if self.normalize:
            scores = scores / math.sqrt(matrix.size(-1))
            return _masked_softmax(scores, matrix_mask)
        return scores


class BilinearAttention(nn.Module):
    def __init__(
        self,
        vector_dim: int,
        matrix_dim: int,
        activation: Callable[[torch.Tensor], torch.Tensor] | None = None,
        normalize: bool = True,
    ):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(vector_dim, matrix_dim))
        nn.init.xavier_uniform_(self.weight)
        self.activation = activation
        self.normalize = normalize

    def forward(
        self, vector: torch.Tensor, matrix: torch.Tensor, matrix_mask: torch.BoolTensor | None = None
    ) -> torch.Tensor:
        projected = torch.matmul(vector, self.weight)
        scores = torch.bmm(matrix, projected.unsqueeze(-1)).squeeze(-1)
        if self.activation is not None:
            scores = self.activation(scores)
        if self.normalize:
            return _masked_softmax(scores, matrix_mask)
        return scores


class AdditiveAttention(nn.Module):
    def __init__(self, vector_dim: int, matrix_dim: int, normalize: bool = True):
        super().__init__()
        hidden_dim = max(vector_dim, matrix_dim)
        self.vector_proj = nn.Linear(vector_dim, hidden_dim, bias=False)
        self.matrix_proj = nn.Linear(matrix_dim, hidden_dim, bias=False)
        self.score_proj = nn.Linear(hidden_dim, 1, bias=False)
        self.normalize = normalize

    def forward(
        self, vector: torch.Tensor, matrix: torch.Tensor, matrix_mask: torch.BoolTensor | None = None
    ) -> torch.Tensor:
        vector_term = self.vector_proj(vector).unsqueeze(1)
        matrix_term = self.matrix_proj(matrix)
        scores = self.score_proj(torch.tanh(vector_term + matrix_term)).squeeze(-1)
        if self.normalize:
            return _masked_softmax(scores, matrix_mask)
        return scores


class CosineAttention(nn.Module):
    def __init__(self, normalize: bool = True):
        super().__init__()
        self.normalize = normalize

    def forward(
        self, vector: torch.Tensor, matrix: torch.Tensor, matrix_mask: torch.BoolTensor | None = None
    ) -> torch.Tensor:
        scores = torch.nn.functional.cosine_similarity(matrix, vector.unsqueeze(1), dim=-1)
        if self.normalize:
            return _masked_softmax(scores, matrix_mask)
        return scores
