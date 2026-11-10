---
name: byox-ai-model
description: Build an LLM or diffusion model from scratch in Python
when_to_use: build my own llm, train a language model, gpt from scratch, diffusion model from scratch, own ai model
---
GOAL: a working character-level language model trained on real text; optionally a DDPM image model.

PHASES
1. Build a Tensor class with autograd (Value node, backward(), topological sort).
2. Bigram LM: embedding lookup + linear layer + softmax; train on Shakespeare.
3. Self-attention head; multi-head Transformer block; positional encoding.
4. Stack 6 Transformer layers; train GPT-2 scale on TinyStories; sample text.
5. DDPM image model: forward noising schedule, U-Net denoiser, DDIM sampling.

CORE CONCEPTS
- Backprop = chain rule applied recursively on a computation graph.
- Attention: Q·K^T / sqrt(d_k) softmax → weight V; causal mask for autoregressive.
- BPE tokeniser: merge most-frequent byte pair, build vocab of ~32k tokens.

VERIFY: model generates coherent sentences after 10k training steps on Shakespeare.
