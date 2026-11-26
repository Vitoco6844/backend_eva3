import { useEffect, useRef, useState } from 'react';
import { all } from './api';

export const roles = [['ADMIN', 'Administrador'], ['BODEGUERO', 'Bodeguero']];
export const field = (name, label, type = 'text', extra = {}) => ({name, label, type, ...extra});
export const ref = (name, label, source, type = 'select', extra = {}) => field(name, label, type, {source, ...extra});
export const check = (name, label, initial = false) => field(name, label, 'checkbox', {initial});
export const optional = (name, label, type = 'text') => field(name, label, type, {optional: true});

export function Fields({fields, initial = {}}) {
  const [choices, setChoices] = useState({});
  const [error, setError] = useState('');
  const sources = [...new Set(fields.map(f => f.source).filter(Boolean))].sort((left, right) => left.localeCompare(right)).join(' ');
  useEffect(() => {
    let alive = true;
    if (sources) Promise.all(sources.split(' ').map(async source => [source, await all(source)]))
      .then(result => { if (alive) setChoices(Object.fromEntries(result)); })
      .catch(e => { if (alive) setError(e.message); });
    return () => { alive = false; };
  }, [sources]);
  return <>{error && <p role="alert">{error}</p>}{fields.map(f => {
    const value = initial[f.name] ?? f.initial ?? '';
    const required = !f.optional;
    if (f.source && !choices[f.source]) return <p key={f.name}>{f.label}: cargando opciones…</p>;
    const options = f.options ?? (choices[f.source] ?? []).map(row =>
      [row.id, [row.code, row.name || '#' + row.id].filter(Boolean).join(' · ')]);
    return <label key={f.name}>{f.label}
      {f.type === 'checkbox' ? <input name={f.name} type="checkbox" defaultChecked={Boolean(value)}/> :
        f.type === 'select' || f.type === 'multiple' ?
          <select name={f.name} required={required} multiple={f.type === 'multiple'}
            defaultValue={f.type === 'multiple' ? [] : value}>
            {f.type !== 'multiple' && <option value="">Selecciona</option>}
            {options.map(([id, label]) => <option value={id} key={id}>{label}</option>)}
          </select> :
          f.type === 'textarea' ? <textarea name={f.name} required={required} defaultValue={value}/> :
          <input name={f.name} type={f.type} required={required} defaultValue={value}
            min={f.type === 'number' ? 0 : undefined} step={f.type === 'number' ? (f.step ?? '1') : undefined}
            autoComplete={f.type === 'password' ? (f.autocomplete ?? 'new-password') : undefined}/>}
    </label>;
  })}</>;
}

export function values(fields, form) {
  const data = new FormData(form);
  return Object.fromEntries(fields.map(f => {
    const value = data.get(f.name);
    if (f.type === 'checkbox') return [f.name, data.has(f.name)];
    if (f.type === 'multiple') return [f.name, data.getAll(f.name).map(Number)];
    if (f.type === 'datetime-local') return [f.name, value ? new Date(value).toISOString() : null];
    if (f.type === 'number' && value === '' && f.optional) return [f.name, null];
    return [f.name, value];
  }));
}

export function Signature({canvas}) {
  const active = useRef(false);
  function draw(event, start) {
    const element = canvas.current;
    const rect = element.getBoundingClientRect();
    const x = (event.clientX - rect.left) * element.width / rect.width;
    const y = (event.clientY - rect.top) * element.height / rect.height;
    const ctx = element.getContext('2d');
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    if (start) {
      element.setPointerCapture(event.pointerId);
      active.current = true;
      ctx.beginPath();
      ctx.moveTo(x, y);
    } else if (active.current) {
      ctx.lineTo(x, y);
      ctx.stroke();
    }
  }
  return <fieldset className="signature"><legend>Firma del responsable</legend>
    <canvas aria-label="Recuadro para firmar" width="600" height="180" ref={canvas}
      onPointerDown={e => draw(e, true)} onPointerMove={e => draw(e, false)}
      onPointerUp={() => { active.current = false; }} onPointerCancel={() => { active.current = false; }}/>
    <button type="button" className="button secondary" onClick={() => canvas.current.getContext('2d').clearRect(0, 0, 600, 180)}>Borrar firma</button>
  </fieldset>;
}
