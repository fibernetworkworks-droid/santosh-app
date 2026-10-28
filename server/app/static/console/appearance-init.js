'use strict';
// Resolve saved appearance before styles paint. Only allow known preference values.
(()=>{let p={};try{p=JSON.parse(localStorage.getItem('hoola.web.appearance')||'{}')||{};}catch{}const t=['light','dark','system'].includes(p.theme)?p.theme:'system';document.documentElement.dataset.theme=t==='system'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):t;document.documentElement.dataset.chatFont=['default','system','readable'].includes(p.font)?p.font:'default';})();
