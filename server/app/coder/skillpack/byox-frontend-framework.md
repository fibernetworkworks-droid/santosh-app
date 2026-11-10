---
name: byox-frontend-framework
description: Build a mini-React with virtual DOM, diffing and hooks
when_to_use: own react, frontend framework, virtual dom, ui framework from scratch
---
GOAL: a working mini-React where components re-render when state changes.

PHASES
1. createElement(type, props, ...children) returns a plain vnode object.
2. render(vnode, container) walks the tree and creates real DOM nodes.
3. diff(oldVnode, newVnode) patches only changed nodes; key-based list diffing.
4. Component functions; re-render on prop change; event listeners attached once.
5. useState hook (global queue + currentHook index); useEffect with deps array.

CORE CONCEPTS
- vnode = { type, props: { ...attrs, children: [] } }
- Reconciliation: same type → patch props; different type → replace node.
- Hooks: each render call moves a pointer through the hook queue; never call conditionally.

VERIFY: a counter component increments correctly; list with keys re-orders without full re-render.
