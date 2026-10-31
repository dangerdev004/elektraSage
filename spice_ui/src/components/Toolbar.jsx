import { TOOLBAR_ITEMS } from '../data/menus.js';
import { SymbolIcon } from './SymbolIcon.jsx';

export function Toolbar({ mode, run }) {
  return (
    <div className="toolbar" role="toolbar" aria-label="Parts">
      <button
        type="button"
        className={`tb${mode === 'select' ? ' on' : ''}`}
        title="Select / Drag Sel"
        onClick={() => run('mode:select')}
      >
        <span className="tb-glyph">↖</span>
        <span className="tb-label">Select</span>
      </button>
      <span className="tb-sep" />
      {TOOLBAR_ITEMS.map(([id, label]) => (
        <button
          key={id}
          type="button"
          className={`tb${mode === `add:${id}` ? ' on' : ''}`}
          title={`Add ${label}`}
          onClick={() => run(`mode:add:${id}`)}
        >
          <SymbolIcon type={id} />
          <span className="tb-label">{label}</span>
        </button>
      ))}
    </div>
  );
}
