/**
 * renderer.js
 * Converts LLM response text to safe, styled HTML.
 * Loaded as a static file by the Python server.
 */
const Renderer = (() => {
  function render(text) {
    // 1. Escape HTML
    let h = text
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

    // 2. Code blocks
    h = h.replace(/```([a-z]*)\n?([\s\S]*?)```/g, (_,lang,code) =>
      `<pre style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:12px 14px;overflow-x:auto;margin:10px 0;font-size:.75rem;line-height:1.6;"><code>${code.trim()}</code></pre>`
    );

    // 3. Inline code
    h = h.replace(/`([^`\n]+)`/g,
      `<code style="background:var(--surface2);border:1px solid var(--border);border-radius:3px;padding:1px 6px;font-size:.77rem;">$1</code>`
    );

    // 4. Bold / italic
    h = h.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

    // 5. Headers
    h = h.replace(/^# (.+)$/gm,
      `<div style="font-family:'Fraunces',serif;font-size:1.05rem;color:var(--text);margin:14px 0 8px;">$1</div>`);
    h = h.replace(/^## (.+)$/gm,
      `<div style="font-size:.82rem;font-weight:500;border-bottom:1px solid var(--border);padding-bottom:4px;margin:14px 0 8px;">$1</div>`);
    h = h.replace(/^### (.+)$/gm,
      `<div style="font-size:.72rem;color:var(--accent);letter-spacing:.1em;text-transform:uppercase;margin:12px 0 5px;font-weight:500;">$1</div>`);

    // 6. Risk tags
    h = h.replace(/🔴\s*(HIGH|High|high)/g, '<span class="risk-tag high">🔴 HIGH</span>');
    h = h.replace(/🟡\s*(MEDIUM|Medium|medium)/g, '<span class="risk-tag medium">🟡 MEDIUM</span>');
    h = h.replace(/🟢\s*(LOW|Low|low)/g, '<span class="risk-tag low">🟢 LOW</span>');

    // 7. Horizontal rule
    h = h.replace(/^-{3,}$/gm,
      `<hr style="border:none;border-top:1px solid var(--border);margin:12px 0;"/>`);

    // 8. Blockquotes
    h = h.replace(/^&gt; (.+)$/gm,
      `<div style="border-left:3px solid var(--accent);padding:6px 12px;margin:6px 0;color:var(--text-dim);font-style:italic;font-size:.78rem;">$1</div>`);

    // 9. Numbered lists
    h = h.replace(/^(\d+)\.\s+(.+)$/gm,
      `<div style="display:flex;gap:10px;margin:4px 0;align-items:flex-start;"><span style="color:var(--muted);min-width:18px;flex-shrink:0;font-size:.75rem;">$1.</span><span>$2</span></div>`);

    // 10. Unordered lists
    h = h.replace(/^[-*•]\s+(.+)$/gm,
      `<div style="display:flex;gap:10px;margin:3px 0;align-items:flex-start;"><span style="color:var(--accent);flex-shrink:0;">›</span><span>$1</span></div>`);

    // 11. Newlines
    h = h.replace(/\n/g, '<br/>');

    return h;
  }

  return { render };
})();
