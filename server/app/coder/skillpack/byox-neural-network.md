---
name: byox-neural-network
description: Build a neural network with backprop and Adam, no ML frameworks
---
GOAL: a 2-layer MLP trained on MNIST that reaches 97%+ test accuracy.

PHASES
1. Single perceptron: XOR with sigmoid; gradient descent by hand.
2. Dense layer class with forward (z = W·x + b, a = relu(z)) and backward.
3. Stack 2 layers: softmax output + cross-entropy loss; train on MNIST.
4. Mini-batch SGD; track train/val loss; plot learning curve.
5. Adam optimiser (m, v moments + bias correction); dropout layer; reach 97%+.

CORE CONCEPTS
- Chain rule: dL/dW = dL/da · da/dz · dz/dW; stack layer Jacobians.
- Softmax: exp(z_i) / sum(exp(z)); numerically stable with max subtraction.
- Adam: m = β1·m + (1-β1)·g; v = β2·v + (1-β2)·g²; θ -= lr·m_hat/√v_hat.

VERIFY: 97%+ test accuracy on MNIST after 20 epochs; loss curve decreasing.
