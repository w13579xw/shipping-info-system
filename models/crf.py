# -*- coding: utf-8 -*-
"""线性链条件随机场（CRF）的 PyTorch 实现。

约定（BIO 标注）：
  - 真实标签编号为 1..num_tags，0 为 padding（掩码后不参与计算）；
  - CRF 内部标签集在真实标签之外额外追加 START（编号 0）与 STOP（编号 num_tags+1）。
"""
import torch
import torch.nn as nn


def log_sum_exp(vec):
    # vec: 任意形状，沿最后一维做 log-sum-exp
    max_score = vec.max(dim=-1, keepdim=True).values
    return max_score + torch.log(torch.exp(vec - max_score).sum(dim=-1, keepdim=True))


class CRF(nn.Module):
    def __init__(self, num_tags):
        """
        num_tags: 真实 BIO 标签数量（不含 padding / START / STOP）。
        """
        super().__init__()
        self.num_tags = num_tags
        self.start_tag = 0
        self.stop_tag = num_tags + 1
        self.tagset_size = num_tags + 2
        self.transitions = nn.Parameter(torch.randn(self.tagset_size, self.tagset_size))
        # 不能转移到 START，不能从 STOP 转移出去
        self.transitions.data[:, self.start_tag] = -10000.0
        self.transitions.data[self.stop_tag, :] = -10000.0

    def _score_sentence(self, emissions, tags, mask):
        # emissions: (B, T, K)，tags: (B, T) 真实标签（1..num_tags），mask: (B, T) 0/1
        bsz, seq_len, _ = emissions.shape
        gold = emissions.gather(2, tags.unsqueeze(2)).squeeze(2)  # (B, T)
        start = torch.full((bsz, 1), self.start_tag, dtype=torch.long, device=emissions.device)
        prev = torch.cat([start, tags[:, :-1]], dim=1)            # (B, T)
        trans = self.transitions[prev, tags]                       # (B, T)
        scores = (gold + trans) * mask
        return scores.sum(dim=1)

    def _forward_alg(self, emissions, mask):
        # 前向算法求归一化因子 log Z
        bsz, seq_len, _ = emissions.shape
        alpha = torch.full((bsz, self.tagset_size), -10000.0, device=emissions.device)
        alpha[:, self.start_tag] = 0.0
        for t in range(seq_len):
            # scores[b, i, j] = alpha_i + trans[i, j] + emit[j]
            scores = alpha.unsqueeze(2) + self.transitions.unsqueeze(0) \
                     + emissions[:, t, :].unsqueeze(1)             # (B, K, K)
            next_alpha = log_sum_exp(scores).squeeze(2)            # (B, K)
            m = mask[:, t].unsqueeze(1).bool()
            alpha = torch.where(m, next_alpha, alpha)
        alpha = alpha + self.transitions[:, self.stop_tag].unsqueeze(0)
        return log_sum_exp(alpha).squeeze(1)                       # (B,)

    def forward(self, emissions, tags, mask):
        # 返回平均负对数似然（训练损失）
        numerator = self._score_sentence(emissions, tags, mask)
        denominator = self._forward_alg(emissions, mask)
        return (denominator - numerator).mean()

    def viterbi_decode(self, emissions):
        # emissions: (T, K) 单句（不含 padding 位置）
        seq_len, _ = emissions.shape
        alpha = torch.full((self.tagset_size,), -10000.0, device=emissions.device)
        alpha[self.start_tag] = 0.0
        backpointers = []
        for t in range(seq_len):
            scores = alpha.unsqueeze(1) + self.transitions           # (K, K): scores[i, j]
            scores = scores + emissions[t].unsqueeze(0)              # + emit[j]
            best_score, best_idx = scores.max(dim=0)                 # 沿 i（上一时刻）取最大
            alpha = best_score
            backpointers.append(best_idx)
        alpha = alpha + self.transitions[:, self.stop_tag]
        _, last = alpha.max(dim=0)
        path = [last.item()]
        for t in range(seq_len - 1, -1, -1):
            last = backpointers[t][last].item()
            path.append(last)
        path.reverse()
        return path[1:]  # 去掉开头的 START，返回每个位置的标签（1..num_tags）
