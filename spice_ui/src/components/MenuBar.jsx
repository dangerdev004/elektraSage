import { useEffect, useLayoutEffect, useRef, useState } from 'react';

// A list of menu rows, positioned with `position: fixed` so tall menus (the Draw submenus have
// up to 23 rows) never get clipped by a parent and can be pulled back inside the window.
export function MenuList({ items, ctx, close, anchor }) {
  const ref = useRef(null);
  const [open, setOpen] = useState(-1);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    let left = anchor.x;
    let top = anchor.y;
    if (left + r.width > window.innerWidth - 4) {
      left = anchor.altX != null ? anchor.altX - r.width : window.innerWidth - r.width - 4;
    }
    if (top + r.height > window.innerHeight - 4) top = Math.max(4, window.innerHeight - r.height - 4);
    el.style.left = `${Math.max(0, left)}px`;
    el.style.top = `${top}px`;
  });

  return (
    <div
      ref={ref}
      className="menu-list"
      style={{ left: anchor.x, top: anchor.y }}
      onPointerDown={(e) => e.stopPropagation()}
    >
      {items.map((it, i) => (
        it === '---'
          ? <div className="menu-sep" key={`s${i}`} />
          : <Row key={`${it.label}${i}`} it={it} i={i} open={open} setOpen={setOpen} ctx={ctx} close={close} />
      ))}
    </div>
  );
}

function Row({ it, i, open, setOpen, ctx, close }) {
  const ref = useRef(null);
  const disabled = it.disabled || ctx.isDisabled?.(it.cmd);

  if (it.items) {
    const isOpen = open === i;
    const rect = isOpen && ref.current ? ref.current.getBoundingClientRect() : null;
    return (
      <div
        ref={ref}
        className={`menu-row has-sub${isOpen ? ' open' : ''}`}
        onMouseEnter={() => setOpen(i)}
      >
        <span className="chk" />
        <span className="lbl">{it.label}</span>
        <span className="arrow">▸</span>
        {rect && (
          <MenuList
            items={it.items}
            ctx={ctx}
            close={close}
            anchor={{ x: rect.right - 2, y: rect.top - 4, altX: rect.left + 2 }}
          />
        )}
      </div>
    );
  }

  const checked = ctx.isChecked?.(it.cmd);
  return (
    <div
      className={`menu-row${disabled ? ' disabled' : ''}`}
      onMouseEnter={() => setOpen(-1)}
      onClick={() => {
        if (disabled) return;
        ctx.run(it.cmd);
        close();
      }}
    >
      <span className={`chk${checked === undefined ? '' : ' box'}${checked ? ' on' : ''}`}>
        {checked ? '✓' : ''}
      </span>
      <span className="lbl">{it.label}</span>
      {it.shortcut && <span className="sc">{it.shortcut}</span>}
    </div>
  );
}

function TopItem({ menu, isOpen, anyOpen, onToggle, onHover, ctx, close }) {
  const ref = useRef(null);
  const rect = isOpen && ref.current ? ref.current.getBoundingClientRect() : null;
  return (
    <div className="top-item">
      <button
        ref={ref}
        type="button"
        className={isOpen ? 'on' : ''}
        onClick={onToggle}
        onMouseEnter={() => anyOpen && onHover()}
      >
        {menu.label}
      </button>
      {rect && <MenuList items={menu.items} ctx={ctx} close={close} anchor={{ x: rect.left, y: rect.bottom }} />}
    </div>
  );
}

export function MenuBar({ menus, ctx }) {
  const [open, setOpen] = useState(-1);
  const barRef = useRef(null);

  useEffect(() => {
    if (open < 0) return undefined;
    const down = (e) => {
      if (!barRef.current?.contains(e.target)) setOpen(-1);
    };
    const key = (e) => {
      if (e.key === 'Escape') setOpen(-1);
    };
    document.addEventListener('pointerdown', down);
    document.addEventListener('keydown', key);
    return () => {
      document.removeEventListener('pointerdown', down);
      document.removeEventListener('keydown', key);
    };
  }, [open]);

  return (
    <nav className="menubar" ref={barRef}>
      {menus.map((m, i) => (
        <TopItem
          key={m.label}
          menu={m}
          isOpen={open === i}
          anyOpen={open >= 0}
          onToggle={() => setOpen(open === i ? -1 : i)}
          onHover={() => setOpen(i)}
          ctx={ctx}
          close={() => setOpen(-1)}
        />
      ))}
    </nav>
  );
}

// Right-click menu: a backdrop catches the next click, and the list sits at the pointer.
export function ContextMenu({ x, y, items, ctx, close }) {
  useEffect(() => {
    const key = (e) => e.key === 'Escape' && close();
    document.addEventListener('keydown', key);
    return () => document.removeEventListener('keydown', key);
  }, [close]);
  return (
    <div
      className="menu-backdrop"
      onPointerDown={close}
      onContextMenu={(e) => { e.preventDefault(); close(); }}
    >
      <MenuList items={items} ctx={ctx} close={close} anchor={{ x, y }} />
    </div>
  );
}
