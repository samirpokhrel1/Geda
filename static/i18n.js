(() => {
  const lang = document.documentElement.lang === 'ne' ? 'ne' : 'en';
  fetch(`/static/locales/${lang}.json`, { credentials: 'same-origin' })
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(catalog => {
      const messages = catalog.messages || {};
      const translate = root => {
        if (root === document.body) document.title = document.title.split(' · ').map(part => messages[part] || part).join(' · ');
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        for (const node of nodes) {
          const source = node.nodeValue.trim();
          if (messages[source]) node.nodeValue = node.nodeValue.replace(source, messages[source]);
        }
        root.querySelectorAll('[placeholder], [title], [aria-label]').forEach(element => {
          for (const attribute of ['placeholder', 'title', 'aria-label']) {
            const source = element.getAttribute(attribute);
            if (source && messages[source]) element.setAttribute(attribute, messages[source]);
          }
        });
      };
      translate(document.body);
      new MutationObserver(records => records.forEach(record => {
        record.addedNodes.forEach(node => { if (node.nodeType === Node.ELEMENT_NODE) translate(node); });
      })).observe(document.body, { childList: true, subtree: true });
    })
    .catch(() => { /* Keep the source language readable if a locale file is unavailable. */ });
})();
